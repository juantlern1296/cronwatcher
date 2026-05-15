"""Alert retention policy: automatically prune old alert records after a configurable TTL."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List

from cronwatcher.webhook import WebhookPayload


@dataclass
class RetentionConfig:
    max_age_seconds: float
    max_records: int = 1000

    def __post_init__(self) -> None:
        if self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        if self.max_records < 1:
            raise ValueError("max_records must be at least 1")


@dataclass
class _RetentionRecord:
    payload: WebhookPayload
    recorded_at: float


class AlertRetention:
    """Wraps an alert handler and maintains a bounded, time-limited record of dispatched alerts."""

    def __init__(self, config: RetentionConfig, handler: Callable[[WebhookPayload], None]) -> None:
        self._config = config
        self._handler = handler
        self._records: List[_RetentionRecord] = []

    def handle(self, payload: WebhookPayload) -> None:
        self._evict()
        self._records.append(_RetentionRecord(payload=payload, recorded_at=time.monotonic()))
        if len(self._records) > self._config.max_records:
            self._records = self._records[-self._config.max_records :]
        self._handler(payload)

    def _evict(self, now: float | None = None) -> None:
        cutoff = (now if now is not None else time.monotonic()) - self._config.max_age_seconds
        self._records = [r for r in self._records if r.recorded_at >= cutoff]

    def recent(self, n: int = 20) -> List[WebhookPayload]:
        self._evict()
        return [r.payload for r in self._records[-n:]]

    def record_count(self) -> int:
        self._evict()
        return len(self._records)
