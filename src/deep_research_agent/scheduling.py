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

    def defer(self, resource: str, deadline: float):
        self.deadlines[resource] = max(self.deadlines.get(resource, 0), deadline)

    @asynccontextmanager
    async def slot(self, resource: str, check):
        semaphore = self.semaphores.setdefault(
            resource, asyncio.Semaphore(self.capacity)
        )
        async with semaphore:
            while self.deadlines.get(resource, 0) > time.time():
                check()
                await asyncio.sleep(min(0.25, self.deadlines[resource] - time.time()))
            check()
            yield
