"""Alert deduplication based on fingerprint within a time window."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class DedupConfig:
    window_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class _DedupRecord:
    fingerprint: str
    first_seen: float
    count: int = 1


class AlertDedup:
    """Suppress duplicate alerts with the same fingerprint within a rolling window."""

    def __init__(self, config: DedupConfig) -> None:
        self._config = config
        self._seen: Dict[str, _DedupRecord] = {}

    def _fingerprint(self, payload: WebhookPayload) -> str:
        parts = "|".join([
            payload.job_name or "",
            payload.exit_code or "",
            payload.hostname or "",
        ])
        return hashlib.sha1(parts.encode()).hexdigest()

    def _evict_expired(self, now: float) -> None:
        expired = [
            k for k, v in self._seen.items()
            if now - v.first_seen >= self._config.window_seconds
        ]
        for k in expired:
            del self._seen[k]

    def is_duplicate(self, payload: WebhookPayload) -> bool:
        now = time.monotonic()
        self._evict_expired(now)
        fp = self._fingerprint(payload)
        return fp in self._seen

    def record(self, payload: WebhookPayload) -> None:
        now = time.monotonic()
        fp = self._fingerprint(payload)
        if fp in self._seen:
            self._seen[fp].count += 1
        else:
            self._seen[fp] = _DedupRecord(fingerprint=fp, first_seen=now)

    def size(self) -> int:
        return len(self._seen)


def parse_alert_dedup(config: dict) -> Optional[AlertDedup]:
    """Parse alert_dedup section from config dict. Returns None if absent."""
    section = config.get("alert_dedup")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_dedup must be a dict")
    window = section.get("window_seconds", 300.0)
    return AlertDedup(DedupConfig(window_seconds=float(window)))
