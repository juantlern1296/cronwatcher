"""Time-window based alert muting (maintenance windows)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MuteWindow:
    job_name: str  # "*" means all jobs
    start: float   # unix timestamp
    end: float     # unix timestamp
    reason: str = ""

    def is_active(self, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.time()
        return self.start <= t < self.end


@dataclass
class AlertMute:
    _windows: List[MuteWindow] = field(default_factory=list)

    def add_window(self, window: MuteWindow) -> None:
        self._windows.append(window)

    def remove_window(self, job_name: str) -> int:
        """Remove all mute windows for the given job. Returns count removed."""
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.job_name != job_name]
        return before - len(self._windows)

    def is_muted(self, job_name: str, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.time()
        for window in self._windows:
            if not window.is_active(t):
                continue
            if window.job_name == "*" or window.job_name == job_name:
                return True
        return False

    def active_windows(self, now: Optional[float] = None) -> List[MuteWindow]:
        t = now if now is not None else time.time()
        return [w for w in self._windows if w.is_active(t)]

    def evict_expired(self, now: Optional[float] = None) -> int:
        """Remove expired windows. Returns count removed."""
        t = now if now is not None else time.time()
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.end > t]
        return before - len(self._windows)
