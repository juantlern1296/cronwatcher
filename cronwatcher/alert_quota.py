"""Per-job and global alert quota enforcement with daily/hourly reset windows."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class QuotaConfig:
    max_per_job: int  # max alerts per job per window
    max_global: int   # max alerts across all jobs per window
    window_seconds: float  # reset window in seconds

    def __post_init__(self) -> None:
        if self.max_per_job < 1:
            raise ValueError("max_per_job must be at least 1")
        if self.max_global < 1:
            raise ValueError("max_global must be at least 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class _QuotaBucket:
    count: int = 0
    window_start: float = field(default_factory=time.monotonic)


class AlertQuota:
    def __init__(self, config: QuotaConfig, now: Optional[Callable[[], float]] = None) -> None:
        self._cfg = config
        self._now = now or time.monotonic
        self._per_job: Dict[str, _QuotaBucket] = {}
        self._global = _QuotaBucket(window_start=self._now())

    def _reset_if_expired(self, bucket: _QuotaBucket) -> None:
        if self._now() - bucket.window_start >= self._cfg.window_seconds:
            bucket.count = 0
            bucket.window_start = self._now()

    def _get_job_bucket(self, job: str) -> _QuotaBucket:
        if job not in self._per_job:
            self._per_job[job] = _QuotaBucket(window_start=self._now())
        return self._per_job[job]

    def is_allowed(self, payload: WebhookPayload) -> bool:
        job = payload.job_name or "__unknown__"
        job_bucket = self._get_job_bucket(job)
        self._reset_if_expired(job_bucket)
        self._reset_if_expired(self._global)

        if job_bucket.count >= self._cfg.max_per_job:
            return False
        if self._global.count >= self._cfg.max_global:
            return False
        return True

    def record(self, payload: WebhookPayload) -> None:
        job = payload.job_name or "__unknown__"
        job_bucket = self._get_job_bucket(job)
        job_bucket.count += 1
        self._global.count += 1

    def check_and_record(self, payload: WebhookPayload) -> bool:
        """Return True and record if allowed; False otherwise."""
        if not self.is_allowed(payload):
            return False
        self.record(payload)
        return True
