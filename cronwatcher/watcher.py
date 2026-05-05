import time
import logging
from pathlib import Path
from typing import Callable

from cronwatcher.log_parser import parse_log_line, CronLogEntry, filter_failures

logger = logging.getLogger(__name__)

DEFAULT_LOG_PATH = "/var/log/syslog"
DEFAULT_POLL_INTERVAL = 5  # seconds


class LogWatcher:
    """Tails a log file and emits cron failure events to a callback."""

    def __init__(
        self,
        log_path: str = DEFAULT_LOG_PATH,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        on_failure: Callable[[CronLogEntry], None] = None,
    ):
        self.log_path = Path(log_path)
        self.poll_interval = poll_interval
        self.on_failure = on_failure or self._default_on_failure
        self._position = 0
        self._running = False

    def _default_on_failure(self, entry: CronLogEntry) -> None:
        logger.warning("Cron failure detected: %s", entry.raw_line)

    def _seek_to_end(self) -> None:
        """Initialize position to end of file to avoid replaying old entries."""
        if self.log_path.exists():
            self._position = self.log_path.stat().st_size
        else:
            self._position = 0

    def _read_new_lines(self) -> list[str]:
        """Read any new lines added since last check."""
        if not self.log_path.exists():
            return []

        current_size = self.log_path.stat().st_size
        if current_size < self._position:
            logger.info("Log file rotated, resetting position.")
            self._position = 0

        if current_size == self._position:
            return []

        with open(self.log_path, "r", errors="replace") as f:
            f.seek(self._position)
            new_content = f.read()
            self._position = f.tell()

        return new_content.splitlines()

    def _process_lines(self, lines: list[str]) -> None:
        entries = [parse_log_line(line) for line in lines]
        valid = [e for e in entries if e is not None]
        for failure in filter_failures(valid):
            try:
                self.on_failure(failure)
            except Exception:
                logger.exception("Error in on_failure callback")

    def start(self) -> None:
        """Start watching the log file. Blocks until stop() is called."""
        logger.info("Starting log watcher on %s", self.log_path)
        self._seek_to_end()
        self._running = True
        while self._running:
            lines = self._read_new_lines()
            if lines:
                self._process_lines(lines)
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        """Signal the watcher loop to stop."""
        self._running = False
        logger.info("Log watcher stopped.")
