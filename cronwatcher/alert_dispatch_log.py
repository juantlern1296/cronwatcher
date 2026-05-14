"""Alert dispatch log — records every outbound alert attempt with outcome."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DispatchRecord:
    job_name: str
    channel: str
    timestamp: float
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None


@dataclass
class DispatchLog:
    max_entries: int = 500
    _records: List[DispatchRecord] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")

    def record(
        self,
        job_name: str,
        channel: str,
        success: bool,
        status_code: Optional[int] = None,
        error: Optional[str] = None,
        now: Optional[float] = None,
    ) -> None:
        entry = DispatchRecord(
            job_name=job_name,
            channel=channel,
            timestamp=now if now is not None else time.time(),
            success=success,
            status_code=status_code,
            error=error,
        )
        self._records.append(entry)
        if len(self._records) > self.max_entries:
            self._records = self._records[-self.max_entries :]

    def recent(self, limit: int = 50) -> List[DispatchRecord]:
        return list(self._records[-limit:])

    def failures(self) -> List[DispatchRecord]:
        return [r for r in self._records if not r.success]

    def for_job(self, job_name: str) -> List[DispatchRecord]:
        return [r for r in self._records if r.job_name == job_name]

    def clear(self) -> None:
        self._records.clear()

    def __len__(self) -> int:
        return len(self._records)
