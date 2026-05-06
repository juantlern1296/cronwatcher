"""Periodic checker that fires alerts for overdue cron jobs."""

import logging
import threading
from typing import Callable, Optional

from cronwatcher.job_timeout import JobTimeoutMonitor

logger = logging.getLogger(__name__)

OnOverdue = Callable[[str], None]


class TimeoutChecker:
    """Runs a background timer that checks for overdue jobs at a fixed interval."""

    def __init__(
        self,
        monitor: JobTimeoutMonitor,
        check_interval_seconds: int,
        on_overdue: OnOverdue,
    ) -> None:
        if check_interval_seconds <= 0:
            raise ValueError("check_interval_seconds must be positive")
        self._monitor = monitor
        self._interval = check_interval_seconds
        self._on_overdue = on_overdue
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._stopped = False

    def start(self) -> None:
        """Start the periodic checker."""
        self._stopped = False
        self._schedule()

    def stop(self) -> None:
        """Stop the periodic checker."""
        self._stopped = True
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def check_now(self) -> list[str]:
        """Run an immediate check and invoke callbacks. Returns overdue job names."""
        overdue = self._monitor.overdue_jobs()
        for job_name in overdue:
            logger.warning("Job '%s' is overdue — triggering alert", job_name)
            try:
                self._on_overdue(job_name)
            except Exception:
                logger.exception("on_overdue callback raised for job '%s'", job_name)
        return overdue

    def _schedule(self) -> None:
        if self._stopped:
            return
        timer = threading.Timer(self._interval, self._tick)
        timer.daemon = True
        with self._lock:
            self._timer = timer
        timer.start()

    def _tick(self) -> None:
        self.check_now()
        self._schedule()
