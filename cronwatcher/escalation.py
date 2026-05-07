"""Escalation policy: send to a secondary webhook after N consecutive failures."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class EscalationPolicy:
    threshold: int  # consecutive failures before escalating
    webhook_url: str
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class _JobState:
    consecutive: int = 0
    escalated: bool = False


class EscalationManager:
    """Tracks consecutive failures per job and decides when to escalate."""

    def __init__(self, policy: EscalationPolicy) -> None:
        if policy.threshold < 1:
            raise ValueError("threshold must be >= 1")
        self._policy = policy
        self._states: Dict[str, _JobState] = {}

    def record_failure(self, job_name: str) -> bool:
        """Record a failure for *job_name*. Returns True if escalation should fire."""
        state = self._states.setdefault(job_name, _JobState())
        state.consecutive += 1
        if state.consecutive >= self._policy.threshold:
            state.escalated = True
            logger.info(
                "Escalation triggered for job '%s' after %d consecutive failures",
                job_name,
                state.consecutive,
            )
            return True
        return False

    def record_success(self, job_name: str) -> None:
        """Reset the consecutive counter when a job succeeds."""
        if job_name in self._states:
            self._states[job_name].consecutive = 0
            self._states[job_name].escalated = False

    def consecutive_count(self, job_name: str) -> int:
        return self._states.get(job_name, _JobState()).consecutive

    def is_escalated(self, job_name: str) -> bool:
        return self._states.get(job_name, _JobState()).escalated
