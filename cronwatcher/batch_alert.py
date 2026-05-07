"""Batch alerting: collect multiple failures within a window and send a single grouped webhook."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List

from cronwatcher.log_parser import CronLogEntry


@dataclass
class BatchConfig:
    window_seconds: float = 30.0
    max_size: int = 20


@dataclass
class AlertBatch:
    entries: List[CronLogEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)

    def add(self, entry: CronLogEntry) -> None:
        self.entries.append(entry)

    def is_full(self, max_size: int) -> bool:
        return len(self.entries) >= max_size

    def is_expired(self, window_seconds: float) -> bool:
        return (time.monotonic() - self.created_at) >= window_seconds


class BatchAlerter:
    """Accumulates CronLogEntry failures and flushes them as a batch."""

    def __init__(
        self,
        config: BatchConfig,
        flush_callback: Callable[[List[CronLogEntry]], None],
    ) -> None:
        if config.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if config.max_size < 1:
            raise ValueError("max_size must be at least 1")
        self._config = config
        self._flush_callback = flush_callback
        self._batch: AlertBatch = AlertBatch()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._start_timer()

    def add(self, entry: CronLogEntry) -> None:
        with self._lock:
            self._batch.add(entry)
            if self._batch.is_full(self._config.max_size):
                self._flush_locked()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        entries = self._batch.entries[:]
        self._batch = AlertBatch()
        if entries:
            self._flush_callback(entries)
        self._start_timer()

    def _start_timer(self) -> None:
        self._timer = threading.Timer(self._config.window_seconds, self._on_timer)
        self._timer.daemon = True
        self._timer.start()

    def _on_timer(self) -> None:
        with self._lock:
            self._flush_locked()

    def stop(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
