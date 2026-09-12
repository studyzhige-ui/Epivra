"""Local Docker execution. No research decisions, provider calls or persistence."""

import asyncio
import json
import os
import re
import subprocess
import time
from pathlib import Path

DEFAULTS = {
    "image": "deep-research-analysis:1",
    "timeout": 120,
    "memory_mb": 1024,
    "cpus": 2,
    "pids": 64,
    "output_mb": 16,
    "input_mb": 256,
}


async def docker(*args, cap=32 * 1024 * 1024, timeout=30):
    allowed = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_CONFIG",
    }
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    try:
        process = await asyncio.create_subprocess_exec(
            "docker",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except OSError:
        raise ValueError(
            "Docker is unavailable; install/start Docker Desktop"
        ) from None

    async def read(stream):
        output = bytearray()
        while chunk := await stream.read(65536):
            output.extend(chunk)
            if len(output) > cap:
                raise ValueError("Docker response exceeds output limit")
        return bytes(output)

    readers = [
        asyncio.create_task(read(process.stdout)),
        asyncio.create_task(read(process.stderr)),
    ]
    try:
        async with asyncio.timeout(timeout):
            out, err = await asyncio.gather(*readers)
            await process.wait()
        if process.returncode:
            raise ValueError(
                "Docker command failed: " + err.decode(errors="replace")[:1200]
            )
        return out
    finally:
        for task in readers:
            if not task.done():
                task.cancel()
        if process.returncode is None:
            process.kill()
        await process.wait()
        await asyncio.gather(*readers, return_exceptions=True)


async def settings(overrides=None):
    overrides = overrides or {}
    if not isinstance(overrides, dict) or set(overrides) - set(DEFAULTS):
        raise ValueError("unknown analysis settings")
    config = {**DEFAULTS, **overrides}
    for key in set(DEFAULTS) - {"image"}:
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError("analysis limits must be positive integers")
    if not isinstance(config["image"], str) or not config["image"].strip():
        raise ValueError("analysis image required")
    inspected = json.loads(await docker("image", "inspect", config["image"]))[0]
    if inspected["Os"] != "linux":
        raise ValueError("analysis requires a Linux image")
    config["image"] = inspected["Id"]
    return config


def filename(value):
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 220
        or any(
            not part
            or re.search(r'[<>:"\\|?*\x00-\x1f]', part)
            or part in {".", ".."}
            or part.endswith((".", " "))
            or part.split(".")[0].upper()
            in {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                *(f"COM{i}" for i in range(1, 10)),
                *(f"LPT{i}" for i in range(1, 10)),
            }
            for part in value.split("/")
        )
    ):
        raise ValueError("use a portable relative file name without traversal")
    return value


class DockerSandbox:
    async def inspect(self, name):
        ids = (
            (await docker("ps", "-aq", "--filter", "name=^/" + name + "$"))
            .decode()
            .strip()
        )
        return json.loads(await docker("inspect", name))[0] if ids else None

    def command(self, name, job, folder, config):
        return [
            "create",
            "--name",
            name,
            "--label",
            "deep-research.job=" + job,
            "--network",
            "none",
            "--read-only",
            "--user",
            "65534:65534",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(config["pids"]),
            "--cpus",
            str(config["cpus"]),
            "--memory",
            str(config["memory_mb"]) + "m",
            "--memory-swap",
            str(config["memory_mb"]) + "m",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=128m,mode=1777",
            "--tmpfs",
            "/outputs:rw,nosuid,nodev,size=" + str(config["output_mb"]) + "m,mode=1777",
            "--mount",
            "type=bind,src=" + str(Path(folder).resolve()) + ",dst=/inputs,readonly",
            "--log-driver",
            "local",
            "--log-opt",
            "max-size=" + str(config["output_mb"] * 3 + 4) + "m",
            "--log-opt",
            "max-file=1",
            "--log-opt",
            "compress=false",
            config["image"],
            str(config["timeout"]),
            str(config["output_mb"] * 1024 * 1024),
        ]

    async def cleanup(self, job):
        name = "dr-analysis-" + job
        found = await self.inspect(name)
        if found:
            if found["Config"]["Labels"].get("deep-research.job") != job:
                raise ValueError("analysis container identity mismatch")
            await docker("rm", "-f", name)

    async def run(self, job, folder, config, fresh, guard):
        name = "dr-analysis-" + job
        info = await self.inspect(name)
        if info is None:
            if not fresh:
                return {
                    "status": "interrupted",
                    "log": "Local container missing; no automatic rerun.",
                    "files": [],
                    "issues": [],
                }
            guard()
            await docker(*self.command(name, job, folder, config))
            info = await self.inspect(name)
        if (
            info["Config"]["Labels"].get("deep-research.job") != job
            or info["Image"] != config["image"]
        ):
            raise ValueError("analysis container identity mismatch")
        if info["State"]["Status"] == "created":
            guard()
            await docker("start", name)
        deadline = time.monotonic() + config["timeout"] + 30
        while True:
            guard()
            info = await self.inspect(name)
            if not info or not info["State"]["Running"]:
                break
            if time.monotonic() > deadline:
                await docker("kill", name)
                return {
                    "status": "timeout",
                    "log": "Sandbox supervisor exceeded deadline",
                    "files": [],
                    "issues": [],
                }
            await asyncio.sleep(0.2)
        if not info:
            return {
                "status": "interrupted",
                "log": "Container disappeared",
                "files": [],
                "issues": [],
            }
        if info["State"].get("OOMKilled"):
            return {
                "status": "resource_limit",
                "log": "Container exceeded memory limit",
                "files": [],
                "issues": [],
            }
        raw = await docker(
            "logs", name, cap=(config["output_mb"] * 2 + 2) * 1024 * 1024
        )
        try:
            result = json.loads(raw)
            if result["status"] not in {
                "succeeded",
                "failed",
                "timeout",
            } or not isinstance(result["files"], list):
                raise ValueError()
            return result
        except (ValueError, KeyError, TypeError):
            return {
                "status": "failed",
                "log": "Sandbox produced no complete result",
                "files": [],
                "issues": [],
            }
