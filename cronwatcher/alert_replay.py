"""Replay failed alerts from the dead letter queue."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from cronwatcher.dead_letter import DeadLetterQueue
from cronwatcher.webhook import WebhookPayload, send_webhook
from cronwatcher.config import WebhookConfig

logger = logging.getLogger(__name__)


class ReplayConfig:
    """Configuration for alert replay behaviour."""

    def __init__(self, max_replays: int = 50, dry_run: bool = False) -> None:
        if max_replays < 1:
            raise ValueError("max_replays must be at least 1")
        self.max_replays = max_replays
        self.dry_run = dry_run


class AlertReplayer:
    """Drains a DeadLetterQueue and retries delivery of failed alerts."""

    def __init__(
        self,
        queue: DeadLetterQueue,
        webhook_cfg: WebhookConfig,
        config: Optional[ReplayConfig] = None,
        send_fn: Callable[[WebhookPayload, WebhookConfig], bool] = send_webhook,
    ) -> None:
        self._queue = queue
        self._webhook_cfg = webhook_cfg
        self._config = config or ReplayConfig()
        self._send_fn = send_fn

    def replay(self) -> int:
        """Attempt to resend all queued dead-letter payloads.

        Returns the number of successfully replayed alerts.
        """
        entries = self._queue.pop_all()
        if not entries:
            logger.debug("Dead letter queue is empty; nothing to replay")
            return 0

        entries = entries[: self._config.max_replays]
        succeeded = 0
        failed_back: list = []

        for entry in entries:
            payload = entry.payload
            if self._config.dry_run:
                logger.info("[dry-run] Would replay alert for job=%s", payload.job_name)
                succeeded += 1
                continue

            ok = self._send_fn(payload, self._webhook_cfg)
            if ok:
                logger.info("Replayed alert for job=%s", payload.job_name)
                succeeded += 1
            else:
                logger.warning("Replay failed for job=%s; re-queuing", payload.job_name)
                failed_back.append(entry)

        for entry in failed_back:
            self._queue.push(entry.payload)

        logger.info("Replay complete: %d/%d succeeded", succeeded, len(entries))
        return succeeded
