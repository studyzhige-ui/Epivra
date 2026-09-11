"""One durable transaction boundary for control, artifacts and paid calls."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

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
            if version not in (0, 2001) or (version == 0 and existing):
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
            self.db.execute("PRAGMA user_version=2001")
        except BaseException:
            if hasattr(self, "db"):
                self.db.close()
            self._lock.close()
            raise

    def close(self) -> None:
        self.db.close()
        self._lock.close()

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
            "INSERT OR IGNORE INTO artifacts(ref,study,kind,body,parents) "
            "VALUES(?,?,?,?,?)",
            (ref, study, kind, encode(body), encode(parents)),
        )
        return self.get(study, ref)

    def put(
        self, study: str, kind: str, body: Any, parents: tuple[str, ...] = ()
    ) -> Artifact:
        if kind in {"control", "direction", "publication", "work"}:
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
                    "runtime": "research-mainline-v1",
                    "policy": policy,
                },
            )
            return self._control(study, 0, direction.ref, False, False, False, ())

    def control(self, study: str) -> Control:
        rows = self.list(study, "control")
        if not rows:
            raise ValueError("study not found")
        return self._decode_control(rows[-1])

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
        if self.get(study, direction).body.get("runtime") != "research-mainline-v1":
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
                expected_roles = (
                    {"investigator"}
                    if role == "synthesizer"
                    else {"investigator", "synthesizer"}
                )
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
                if not valid or (role == "writer" and len(valid) != 1):
                    raise NotAllowed(
                        f"{role} requires {'one answer' if role == 'writer' else 'an investigation'} result from current research"
                    )
            if role == "reviewer":
                reports = [
                    self.get(study, ref)
                    for ref in inputs
                    if self.get(study, ref).kind == "report"
                ]
                if len(reports) != 1:
                    raise NotAllowed("review requires one report")
            return self._put(
                study,
                "work",
                {
                    "direction": current.direction,
                    "role": role,
                    "task": task,
                    "inputs": inputs,
                    "owner": owner,
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

    def admit(
        self, study: str, work: str, epoch: int, operation_id: str, request: Any
    ) -> Any | None:
        """None means newly admitted. Existing completed result is replayed."""
        import json

        serialized = encode(request)
        with self.transaction():
            self.require_work(study, work, epoch)
            row = self.db.execute(
                "SELECT * FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
            if row:
                if (row["study"], row["work"], row["request"]) != (
                    study,
                    work,
                    serialized,
                ):
                    raise Conflict("operation identity reused with different request")
                if row["status"] == "unknown":
                    raise UnknownOutcome(operation_id)
                return json.loads(row["result"])
            direction = self.control(study).direction
            self.db.execute(
                "INSERT INTO operations VALUES(?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    study,
                    work,
                    direction,
                    epoch,
                    serialized,
                    "unknown",
                    None,
                ),
            )
            return None

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
                or reviewer.body["direction"] != direction
                or report.ref not in reviewer.body["inputs"]
            ):
                raise Conflict("review must come from a separate bound review work")
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
