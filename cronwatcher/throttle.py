"""Per-job alert throttling: limits how many alerts can fire within a sliding time window."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Deque


@dataclass
class ThrottleConfig:
    max_alerts: int  # max alerts allowed within the window
    window_seconds: float  # size of the sliding window in seconds


@dataclass
class _JobWindow:
    timestamps: Deque[float] = field(default_factory=deque)


class AlertThrottle:
    """Tracks per-job alert timestamps and enforces a sliding-window cap."""

    def __init__(self, config: ThrottleConfig) -> None:
        if config.max_alerts < 1:
            raise ValueError("max_alerts must be >= 1")
        if config.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self._config = config
        self._windows: Dict[str, _JobWindow] = {}

    def _get_window(self, job: str) -> _JobWindow:
        if job not in self._windows:
            self._windows[job] = _JobWindow()
        return self._windows[job]

    def _evict_old(self, window: _JobWindow, now: float) -> None:
        cutoff = now - self._config.window_seconds
        while window.timestamps and window.timestamps[0] <= cutoff:
            window.timestamps.popleft()

    def is_allowed(self, job: str, now: float | None = None) -> bool:
        """Return True if another alert for *job* is permitted right now."""
        if now is None:
            now = time.monotonic()
        window = self._get_window(job)
        self._evict_old(window, now)
        return len(window.timestamps) < self._config.max_alerts

    def record(self, job: str, now: float | None = None) -> None:
        """Record that an alert was sent for *job*."""
        if now is None:
            now = time.monotonic()
        window = self._get_window(job)
        self._evict_old(window, now)
        window.timestamps.append(now)

    def current_count(self, job: str, now: float | None = None) -> int:
        """Return how many alerts have been recorded within the current window."""
        if now is None:
            now = time.monotonic()
        window = self._get_window(job)
        self._evict_old(window, now)
        return len(window.timestamps)
