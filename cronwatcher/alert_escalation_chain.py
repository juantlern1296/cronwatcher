"""Alert escalation chain: routes alerts through a sequence of channels
based on how many times a job has failed consecutively."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class ChainStep:
    """A single step in an escalation chain."""
    min_failures: int
    channel_name: str
    label: str = ""


@dataclass
class EscalationChainConfig:
    steps: List[ChainStep] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("EscalationChainConfig requires at least one step")
        for step in self.steps:
            if step.min_failures < 1:
                raise ValueError("min_failures must be >= 1")


class EscalationChain:
    """Tracks consecutive failure counts per job and dispatches to the
    appropriate channel based on configured thresholds."""

    def __init__(
        self,
        config: EscalationChainConfig,
        dispatch: Callable[[str, WebhookPayload], None],
    ) -> None:
        self._config = config
        self._dispatch = dispatch
        self._counts: dict[str, int] = {}
        # Sort steps descending so we match the highest threshold first
        self._steps = sorted(
            config.steps, key=lambda s: s.min_failures, reverse=True
        )

    def record_failure(self, payload: WebhookPayload) -> Optional[str]:
        """Increment failure count for the job and dispatch to the matching
        channel. Returns the channel name used, or None if no step matched."""
        job = payload.job_name or "unknown"
        self._counts[job] = self._counts.get(job, 0) + 1
        count = self._counts[job]

        for step in self._steps:
            if count >= step.min_failures:
                self._dispatch(step.channel_name, payload)
                return step.channel_name
        return None

    def record_success(self, job_name: str) -> None:
        """Reset the failure counter for a job on success."""
        self._counts.pop(job_name, None)

    def failure_count(self, job_name: str) -> int:
        return self._counts.get(job_name, 0)
