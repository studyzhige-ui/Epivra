"""Shared provider capacity; admission remains the Harness's responsibility."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager


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
        self.history = {}
        for event in history:
            if event["at"] > self.clock() - 60:
                self.history.setdefault(event["resource"], []).append(
                    (event["at"], event["tokens"])
                )
        self.semaphores = {}
        self.deadlines = {}
        self.active = {}
        self.waiting = {}
        self.spacing = {}

    def constrain(self, resource, interval):
        """Public service spacing, shared by every work using this scheduler."""
        import math
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError("positive finite spacing required")
        self.spacing[resource] = max(self.spacing.get(resource, 0), interval)

    def snapshot(self):
        resources = self.semaphores.keys() | self.deadlines.keys()
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
    async def slot(self, resource: str, check, tokens=0):
        semaphore = self.semaphores.setdefault(
            resource,
            asyncio.Semaphore(
                self.limits.get(resource, {}).get("concurrency", self.capacity)
            ),
        )
        acquired = False
        self.waiting[resource] = self.waiting.get(resource, 0) + 1
        try:
            while not acquired:
                check()
                try:
                    await asyncio.wait_for(semaphore.acquire(), timeout=0.25)
                    acquired = True
                except TimeoutError:
                    pass
            while True:
                check()
                delay = self.rate_delay(resource, tokens)
                if delay <= 0:
                    break
                await asyncio.sleep(min(0.25, delay))
            check()
        except BaseException:
            if acquired:
                semaphore.release()
            raise
        finally:
            self.waiting[resource] -= 1
        self.active[resource] = self.active.get(resource, 0) + 1
        try:
            admitted = self.clock()
            self.history.setdefault(resource, []).append((admitted, tokens))
            yield admitted
        finally:
            self.active[resource] -= 1
            semaphore.release()
