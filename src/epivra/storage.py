"""One durable transaction boundary for control, artifacts and paid calls."""

from __future__ import annotations

import builtins
import math
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .citations import validate as validate_citations
from .domain import (
    Artifact,
    Conflict,
    Control,
    NotAllowed,
    OwnershipError,
    RuntimeMismatch,
    UnknownOutcome,
    encode,
    identity,
)
from .local_security import protect
from .writing import WritingWorkspace


class Store:
    def __init__(self, path: Path):
        if path.is_symlink():
            raise ValueError("database must not be a symbolic link")
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = self.path.with_suffix(self.path.suffix + ".lock").open("a+b")
        self._lock.seek(0, 2)
        if self._lock.tell() == 0:
            self._lock.write(b"0")
            self._lock.flush()
        self._lock.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._lock.close()
            raise OwnershipError("database already has a live host") from exc
        try:
            self.db = sqlite3.connect(self.path, isolation_level=None)
            protect(self.path)
            self.db.row_factory = sqlite3.Row
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            existing = self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if version not in (0, 2001, 2002, 2003, 2004) or (
                version == 0 and existing
            ):
                raise ValueError("incompatible database; use a new redesign workspace")
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    ref TEXT NOT NULL UNIQUE,
                    study TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    body TEXT NOT NULL,
                    parents TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS artifact_lookup
                    ON artifacts(study, kind, seq);
                CREATE INDEX IF NOT EXISTS artifact_work
                    ON artifacts(study, kind, json_extract(parents,'$[0]'), seq);
                CREATE INDEX IF NOT EXISTS artifact_producer
                    ON artifacts(study, kind, json_extract(body,'$.producer'), seq);
                CREATE INDEX IF NOT EXISTS source_origin
                    ON artifacts(study,json_extract(body,'$.origin'),seq)
                    WHERE kind='source';
                CREATE INDEX IF NOT EXISTS source_digest
                    ON artifacts(study,json_extract(body,'$.sha256'),json_extract(body,'$.format'),seq)
                    WHERE kind='source';
                CREATE TABLE IF NOT EXISTS commands (
                    study TEXT NOT NULL,
                    command_id TEXT NOT NULL,
                    request TEXT NOT NULL,
                    receipt TEXT NOT NULL REFERENCES artifacts(ref),
                    PRIMARY KEY(study, command_id)
                );
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    study TEXT NOT NULL,
                    work TEXT NOT NULL REFERENCES artifacts(ref),
                    direction TEXT NOT NULL REFERENCES artifacts(ref),
                    epoch INTEGER NOT NULL,
                    request TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('unknown','succeeded')),
                    result TEXT,
                    CHECK((status='succeeded') = (result IS NOT NULL))
                );
            """)
            # Additive migration preserves every paid request and result verbatim.
            with self.transaction():
                columns = {
                    row[1] for row in self.db.execute("PRAGMA table_info(operations)")
                }
                if "request_step" not in columns:
                    self.db.execute(
                        "ALTER TABLE operations ADD COLUMN request_step TEXT "
                        "REFERENCES artifacts(ref)"
                    )
                if "admission" not in columns:
                    self.db.execute("ALTER TABLE operations ADD COLUMN admission TEXT")
                artifact_columns = {
                    row[1] for row in self.db.execute("PRAGMA table_info(artifacts)")
                }
                if "created_at" not in artifact_columns:
                    self.db.execute("ALTER TABLE artifacts ADD COLUMN created_at REAL")
                self.db.execute(
                    "CREATE INDEX IF NOT EXISTS operation_study_status ON operations(study,status)"
                )
                self.db.execute("PRAGMA user_version=2004")
        except BaseException:
            if hasattr(self, "db"):
                self.db.close()
            self._lock.close()
            raise

    def close(self) -> None:
        self.db.close()
        self._lock.close()

    def import_completed(self, path: Path, study: str) -> dict:
        """Import a complete immutable study, including its paid-call ledger."""
        source = sqlite3.connect(
            path.resolve(strict=True).as_uri() + "?mode=ro", uri=True
        )
        source.row_factory = sqlite3.Row
        try:
            source.execute("BEGIN")
            if source.execute("PRAGMA user_version").fetchone()[0] != 2004:
                raise ValueError("import requires the current database format")
            rows = source.execute(
                "SELECT * FROM artifacts WHERE study=? ORDER BY seq", (study,)
            )
            refs = set()
            direction = None
            publications = []
            for row in rows:
                artifact = self._artifact(row)
                if any(ref not in refs for ref in artifact.parents):
                    raise ValueError(
                        "import has missing or out-of-order research parents"
                    )
                refs.add(artifact.ref)
                if artifact.kind == "control":
                    direction = artifact.body["direction"]
                if artifact.kind == "publication":
                    publications.append(artifact)
                if artifact.kind == "delete_request":
                    raise ValueError("cannot import a study pending deletion")
            if direction is None or not any(
                direction in publication.parents for publication in publications
            ):
                raise ValueError("only completed studies can be imported")
            with self.transaction():
                existing = {
                    r[0]
                    for r in self.db.execute(
                        "SELECT ref FROM artifacts WHERE study=?", (study,)
                    )
                }
                if existing:
                    if existing != refs:
                        raise Conflict("study ID already contains different research")
                for table in ("artifacts", "operations", "commands"):
                    columns = [
                        r[1]
                        for r in self.db.execute(f"PRAGMA table_info({table})")
                        if r[1] != "seq"
                    ]
                    names = ",".join(columns)
                    placeholders = ",".join("?" for _ in columns)
                    order = " ORDER BY seq" if table == "artifacts" else ""
                    source_rows = [
                        tuple(row)
                        for row in source.execute(
                            f"SELECT {names} FROM {table} WHERE study=?{order}",
                            (study,),
                        )
                    ]
                    if table in ("operations", "commands"):
                        ref_columns = (
                            ("work", "direction", "request_step")
                            if table == "operations"
                            else ("receipt",)
                        )
                        for row in source_rows:
                            data = dict(zip(columns, row))
                            if any(
                                data[key] is not None and data[key] not in refs
                                for key in ref_columns
                            ):
                                raise ValueError(
                                    "import ledger references another or missing study"
                                )
                    if existing:
                        target_rows = [
                            tuple(row)
                            for row in self.db.execute(
                                f"SELECT {names} FROM {table} WHERE study=?{order}",
                                (study,),
                            )
                        ]
                        if set(source_rows) != set(target_rows):
                            raise Conflict(
                                "existing study artifacts or call ledger differ; import refused"
                            )
                        continue
                    for row in source_rows:
                        self.db.execute(
                            f"INSERT INTO {table} ({names}) VALUES ({placeholders})",
                            tuple(row),
                        )
            return {
                "study": study,
                "imported": not bool(existing),
                "already_imported": bool(existing),
                "artifacts": len(refs),
            }
        finally:
            source.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException as exc:
            if self.db.in_transaction:
                try:
                    self.db.execute("ROLLBACK")
                except sqlite3.Error as rollback_error:
                    exc.add_note(
                        "rollback also failed: " + type(rollback_error).__name__
                    )
            raise

    @staticmethod
    def _artifact(row: sqlite3.Row) -> Artifact:
        import json

        body, parents = json.loads(row["body"]), tuple(json.loads(row["parents"]))
        if identity(row["study"], row["kind"], body, parents) != row["ref"]:
            raise ValueError("artifact content integrity failure")
        return Artifact(
            row["ref"], row["study"], row["kind"], body, parents, row["seq"]
        )

    def latest_sequence(self, study: str, kinds: tuple[str, ...]) -> int:
        """Read a progress watermark without loading original document bodies."""
        if not kinds:
            return 0
        placeholders = ",".join("?" for _ in kinds)
        return self.db.execute(
            f"SELECT COALESCE(MAX(seq), 0) FROM artifacts WHERE study=? AND kind IN ({placeholders})",
            (study, *kinds),
        ).fetchone()[0]

    def get(self, study: str, ref: str) -> Artifact:
        row = self.db.execute(
            "SELECT * FROM artifacts WHERE study=? AND ref=?", (study, ref)
        ).fetchone()
        if row is None:
            raise ValueError(
                f"artifact not found in this study: {str(ref)[:80]}; use an exact ref from read_context or find_artifacts"
            )
        return self._artifact(row)

    def list(self, study: str, kind: str) -> builtins.list[Artifact]:
        return list(self.iter_artifacts(study, kind))

    def iter_artifacts(self, study: str, kind: str) -> Iterator[Artifact]:
        for row in self.db.execute(
            "SELECT * FROM artifacts WHERE study=? AND kind=? ORDER BY seq",
            (study, kind),
        ):
            yield self._artifact(row)

    def count(self, study: str, kind: str) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM artifacts WHERE study=? AND kind=?", (study, kind)
        ).fetchone()[0]

    def matching(self, study, kind, fields, *, limit=None):
        """Filter immutable bodies in SQLite before loading/decoding originals."""
        sql = "SELECT * FROM artifacts WHERE study=? AND kind=?"
        args = [study, kind]
        for key, value in fields.items():
            if not key.isidentifier():
                raise ValueError("invalid artifact field")
            # Identifiers are checked above; literal paths let SQLite use the
            # expression indexes. Values remain bound parameters.
            sql += f" AND json_extract(body,'$.{key}')=?"
            args.append(value)
        sql += " ORDER BY seq"
        if limit is not None:
            sql += " DESC LIMIT ?"
            args.append(limit)
        return [self._artifact(row) for row in self.db.execute(sql, args)]

    def catalog_index(self, study):
        rows = self.db.execute(
            "SELECT ref,json_extract(body,'$.root') AS root,"
            "json_array_length(body,'$.entries') AS entries FROM artifacts "
            "WHERE study=? AND kind='catalog' ORDER BY seq",
            (study,),
        )
        latest = {}
        for row in rows:
            latest[row["root"]] = {
                "ref": row["ref"],
                "kind": "catalog",
                "root": row["root"],
                "entries": row["entries"],
            }
        return list(latest.values())

    def catalog_page(self, study, ref, offset, limit):
        import json

        row = self.db.execute(
            "SELECT json_array_length(body,'$.entries') AS total FROM artifacts "
            "WHERE study=? AND ref=? AND kind='catalog'",
            (study, ref),
        ).fetchone()
        if row is None:
            raise ValueError("expected catalog")
        entries = []
        for item in self.db.execute(
            "SELECT j.value FROM artifacts a,json_each(a.body,'$.entries') j "
            "WHERE a.study=? AND a.ref=? ORDER BY j.key LIMIT ? OFFSET ?",
            (study, ref, limit, offset),
        ):
            entry = json.loads(item[0])
            source = self.db.execute(
                "SELECT ref FROM artifacts WHERE study=? AND kind='source' "
                "AND json_extract(body,'$.origin')=? "
                "AND EXISTS(SELECT 1 FROM json_each(parents) WHERE value=?) ORDER BY seq DESC LIMIT 1",
                (study, entry["path"], ref),
            ).fetchone()
            entries.append({**entry, "source_ref": source[0] if source else None})
        end = offset + len(entries)
        return {
            "ref": ref,
            "kind": "catalog",
            "entries": entries,
            "total": row["total"],
            "next_offset": end if end < row["total"] else None,
        }

    def revisions(self, study, refs, direction):
        replacements, pending, seen = {}, list(refs), set()
        while pending:
            ref = pending.pop()
            if ref in seen:
                continue
            seen.add(ref)
            dependency = self.db.execute(
                "SELECT kind,parents FROM artifacts WHERE study=? AND ref=?",
                (study, ref),
            ).fetchone()
            if dependency is not None and dependency["kind"] in {
                "work_result",
                "note",
                "report",
                "memory",
                "evidence_anchor",
                "clarification_answer",
            }:
                import json

                pending.extend(json.loads(dependency["parents"]))
            row = self.db.execute(
                "SELECT * FROM artifacts WHERE study=? AND kind='work_result' "
                "AND EXISTS(SELECT 1 FROM json_each(body,'$.supersedes') WHERE value=?) "
                "AND EXISTS(SELECT 1 FROM json_each(parents) WHERE value=?) ORDER BY seq DESC LIMIT 1",
                (study, ref, direction),
            ).fetchone()
            if row is not None:
                item = self._artifact(row)
                replacements[ref] = item.ref
                pending.append(item.ref)
        return replacements

    def step_sequence(self, study: str, work: str) -> int:
        """Scheduling needs sequence metadata, never a full frozen model request."""
        return self.db.execute(
            "SELECT COALESCE(MAX(seq),-1) FROM artifacts "
            "WHERE study=? AND kind='step' AND json_extract(parents,'$[0]')=?",
            (study, work),
        ).fetchone()[0]

    def related(
        self,
        study: str,
        kind: str,
        ref: str,
        *,
        producer=False,
        first_parent=False,
        limit=None,
    ) -> builtins.list[Artifact]:
        """Filter before decoding immutable bodies, especially frozen model requests."""
        predicate = (
            "json_extract(body,'$.producer')=?"
            if producer
            else "json_extract(parents,'$[0]')=?"
            if first_parent
            else "EXISTS (SELECT 1 FROM json_each(artifacts.parents) WHERE value=?)"
        )
        sql = f"SELECT * FROM artifacts WHERE study=? AND kind=? AND {predicate} ORDER BY seq"
        args = [study, kind, ref]
        if limit is not None:
            sql += " DESC LIMIT ?"
            args.append(limit)
        rows = self.db.execute(sql, args).fetchall()
        return [
            self._artifact(row)
            for row in (reversed(rows) if limit is not None else rows)
        ]

    def search(
        self, study: str, kind: str, query: str, after: int, limit: int
    ) -> builtins.list[Artifact]:
        if after < 0 or not 1 <= limit <= 100:
            raise ValueError("invalid search cursor or page size")
        return [
            self._artifact(r)
            for r in self.db.execute(
                "SELECT * FROM artifacts WHERE study=? AND kind=? AND seq>? "
                "AND (instr(body,?)>0 OR instr(ref,?)>0 OR instr(parents,?)>0) "
                "ORDER BY seq LIMIT ?",
                (study, kind, after, query, query, query, limit),
            )
        ]

    def unsettled(self, study: str) -> builtins.list[dict[str, Any]]:
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT id,work,epoch FROM operations WHERE study=? AND status='unknown'",
                (study,),
            )
        ]

    def _put(
        self, study: str, kind: str, body: Any, parents: tuple[str, ...] = ()
    ) -> Artifact:
        parents = tuple(sorted(set(parents)))
        for ref in parents:
            self.get(study, ref)
        ref = identity(study, kind, body, parents)
        self.db.execute(
            "INSERT OR IGNORE INTO artifacts(ref,study,kind,body,parents,created_at) "
            "VALUES(?,?,?,?,?,?)",
            (ref, study, kind, encode(body), encode(parents), time.time()),
        )
        return self.get(study, ref)

    def put(
        self, study: str, kind: str, body: Any, parents: tuple[str, ...] = ()
    ) -> Artifact:
        if kind in {
            "control",
            "direction",
            "publication",
            "work",
            "clarification",
            "clarification_answer",
        }:
            raise NotAllowed("reserved artifact requires its transaction entry point")
        with self.transaction():
            return self._put(study, kind, body, parents)

    def create(self, study: str, request: str, policy: dict[str, Any]) -> Control:
        if not study.strip() or not request.strip():
            raise ValueError("study and request are required")
        with self.transaction():
            if self.list(study, "control"):
                raise Conflict("study already exists")
            direction = self._put(
                study,
                "direction",
                {
                    "request": request,
                    "runtime": "continuous-research-v2",
                    "policy": policy,
                },
            )
            return self._control(study, 0, direction.ref, False, False, False, ())

    def control(self, study: str) -> Control:
        row = self.db.execute(
            "SELECT * FROM artifacts WHERE study=? AND kind='control' ORDER BY seq DESC LIMIT 1",
            (study,),
        ).fetchone()
        if row is None:
            raise ValueError("study not found")
        return self._decode_control(self._artifact(row))

    def request_deletion(self, study: str, expected: str) -> None:
        with self.transaction():
            current = self.control(study)
            intents = self.list(study, "delete_request")
            if intents:
                if expected not in {current.ref, intents[0].body["expected"]}:
                    raise Conflict("control version changed")
                return
            if current.ref != expected:
                raise Conflict("control version changed")
            stopped = self._control(
                study,
                current.epoch + 1,
                current.direction,
                current.approved,
                True,
                True,
                (current.ref,),
                current.plan,
            )
            self._put(study, "delete_request", {"expected": expected}, (stopped.ref,))

    def delete_study(self, study: str) -> None:
        """Host must finish owned-resource cleanup before erasing its manifest."""
        with self.transaction():
            if not self.control(study).cancelled or not self.count(
                study, "delete_request"
            ):
                raise NotAllowed(
                    "deletion requires explicit intent and stopped execution"
                )
            self.db.execute("DELETE FROM commands WHERE study=?", (study,))
            self.db.execute("DELETE FROM operations WHERE study=?", (study,))
            self.db.execute("DELETE FROM artifacts WHERE study=?", (study,))
        getattr(self, "_usage_cache", {}).pop(study, None)

    def timing(self, study: str, now: float | None = None) -> dict[str, Any]:
        """Elapsed wall time, not summed parallel work or estimated compute time."""
        control = self.control(study)
        start = self.db.execute(
            "SELECT created_at FROM artifacts WHERE study=? AND kind='control' "
            "AND json_extract(body,'$.approved')=1 ORDER BY seq LIMIT 1",
            (study,),
        ).fetchone()
        end = self.db.execute(
            "SELECT created_at FROM artifacts WHERE study=? AND kind='publication' "
            "AND EXISTS (SELECT 1 FROM json_each(artifacts.parents) WHERE value=?) "
            "ORDER BY seq DESC LIMIT 1",
            (study, control.direction),
        ).fetchone()
        if end is None and control.cancelled:
            end = self.db.execute(
                "SELECT created_at FROM artifacts WHERE ref=?", (control.ref,)
            ).fetchone()
        started_at = start[0] if start else None
        ended_at = end[0] if end else None
        until = ended_at if end else (time.time() if now is None else now)
        elapsed = (
            until - started_at
            if started_at is not None and until is not None and until >= started_at
            else None
        )
        return {
            "basis": "approval_to_publication_wall_time",
            "includes_waiting": True,
            "started_at": started_at,
            "ended_at": ended_at,
            "elapsed_seconds": elapsed,
        }

    @staticmethod
    def _decode_control(artifact: Artifact) -> Control:
        return Control(artifact.ref, **artifact.body)

    def _control(
        self,
        study: str,
        epoch: int,
        direction: str,
        approved: bool,
        paused: bool,
        cancelled: bool,
        parents: tuple[str, ...],
        plan: str | None = None,
    ) -> Control:
        artifact = self._put(
            study,
            "control",
            {
                "epoch": epoch,
                "direction": direction,
                "approved": approved,
                "paused": paused,
                "cancelled": cancelled,
                "plan": plan,
            },
            (*parents, direction, *((plan,) if plan else ())),
        )
        return self._decode_control(artifact)

    def command(
        self,
        study: str,
        command_id: str,
        expected: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> Control:
        if not command_id.strip():
            raise ValueError("command ID required")
        payload = payload or {}
        request = encode([expected, action, payload])
        with self.transaction():
            old = self.db.execute(
                "SELECT request,receipt FROM commands WHERE study=? AND command_id=?",
                (study, command_id),
            ).fetchone()
            if old:
                if old["request"] != request:
                    raise Conflict("command ID reused with different content")
                return self._decode_control(self.get(study, old["receipt"]))
            current = self.control(study)
            if current.ref != expected:
                raise Conflict("control version changed")
            if current.cancelled:
                raise NotAllowed("cancelled study cannot restart")
            approved, paused = current.approved, current.paused
            direction, cancelled = current.direction, False
            approved_plan = current.plan
            if action == "approve":
                if current.approved:
                    raise NotAllowed(
                        "research route is already approved; no second approval"
                    )
                plan = self.get(study, payload["plan"])
                if plan.kind != "plan" or direction not in plan.parents:
                    raise Conflict(
                        "approval must name a plan for the current direction"
                    )
                approved = True
                approved_plan = plan.ref
            elif action == "pause":
                paused = True
            elif action == "resume":
                paused = False
            elif action == "cancel":
                cancelled = True
            elif action == "steer":
                text = payload.get("request", "")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("new direction is required")
                previous = self.get(study, direction)
                direction = self._put(
                    study,
                    "direction",
                    {
                        "request": text,
                        "runtime": previous.body.get("runtime"),
                        "policy": previous.body["policy"],
                    },
                    (direction,),
                ).ref
                # An accepted user revision keeps existing authority, not new grants.
            else:
                raise ValueError("unknown control command")
            result = self._control(
                study,
                current.epoch + 1,
                direction,
                approved,
                paused,
                cancelled,
                (current.ref,),
                approved_plan,
            )
            self.db.execute(
                "INSERT INTO commands VALUES(?,?,?,?)",
                (study, command_id, request, result.ref),
            )
            return result

    def require_runtime(self, study: str, direction: str) -> None:
        if self.get(study, direction).body.get("runtime") != "continuous-research-v2":
            raise RuntimeMismatch(
                "Archived research runtime: read-only audit; start a new study"
            )

    def work(
        self,
        study: str,
        expected: str,
        role: str,
        task: str,
        inputs: tuple[str, ...] = (),
        owner: str | None = None,
        review_mode: str = "final",
        shared_context: str = "",
        deliverable: str = "",
    ) -> Artifact:
        with self.transaction():
            current = self.control(study)
            if current.ref != expected:
                raise Conflict("control version changed")
            if current.paused or current.cancelled:
                raise NotAllowed("study is not accepting work")
            if not current.approved and role != "lead":
                raise NotAllowed("strategy approval required")
            self.require_runtime(study, current.direction)
            if review_mode not in {"final", "check"} or (
                review_mode == "check" and role != "reviewer"
            ):
                raise ValueError("review mode applies only to reviewer work")
            if role not in {
                "lead",
                "reviewer",
                "investigator",
                "synthesizer",
                "writer",
            }:
                raise ValueError("unknown role")
            if owner is not None:
                parent = self.get(study, owner)
                if parent.kind != "work" or parent.body["role"] != "lead":
                    raise NotAllowed("only a lead may delegate")
                if parent.body["direction"] != current.direction:
                    raise Conflict("delegating work belongs to a superseded direction")
            # Specialization is not a prerequisite chain. A helper may start
            # from direct evidence; its authority is inherited from this study.
            if role in {"writer", "synthesizer"}:
                for ref in inputs:
                    result = self.get(study, ref)
                    if result.kind == "work_result" and result.body.get("producer"):
                        producer = self.get(study, result.body["producer"])
                        if (
                            producer.kind == "work"
                            and producer.body["direction"] != current.direction
                        ):
                            raise NotAllowed(
                                "historical findings require reassessment from their sources"
                            )
            if role == "reviewer":
                reports = [
                    self.get(study, ref)
                    for ref in inputs
                    if self.get(study, ref).kind == "report"
                ]
                if len(reports) != 1:
                    raise NotAllowed("review requires one report")
                for ref in inputs:
                    result = self.get(study, ref)
                    if result.kind == "work_result" and result.body.get("report"):
                        if result.body["report"] != reports[0].ref:
                            raise Conflict(
                                "argument check belongs to another report version"
                            )
            return self._put(
                study,
                "work",
                {
                    "direction": current.direction,
                    "role": role,
                    "task": task,
                    "inputs": inputs,
                    "owner": owner,
                    **({"review_mode": "check"} if review_mode == "check" else {}),
                    **({"shared_context": shared_context} if shared_context else {}),
                    **({"deliverable": deliverable} if deliverable else {}),
                },
                (current.direction, *inputs, *((owner,) if owner else ())),
            )

    def require_work(self, study: str, work: str, epoch: int) -> Artifact:
        current = self.control(study)
        self.require_runtime(study, current.direction)
        item = self.get(study, work)
        if item.kind != "work":
            raise ValueError("expected work")
        if current.epoch != epoch or item.body["direction"] != current.direction:
            raise Conflict("work or admission belongs to an older control version")
        if current.paused or current.cancelled:
            raise NotAllowed("study is paused or cancelled")
        if not current.approved and item.body["role"] != "lead":
            raise NotAllowed("strategy approval required")
        return item

    def clarifications(
        self,
        study: str,
        *,
        work: str | None = None,
        owner: str | None = None,
        open_only: bool = False,
    ) -> builtins.list[Artifact]:
        direction = self.control(study).direction
        answered = {
            a.body["question"] for a in self.list(study, "clarification_answer")
        }
        return [
            q
            for q in self.list(study, "clarification")
            if q.body["direction"] == direction
            and (work is None or q.body["work"] == work)
            and (owner is None or q.body["owner"] == owner)
            and (not open_only or q.ref not in answered)
        ]

    def ask(
        self,
        study: str,
        work: str,
        epoch: int,
        text: str,
        refs: builtins.list[str],
        step: str,
    ) -> Artifact:
        with self.transaction():
            item = self.require_work(study, work, epoch)
            if item.body["role"] == "lead" or not item.body["owner"]:
                raise NotAllowed("only delegated research work may ask its owner")
            self._step_request(study, work, step)
            if not text.strip():
                raise ValueError("clarification requires a concrete question")
            body = {
                "text": text,
                "refs": list(dict.fromkeys(refs)),
                "work": work,
                "owner": item.body["owner"],
                "direction": item.body["direction"],
            }
            for old in self.clarifications(study, work=work):
                if step in old.parents and old.body == body:
                    return old
            if self.clarifications(study, work=work, open_only=True):
                raise Conflict("work is already waiting for clarification")
            if any(
                a.body.get("producer") == work for a in self.list(study, "work_result")
            ):
                raise Conflict("completed work cannot ask for clarification")
            return self._put(
                study,
                "clarification",
                body,
                (work, item.body["direction"], step, *refs),
            )

    def answer(
        self,
        study: str,
        work: str,
        epoch: int,
        question: str,
        text: str,
        refs: builtins.list[str],
    ) -> Artifact:
        with self.transaction():
            owner = self.require_work(study, work, epoch)
            q = self.get(study, question)
            if (
                owner.body["role"] != "lead"
                or q.kind != "clarification"
                or q.body["owner"] != work
                or q.body["direction"] != owner.body["direction"]
            ):
                raise NotAllowed("only the current question owner may answer")
            if not text.strip():
                raise ValueError("answer requires a decision or explanation")
            body = {
                "question": question,
                "text": text,
                "refs": list(dict.fromkeys(refs)),
                "producer": work,
            }
            old = [
                a
                for a in self.list(study, "clarification_answer")
                if a.body["question"] == question
            ]
            if old:
                if old[0].body != body:
                    raise Conflict("cannot replace a submitted clarification answer")
                return old[0]
            return self._put(
                study,
                "clarification_answer",
                body,
                (work, owner.body["direction"], question, *refs),
            )

    def _step_request(self, study: str, work: str, ref: str) -> Any:
        step = self.get(study, ref)
        if (
            step.kind != "step"
            or work not in step.parents
            or "request" not in step.body
        ):
            raise Conflict("request step must belong to the operation work")
        return step.body["request"]

    def admit(
        self,
        study: str,
        work: str,
        epoch: int,
        operation_id: str,
        request: Any,
        *,
        request_step: str | None = None,
        admission: dict | None = None,
    ) -> Any | None:
        """None means newly admitted. Existing completed result is replayed."""
        import json

        serialized = encode(request)
        with self.transaction():
            self.require_work(study, work, epoch)
            if (
                request_step is not None
                and encode(self._step_request(study, work, request_step)) != serialized
            ):
                raise Conflict("request differs from its frozen step")
            row = self.db.execute(
                "SELECT * FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
            if row:
                if (row["study"], row["work"]) != (study, work):
                    raise Conflict("operation identity reused with different request")
                stored_request = (
                    encode(self._step_request(study, work, row["request_step"]))
                    if row["request_step"] is not None
                    else row["request"]
                )
                if stored_request != serialized:
                    raise Conflict("operation identity reused with different request")
                if row["status"] == "unknown":
                    raise UnknownOutcome(operation_id)
                return json.loads(row["result"])
            direction = self.control(study).direction
            self.db.execute(
                "INSERT INTO operations"
                "(id,study,work,direction,epoch,request,status,result,request_step,admission) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    study,
                    work,
                    direction,
                    epoch,
                    serialized if request_step is None else "",
                    "unknown",
                    None,
                    request_step,
                    encode(admission) if admission is not None else None,
                ),
            )
            return None

    def mark_invoked(self, operation_id: str, at: float) -> None:
        """Persist the first actual send/execute timestamp for one operation."""
        import json

        if type(at) not in (int, float) or not math.isfinite(at):
            raise ValueError("finite operation timestamp required")
        with self.transaction():
            row = self.db.execute(
                "SELECT study,admission FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
            if row is None:
                raise ValueError("operation was not admitted")
            if row["admission"] is None:
                return
            admission = json.loads(row["admission"])
            admission.setdefault("timing", {}).setdefault("invoked_at", float(at))
            self.db.execute(
                "UPDATE operations SET admission=? WHERE id=?",
                (encode(admission), operation_id),
            )
            if hasattr(self, "_usage_cache"):
                self._usage_cache.pop(row["study"], None)

    def admissions(self):
        import json

        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT admission FROM operations WHERE admission IS NOT NULL"
            )
        ]

    def usage_records(self, study):
        import json

        from .usage import counters

        # Operations only transition unknown -> succeeded. This small watermark
        # invalidates the disposable display cache on admission and settlement.
        watermark = tuple(
            self.db.execute(
                "SELECT COUNT(*), COALESCE(SUM(status='succeeded'), 0) "
                "FROM operations WHERE study=?",
                (study,),
            ).fetchone()
        )
        if not hasattr(self, "_usage_cache"):
            self._usage_cache: dict[str, Any] = {}
        cached = self._usage_cache.get(study)
        if cached and cached[0] == watermark:
            return cached[1]
        records = []
        # UI accounting is a projection, not a replay of paid model contexts.
        for row in self.db.execute(
            """
            WITH calls AS (
                SELECT o.id, o.work, o.status, o.admission,
                    CASE WHEN o.request_step IS NOT NULL
                        THEN json_extract(a.body, '$.request') ELSE o.request END AS req,
                    o.result
                FROM operations o LEFT JOIN artifacts a
                    ON a.ref=o.request_step AND a.study=o.study
                WHERE o.study=?
                ORDER BY o.rowid
            ), projected AS (
                SELECT id, work, status, admission,
                    json_extract(req, '$.tool') AS tool,
                    json_extract(req, '$.wire.payload.model') AS model,
                    CASE WHEN json_type(req, '$.tool') IS NOT NULL
                        THEN CASE WHEN json_type(result, '$.value')='object'
                            THEN json_extract(result, '$.value') END
                        ELSE result END AS raw
                FROM calls
            )
            SELECT id, work, status, admission, tool, model,
                json_extract(raw, '$.http_status') AS http_status,
                CASE WHEN json_type(raw, '$.data.usage')='object'
                    THEN json_extract(raw, '$.data.usage') END AS usage,
                CASE WHEN json_type(raw, '$.data.usageMetadata')='object'
                    THEN json_extract(raw, '$.data.usageMetadata') END AS metadata,
                CASE WHEN json_type(raw, '$.data.data.usage')='object'
                    THEN json_extract(raw, '$.data.data.usage') END AS reader_usage,
                CASE WHEN json_type(raw, '$.data.costDollars')='object'
                    THEN json_extract(raw, '$.data.costDollars') END AS cost_dollars
            FROM projected
            """,
            (study,),
        ):
            admission = json.loads(row["admission"]) if row["admission"] else {}
            raw = {
                "data": {
                    key: json.loads(row[column])
                    for key, column in (
                        ("usage", "usage"),
                        ("usageMetadata", "metadata"),
                    )
                    if row[column] is not None
                }
            }
            if row["reader_usage"] is not None:
                raw["data"]["data"] = {"usage": json.loads(row["reader_usage"])}
            if row["cost_dollars"] is not None:
                raw["data"]["costDollars"] = json.loads(row["cost_dollars"])
            timing = admission.get("timing", {})
            queued_at = admission.get("queued_at")
            admitted_at = admission.get("at")
            invoked_at = timing.get("invoked_at")
            settled_at = timing.get("settled_at")

            def elapsed(start: Any, end: Any) -> float | None:
                if (
                    type(start) not in (int, float)
                    or type(end) not in (int, float)
                    or end < start
                ):
                    return None
                return end - start

            records.append(
                {
                    "operation": row["id"],
                    "work": row["work"],
                    "resource": admission.get("resource", "legacy"),
                    "model": admission.get("model") or row["model"],
                    "tool": row["tool"],
                    "status": row["status"],
                    "http_status": row["http_status"],
                    "queued_at": queued_at,
                    "admitted_at": admitted_at,
                    "invoked_at": invoked_at,
                    "settled_at": settled_at,
                    "queue_seconds": elapsed(queued_at, admitted_at),
                    "admission_to_invoke_seconds": elapsed(admitted_at, invoked_at),
                    "external_seconds": elapsed(invoked_at, settled_at),
                    "usage": counters(raw, admission.get("resource")),
                }
            )
        self._usage_cache[study] = (watermark, records)
        return records

    def reconcile(
        self,
        study: str,
        expected: str,
        operation_id: str,
        receipt_id: str,
        result: Any,
        evidence: str,
    ) -> Artifact:
        """Operator attests an externally verified result, never authorizes resend."""
        if (
            not receipt_id.strip()
            or not evidence.strip()
            or not isinstance(result, dict)
        ):
            raise ValueError(
                "receipt, verification evidence and response object required"
            )
        body = {
            "operation": operation_id,
            "receipt": receipt_id,
            "result_hash": identity(result),
            "evidence": evidence,
            "control": expected,
        }
        with self.transaction():
            existing = [
                a
                for a in self.list(study, "reconciliation")
                if a.body["receipt"] == receipt_id
            ]
            if existing:
                if existing[0].body != body:
                    raise Conflict("reconciliation receipt reused")
                return existing[0]
            control = self.control(study)
            if control.ref != expected or not control.paused:
                raise Conflict("reconciliation requires current paused control")
            row = self.db.execute(
                "SELECT work,status FROM operations WHERE study=? AND id=?",
                (study, operation_id),
            ).fetchone()
            if row is None or row["status"] != "unknown":
                raise Conflict("only an unknown operation can be reconciled")
            self.db.execute(
                "UPDATE operations SET status='succeeded',result=? WHERE id=?",
                (encode(result), operation_id),
            )
            return self._put(study, "reconciliation", body, (row["work"], expected))

    def operation_status(self, study: str, operation_id: str) -> str | None:
        row = self.db.execute(
            "SELECT status FROM operations WHERE study=? AND id=?",
            (study, operation_id),
        ).fetchone()
        return row[0] if row else None

    def admission_epoch(self, study: str, operation_id: str) -> int:
        row = self.db.execute(
            "SELECT epoch FROM operations WHERE study=? AND id=?",
            (study, operation_id),
        ).fetchone()
        if row is None:
            raise ValueError("unknown operation")
        return row[0]

    def result(self, study: str, operation_id: str) -> Any:
        import json

        row = self.db.execute(
            "SELECT result FROM operations WHERE study=? AND id=? AND status='succeeded'",
            (study, operation_id),
        ).fetchone()
        if row is None:
            raise UnknownOutcome(operation_id)
        return json.loads(row[0])

    def settle(
        self, operation_id: str, result: Any, *, settled_at: float | None = None
    ) -> None:
        """Persist the returned envelope and first receipt time atomically."""
        import json

        if result is None:
            raise ValueError("operation result must have an envelope")
        at = time.time() if settled_at is None else settled_at
        if type(at) not in (int, float) or not math.isfinite(at):
            raise ValueError("finite operation timestamp required")
        serialized = encode(result)
        with self.transaction():
            row = self.db.execute(
                "SELECT * FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
            if row is None:
                raise ValueError("operation was not admitted")
            if row["status"] == "succeeded" and row["result"] != serialized:
                raise Conflict("cannot replace a settled result")
            admission = json.loads(row["admission"]) if row["admission"] else None
            if admission is not None:
                admission.setdefault("timing", {}).setdefault("settled_at", float(at))
            self.db.execute(
                "UPDATE operations SET status='succeeded',result=?,admission=? WHERE id=?",
                (
                    serialized,
                    encode(admission) if admission is not None else None,
                    operation_id,
                ),
            )
            if hasattr(self, "_usage_cache"):
                self._usage_cache.pop(row["study"], None)

    def observation(
        self,
        study: str,
        work: str,
        epoch: int,
        body: Any,
        parents: tuple[str, ...] = (),
    ) -> Artifact:
        with self.transaction():
            self.require_work(study, work, epoch)
            return self._put(study, "observation", body, (work, *parents))

    def require_report_delivery(self, study, work, report_ref):
        """Prove input delivery from settled model requests, never model assertions."""
        import json

        from .review import public_inputs, units

        report = self.get(study, report_ref)
        parts = units(report.body["text"])
        received = set()
        rows = self.db.execute(
            "SELECT DISTINCT a.*,o.result AS model_result FROM artifacts a JOIN operations o "
            "ON o.request_step=a.ref AND o.study=a.study "
            "WHERE a.study=? AND o.work=? AND o.status='succeeded' ORDER BY a.seq",
            (study, work),
        )
        for row in rows:
            raw = json.loads(row["model_result"])
            if raw.get("http_status", 200) != 200 or raw.get("malformed_json"):
                continue
            request = self._artifact(row).body["request"]
            entries = []
            for value in public_inputs(request):
                entries.extend(value.get("context", []))
                if "observation_ref" in value and "result" in value:
                    observation = self.get(study, value["observation_ref"])
                    if (
                        observation.kind == "observation"
                        and observation.body.get("result") == value["result"]
                    ):
                        entries.append(
                            {"kind": "observation", "body": observation.body}
                        )
            for entry in entries:
                body = entry.get("body", {})
                if entry.get("ref") == report_ref and body == report.body:
                    return
                if entry.get("kind") != "observation":
                    continue
                result = body.get("result", {})
                if (
                    body.get("tool") != "read_report"
                    or result.get("report") != report_ref
                ):
                    continue
                for unit in result.get("units", []):
                    index = unit.get("unit")
                    if (
                        type(index) is int
                        and 0 <= index < len(parts)
                        and unit == parts[index]
                    ):
                        received.add(index)
        if len(received) != len(parts):
            missing = next(i for i in range(len(parts)) if i not in received)
            raise ValueError(
                f"whole report has not reached reviewer model input; read_report offset={missing} then review in a subsequent turn"
            )

    def publish(
        self, study: str, work: str, epoch: int, report_ref: str, review_ref: str
    ) -> Artifact:
        with self.transaction():
            item = self.require_work(study, work, epoch)
            if item.body["role"] != "lead":
                raise NotAllowed("only lead can publish")
            direction = self.control(study).direction
            report = self.get(study, report_ref)
            review = self.get(study, review_ref)
            if review.kind != "review":
                raise Conflict(
                    "publication requires an accepting final review artifact; a check work_result is not a final review. Delegate reviewer with review_mode='final' for this report"
                )
            if (
                report.kind != "report"
                or direction not in report.parents
                or review.kind != "review"
                or report.ref not in review.parents
                or review.body.get("accepted") is not True
            ):
                raise Conflict("report and accepting review must bind this direction")
            author = self.get(study, report.body.get("producer", report.ref))
            if (
                author.kind != "work"
                or author.body["role"]
                not in {"lead", "investigator", "synthesizer", "writer"}
                or not (author.ref == work or author.body["owner"] == work)
                or author.body["direction"] != direction
                or author.ref not in report.parents
            ):
                raise Conflict(
                    "report must come from this research owner or its authorized helper"
                )
            drafts = self.related(study, "draft_saved", author.ref, producer=True)
            if drafts and drafts[-1].body["ref"] != report.ref:
                raise Conflict("report is not the author's current saved version")
            reviewer = self.get(study, review.body["work"])
            if any(
                other.seq > review.seq and report.ref in other.parents
                for other in self.list(study, "review")
            ):
                raise Conflict("publication requires the latest review of this report")
            if (
                reviewer.kind != "work"
                or reviewer.body["role"] != "reviewer"
                or reviewer.body.get("review_mode", "final") != "final"
                or reviewer.body["direction"] != direction
                or report.ref not in reviewer.body["inputs"]
            ):
                raise Conflict("review must come from a separate bound review work")
            WritingWorkspace(self).require_publishable(study, report)
            validate_citations(report.body, lambda ref: self.get(study, ref))
            revisions = self.revisions(study, [report.ref], direction)
            if any(self.get(study, ref).seq > review.seq for ref in revisions.values()):
                raise Conflict(
                    "report premise changed after review; obtain a new final review"
                )
            self.require_report_delivery(study, reviewer.ref, report.ref)
            for ref in report.body["evidence"]:
                source = self.get(study, ref)
                if source.kind != "source":
                    raise ValueError("report evidence must name source snapshots")
            return self._put(
                study,
                "publication",
                {
                    "report": report_ref,
                    "review": review_ref,
                },
                (direction, report_ref, review_ref),
            )
