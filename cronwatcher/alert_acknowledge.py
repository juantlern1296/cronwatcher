"""Alert acknowledgement — allows operators to ack a job alert, suppressing
further notifications until the ack expires or is cleared."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AckEntry:
    job_name: str
    acked_by: str
    expires_at: float  # unix timestamp; 0 means never expires
    note: str = ""

    def is_active(self, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.time()
        if self.expires_at == 0:
            return True
        return now < self.expires_at


class AlertAcknowledge:
    """Tracks acknowledgements for cron job alerts."""

    def __init__(self) -> None:
        self._acks: Dict[str, AckEntry] = {}

    def acknowledge(
        self,
        job_name: str,
        acked_by: str,
        duration_seconds: float = 0,
        note: str = "",
        now: Optional[float] = None,
    ) -> AckEntry:
        if not job_name:
            raise ValueError("job_name must not be empty")
        if not acked_by:
            raise ValueError("acked_by must not be empty")
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be >= 0")
        ts = now if now is not None else time.time()
        expires_at = (ts + duration_seconds) if duration_seconds > 0 else 0
        entry = AckEntry(
            job_name=job_name,
            acked_by=acked_by,
            expires_at=expires_at,
            note=note,
        )
        self._acks[job_name] = entry
        return entry

    def clear(self, job_name: str) -> None:
        self._acks.pop(job_name, None)

    def is_acknowledged(self, job_name: str, now: Optional[float] = None) -> bool:
        entry = self._acks.get(job_name)
        if entry is None:
            return False
        if entry.is_active(now):
            return True
        # expired — evict lazily
        del self._acks[job_name]
        return False

    def get(self, job_name: str) -> Optional[AckEntry]:
        return self._acks.get(job_name)

    def all_active(self, now: Optional[float] = None) -> Dict[str, AckEntry]:
        ts = now if now is not None else time.time()
        return {
            k: v for k, v in self._acks.items() if v.is_active(ts)
        }
