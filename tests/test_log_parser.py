import pytest
from cronwatcher.log_parser import (
    parse_log_line,
    parse_log_lines,
    filter_failures,
    CronLogEntry,
)


FAILED_LINE = (
    "Jan 15 03:00:01 myhost CRON[12345]: (root) FAILED (job failed with exit code 1)"
)
CMD_LINE = (
    "Jan 15 03:00:01 myhost CRON[12346]: (deploy) CMD (/usr/bin/backup.sh)"
)
GARBAGE_LINE = "This is not a cron log line at all"


def test_parse_log_line_failure():
    entry = parse_log_line(FAILED_LINE)
    assert entry is not None
    assert entry.status == "FAILED"
    assert entry.user == "root"
    assert entry.pid == 12345
    assert entry.is_failure is True


def test_parse_log_line_cmd():
    entry = parse_log_line(CMD_LINE)
    assert entry is not None
    assert entry.status == "CMD"
    assert entry.user == "deploy"
    assert entry.is_failure is False


def test_parse_log_line_garbage():
    entry = parse_log_line(GARBAGE_LINE)
    assert entry is None


def test_parse_log_line_empty():
    assert parse_log_line("") is None


def test_job_name_from_cmd_line():
    entry = parse_log_line(CMD_LINE)
    assert entry is not None
    assert entry.job_name == "/usr/bin/backup.sh"


def test_job_name_from_failure_line():
    entry = parse_log_line(FAILED_LINE)
    assert entry is not None
    assert entry.job_name == "job failed with exit code 1"


def test_parse_log_lines_mixed():
    lines = [FAILED_LINE, CMD_LINE, GARBAGE_LINE]
    entries = parse_log_lines(lines)
    assert len(entries) == 2


def test_filter_failures():
    lines = [FAILED_LINE, CMD_LINE]
    entries = parse_log_lines(lines)
    failures = filter_failures(entries)
    assert len(failures) == 1
    assert failures[0].status == "FAILED"


def test_raw_line_preserved():
    entry = parse_log_line(FAILED_LINE)
    assert entry is not None
    assert entry.raw_line == FAILED_LINE.strip()
