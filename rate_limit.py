"""Small bounded in-memory limiter for failed authentication attempts."""
from __future__ import annotations

from dataclasses import dataclass
import math
import threading
import time
from typing import Callable


@dataclass
class _FailureWindow:
    failures: int
    resets_at: float


class RequestRateLimiter:
    """Allow a bounded number of requests per client in a fixed window."""

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: int,
        max_clients: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1 or window_seconds < 1 or max_clients < 1:
            raise ValueError("rate-limit settings must be positive")
        self._limit = limit
        self._window_seconds = window_seconds
        self._max_clients = max_clients
        self._clock = clock
        self._entries: dict[str, _FailureWindow] = {}
        self._lock = threading.Lock()

    def consume(self, client: str) -> int | None:
        """Record one request, or return retry seconds without recording when full."""
        now = self._clock()
        with self._lock:
            entry = self._entries.get(client)
            if entry is not None and now >= entry.resets_at:
                self._entries.pop(client, None)
                entry = None
            if entry is not None and entry.failures >= self._limit:
                return max(1, math.ceil(entry.resets_at - now))
            if entry is None:
                expired = [key for key, value in self._entries.items() if now >= value.resets_at]
                for key in expired:
                    self._entries.pop(key, None)
                if len(self._entries) >= self._max_clients:
                    oldest = min(self._entries, key=lambda key: self._entries[key].resets_at)
                    self._entries.pop(oldest, None)
                self._entries[client] = _FailureWindow(1, now + self._window_seconds)
            else:
                entry.failures += 1
            return None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class FailureRateLimiter:
    """Block a client after repeated failures within a fixed window.

    Successful authentication clears the client's failures. State is intentionally
    process-local: it contains no credentials, survives concurrent request threads,
    and resets safely when the service restarts.
    """

    def __init__(
        self,
        *,
        limit: int = 10,
        window_seconds: int = 600,
        max_clients: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1 or window_seconds < 1 or max_clients < 1:
            raise ValueError("rate-limit settings must be positive")
        self._limit = limit
        self._window_seconds = window_seconds
        self._max_clients = max_clients
        self._clock = clock
        self._entries: dict[str, _FailureWindow] = {}
        self._lock = threading.Lock()

    def retry_after(self, client: str) -> int | None:
        """Return seconds until retry when blocked, otherwise ``None``."""
        now = self._clock()
        with self._lock:
            entry = self._live_entry(client, now)
            if entry is None or entry.failures < self._limit:
                return None
            return max(1, math.ceil(entry.resets_at - now))

    def record_failure(self, client: str) -> None:
        now = self._clock()
        with self._lock:
            entry = self._live_entry(client, now)
            if entry is None:
                self._make_room(now)
                self._entries[client] = _FailureWindow(
                    failures=1,
                    resets_at=now + self._window_seconds,
                )
            else:
                entry.failures += 1

    def record_success(self, client: str) -> None:
        with self._lock:
            self._entries.pop(client, None)

    def clear(self) -> None:
        """Clear all counters; primarily useful for deterministic test setup."""
        with self._lock:
            self._entries.clear()

    def _live_entry(self, client: str, now: float) -> _FailureWindow | None:
        entry = self._entries.get(client)
        if entry is not None and now >= entry.resets_at:
            self._entries.pop(client, None)
            return None
        return entry

    def _make_room(self, now: float) -> None:
        expired = [key for key, value in self._entries.items() if now >= value.resets_at]
        for key in expired:
            self._entries.pop(key, None)
        if len(self._entries) >= self._max_clients:
            oldest = min(self._entries, key=lambda key: self._entries[key].resets_at)
            self._entries.pop(oldest, None)
