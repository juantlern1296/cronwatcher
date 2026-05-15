"""Tracks circuit breaker state transitions and logs them for audit/debugging."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from cronwatcher.circuit_breaker import CircuitState

logger = logging.getLogger(__name__)


@dataclass
class CircuitTransition:
    job_name: str
    from_state: CircuitState
    to_state: CircuitState
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CircuitTransitionLog:
    max_entries: int = 200
    _entries: List[CircuitTransition] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")

    def record(self, job_name: str, from_state: CircuitState, to_state: CircuitState, reason: str) -> None:
        entry = CircuitTransition(
            job_name=job_name,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
        )
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries :]
        logger.info(
            "circuit_breaker transition job=%s %s -> %s reason=%s",
            job_name,
            from_state.value,
            to_state.value,
            reason,
        )

    def recent(self, n: int = 10) -> List[CircuitTransition]:
        return list(self._entries[-n:])

    def for_job(self, job_name: str) -> List[CircuitTransition]:
        return [e for e in self._entries if e.job_name == job_name]

    def size(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
