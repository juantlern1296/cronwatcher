"""Aggregates repeated alerts for the same job within a time window before dispatching."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class AggregatorConfig:
    window_seconds: float  # how long to collect before flushing
    min_count: int = 1    # minimum alerts before flushing early


@dataclass
_BucketState:
    payloads: List[WebhookPayload] = field(default_factory=list)
    window_start: float = field(default_factory=time.monotonic)


class AlertAggregator:
    """Collects alerts per job and flushes them as a batch after a window expires."""

    def __init__(
        self,
        config: AggregatorConfig,
        on_flush: Callable[[str, List[WebhookPayload]], None],
    ) -> None:
        if config.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if config.min_count < 1:
            raise ValueError("min_count must be >= 1")
        self._config = config
        self._on_flush = on_flush
        self._buckets: Dict[str, _BucketState] = {}

    def add(self, job_name: str, payload: WebhookPayload) -> None:
        """Add a payload to the aggregation bucket for job_name."""
        if job_name not in self._buckets:
            self._buckets[job_name] = _BucketState()
        bucket = self._buckets[job_name]
        bucket.payloads.append(payload)
        elapsed = time.monotonic() - bucket.window_start
        if elapsed >= self._config.window_seconds or len(bucket.payloads) >= self._config.min_count:
            self._flush(job_name)

    def flush_all(self) -> None:
        """Flush all pending buckets regardless of window state."""
        for job_name in list(self._buckets):
            self._flush(job_name)

    def pending_count(self, job_name: str) -> int:
        """Return number of pending payloads for a job."""
        bucket = self._buckets.get(job_name)
        return len(bucket.payloads) if bucket else 0

    def _flush(self, job_name: str) -> None:
        bucket = self._buckets.pop(job_name, None)
        if bucket and bucket.payloads:
            self._on_flush(job_name, bucket.payloads)


def parse_alert_aggregator(
    config: dict,
    on_flush: Callable[[str, List[WebhookPayload]], None],
) -> Optional[AlertAggregator]:
    """Build an AlertAggregator from config dict, or None if section absent."""
    section = config.get("alert_aggregator")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_aggregator must be a dict")
    window = float(section.get("window_seconds", 30))
    min_count = int(section.get("min_count", 1))
    return AlertAggregator(AggregatorConfig(window_seconds=window, min_count=min_count), on_flush)
