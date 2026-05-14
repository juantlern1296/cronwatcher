"""On-call schedule integration: routes alerts to the current on-call contact."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Callable, List, Optional

from cronwatcher.webhook import WebhookPayload

logger = logging.getLogger(__name__)


@dataclass
class OnCallSlot:
    """A single on-call slot covering a weekday range and time window."""

    name: str
    webhook_url: str
    weekdays: List[int]  # 0=Monday .. 6=Sunday
    start_time: time
    end_time: time

    def is_active(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        if now.weekday() not in self.weekdays:
            return False
        current = now.time().replace(second=0, microsecond=0)
        return self.start_time <= current < self.end_time


@dataclass
class OnCallSchedule:
    slots: List[OnCallSlot] = field(default_factory=list)
    fallback_url: Optional[str] = None

    def current_url(self, now: Optional[datetime] = None) -> Optional[str]:
        for slot in self.slots:
            if slot.is_active(now):
                return slot.webhook_url
        return self.fallback_url


class AlertOnCall:
    """Routes a payload to the on-call webhook URL for the current time."""

    def __init__(
        self,
        schedule: OnCallSchedule,
        send_fn: Callable[[str, WebhookPayload], bool],
    ) -> None:
        self._schedule = schedule
        self._send = send_fn

    def dispatch(self, payload: WebhookPayload, now: Optional[datetime] = None) -> bool:
        url = self._schedule.current_url(now)
        if url is None:
            logger.warning("on-call: no active slot and no fallback configured")
            return False
        logger.debug("on-call: dispatching to %s", url)
        return self._send(url, payload)
