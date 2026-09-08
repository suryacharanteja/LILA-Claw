"""Deterministic supervision decisions; transport/process adapters call these."""
from collections import deque
from enum import StrEnum


class State(StrEnum):
    STARTING = "STARTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


class Supervisor:
    def __init__(self, persist_stop, fence_worker):
        self.state = State.STARTING
        self.persist_stop = persist_stop
        self.fence_worker = fence_worker
        self.failures = 0
        self.restarts = deque()
        self.blockers = ["STARTING"]
        self.intervention_required = False

    def health(self, healthy, monotonic):
        if self.state in (State.STOPPING, State.STOPPED) or self.intervention_required:
            return None
        if healthy:
            self.failures = 0
            self.state = State.READY
            self.blockers = []
            return None
        self.failures += 1
        if self.failures < 3:
            return None
        self.state = State.DEGRADED
        self.blockers = ["WORKER_UNAVAILABLE"]
        while self.restarts and monotonic-self.restarts[0] >= 300:
            self.restarts.popleft()
        if len(self.restarts) >= 3:
            self.blockers = ["INTERVENTION_REQUIRED"]
            self.intervention_required = True
            return None
        self.fence_worker()
        delay = 2 ** len(self.restarts)
        self.restarts.append(monotonic)
        self.failures = 0
        return delay

    def quit(self):
        # Persistence must succeed before acknowledging intentional shutdown.
        self.persist_stop()
        self.state = State.STOPPING
        self.fence_worker()

    def stopped(self):
        if self.state != State.STOPPING:
            raise RuntimeError("shutdown not requested")
        self.state = State.STOPPED
