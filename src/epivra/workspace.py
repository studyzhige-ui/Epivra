"""Authorized local material discovery and immutable source snapshots."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

from .analysis import filename
from .domain import Artifact, ContextCapacity, NotAllowed, encode
from .materials import MAX_INPUT_BYTES, SUPPORTED_SUFFIXES, parse, parse_isolated
from .storage import Store


class Workspace:
    def __init__(self, store: Store, parse_timeout: float = 60):
        self.store = store
        self.parse_timeout = parse_timeout

    def search_sources(self, study, terms, refs=(), offset=0, limit=8, capacity=16000):
        """Find literal passages across saved originals without a model roundtrip per page.

        Source-sequence/character order is deterministic and append stable. Results
        are excerpts, not summaries, rankings or proofs of source completeness.
        """
        terms = list(dict.fromkeys(t.strip() for t in terms))
        if not 1 <= len(terms) <= 16 or any(not t or len(t) > 200 for t in terms):
            raise ValueError(
                "use 1-16 nonempty literal terms of at most 200 characters"
            )
        if offset < 0 or limit < 1:
            raise ValueError("invalid search page")
        if refs:
            sources = [self.store.get(study, ref) for ref in dict.fromkeys(refs)]
            if any(source.kind != "source" for source in sources):
                raise ValueError("refs must name source snapshots in this study")
            sources = sorted(sources, key=lambda source: source.seq)
        else:
            sources = self.store.iter_artifacts(study, "source")
        pattern = re.compile(
            "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)), re.I
        )
        result = {
            "matches": [],
            "offset": offset,
            "next_offset": None,
            "scope": "specified source snapshots"
            if refs
            else "saved source snapshots in this study",
            "method": "literal, case-insensitive OR; source sequence then position, not semantic ranking",
            "limitation": "Excerpts only. No hit does not establish absence. Read surrounding originals, change terms or investigate further as needed.",
        }
        if len(encode(result)) > capacity:
            raise ContextCapacity("source search metadata exceeds capacity")
        seen = 0
        for source in sources:
            text = source.body["text"]
            stop = 0
            for match in pattern.finditer(text):
                if match.start() < stop:
                    continue  # A returned window already contains this match.
                start, stop = (
                    max(0, match.start() - 350),
                    min(len(text), match.end() + 750),
                )
                if seen < offset:
                    seen += 1
                    continue
                hit = {
                    "ref": source.ref,
                    "kind": "source",
                    "origin": str(source.body.get("origin", ""))[:400],
                    "offset": start,
                    "end": stop,
                    "total": len(text),
                    "match_offset": match.start(),
                    "match_end": match.end(),
                    "text": text[start:stop],
                    "selection": f"{source.ref}:{start}:{stop}",
                    "source_coverage": source.body.get("coverage"),
                }
                # Both full source acquisition status and this selected range matter.
                if len(encode(hit["source_coverage"])) > 400:
                    hit["source_coverage"] = (
                        "see source snapshot for acquisition coverage"
                    )
                next_index = seen + 1
                trial = {
                    **result,
                    "matches": [*result["matches"], hit],
                    "next_offset": next_index,
                }
                if len(result["matches"]) >= limit or len(encode(trial)) > capacity:
                    if not result["matches"]:
                        raise ContextCapacity(
                            "source excerpt cannot fit; increase context capacity"
                        )
                    result["next_offset"] = seen
                    return result
                result["matches"].append(hit)
                seen = next_index
        # All matching windows were visited; null is checked in its actual encoding.
        if len(encode(result)) > capacity:
            last = result["matches"].pop()
            del last
            result["next_offset"] = offset + len(result["matches"])
            if not result["matches"]:
                raise ContextCapacity("source search cursor cannot fit")
        return result

    def _options(self, study):
        control = self.store.control(study)
        return (
            self.store.get(study, control.direction).body["policy"].get("parsing", {})
        )

    def analysis_inputs(self, study, inputs, limit):
        files, total = {}, 0
        for name, ref in inputs.items():
            filename(name)
            if name.casefold() in {n.casefold() for n in files}:
                raise ValueError("duplicate analysis input name")
            source = self.store.get(study, ref)
            if source.kind != "source":
                raise ValueError("analysis input must name a source snapshot")
            raw = self.original(study, ref)
            total += len(raw)
            if total > limit:
                raise ValueError("analysis input size exceeds configured limit")
            files[name] = raw
        names = {name.casefold() for name in files}
        if any(
            "/".join(name.split("/")[:i]) in names
            for name in names
            for i in range(1, len(name.split("/")))
        ):
            raise ValueError("input file and directory names conflict")
        return files

    def stage_analysis(self, job, files):
        folder = self.store.path.parent / "analysis" / job.ref
        if folder.is_symlink():
            raise ValueError("invalid staging directory")
        folder.mkdir(parents=True, exist_ok=True)
        for name, raw in files.items():
            target = folder / "data" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (folder / "analysis.py").write_text(job.body["code"], encoding="utf-8")
        return folder

    def clear_analysis_staging(self, job):
        state = self.store.path.parent.resolve()
        root = (state / "analysis").resolve()
        if root != state / "analysis":
            raise ValueError(
                "analysis staging root must not redirect outside its location"
            )
        folder = root / job.ref
        if folder.exists():
            if folder.is_symlink() or folder.resolve().parent != root:
                raise ValueError("invalid staging directory")
            shutil.rmtree(folder)

    def original(self, study, ref):
        source = self.store.get(study, ref)
        if source.kind != "source":
            raise ValueError("expected source snapshot")
        original = source.body.get("original_ref")
        if original:
            return base64.b64decode(
                self.store.get(study, original).body["data"], validate=True
            )
        return source.body["text"].encode("utf-8")

    def save_analysis(self, study, job, result, limit):
        files, total, names = [], 0, set()
        output = result.get("files", [])
        if len(output) > 100:
            raise ValueError("too many analysis outputs")
        decoded = []
        issues = list(result.get("issues", []))
        for item in output:
            try:
                name = filename(item["name"])
            except ValueError:
                issues.append(
                    "Output name is not portable; file omitted: "
                    + str(item["name"])[:220]
                )
                continue
            if name.casefold() in names:
                raise ValueError("duplicate output name")
            names.add(name.casefold())
            raw = base64.b64decode(item["data"], validate=True)
            total += len(raw)
            if total > limit:
                raise ValueError("analysis output exceeds configured limit")
            decoded.append((name, raw))
        log = result.get("log", "")
        if not isinstance(log, str) or len(log) > 512 * 1024:
            raise ValueError("invalid analysis log")
        parents = (job.ref, *job.body["inputs"].values())
        status = result["status"]

        def parsed(text):
            return {
                "text": text,
                "segments": [
                    {
                        "start": 0,
                        "end": len(text),
                        "locator": {"analysis": job.ref},
                        "status": "computed_not_reviewed",
                    }
                ],
                "parser": "python-analysis-v1",
                "coverage": "computed_not_reviewed",
                "issues": issues,
                "analysis": job.ref,
                "execution_status": status,
            }

        with self.store.transaction():
            for name, raw in decoded:
                text = f"Computed file: {name}; {len(raw)} bytes. Use this source as a run_analysis input to inspect binary or large data."
                if len(raw) < 1024 * 1024:
                    try:
                        text = raw.decode("utf-8")
                    except UnicodeError:
                        pass
                source = self._save_material(study, name, raw, parsed(text), parents)
                files.append({"ref": source.ref, "name": name, "bytes": len(raw)})
            text = f"Analysis purpose: {job.body['purpose']}\nExecution status: {status}\nExit code: {result.get('exit_code')}\n\n{log}"
            log_source = self.store._put(
                study,
                "source",
                {**parsed(text), "origin": "analysis:" + job.ref},
                parents,
            )
            return self.store._put(
                study,
                "analysis_result",
                {
                    "job": job.ref,
                    "status": status,
                    "log": log_source.ref,
                    "files": files,
                },
                (job.ref, log_source.ref, *(f["ref"] for f in files)),
            )

    async def _parse(self, study, name, raw):
        digest = hashlib.sha256(raw).hexdigest()
        for prior in self.store.matching(
            study,
            "source",
            {"sha256": digest, "format": Path(name).suffix.lower()},
            limit=1,
        ):
            if (
                prior.body.get("sha256") == digest
                and prior.body.get("format") == Path(name).suffix.lower()
            ):
                return {
                    key: prior.body[key]
                    for key in ("text", "segments", "coverage", "issues", "parser")
                }
        options = self._options(study)
        if options:
            return await parse_isolated(
                name, raw, options.get("timeout", self.parse_timeout), options
            )
        return await parse_isolated(name, raw, self.parse_timeout)

    @staticmethod
    def web_source_info(source):
        """The same usable source handle for newly acquired and reused text."""
        return {
            "ref": source.ref,
            "url": source.body["origin"],
            "title": source.body.get("title", ""),
            "read": {"ref": source.ref},
            "characters": len(source.body["text"]),
        }

    def web_snapshot(self, study: str, decoded: dict, acquisition: dict) -> dict:
        """Persist extracted text with its successful acquisition, never raw envelopes."""
        work, step = acquisition["work"], acquisition["step"]
        producer = self.store.get(study, work)
        event = self.store.get(study, step)
        operation = self.store.db.execute(
            "SELECT work,status FROM operations WHERE study=? AND id=?",
            (study, acquisition["operation"]),
        ).fetchone()
        if (
            producer.kind != "work"
            or event.kind != "step"
            or work not in event.parents
            or operation is None
            or operation["work"] != work
            or operation["status"] != "succeeded"
        ):
            raise ValueError("web source requires its successful work acquisition")
        sources = []
        with self.store.transaction():
            for item in decoded["sources"]:
                if not isinstance(item["text"], str) or not item["text"].strip():
                    raise ValueError("web source requires readable extracted text")
                source = self.store._put(
                    study,
                    "source",
                    {**item, "acquisition": dict(acquisition)},
                    (work, step),
                )
                sources.append(self.web_source_info(source))
        return {"sources": sources, "failures": decoded["failures"]}

    def _root(self, study: str, root: str) -> Path:
        direction = self.store.get(study, self.store.control(study).direction)
        allowed = direction.body["policy"].get("local_roots", [])
        requested = Path(root).resolve(strict=True)
        if not any(requested == Path(value).resolve(strict=True) for value in allowed):
            raise NotAllowed("directory root is not authorized")
        if not requested.is_dir():
            raise ValueError("authorized root is not a directory")
        return requested

    @staticmethod
    def _inside(root: Path, path: Path) -> Path:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise NotAllowed("resolved source lies outside the authorized root")
        return resolved

    def discover(self, study: str, root: str) -> Artifact:
        directory = self._root(study, root)
        return self.store.put(study, "catalog", self._scan(directory))

    async def discover_async(self, study: str, root: str) -> Artifact:
        directory = self._root(study, root)
        body = await self._io(self._scan, directory)
        return self.store.put(study, "catalog", body)

    @staticmethod
    async def _io(function, *args):
        task = asyncio.create_task(asyncio.to_thread(function, *args))
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
            except Exception:
                break
        if cancelled:
            if not task.cancelled():
                task.exception()
            raise asyncio.CancelledError
        return task.result()

    @classmethod
    def _scan(cls, directory):
        entries: list[dict[str, Any]] = []
        visited: set[Path] = set()

        pending = [directory]
        while pending:
            current = pending.pop()
            try:
                resolved = cls._inside(directory, current)
                if resolved in visited:
                    continue
                visited.add(resolved)
                for path in current.iterdir():
                    if len(entries) + len(visited) + len(pending) >= 100000:
                        raise ValueError(
                            "directory snapshot exceeds capacity; authorize smaller roots"
                        )
                    relative = path.relative_to(directory).as_posix()
                    try:
                        target = cls._inside(directory, path)
                        if target.is_dir():
                            pending.append(path)
                        elif target.is_file():
                            stat = target.stat()
                            entries.append(
                                {
                                    "path": relative,
                                    "bytes": stat.st_size,
                                    "mtime_ns": stat.st_mtime_ns,
                                    "status": "available"
                                    if path.suffix.lower() in SUPPORTED_SUFFIXES
                                    else "unsupported",
                                }
                            )
                    except (OSError, NotAllowed):
                        entries.append({"path": relative, "status": "unavailable"})
            except (OSError, NotAllowed):
                if current == directory:
                    raise
                entries.append(
                    {
                        "path": current.relative_to(directory).as_posix(),
                        "status": "unavailable",
                    }
                )

        return {
            "root": str(directory),
            "entries": sorted(entries, key=lambda x: x["path"]),
        }

    def catalog_page(
        self, study: str, ref: str, offset: int, limit: int
    ) -> dict[str, Any]:
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("invalid catalog page")
        return self.store.catalog_page(study, ref, offset, limit)

    def snapshot(self, study: str, catalog_ref: str, relative: str) -> Artifact:
        try:
            loaded = self._load(study, catalog_ref, relative)
            if isinstance(loaded, Artifact):
                return loaded
            return self._save(
                study,
                relative,
                loaded,
                parse(relative, loaded, self._options(study)),
                (catalog_ref,),
            )
        except OSError as exc:
            # Local material failure is an observation, not a broken database.
            raise ValueError(
                "local source unavailable; refresh or choose another source"
            ) from exc

    def _load(self, study: str, catalog_ref: str, relative: str) -> Artifact | bytes:
        loaded = self._load_target(study, catalog_ref, relative)
        if isinstance(loaded, Artifact):
            return loaded
        return self._read_file(*loaded)

    def _load_target(self, study, catalog_ref, relative):
        catalog = self.store.get(study, catalog_ref)
        if catalog.kind != "catalog":
            raise ValueError("expected catalog")
        entry = next(
            (e for e in catalog.body["entries"] if e["path"] == relative), None
        )
        if not entry or entry["status"] != "available":
            raise ValueError("source was not readable in this catalog")
        root = self._root(study, catalog.body["root"])
        for prior in self.store.matching(study, "source", {"origin": relative}):
            if catalog_ref in prior.parents and prior.body.get("origin") == relative:
                return prior
        target = self._inside(root, root / relative)
        return root, target, relative, entry

    @classmethod
    def _read_file(cls, root, target, relative, entry):
        # The snapshot freezes bytes. Catalog changes require explicit rediscovery,
        # rather than silently substituting a newer file for the selected entry.
        with target.open("rb") as stream:
            import os

            before = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns) != (
                entry["bytes"],
                entry["mtime_ns"],
            ):
                raise ValueError("source changed since discovery; refresh catalog")
            if before.st_size > MAX_INPUT_BYTES:
                raise ValueError("material exceeds input byte limit")
            raw = stream.read(MAX_INPUT_BYTES + 1)
            if len(raw) > MAX_INPUT_BYTES:
                raise ValueError("material exceeds input byte limit")
            after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ino,
        ):
            raise ValueError("source changed while reading")
        # Re-resolve to reject replacement by a link while opening.
        if cls._inside(root, root / relative) != target:
            raise NotAllowed("source target changed while reading")
        final = target.stat()
        if (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError("source was replaced while reading")
        return raw

    async def snapshot_async(
        self, study: str, catalog_ref: str, relative: str
    ) -> Artifact:
        try:
            target = self._load_target(study, catalog_ref, relative)
            loaded = (
                target
                if isinstance(target, Artifact)
                else await self._io(self._read_file, *target)
            )
        except OSError:
            raise ValueError("local source unavailable; refresh catalog") from None
        if isinstance(loaded, Artifact):
            return loaded
        parsed = await self._parse(study, relative, loaded)
        return self._save(study, relative, loaded, parsed, (catalog_ref,))

    def _save(
        self,
        study: str,
        name: str,
        raw: bytes,
        parsed: dict,
        parents: tuple[str, ...] = (),
    ) -> Artifact:
        with self.store.transaction():
            return self._save_material(study, name, raw, parsed, parents)

    def _save_material(self, study, name, raw, parsed, parents):
        digest = hashlib.sha256(raw).hexdigest()
        original = self.store._put(
            study,
            "material_bytes",
            {
                "sha256": digest,
                "encoding": "base64",
                "data": base64.b64encode(raw).decode("ascii"),
            },
            (),
        )
        return self.store._put(
            study,
            "source",
            {
                **parsed,
                "origin": name,
                "format": Path(name).suffix.lower(),
                "sha256": digest,
                "original_ref": original.ref,
            },
            (*parents, original.ref),
        )

    def upload(self, study: str, name: str, raw: bytes) -> Artifact:
        """Host-only import: user-selected bytes, never a model-supplied host path."""
        self.store.control(study)
        name = Path(name).name
        digest = hashlib.sha256(raw).hexdigest()
        for prior in self.store.matching(
            study, "source", {"sha256": digest, "origin": name}, limit=1
        ):
            if prior.body.get("sha256") == digest and prior.body.get("origin") == name:
                return prior
        return self._save(study, name, raw, parse(name, raw, self._options(study)))

    def mcp_snapshot(self, study, server, raw, acquisition):
        import json

        blocks = list(raw.get("contents", raw.get("content", [])))
        structured = raw.get("structuredContent")
        if structured is not None:
            duplicate = False
            for block in blocks:
                try:
                    duplicate |= json.loads(block.get("text", "")) == structured
                except (ValueError, TypeError):
                    pass
            if not duplicate:
                blocks.append(
                    {"type": "text", "text": json.dumps(structured, ensure_ascii=False)}
                )
        sources, links = [], []
        for index, block in enumerate(blocks):
            if block.get("type") == "resource_link":
                links.append(block)
                continue
            content = block.get("resource", block)
            text = content.get("text", "")
            binary = content.get("blob", content.get("data"))
            data = (
                base64.b64decode(binary, validate=True)
                if binary is not None
                else text.encode("utf-8")
            )
            origin = f"mcp://{server}/{acquisition['operation']}/{index}"
            source = self._save(
                study,
                origin,
                data,
                {
                    "text": text,
                    "coverage": "mcp_output_not_reviewed",
                    "issues": []
                    if text
                    else [
                        "Binary MCP content retained; semantic interpretation not performed"
                    ],
                    "mime_type": content.get("mimeType"),
                    "resource_uri": content.get("uri"),
                    "acquisition": acquisition,
                },
            )
            sources.append(
                {"ref": source.ref, "characters": len(text), "preview": text[:1000]}
            )
        return {
            "sources": sources,
            "links": links,
            "structured_available": raw.get("structuredContent") is not None,
        }

    async def upload_async(
        self, study: str, expected: str, name: str, raw: bytes
    ) -> Artifact:
        name = Path(name).name
        digest = hashlib.sha256(raw).hexdigest()
        if self.store.control(study).ref != expected:
            raise ValueError("control changed before upload")
        for prior in self.store.matching(
            study, "source", {"sha256": digest, "origin": name}, limit=1
        ):
            if prior.body.get("sha256") == digest and prior.body.get("origin") == name:
                return prior
        parsed = await self._parse(study, name, raw)
        if self.store.control(study).ref != expected:
            raise ValueError(
                "control changed during upload; retry with current control"
            )
        return self._save(study, name, raw, parsed)
