from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class CounterConfig:
    window: float  # seconds
    max_count: int  # max alerts to count before resetting label

    def __post_init__(self) -> None:
        if self.window <= 0:
            raise ValueError("window must be positive")
        if self.max_count < 1:
            raise ValueError("max_count must be at least 1")


@dataclass
class _CounterBucket:
    count: int = 0
    window_start: float = field(default_factory=time.monotonic)


class AlertCounter:
    """Counts alerts per job within a rolling window and annotates the payload."""

    def __init__(self, config: CounterConfig) -> None:
        self._config = config
        self._buckets: Dict[str, _CounterBucket] = {}

    def _get_bucket(self, job: str, now: float) -> _CounterBucket:
        bucket = self._buckets.get(job)
        if bucket is None or (now - bucket.window_start) >= self._config.window:
            bucket = _CounterBucket(window_start=now)
            self._buckets[job] = bucket
        return bucket

    def increment(self, payload: WebhookPayload, now: Optional[float] = None) -> WebhookPayload:
        """Increment the counter for the job and annotate the payload with count info."""
        if now is None:
            now = time.monotonic()
        job = payload.job_name or "__unknown__"
        bucket = self._get_bucket(job, now)
        bucket.count += 1
        extra = dict(payload.extra_fields or {})
        extra["alert_count_in_window"] = bucket.count
        extra["alert_count_window_seconds"] = self._config.window
        extra["alert_count_limit"] = self._config.max_count
        extra["alert_count_exceeded"] = bucket.count > self._config.max_count
        return WebhookPayload(
            job_name=payload.job_name,
            exit_code=payload.exit_code,
            timestamp=payload.timestamp,
            hostname=payload.hostname,
            log_line=payload.log_line,
            extra_fields=extra,
        )

    def count_for(self, job: str, now: Optional[float] = None) -> int:
        if now is None:
            now = time.monotonic()
        bucket = self._get_bucket(job, now)
        return bucket.count


def wrap_with_counter(
    config: CounterConfig,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    counter = AlertCounter(config)

    def _handler(payload: WebhookPayload) -> None:
        annotated = counter.increment(payload)
        handler(annotated)

    return _handler
