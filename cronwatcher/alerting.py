"""Alert deduplication and rate-limiting for cronwatcher."""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AlertState:
    last_sent: float = 0.0
    count: int = 0


@dataclass
class AlertManager:
    """Tracks sent alerts to avoid spamming webhooks."""

    cooldown_seconds: int = 300  # 5 minutes default
    _state: Dict[str, AlertState] = field(default_factory=dict)

    def should_alert(self, job_name: str) -> bool:
        """Return True if enough time has passed since the last alert for this job."""
        now = time.time()
        state = self._state.get(job_name)
        if state is None:
            return True
        return (now - state.last_sent) >= self.cooldown_seconds

    def record_alert(self, job_name: str) -> None:
        """Mark that an alert was just sent for the given job."""
        now = time.time()
        if job_name in self._state:
            self._state[job_name].last_sent = now
            self._state[job_name].count += 1
        else:
            self._state[job_name] = AlertState(last_sent=now, count=1)

    def alert_count(self, job_name: str) -> int:
        """Return how many times an alert has been sent for this job."""
        state = self._state.get(job_name)
        return state.count if state else 0

    def reset(self, job_name: Optional[str] = None) -> None:
        """Reset state for a specific job or all jobs."""
        if job_name is not None:
            self._state.pop(job_name, None)
        else:
            self._state.clear()
