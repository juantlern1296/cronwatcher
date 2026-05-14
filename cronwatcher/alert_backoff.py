"""Exponential backoff for alert delivery retries."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class BackoffConfig:
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    max_attempts: int = 5

    def __post_init__(self) -> None:
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.multiplier <= 1.0:
            raise ValueError("multiplier must be > 1.0")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

    def delay_for(self, attempt: int) -> float:
        """Return the delay in seconds for a given attempt (0-indexed)."""
        delay = self.base_delay * (self.multiplier ** attempt)
        return min(delay, self.max_delay)


@dataclass
class _AttemptState:
    attempts: int = 0
    last_attempt: float = field(default_factory=time.monotonic)


class AlertBackoff:
    """Wraps an alert handler with exponential backoff retry logic."""

    def __init__(
        self,
        config: BackoffConfig,
        handler: Callable[[WebhookPayload], bool],
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._handler = handler
        self._sleep = sleep_fn
        self._states: Dict[str, _AttemptState] = {}

    def send(self, payload: WebhookPayload) -> bool:
        """Attempt delivery with exponential backoff. Returns True on success."""
        job = payload.job_name or "__unknown__"
        cfg = self._config

        for attempt in range(cfg.max_attempts):
            if attempt > 0:
                delay = cfg.delay_for(attempt - 1)
                self._sleep(delay)
            success = self._handler(payload)
            if success:
                self._states.pop(job, None)
                return True

        state = self._states.setdefault(job, _AttemptState())
        state.attempts += 1
        state.last_attempt = time.monotonic()
        return False

    def attempt_count(self, job_name: str) -> int:
        state = self._states.get(job_name)
        return state.attempts if state else 0


def parse_backoff_config(raw: dict) -> Optional[BackoffConfig]:
    section = raw.get("alert_backoff")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_backoff must be a dict")
    return BackoffConfig(
        base_delay=float(section.get("base_delay", 1.0)),
        max_delay=float(section.get("max_delay", 60.0)),
        multiplier=float(section.get("multiplier", 2.0)),
        max_attempts=int(section.get("max_attempts", 5)),
    )
