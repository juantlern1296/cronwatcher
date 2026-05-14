"""Filter alerts to only fire within configured time windows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Callable, List, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class TimeWindow:
    start: time  # inclusive
    end: time    # exclusive
    weekdays: List[int] = field(default_factory=lambda: list(range(7)))  # 0=Mon

    def is_active(self, now: Optional[datetime] = None) -> bool:
        if now is None:
            now = datetime.now()
        if now.weekday() not in self.weekdays:
            return False
        current = now.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= current < self.end
        # overnight window e.g. 22:00 – 06:00
        return current >= self.start or current < self.end


@dataclass
class WindowFilterConfig:
    windows: List[TimeWindow]
    allow_outside: bool = False  # if True, pass alerts through when no window active


class AlertWindowFilter:
    """Only forward alerts when at least one configured time window is active."""

    def __init__(self, config: WindowFilterConfig, handler: Callable[[WebhookPayload], None]) -> None:
        if not config.windows:
            raise ValueError("AlertWindowFilter requires at least one time window")
        self._config = config
        self._handler = handler

    def filter(self, payload: WebhookPayload, now: Optional[datetime] = None) -> bool:
        """Return True if the alert was forwarded, False if suppressed."""
        active = any(w.is_active(now) for w in self._config.windows)
        if active or self._config.allow_outside:
            self._handler(payload)
            return True
        return False


_TIME_RE = re.compile(r'^(\d{1,2}):(\d{2})$')


def _parse_time(value: str) -> time:
    m = _TIME_RE.match(value.strip())
    if not m:
        raise ValueError(f"Invalid time format (expected HH:MM): {value!r}")
    return time(int(m.group(1)), int(m.group(2)))


def parse_window_filter(config: dict, handler: Callable[[WebhookPayload], None]) -> Optional[AlertWindowFilter]:
    section = config.get("alert_window_filter")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_window_filter must be a dict")
    raw_windows = section.get("windows", [])
    if not isinstance(raw_windows, list):
        raise ValueError("alert_window_filter.windows must be a list")
    windows: List[TimeWindow] = []
    for item in raw_windows:
        if not isinstance(item, dict):
            raise ValueError("Each window entry must be a dict")
        start = _parse_time(item["start"])
        end = _parse_time(item["end"])
        weekdays = item.get("weekdays", list(range(7)))
        if not isinstance(weekdays, list):
            raise ValueError("weekdays must be a list of integers")
        windows.append(TimeWindow(start=start, end=end, weekdays=weekdays))
    allow_outside = bool(section.get("allow_outside", False))
    cfg = WindowFilterConfig(windows=windows, allow_outside=allow_outside)
    return AlertWindowFilter(cfg, handler)
