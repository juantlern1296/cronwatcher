"""Per-job alert rate limiting using a token bucket approach."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class RateLimitConfig:
    max_alerts: int  # max alerts per window
    window_seconds: float  # rolling window in seconds
    per_job: Dict[str, int] = field(default_factory=dict)  # per-job overrides

    def __post_init__(self) -> None:
        if self.max_alerts < 1:
            raise ValueError("max_alerts must be >= 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        for job, limit in self.per_job.items():
            if limit < 1:
                raise ValueError(f"per-job max_alerts for '{job}' must be >= 1")

    def limit_for(self, job_name: str) -> int:
        return self.per_job.get(job_name, self.max_alerts)


@dataclass
_class _Window:
    timestamps: list = field(default_factory=list)


class AlertRateLimiter:
    """Tracks alert counts per job in a rolling time window."""

    def __init__(self, config: RateLimitConfig, now_fn: Callable[[], float] = time.time) -> None:
        self._cfg = config
        self._now = now_fn
        self._windows: Dict[str, _Window] = {}

    def _get_window(self, job_name: str) -> _Window:
        if job_name not in self._windows:
            self._windows[job_name] = _Window()
        return self._windows[job_name]

    def _evict(self, window: _Window, cutoff: float) -> None:
        window.timestamps = [t for t in window.timestamps if t >= cutoff]

    def is_allowed(self, job_name: str) -> bool:
        now = self._now()
        cutoff = now - self._cfg.window_seconds
        win = self._get_window(job_name)
        self._evict(win, cutoff)
        limit = self._cfg.limit_for(job_name)
        return len(win.timestamps) < limit

    def record(self, job_name: str) -> None:
        now = self._now()
        cutoff = now - self._cfg.window_seconds
        win = self._get_window(job_name)
        self._evict(win, cutoff)
        win.timestamps.append(now)

    def check_and_record(self, job_name: str) -> bool:
        """Returns True and records if allowed; returns False and skips if rate-limited."""
        if self.is_allowed(job_name):
            self.record(job_name)
            return True
        return False
