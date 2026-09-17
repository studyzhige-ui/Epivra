"""One durable transaction boundary for control, artifacts and paid calls."""

from __future__ import annotations

import os
import sqlite3
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


class Store:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = self.path.with_suffix(self.path.suffix + ".lock").open("a+b")
        self._lock.seek(0, 2)
        if self._lock.tell() == 0:
            self._lock.write(b"0")
            self._lock.flush()
        self._lock.seek(0)
        try:
            if os.name == "nt":
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
        except BaseException:
            self.db.execute("ROLLBACK")
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
            raise ValueError("artifact not found in this study")
        return self._artifact(row)

    def list(self, study: str, kind: str) -> list[Artifact]:
        return [
            self._artifact(r)
            for r in self.db.execute(
                "SELECT * FROM artifacts WHERE study=? AND kind=? ORDER BY seq",
                (study, kind),
            )
        ]

    def count(self, study: str, kind: str) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM artifacts WHERE study=? AND kind=?", (study, kind)
        ).fetchone()[0]

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
    ) -> list[Artifact]:
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
    ) -> list[Artifact]:
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

    def unsettled(self, study: str) -> list[dict[str, Any]]:
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
                    "runtime": "research-mainline-v2",
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
        if self.get(study, direction).body.get("runtime") != "research-mainline-v2":
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
            if role in {"synthesizer", "writer"}:
                expected_roles = {"investigator", "synthesizer"}
                results = [self.get(study, ref) for ref in inputs]
                valid = set()
                for result in results:
                    if result.kind != "work_result" or not result.body.get("producer"):
                        continue
                    producer = self.get(study, result.body["producer"])
                    if (
                        producer.kind == "work"
                        and producer.ref in result.parents
                        and producer.body["role"] in expected_roles
                        and producer.body["direction"] == current.direction
                    ):
                        valid.add(result.ref)
                if not valid:
                    raise NotAllowed(
                        f"{role} requires research results from current research"
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
    ) -> list[Artifact]:
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
        self, study: str, work: str, epoch: int, text: str, refs: list[str], step: str
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
        refs: list[str],
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
            self._usage_cache = {}
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
            records.append(
                {
                    "operation": row["id"],
                    "work": row["work"],
                    "resource": admission.get("resource", "legacy"),
                    "model": admission.get("model") or row["model"],
                    "tool": row["tool"],
                    "status": row["status"],
                    "http_status": row["http_status"],
                    "admitted_at": admission.get("at"),
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

    def settle(self, operation_id: str, result: Any) -> None:
        """Persist the returned envelope, including explicit provider failures."""
        if result is None:
            raise ValueError("operation result must have an envelope")
        serialized = encode(result)
        with self.transaction():
            row = self.db.execute(
                "SELECT * FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
            if row is None:
                raise ValueError("operation was not admitted")
            if row["status"] == "succeeded" and row["result"] != serialized:
                raise Conflict("cannot replace a settled result")
            self.db.execute(
                "UPDATE operations SET status='succeeded',result=? WHERE id=?",
                (serialized, operation_id),
            )

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
                or author.body["role"] != "writer"
                or author.body["owner"] != work
                or author.ref not in report.parents
            ):
                raise Conflict("report must come from this lead's writer")
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
            validate_citations(report.body, lambda ref: self.get(study, ref))
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
