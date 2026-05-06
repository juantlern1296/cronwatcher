"""Periodic metrics reporter — logs a summary on a fixed interval."""

import json
import logging
import threading
from typing import Optional

from cronwatcher.metrics import MetricsStore

logger = logging.getLogger(__name__)


class MetricsReporter:
    """Logs a JSON metrics summary every `interval_seconds`."""

    def __init__(self, store: MetricsStore, interval_seconds: int = 300):
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.store = store
        self.interval_seconds = interval_seconds
        self._timer: Optional[threading.Timer] = None
        self._stopped = threading.Event()

    def start(self) -> None:
        """Start the periodic reporting loop."""
        self._stopped.clear()
        self._schedule()
        logger.info("MetricsReporter started (interval=%ds)", self.interval_seconds)

    def stop(self) -> None:
        """Stop the periodic reporting loop."""
        self._stopped.set()
        if self._timer is not None:
            self._timer.cancel()
        logger.info("MetricsReporter stopped")

    def report_now(self) -> None:
        """Emit a metrics summary immediately."""
        summary = self.store.summary()
        logger.info("[metrics] %s", json.dumps(summary))

    def _schedule(self) -> None:
        if self._stopped.is_set():
            return
        self._timer = threading.Timer(self.interval_seconds, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        self.report_now()
        self._schedule()
