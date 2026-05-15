"""Alert staggering: spread alert delivery over a time window to avoid thundering herd."""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict

from cronwatcher.webhook import WebhookPayload


@dataclass
class StaggerConfig:
    window: float  # seconds to spread alerts over
    per_job: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.window <= 0:
            raise ValueError("stagger window must be positive")
        for job, w in self.per_job.items():
            if w <= 0:
                raise ValueError(f"stagger window for job '{job}' must be positive")

    def window_for(self, job_name: str) -> float:
        return self.per_job.get(job_name, self.window)


class AlertStagger:
    def __init__(self, config: StaggerConfig, handler: Callable[[WebhookPayload], None]) -> None:
        self._config = config
        self._handler = handler
        self._timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def dispatch(self, payload: WebhookPayload) -> None:
        job = payload.job_name or ""
        delay = random.uniform(0, self._config.window_for(job))
        with self._lock:
            existing = self._timers.get(job)
            if existing is not None:
                existing.cancel()
            t = threading.Timer(delay, self._fire, args=(job, payload))
            self._timers[job] = t
            t.daemon = True
            t.start()

    def _fire(self, job: str, payload: WebhookPayload) -> None:
        with self._lock:
            self._timers.pop(job, None)
        self._handler(payload)

    def cancel_all(self) -> None:
        with self._lock:
            for t in self._timers.values():
                t.cancel()
            self._timers.clear()

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._timers)
