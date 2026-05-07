"""Circuit breaker to pause alerting for a job after repeated failures."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class CircuitState(Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # alerting paused
    HALF_OPEN = "half_open"  # testing recovery


@dataclass
class _BreakerState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: float = 0.0


class CircuitBreaker:
    """Per-job circuit breaker.

    Opens after *threshold* consecutive failures and stays open for
    *reset_timeout* seconds before moving to HALF_OPEN.
    """

    def __init__(self, threshold: int = 5, reset_timeout: float = 300.0) -> None:
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        if reset_timeout <= 0:
            raise ValueError("reset_timeout must be positive")
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self._states: Dict[str, _BreakerState] = {}

    def _get(self, job: str) -> _BreakerState:
        if job not in self._states:
            self._states[job] = _BreakerState()
        return self._states[job]

    def is_open(self, job: str) -> bool:
        """Return True if alerts for *job* should be suppressed."""
        s = self._get(job)
        if s.state == CircuitState.OPEN:
            if time.monotonic() - s.opened_at >= self.reset_timeout:
                s.state = CircuitState.HALF_OPEN
                return False
            return True
        return False

    def record_failure(self, job: str) -> CircuitState:
        """Record a failure event and return the resulting state."""
        s = self._get(job)
        if s.state == CircuitState.HALF_OPEN:
            # Still failing — reopen immediately.
            s.state = CircuitState.OPEN
            s.opened_at = time.monotonic()
            return s.state
        s.failure_count += 1
        if s.failure_count >= self.threshold:
            s.state = CircuitState.OPEN
            s.opened_at = time.monotonic()
        return s.state

    def record_success(self, job: str) -> None:
        """Reset the breaker for *job* (call when a job succeeds)."""
        self._states[job] = _BreakerState()

    def state_of(self, job: str) -> CircuitState:
        self.is_open(job)  # trigger timeout check
        return self._get(job).state
