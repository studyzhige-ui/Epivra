"""Authorized local material discovery and immutable source snapshots."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from pathlib import Path
from typing import Any

from .domain import Artifact, NotAllowed
from .materials import SUPPORTED_SUFFIXES, parse
from .storage import Store


class Workspace:
    def __init__(self, store: Store):
        self.store = store

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
        entries: list[dict[str, Any]] = []
        visited: set[Path] = set()

        def walk(current: Path) -> None:
            resolved = self._inside(directory, current)
            if resolved in visited:
                return
            visited.add(resolved)
            for path in sorted(current.iterdir(), key=lambda p: p.name):
                relative = path.relative_to(directory).as_posix()
                try:
                    target = self._inside(directory, path)
                    if target.is_dir():
                        walk(path)
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
                except (OSError, ValueError, NotAllowed):
                    entries.append({"path": relative, "status": "unavailable"})

        walk(directory)
        return self.store.put(
            study,
            "catalog",
            {
                "root": str(directory),
                "entries": entries,
            },
        )

    def catalog_page(
        self, study: str, ref: str, offset: int, limit: int
    ) -> dict[str, Any]:
        catalog = self.store.get(study, ref)
        if catalog.kind != "catalog":
            raise ValueError("expected catalog")
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("invalid catalog page")
        entries = catalog.body["entries"]
        end = min(len(entries), offset + limit)
        return {
            "entries": entries[offset:end],
            "total": len(entries),
            "next_offset": end if end < len(entries) else None,
        }

    def snapshot(self, study: str, catalog_ref: str, relative: str) -> Artifact:
        try:
            loaded = self._load(study, catalog_ref, relative)
            if isinstance(loaded, Artifact):
                return loaded
            return self._save(
                study, relative, loaded, parse(relative, loaded), (catalog_ref,)
            )
        except OSError as exc:
            # Local material failure is an observation, not a broken database.
            raise ValueError(
                "local source unavailable; refresh or choose another source"
            ) from exc

    def _load(self, study: str, catalog_ref: str, relative: str) -> Artifact | bytes:
        catalog = self.store.get(study, catalog_ref)
        if catalog.kind != "catalog":
            raise ValueError("expected catalog")
        entry = next(
            (e for e in catalog.body["entries"] if e["path"] == relative), None
        )
        if not entry or entry["status"] != "available":
            raise ValueError("source was not readable in this catalog")
        root = self._root(study, catalog.body["root"])
        for prior in self.store.list(study, "source"):
            if catalog_ref in prior.parents and prior.body.get("origin") == relative:
                return prior
        target = self._inside(root, root / relative)
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
            raw = stream.read()
            after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ino,
        ):
            raise ValueError("source changed while reading")
        # Re-resolve to reject replacement by a link while opening.
        if self._inside(root, root / relative) != target:
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
            loaded = self._load(study, catalog_ref, relative)
        except OSError:
            raise ValueError("local source unavailable; refresh catalog") from None
        if isinstance(loaded, Artifact):
            return loaded
        parsed = await asyncio.to_thread(parse, relative, loaded)
        return self._save(study, relative, loaded, parsed, (catalog_ref,))

    def _save(
        self,
        study: str,
        name: str,
        raw: bytes,
        parsed: dict,
        parents: tuple[str, ...] = (),
    ) -> Artifact:
        digest = hashlib.sha256(raw).hexdigest()
        with self.store.transaction():
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
        for prior in self.store.list(study, "source"):
            if prior.body.get("sha256") == digest and prior.body.get("origin") == name:
                return prior
        return self._save(study, name, raw, parse(name, raw))

    async def upload_async(
        self, study: str, expected: str, name: str, raw: bytes
    ) -> Artifact:
        name = Path(name).name
        digest = hashlib.sha256(raw).hexdigest()
        if self.store.control(study).ref != expected:
            raise ValueError("control changed before upload")
        for prior in self.store.list(study, "source"):
            if prior.body.get("sha256") == digest and prior.body.get("origin") == name:
                return prior
        parsed = await asyncio.to_thread(parse, name, raw)
        if self.store.control(study).ref != expected:
            raise ValueError(
                "control changed during upload; retry with current control"
            )
        return self._save(study, name, raw, parsed)
