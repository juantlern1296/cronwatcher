"""Job suppression: temporarily silence alerts for specific jobs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SuppressionEntry:
    job_name: str
    expires_at: float  # unix timestamp
    reason: str = ""

    def is_active(self, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.time()
        return now < self.expires_at


class JobSuppression:
    """Tracks which jobs are currently suppressed from alerting."""

    def __init__(self) -> None:
        self._entries: Dict[str, SuppressionEntry] = {}

    def suppress(self, job_name: str, duration_seconds: float, reason: str = "") -> None:
        """Suppress alerts for *job_name* for *duration_seconds* seconds."""
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        expires_at = time.time() + duration_seconds
        self._entries[job_name] = SuppressionEntry(
            job_name=job_name, expires_at=expires_at, reason=reason
        )

    def lift(self, job_name: str) -> bool:
        """Remove suppression for *job_name*. Returns True if one was active."""
        return self._entries.pop(job_name, None) is not None

    def is_suppressed(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if *job_name* currently has an active suppression."""
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        if entry.is_active(now):
            return True
        # Lazy eviction of expired entries
        del self._entries[job_name]
        return False

    def active_suppressions(self, now: Optional[float] = None) -> list[SuppressionEntry]:
        """Return all currently active suppression entries."""
        if now is None:
            now = time.time()
        active = [e for e in self._entries.values() if e.is_active(now)]
        # Evict expired
        expired = [e.job_name for e in self._entries.values() if not e.is_active(now)]
        for name in expired:
            del self._entries[name]
        return active

    def __len__(self) -> int:
        return len(self._entries)
