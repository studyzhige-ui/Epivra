"""Shared provider capacity; admission remains the Harness's responsibility."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager


class Scheduler:
    def __init__(self, capacity: int = 4):
        if capacity < 1:
            raise ValueError("positive provider capacity required")
        self.capacity = capacity
        self.semaphores = {}
        self.deadlines = {}
        self.active = {}
        self.waiting = {}

    def snapshot(self):
        resources = self.semaphores.keys() | self.deadlines.keys()
        return {
            key: {
                "capacity": self.capacity,
                "active": self.active.get(key, 0),
                "waiting": self.waiting.get(key, 0),
                "not_before": self.deadlines.get(key, 0),
            }
            for key in sorted(resources)
        }

    def defer(self, resource: str, deadline: float):
        self.deadlines[resource] = max(self.deadlines.get(resource, 0), deadline)

    @asynccontextmanager
    async def slot(self, resource: str, check):
        semaphore = self.semaphores.setdefault(
            resource, asyncio.Semaphore(self.capacity)
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
            while self.deadlines.get(resource, 0) > time.time():
                check()
                await asyncio.sleep(min(0.25, self.deadlines[resource] - time.time()))
            check()
        except BaseException:
            if acquired:
                semaphore.release()
            raise
        finally:
            self.waiting[resource] -= 1
        self.active[resource] = self.active.get(resource, 0) + 1
        try:
            yield
        finally:
            self.active[resource] -= 1
            semaphore.release()
