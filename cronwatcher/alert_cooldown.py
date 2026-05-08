"""Per-job cooldown enforcement to suppress repeated alerts within a time window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class CooldownConfig:
    default_seconds: float
    per_job: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.default_seconds < 0:
            raise ValueError("default_seconds must be >= 0")
        for job, secs in self.per_job.items():
            if secs < 0:
                raise ValueError(f"cooldown for job '{job}' must be >= 0")

    def cooldown_for(self, job_name: str) -> float:
        return self.per_job.get(job_name, self.default_seconds)


@dataclass
class _CooldownState:
    last_alert_at: float


class AlertCooldown:
    """Tracks last-alert timestamps and decides whether a new alert is allowed."""

    def __init__(self, config: CooldownConfig) -> None:
        self._config = config
        self._state: Dict[str, _CooldownState] = {}

    def is_allowed(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if the job is outside its cooldown window."""
        t = now if now is not None else time.monotonic()
        state = self._state.get(job_name)
        if state is None:
            return True
        elapsed = t - state.last_alert_at
        return elapsed >= self._config.cooldown_for(job_name)

    def record(self, job_name: str, now: Optional[float] = None) -> None:
        """Record that an alert was just sent for this job."""
        t = now if now is not None else time.monotonic()
        self._state[job_name] = _CooldownState(last_alert_at=t)

    def reset(self, job_name: str) -> None:
        """Clear cooldown state for a job (e.g. after recovery)."""
        self._state.pop(job_name, None)

    def remaining(self, job_name: str, now: Optional[float] = None) -> float:
        """Return seconds remaining in cooldown, or 0.0 if not in cooldown."""
        t = now if now is not None else time.monotonic()
        state = self._state.get(job_name)
        if state is None:
            return 0.0
        window = self._config.cooldown_for(job_name)
        elapsed = t - state.last_alert_at
        return max(0.0, window - elapsed)


def parse_cooldown_config(raw: dict) -> CooldownConfig:
    """Parse cooldown section from config dict."""
    section = raw.get("cooldown")
    if not section or not isinstance(section, dict):
        return CooldownConfig(default_seconds=0.0)
    default = float(section.get("default_seconds", 0.0))
    per_job_raw = section.get("per_job", {})
    if not isinstance(per_job_raw, dict):
        raise ValueError("cooldown.per_job must be a dict")
    per_job = {k: float(v) for k, v in per_job_raw.items()}
    return CooldownConfig(default_seconds=default, per_job=per_job)
