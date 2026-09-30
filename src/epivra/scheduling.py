"""Joint, cancellable send capacity; durable admission belongs to the Harness.

Waiting never spends a rate allowance or holds a provider slot. A caller may
also require an execution turn; readiness is rechecked after that queue drains,
and the allowance is committed only when both resources are available.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager, nullcontext


class Scheduler:
    def __init__(self, capacity: int = 4, *, limits=None, history=(), clock=time.time):
        if capacity < 1:
            raise ValueError("positive provider capacity required")
        self.capacity = capacity
        self.clock = clock
        self.limits = limits or {}
        for rule in self.limits.values():
            if not isinstance(rule, dict) or set(rule) - {"concurrency", "rpm", "tpm"}:
                raise ValueError("expected concurrency/rpm/tpm limits")
            if any(type(v) is not int or v < 1 for v in rule.values()):
                raise ValueError("limits must be positive integers")
        self.history: dict[str, list[tuple[float, int]]] = {}
        for event in history:
            # Older versions reserved before waiting for an Agent turn. Restore
            # the actual send time when known, or conservatively the admission.
            at = event.get("timing", {}).get("invoked_at", event["at"])
            if at > self.clock() - 60:
                self.history.setdefault(event["resource"], []).append(
                    (at, event["tokens"])
                )
        self.deadlines: dict[str, float] = {}
        self.active: dict[str, int] = {}
        self.waiting: dict[str, int] = {}
        self.spacing: dict[str, float] = {}

    def constrain(self, resource, interval):
        """Public service spacing, shared by every work using this scheduler."""
        import math
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError("positive finite spacing required")
        self.spacing[resource] = max(self.spacing.get(resource, 0), interval)

    def snapshot(self):
        resources = self.active.keys() | self.waiting.keys() | self.deadlines.keys()
        return {
            key: {
                "capacity": self.limits.get(key, {}).get("concurrency", self.capacity),
                "limits": self.limits.get(key, {}),
                "active": self.active.get(key, 0),
                "waiting": self.waiting.get(key, 0),
                "not_before": self.deadlines.get(key, 0),
            }
            for key in sorted(resources)
        }

    def defer(self, resource: str, deadline: float):
        self.deadlines[resource] = max(self.deadlines.get(resource, 0), deadline)

    def rate_delay(self, resource, tokens):
        rule = self.limits.get(resource, {})
        if rule.get("tpm") is not None and tokens > rule["tpm"]:
            raise ValueError(
                "request token reservation exceeds configured TPM; adjust request or account limit"
            )
        now = self.clock()
        events = sorted(
            (t, n) for t, n in self.history.get(resource, []) if t > now - 60
        )
        self.history[resource] = events
        delay = max(0, self.deadlines.get(resource, 0) - now)
        if events and resource in self.spacing:
            delay = max(delay, events[-1][0] + self.spacing[resource] - now)
        remaining = sum(n for _, n in events)
        for index in range(len(events) + 1):
            if (not rule.get("rpm") or len(events) - index < rule["rpm"]) and (
                not rule.get("tpm") or remaining + tokens <= rule["tpm"]
            ):
                return delay
            timestamp, count = events[index]
            delay = max(delay, timestamp + 60 - now)
            remaining -= count
        return delay

    @asynccontextmanager
    async def slot(self, resource: str, check, tokens=0, *, turn=None):
        """Commit a send allowance immediately before yielding to the caller.

        ``turn`` is a fresh async-context factory, not an already-held lease.
        If provider readiness changes while acquiring it, release it and wait
        again. No scarce resource is held while waiting for another resource.
        Checks fence every waiting phase; cancellation only withdraws unsent
        work. Once yielded, the caller owns settlement of an admitted request.
        """
        capacity = self.limits.get(resource, {}).get("concurrency", self.capacity)
        admitted = False
        self.waiting[resource] = self.waiting.get(resource, 0) + 1
        try:
            while True:
                check()
                delay = self.rate_delay(resource, tokens)
                if delay > 0 or self.active.get(resource, 0) >= capacity:
                    await asyncio.sleep(min(0.25, delay) if delay > 0 else 0.25)
                    continue
                async with turn() if turn else nullcontext():
                    check()
                    if (self.active.get(resource, 0) >= capacity
                            or self.rate_delay(resource, tokens) > 0):
                        continue
                    # This event loop owns the scheduler: no suspension between
                    # the last check and claiming both concurrency and rate.
                    at = self.clock()
                    self.active[resource] = self.active.get(resource, 0) + 1
                    self.history.setdefault(resource, []).append((at, tokens))
                    self.waiting[resource] -= 1
                    admitted = True
                    try:
                        yield at
                    finally:
                        self.active[resource] -= 1
                    return
        finally:
            if not admitted:
                self.waiting[resource] -= 1
