"""Alert jitter: adds randomized delay before dispatching alerts to avoid thundering herd."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class JitterConfig:
    min_delay: float  # seconds
    max_delay: float  # seconds
    per_job: dict[str, tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.min_delay < 0:
            raise ValueError("min_delay must be non-negative")
        if self.max_delay < self.min_delay:
            raise ValueError("max_delay must be >= min_delay")
        for job, (lo, hi) in self.per_job.items():
            if lo < 0:
                raise ValueError(f"per_job min_delay for '{job}' must be non-negative")
            if hi < lo:
                raise ValueError(f"per_job max_delay for '{job}' must be >= min_delay")

    def range_for(self, job_name: Optional[str]) -> tuple[float, float]:
        if job_name and job_name in self.per_job:
            return self.per_job[job_name]
        return self.min_delay, self.max_delay


class AlertJitter:
    def __init__(
        self,
        config: JitterConfig,
        handler: Callable[[WebhookPayload], None],
        *,
        _sleep: Callable[[float], None] = time.sleep,
        _random: Callable[[float, float], float] = random.uniform,
    ) -> None:
        self._config = config
        self._handler = handler
        self._sleep = _sleep
        self._random = _random

    def dispatch(self, payload: WebhookPayload) -> None:
        job = payload.extra.get("job_name") if payload.extra else None
        lo, hi = self._config.range_for(job)
        delay = self._random(lo, hi)
        if delay > 0:
            self._sleep(delay)
        self._handler(payload)

    @property
    def dispatch_count(self) -> int:
        return getattr(self, "_count", 0)


def wrap_with_jitter(
    config: JitterConfig,
    handler: Callable[[WebhookPayload], None],
    **kwargs,
) -> AlertJitter:
    return AlertJitter(config, handler, **kwargs)
