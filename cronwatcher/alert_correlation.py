"""Correlate related alert payloads by shared labels or job name patterns."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class CorrelationConfig:
    window_seconds: float  # how long to accumulate correlated events
    group_by: str  # "job" or a label key
    min_count: int = 2  # minimum events before firing correlated alert
    pattern: Optional[str] = None  # optional regex to restrict which jobs correlate

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.min_count < 1:
            raise ValueError("min_count must be at least 1")
        if self.group_by not in ("job",) and not self.group_by.startswith("label:"):
            raise ValueError("group_by must be 'job' or 'label:<key>'")


@dataclass
class _CorrelationBucket:
    key: str
    events: List[WebhookPayload] = field(default_factory=list)
    opened_at: float = field(default_factory=time.monotonic)


class AlertCorrelator:
    def __init__(
        self,
        config: CorrelationConfig,
        on_correlated: Callable[[str, List[WebhookPayload]], None],
    ) -> None:
        self._cfg = config
        self._on_correlated = on_correlated
        self._buckets: Dict[str, _CorrelationBucket] = {}
        self._pattern = re.compile(config.pattern) if config.pattern else None

    def _resolve_key(self, payload: WebhookPayload) -> Optional[str]:
        if self._pattern and not self._pattern.search(payload.job_name or ""):
            return None
        if self._cfg.group_by == "job":
            return payload.job_name or "unknown"
        label_key = self._cfg.group_by.removeprefix("label:")
        labels = payload.extra_fields or {}
        return labels.get(label_key)

    def add(self, payload: WebhookPayload) -> None:
        self._flush_expired()
        key = self._resolve_key(payload)
        if key is None:
            return
        if key not in self._buckets:
            self._buckets[key] = _CorrelationBucket(key=key)
        self._buckets[key].events.append(payload)
        if len(self._buckets[key].events) >= self._cfg.min_count:
            bucket = self._buckets.pop(key)
            self._on_correlated(key, bucket.events)

    def _flush_expired(self) -> None:
        now = time.monotonic()
        expired = [
            k
            for k, b in self._buckets.items()
            if now - b.opened_at >= self._cfg.window_seconds
        ]
        for k in expired:
            del self._buckets[k]

    def flush_all(self) -> None:
        """Fire correlated alerts for any bucket that meets min_count, then clear."""
        for key, bucket in list(self._buckets.items()):
            if len(bucket.events) >= self._cfg.min_count:
                self._on_correlated(key, bucket.events)
        self._buckets.clear()
