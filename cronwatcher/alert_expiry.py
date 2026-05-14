"""Alert expiry: automatically expire alerts that have not recurred within a window."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Callable, Dict, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class ExpiryConfig:
    window_seconds: float  # silence an alert after this many seconds without recurrence
    on_expire: Optional[Callable[[str], None]] = None  # called with job_name when expired

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class _ExpiryRecord:
    last_seen: float
    fired: bool = True


class AlertExpiry:
    """Tracks the last time each job fired and marks alerts as expired."""

    def __init__(self, config: ExpiryConfig) -> None:
        self._config = config
        self._records: Dict[str, _ExpiryRecord] = {}

    def record(self, payload: WebhookPayload, now: Optional[float] = None) -> None:
        """Record that a job alert fired right now."""
        ts = now if now is not None else monotonic()
        job = payload.job_name
        self._records[job] = _ExpiryRecord(last_seen=ts)

    def is_expired(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if the job has not fired within the expiry window."""
        record = self._records.get(job_name)
        if record is None:
            return False  # never seen — not expired, just unknown
        ts = now if now is not None else monotonic()
        return (ts - record.last_seen) > self._config.window_seconds

    def sweep(self, now: Optional[float] = None) -> list[str]:
        """Expire stale records and return names of jobs that were expired."""
        ts = now if now is not None else monotonic()
        expired = [
            job
            for job, rec in self._records.items()
            if (ts - rec.last_seen) > self._config.window_seconds
        ]
        for job in expired:
            del self._records[job]
            if self._config.on_expire:
                self._config.on_expire(job)
        return expired

    def known_jobs(self) -> list[str]:
        return list(self._records.keys())
