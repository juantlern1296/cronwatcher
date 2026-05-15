"""Alert sequence detector — fires when a job fails N times in a row."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict

from cronwatcher.webhook import WebhookPayload


@dataclass
class SequenceConfig:
    min_consecutive: int = 3
    per_job: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.min_consecutive < 1:
            raise ValueError("min_consecutive must be >= 1")
        for job, val in self.per_job.items():
            if val < 1:
                raise ValueError(
                    f"per_job min_consecutive for '{job}' must be >= 1"
                )

    def threshold_for(self, job: str) -> int:
        return self.per_job.get(job, self.min_consecutive)


@dataclass
class _SequenceState:
    count: int = 0


class AlertSequence:
    """Passes a payload to *handler* only after a job has failed
    *threshold* consecutive times."""

    def __init__(
        self,
        config: SequenceConfig,
        handler: Callable[[WebhookPayload], None],
    ) -> None:
        self._config = config
        self._handler = handler
        self._state: Dict[str, _SequenceState] = {}

    def _get_state(self, job: str) -> _SequenceState:
        if job not in self._state:
            self._state[job] = _SequenceState()
        return self._state[job]

    def record(self, payload: WebhookPayload) -> None:
        """Record a failure for the job in *payload*.

        If the consecutive failure count reaches the threshold the
        handler is invoked and the counter resets.
        """
        job = payload.job_name or "__unknown__"
        state = self._get_state(job)
        state.count += 1
        threshold = self._config.threshold_for(job)
        if state.count >= threshold:
            state.count = 0
            self._handler(payload)

    def reset(self, job: str) -> None:
        """Manually reset the consecutive failure counter for *job*."""
        if job in self._state:
            self._state[job].count = 0

    def consecutive_count(self, job: str) -> int:
        """Return the current consecutive failure count for *job*."""
        return self._state.get(job, _SequenceState()).count
