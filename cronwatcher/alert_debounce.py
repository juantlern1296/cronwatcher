"""Alert debounce: suppress alerts until a job has failed N times in a row."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict

from cronwatcher.webhook import WebhookPayload


@dataclass
class DebounceConfig:
    min_failures: int = 2
    per_job: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.min_failures < 1:
            raise ValueError("min_failures must be at least 1")
        for job, val in self.per_job.items():
            if val < 1:
                raise ValueError(
                    f"per_job min_failures for '{job}' must be at least 1"
                )

    def threshold_for(self, job: str) -> int:
        return self.per_job.get(job, self.min_failures)


@dataclass
class _DebounceState:
    consecutive: int = 0


class AlertDebounce:
    """Only forward an alert after a job has failed consecutively >= threshold times."""

    def __init__(self, config: DebounceConfig, handler: Callable[[WebhookPayload], None]) -> None:
        self._config = config
        self._handler = handler
        self._state: Dict[str, _DebounceState] = {}

    def _get_state(self, job: str) -> _DebounceState:
        if job not in self._state:
            self._state[job] = _DebounceState()
        return self._state[job]

    def record_success(self, job: str) -> None:
        """Reset consecutive counter on success."""
        if job in self._state:
            self._state[job].consecutive = 0

    def process(self, payload: WebhookPayload) -> bool:
        """Record a failure and forward if threshold is reached. Returns True if forwarded."""
        job = payload.job_name or ""
        state = self._get_state(job)
        state.consecutive += 1
        threshold = self._config.threshold_for(job)
        if state.consecutive >= threshold:
            self._handler(payload)
            return True
        return False

    def consecutive_count(self, job: str) -> int:
        return self._state.get(job, _DebounceState()).consecutive
