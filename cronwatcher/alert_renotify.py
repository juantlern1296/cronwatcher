"""Periodic re-notification for unresolved (still-failing) jobs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class RenotifyConfig:
    interval: float  # seconds between re-notifications
    max_renotifies: int = 0  # 0 = unlimited

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError("interval must be positive")
        if self.max_renotifies < 0:
            raise ValueError("max_renotifies must be >= 0")


@dataclass
class _RenotifyState:
    last_sent: float
    count: int = 0


class AlertRenotifier:
    """Tracks active failures and re-notifies after a configurable interval."""

    def __init__(self, config: RenotifyConfig, handler: Callable[[WebhookPayload], None]) -> None:
        self._cfg = config
        self._handler = handler
        self._state: Dict[str, _RenotifyState] = {}

    def mark_firing(self, payload: WebhookPayload, now: Optional[float] = None) -> None:
        """Call when a job first fires an alert. Records state."""
        t = now if now is not None else time.monotonic()
        job = payload.job_name or "__unknown__"
        if job not in self._state:
            self._state[job] = _RenotifyState(last_sent=t)

    def mark_resolved(self, job_name: str) -> None:
        """Call when a job is no longer failing."""
        self._state.pop(job_name, None)

    def check(self, payload: WebhookPayload, now: Optional[float] = None) -> bool:
        """Return True and invoke handler if a re-notification is due."""
        t = now if now is not None else time.monotonic()
        job = payload.job_name or "__unknown__"
        state = self._state.get(job)
        if state is None:
            return False
        if t - state.last_sent < self._cfg.interval:
            return False
        if self._cfg.max_renotifies > 0 and state.count >= self._cfg.max_renotifies:
            return False
        state.last_sent = t
        state.count += 1
        self._handler(payload)
        return True

    def renotify_count(self, job_name: str) -> int:
        state = self._state.get(job_name)
        return state.count if state else 0
