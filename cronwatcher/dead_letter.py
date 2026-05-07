"""Dead letter queue for failed webhook deliveries."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwatcher.webhook import WebhookPayload

logger = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 500


@dataclass
class DeadLetterEntry:
    payload: WebhookPayload
    failed_at: float
    attempts: int
    last_error: str


@dataclass
class DeadLetterQueue:
    max_size: int = MAX_QUEUE_SIZE
    _entries: List[DeadLetterEntry] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.max_size < 1:
            raise ValueError("max_size must be at least 1")

    def push(self, payload: WebhookPayload, attempts: int, error: str) -> None:
        if len(self._entries) >= self.max_size:
            dropped = self._entries.pop(0)
            logger.warning(
                "dead_letter_queue full, dropping oldest entry job=%s",
                dropped.payload.job_name,
            )
        entry = DeadLetterEntry(
            payload=payload,
            failed_at=time.time(),
            attempts=attempts,
            last_error=error,
        )
        self._entries.append(entry)
        logger.info(
            "queued failed delivery job=%s attempts=%d",
            payload.job_name,
            attempts,
        )

    def pop_all(self) -> List[DeadLetterEntry]:
        entries, self._entries = self._entries, []
        return entries

    def size(self) -> int:
        return len(self._entries)

    def flush(self, retry_fn: Callable[[WebhookPayload], bool]) -> int:
        """Retry all queued entries. Returns count of successfully resent."""
        remaining: List[DeadLetterEntry] = []
        success_count = 0
        for entry in self.pop_all():
            try:
                ok = retry_fn(entry.payload)
            except Exception as exc:  # noqa: BLE001
                ok = False
                entry.last_error = str(exc)
            if ok:
                success_count += 1
                logger.info("dead_letter resend succeeded job=%s", entry.payload.job_name)
            else:
                entry.attempts += 1
                remaining.append(entry)
                logger.warning(
                    "dead_letter resend failed job=%s attempts=%d",
                    entry.payload.job_name,
                    entry.attempts,
                )
        self._entries = remaining
        return success_count
