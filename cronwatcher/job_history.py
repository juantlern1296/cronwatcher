"""Tracks recent failure history per cron job for diagnostics and reporting."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Dict, List, Optional

from cronwatcher.log_parser import CronLogEntry

DEFAULT_MAX_HISTORY = 20


@dataclass
class FailureRecord:
    job_name: str
    timestamp: datetime
    exit_code: Optional[int]
    raw_line: str


class JobHistory:
    """Stores a bounded history of failures for a single job."""

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self._max_entries = max_entries
        self._records: Deque[FailureRecord] = deque(maxlen=max_entries)

    def record(self, entry: CronLogEntry) -> None:
        record = FailureRecord(
            job_name=entry.job_name or "",
            timestamp=entry.timestamp,
            exit_code=entry.exit_code,
            raw_line=entry.raw_line,
        )
        self._records.append(record)

    def recent(self, n: int = 5) -> List[FailureRecord]:
        records = list(self._records)
        return records[-n:]

    def total(self) -> int:
        return len(self._records)

    def last(self) -> Optional[FailureRecord]:
        return self._records[-1] if self._records else None


class JobHistoryStore:
    """Registry of per-job failure histories."""

    def __init__(self, max_entries_per_job: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_entries = max_entries_per_job
        self._histories: Dict[str, JobHistory] = {}

    def record(self, entry: CronLogEntry) -> None:
        name = entry.job_name or "unknown"
        if name not in self._histories:
            self._histories[name] = JobHistory(self._max_entries)
        self._histories[name].record(entry)

    def get(self, job_name: str) -> Optional[JobHistory]:
        return self._histories.get(job_name)

    def all_jobs(self) -> List[str]:
        return list(self._histories.keys())

    def summary(self) -> Dict[str, int]:
        return {name: h.total() for name, h in self._histories.items()}
