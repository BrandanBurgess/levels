from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic


class LoginRateLimiter:
    def __init__(
        self,
        *,
        limit: int = 5,
        window_seconds: int = 900,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._failures: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _keys(self, ip_address: str, username: str) -> tuple[str, str]:
        return f"ip:{ip_address}", f"username:{username.casefold()}"

    def _prune(self, key: str, now: float) -> None:
        failures = self._failures[key]
        cutoff = now - self.window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        if not failures:
            self._failures.pop(key, None)

    def blocked(self, ip_address: str, username: str) -> bool:
        with self._lock:
            now = self._clock()
            for key in self._keys(ip_address, username):
                self._prune(key, now)
                if len(self._failures.get(key, ())) >= self.limit:
                    return True
            return False

    def record_failure(self, ip_address: str, username: str) -> None:
        with self._lock:
            now = self._clock()
            for key in self._keys(ip_address, username):
                self._prune(key, now)
                self._failures[key].append(now)

    def clear(self, ip_address: str, username: str) -> None:
        with self._lock:
            for key in self._keys(ip_address, username):
                self._failures.pop(key, None)
