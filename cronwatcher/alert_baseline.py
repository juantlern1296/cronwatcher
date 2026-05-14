"""Baseline deviation detection: alert when failure count exceeds historical average by a threshold."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class BaselineConfig:
    window_size: int  # number of historical samples to average over
    deviation_factor: float  # alert if current > avg * factor

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("window_size must be at least 1")
        if self.deviation_factor <= 1.0:
            raise ValueError("deviation_factor must be greater than 1.0")


@dataclass
class _JobBaseline:
    history: List[int] = field(default_factory=list)

    def record(self, count: int, window_size: int) -> None:
        self.history.append(count)
        if len(self.history) > window_size:
            self.history = self.history[-window_size:]

    def average(self) -> Optional[float]:
        if not self.history:
            return None
        return sum(self.history) / len(self.history)


class AlertBaseline:
    def __init__(self, config: BaselineConfig, on_deviation: Callable[[WebhookPayload], None]) -> None:
        self._config = config
        self._on_deviation = on_deviation
        self._state: Dict[str, _JobBaseline] = defaultdict(_JobBaseline)
        self._current_counts: Dict[str, int] = defaultdict(int)

    def record_failure(self, payload: WebhookPayload) -> None:
        job = payload.job_name or "unknown"
        self._current_counts[job] += 1

    def flush(self, payload: WebhookPayload) -> None:
        """Call at end of observation window to compare and reset."""
        job = payload.job_name or "unknown"
        current = self._current_counts.get(job, 0)
        baseline = self._state[job]
        avg = baseline.average()

        if avg is not None and current > avg * self._config.deviation_factor:
            self._on_deviation(payload)

        baseline.record(current, self._config.window_size)
        self._current_counts[job] = 0

    def current_count(self, job_name: str) -> int:
        return self._current_counts.get(job_name, 0)

    def average_for(self, job_name: str) -> Optional[float]:
        return self._state[job_name].average()
