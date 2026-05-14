"""Alert pausing — temporarily halt all alerts for a specific job or globally."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class PauseEntry:
    job_name: str
    expires_at: float  # 0 means indefinite

    def is_active(self, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.time()
        if self.expires_at == 0:
            return True
        return now < self.expires_at


class AlertPause:
    """Tracks paused jobs and suppresses alerts while a pause is active."""

    # Sentinel key used for a global (all-jobs) pause.
    _GLOBAL = "*"

    def __init__(self) -> None:
        self._pauses: Dict[str, PauseEntry] = {}

    def pause(self, job_name: str, duration: float = 0) -> None:
        """Pause alerts for *job_name* for *duration* seconds (0 = indefinite)."""
        if duration < 0:
            raise ValueError("duration must be >= 0")
        expires_at = (time.time() + duration) if duration > 0 else 0
        self._pauses[job_name] = PauseEntry(job_name=job_name, expires_at=expires_at)

    def pause_all(self, duration: float = 0) -> None:
        """Pause all alerts globally."""
        self.pause(self._GLOBAL, duration)

    def resume(self, job_name: str) -> None:
        """Lift a pause for *job_name* (no-op if not paused)."""
        self._pauses.pop(job_name, None)

    def resume_all(self) -> None:
        """Lift the global pause."""
        self._pauses.pop(self._GLOBAL, None)

    def is_paused(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if *job_name* or the global key is actively paused."""
        if now is None:
            now = time.time()
        global_entry = self._pauses.get(self._GLOBAL)
        if global_entry and global_entry.is_active(now):
            return True
        entry = self._pauses.get(job_name)
        return bool(entry and entry.is_active(now))

    def wrap(self, handler: Callable[[WebhookPayload], None]) -> Callable[[WebhookPayload], None]:
        """Return a handler that skips delivery when the job is paused."""
        def _inner(payload: WebhookPayload) -> None:
            if self.is_paused(payload.job_name):
                return
            handler(payload)
        return _inner
