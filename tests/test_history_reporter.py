"""Tests for cronwatcher.history_reporter."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.history_reporter import (
    build_history_report,
    history_as_json,
    log_history_report,
)
from cronwatcher.job_history import JobHistoryStore
from cronwatcher.log_parser import CronLogEntry


def make_entry(job_name: str = "backup", exit_code: int = 1) -> CronLogEntry:
    entry = MagicMock(spec=CronLogEntry)
    entry.job_name = job_name
    entry.timestamp = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    entry.exit_code = exit_code
    entry.raw_line = f"cron line for {job_name}"
    return entry


@pytest.fixture
def populated_store() -> JobHistoryStore:
    store = JobHistoryStore(max_entries_per_job=10)
    for _ in range(3):
        store.record(make_entry("backup", exit_code=1))
    store.record(make_entry("deploy", exit_code=127))
    return store


def test_build_history_report_contains_all_jobs(populated_store):
    report = build_history_report(populated_store)
    assert "backup" in report
    assert "deploy" in report


def test_build_history_report_total(populated_store):
    report = build_history_report(populated_store)
    assert report["backup"]["total_recorded"] == 3
    assert report["deploy"]["total_recorded"] == 1


def test_build_history_report_recent_failures_length(populated_store):
    report = build_history_report(populated_store, recent_n=2)
    assert len(report["backup"]["recent_failures"]) == 2


def test_build_history_report_record_fields(populated_store):
    report = build_history_report(populated_store)
    record = report["backup"]["recent_failures"][0]
    assert "job_name" in record
    assert "timestamp" in record
    assert "exit_code" in record
    assert "raw_line" in record


def test_build_history_report_empty_store():
    store = JobHistoryStore()
    report = build_history_report(store)
    assert report == {}


def test_history_as_json_is_valid_json(populated_store):
    result = history_as_json(populated_store)
    parsed = json.loads(result)
    assert "backup" in parsed


def test_log_history_report_calls_logger(populated_store):
    with patch("cronwatcher.history_reporter.logger") as mock_logger:
        log_history_report(populated_store)
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0]
        assert "job_history" in call_args[0]


def test_log_history_report_empty_store_logs_empty():
    store = JobHistoryStore()
    with patch("cronwatcher.history_reporter.logger") as mock_logger:
        log_history_report(store)
        mock_logger.info.assert_called_once()
        assert "{}" in mock_logger.info.call_args[0][0]
