"""Periodic digest of accumulated alerts, grouped by job name."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List

from cronwatcher.webhook import WebhookPayload

logger = logging.getLogger(__name__)


@dataclass
class DigestConfig:
    interval_seconds: float  # how often to flush the digest
    min_alerts: int = 1      # only send digest if at least this many alerts accumulated


@dataclass
class _DigestBucket:
    payloads: List[WebhookPayload] = field(default_factory=list)


class AlertDigest:
    """Accumulates WebhookPayload objects and flushes them as a grouped digest."""

    def __init__(
        self,
        config: DigestConfig,
        on_flush: Callable[[str, List[WebhookPayload]], None],
    ) -> None:
        if config.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if config.min_alerts < 1:
            raise ValueError("min_alerts must be at least 1")
        self._config = config
        self._on_flush = on_flush
        self._buckets: Dict[str, _DigestBucket] = {}
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def add(self, payload: WebhookPayload) -> None:
        job = payload.job_name or "unknown"
        with self._lock:
            if job not in self._buckets:
                self._buckets[job] = _DigestBucket()
            self._buckets[job].payloads.append(payload)

    def flush(self) -> None:
        with self._lock:
            snapshot = self._buckets
            self._buckets = {}
        for job, bucket in snapshot.items():
            if len(bucket.payloads) >= self._config.min_alerts:
                try:
                    self._on_flush(job, bucket.payloads)
                except Exception:
                    logger.exception("Digest flush callback failed for job %s", job)
            else:
                logger.debug(
                    "Digest skipped for %s: only %d alert(s) (min=%d)",
                    job, len(bucket.payloads), self._config.min_alerts,
                )

    def start(self) -> None:
        self._schedule()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _schedule(self) -> None:
        self._timer = threading.Timer(self._config.interval_seconds, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        self.flush()
        self._schedule()
