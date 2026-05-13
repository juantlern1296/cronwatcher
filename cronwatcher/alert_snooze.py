"""Alert snooze: temporarily silence alerts for a specific job until a given time."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SnoozeEntry:
    job_name: str
    until: float  # epoch seconds
    reason: str = ""

    def is_active(self, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.time()
        return t < self.until


class AlertSnooze:
    """Tracks per-job snooze windows."""

    def __init__(self) -> None:
        self._entries: Dict[str, SnoozeEntry] = {}

    def snooze(self, job_name: str, duration: float, reason: str = "") -> None:
        """Snooze alerts for *job_name* for *duration* seconds."""
        if duration <= 0:
            raise ValueError(f"duration must be positive, got {duration}")
        self._entries[job_name] = SnoozeEntry(
            job_name=job_name,
            until=time.time() + duration,
            reason=reason,
        )

    def lift(self, job_name: str) -> None:
        """Remove snooze for *job_name* if present."""
        self._entries.pop(job_name, None)

    def is_snoozed(self, job_name: str, now: Optional[float] = None) -> bool:
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        if entry.is_active(now):
            return True
        # expired — clean up
        del self._entries[job_name]
        return False

    def active_snoozes(self, now: Optional[float] = None) -> Dict[str, SnoozeEntry]:
        """Return a dict of currently active snooze entries."""
        t = now if now is not None else time.time()
        expired = [k for k, v in self._entries.items() if not v.is_active(t)]
        for k in expired:
            del self._entries[k]
        return dict(self._entries)
