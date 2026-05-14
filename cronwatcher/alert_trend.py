"""Alert trend detection: flags when failure rate is increasing over time."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, Optional
import time

from cronwatcher.webhook import WebhookPayload


@dataclass
class TrendConfig:
    window_size: int  # number of recent samples to consider
    min_samples: int  # minimum samples before trend is evaluated
    spike_ratio: float  # ratio of recent_avg / baseline_avg to trigger alert

    def __post_init__(self) -> None:
        if self.window_size < 2:
            raise ValueError("window_size must be at least 2")
        if self.min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        if self.spike_ratio <= 1.0:
            raise ValueError("spike_ratio must be greater than 1.0")


@dataclass
class _TrendBucket:
    timestamps: Deque[float] = field(default_factory=deque)


class AlertTrend:
    def __init__(self, config: TrendConfig, on_trend: Callable[[WebhookPayload, float], None]) -> None:
        self._cfg = config
        self._on_trend = on_trend
        self._buckets: Dict[str, _TrendBucket] = {}

    def _get_bucket(self, job: str) -> _TrendBucket:
        if job not in self._buckets:
            self._buckets[job] = _TrendBucket()
        return self._buckets[job]

    def record(self, payload: WebhookPayload, now: Optional[float] = None) -> None:
        ts = now if now is not None else time.time()
        job = payload.job_name or "unknown"
        bucket = self._get_bucket(job)
        bucket.timestamps.append(ts)

        all_ts = list(bucket.timestamps)
        if len(all_ts) < self._cfg.min_samples:
            return

        half = max(1, len(all_ts) // 2)
        baseline = all_ts[:half]
        recent = all_ts[half:]

        baseline_span = (baseline[-1] - baseline[0]) or 1.0
        recent_span = (recent[-1] - recent[0]) or 1.0

        baseline_rate = len(baseline) / baseline_span
        recent_rate = len(recent) / recent_span

        if baseline_rate > 0:
            ratio = recent_rate / baseline_rate
            if ratio >= self._cfg.spike_ratio:
                self._on_trend(payload, ratio)

        if len(bucket.timestamps) > self._cfg.window_size:
            bucket.timestamps.popleft()
