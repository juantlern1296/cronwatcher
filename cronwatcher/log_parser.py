import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


CRON_LOG_PATTERN = re.compile(
    r"(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+\S+\s+CRON\[(?P<pid>\d+)\]:\s+"
    r"\((?P<user>\S+)\)\s+(?P<status>\S+)\s+\((?P<message>.+)\)"
)


@dataclass
class CronLogEntry:
    timestamp: str
    pid: int
    user: str
    status: str
    message: str
    raw_line: str

    @property
    def is_failure(self) -> bool:
        failure_statuses = {"FAILED", "ERROR"}
        return self.status.upper() in failure_statuses

    @property
    def job_name(self) -> Optional[str]:
        match = re.search(r"CMD\s+\((.+)\)", self.message)
        if match:
            return match.group(1).strip()
        return self.message.strip()


def parse_log_line(line: str) -> Optional[CronLogEntry]:
    """Parse a single syslog cron line into a CronLogEntry."""
    match = CRON_LOG_PATTERN.match(line.strip())
    if not match:
        return None

    return CronLogEntry(
        timestamp=match.group("timestamp"),
        pid=int(match.group("pid")),
        user=match.group("user"),
        status=match.group("status"),
        message=match.group("message"),
        raw_line=line.strip(),
    )


def parse_log_lines(lines: list[str]) -> list[CronLogEntry]:
    """Parse multiple log lines, returning only successfully parsed entries."""
    entries = []
    for line in lines:
        entry = parse_log_line(line)
        if entry is not None:
            entries.append(entry)
    return entries


def filter_failures(entries: list[CronLogEntry]) -> list[CronLogEntry]:
    """Return only entries that represent cron job failures."""
    return [e for e in entries if e.is_failure]


def group_by_user(entries: list[CronLogEntry]) -> dict[str, list[CronLogEntry]]:
    """Group log entries by the user that ran the cron job.

    Returns a dict mapping each username to a list of their log entries,
    in the order they were encountered.
    """
    grouped: dict[str, list[CronLogEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.user, []).append(entry)
    return grouped
