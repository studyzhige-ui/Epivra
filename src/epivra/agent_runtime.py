"""Fair in-process Agent turn admission; durable work lives in Store."""
import asyncio
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager, contextmanager


class AgentRuntime:
    def __init__(self, capacity=4):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("positive Agent capacity required")
        self.capacity = capacity
        self.queues = OrderedDict()
        self.active = {}
        self.pending = {}
        self.executions = {}

    @contextmanager
    def execution(self, study, work):
        key = (study, work)
        if key in self.executions:
            raise RuntimeError("work already has an active execution")
        self.executions[key] = {"state": "active", "started_at": time.time()}
        try:
            yield
        finally:
            self.executions.pop(key, None)

    @contextmanager
    def phase(self, study, work, state, resource=None):
        value = self.executions.get((study, work))
        previous = dict(value) if value is not None else None
        if value is not None:
            value.update(state=state, resource=resource)
        try:
            yield
        finally:
            if value is not None:
                value.clear()
                value.update(previous)

    def _drain(self):
        while self.queues and len(self.active) < self.capacity:
            study, queue = self.queues.popitem(last=False)
            key, future = queue.popleft()
            if queue:
                self.queues[study] = queue
            if future.cancelled():
                self.pending.pop(key, None)
                continue
            queued_at = self.pending.pop(key)
            self.active[key] = {"started_at": time.time(), "queued_at": queued_at}
            future.set_result(None)

    @asynccontextmanager
    async def turn(self, study, work, check):
        key = (study, work)
        if key in self.active or key in self.pending:
            raise RuntimeError("work already owns an Agent turn")
        future = asyncio.get_running_loop().create_future()
        self.pending[key] = time.time()
        self.queues.setdefault(study, deque()).append((key, future))
        self._drain()
        try:
            await future
            check()
            yield
        finally:
            self.active.pop(key, None)
            self.pending.pop(key, None)
            queue = self.queues.get(study)
            if queue is not None:
                kept = deque((k, f) for k, f in queue if k != key)
                if kept:
                    self.queues[study] = kept
                else:
                    del self.queues[study]
            if not future.done():
                future.cancel()
            self._drain()

    def snapshot(self, study):
        return {
            "capacity": self.capacity,
            "active_total": len(self.active),
            "queued_total": len(self.pending),
            "work": {
                **{w: dict(state) for (s, w), state in self.executions.items() if s == study},
                **{w: {"state": "queued", "queued_at": at}
                   for (s, w), at in self.pending.items() if s == study},
                **{w: {"state": "running", **state}
                   for (s, w), state in self.active.items() if s == study},
            },
        }
