"""Deduplication of cron failure alerts based on a rolling time window."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from cronwatcher.log_parser import CronLogEntry


@dataclass
class DedupEntry:
    first_seen: float
    last_seen: float
    count: int = 1


class DedupStore:
    """Tracks recently seen failure fingerprints to suppress duplicate alerts."""

    def __init__(self, window_seconds: float = 300.0) -> None:
        self.window_seconds = window_seconds
        self._store: Dict[str, DedupEntry] = {}

    def _fingerprint(self, entry: CronLogEntry) -> str:
        """Create a stable hash from job name and exit code."""
        raw = f"{entry.job_name}:{entry.exit_code}"
        return hashlib.sha1(raw.encode()).hexdigest()

    def _evict_expired(self, now: float) -> None:
        expired = [
            k for k, v in self._store.items()
            if now - v.last_seen > self.window_seconds
        ]
        for k in expired:
            del self._store[k]

    def is_duplicate(self, entry: CronLogEntry, now: Optional[float] = None) -> bool:
        """Return True if this failure was already seen within the window."""
        now = now if now is not None else time.monotonic()
        self._evict_expired(now)
        fp = self._fingerprint(entry)
        return fp in self._store

    def record(self, entry: CronLogEntry, now: Optional[float] = None) -> DedupEntry:
        """Record a failure fingerprint and return the updated entry."""
        now = now if now is not None else time.monotonic()
        self._evict_expired(now)
        fp = self._fingerprint(entry)
        if fp in self._store:
            self._store[fp].last_seen = now
            self._store[fp].count += 1
        else:
            self._store[fp] = DedupEntry(first_seen=now, last_seen=now)
        return self._store[fp]

    def clear(self) -> None:
        self._store.clear()
