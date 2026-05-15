"""Alert deduplication based on a rolling time window per job."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional
import hashlib
import time

from cronwatcher.webhook import WebhookPayload


@dataclass
class DeduplicateWindowConfig:
    window_seconds: float
    fields: tuple = ("job", "exit_code", "message")

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if not self.fields:
            raise ValueError("fields must not be empty")


@dataclass
class _WindowRecord:
    fingerprint: str
    expires_at: float


class AlertDeduplicateWindow:
    """Suppress duplicate alerts for the same job within a sliding window."""

    def __init__(self, config: DeduplicateWindowConfig) -> None:
        self._config = config
        self._records: Dict[str, _WindowRecord] = {}

    def _fingerprint(self, payload: WebhookPayload) -> str:
        parts = []
        d = payload.to_dict()
        for f in self._config.fields:
            parts.append(str(d.get(f, "")))
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    def is_duplicate(self, payload: WebhookPayload, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.monotonic()
        job = payload.job_name or ""
        rec = self._records.get(job)
        if rec is None:
            return False
        if now >= rec.expires_at:
            del self._records[job]
            return False
        fp = self._fingerprint(payload)
        return rec.fingerprint == fp

    def record(self, payload: WebhookPayload, now: Optional[float] = None) -> None:
        if now is None:
            now = time.monotonic()
        job = payload.job_name or ""
        fp = self._fingerprint(payload)
        self._records[job] = _WindowRecord(
            fingerprint=fp,
            expires_at=now + self._config.window_seconds,
        )

    def handle(self, payload: WebhookPayload, handler: Callable[[WebhookPayload], None]) -> None:
        if not self.is_duplicate(payload):
            self.record(payload)
            handler(payload)


def parse_deduplicate_window_config(raw: dict) -> Optional[DeduplicateWindowConfig]:
    section = raw.get("alert_deduplicate_window")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_deduplicate_window must be a dict")
    if section.get("enabled") is False:
        return None
    window = float(section.get("window_seconds", 60.0))
    fields_raw = section.get("fields", ["job", "exit_code", "message"])
    if not isinstance(fields_raw, list) or not fields_raw:
        raise ValueError("fields must be a non-empty list")
    return DeduplicateWindowConfig(window_seconds=window, fields=tuple(fields_raw))
