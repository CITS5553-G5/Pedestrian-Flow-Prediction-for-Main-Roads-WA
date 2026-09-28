"""Shared pacing and bounded retry for concurrent remote calls."""

from __future__ import annotations

import random
import threading
import time

from pedflow.imagery.contracts import ExtractionError


class RequestGate:
    """Optionally pace starts; always share failure cooldowns across workers."""

    def __init__(self, requests_per_minute, *, clock=time.monotonic, sleep=time.sleep):
        """Use a monotonic clock so wall-clock adjustments cannot change pacing."""
        self._interval = 0.0 if requests_per_minute is None else 60.0 / requests_per_minute
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next = 0.0

    def acquire(self):
        """Reserve a request start under the lock; wait without blocking other workers."""
        while True:
            with self._lock:
                now = self._clock()
                delay = self._next - now
                if delay <= 0:
                    self._next = now + self._interval
                    return
            self._sleep(delay)

    def defer(self, seconds):
        """Extend the shared cooldown when any worker receives a transient failure."""
        with self._lock:
            self._next = max(self._next, self._clock() + seconds)


def request_with_retry(operation, gate: RequestGate, attempts: int):
    """Bound total attempts and apply provider cooldown without nested SDK retries."""
    for attempt in range(attempts):
        gate.acquire()
        try:
            return operation()
        except ExtractionError as exc:
            if not exc.retryable or attempt + 1 == attempts:
                raise
            delay = max(exc.retry_after, min(30, 2**attempt) + random.uniform(0, 0.5))
            gate.defer(delay)
    raise AssertionError("Invalid retry attempt count")
