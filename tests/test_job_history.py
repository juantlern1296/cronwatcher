"""Tests for cronwatcher.job_history."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.job_history import (
    DEFAULT_MAX_HISTORY,
    FailureRecord,
    JobHistory,
    JobHistoryStore,
)
from cronwatcher.log_parser import CronLogEntry


def make_entry(job_name: str = "backup", exit_code: int = 1) -> CronLogEntry:
    entry = MagicMock(spec=CronLogEntry)
    entry.job_name = job_name
    entry.timestamp = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    entry.exit_code = exit_code
    entry.raw_line = f"CRON[1234]: ({job_name}) CMD (exit {exit_code})"
    return entry


@pytest.fixture
def history() -> JobHistory:
    return JobHistory(max_entries=5)


@pytest.fixture
def store() -> JobHistoryStore:
    return JobHistoryStore(max_entries_per_job=5)


def test_invalid_max_entries_raises():
    with pytest.raises(ValueError):
        JobHistory(max_entries=0)


def test_record_adds_entry(history):
    history.record(make_entry())
    assert history.total() == 1


def test_last_returns_most_recent(history):
    history.record(make_entry(exit_code=1))
    history.record(make_entry(exit_code=2))
    assert history.last().exit_code == 2


def test_last_on_empty_returns_none(history):
    assert history.last() is None


def test_recent_returns_up_to_n(history):
    for i in range(5):
        history.record(make_entry(exit_code=i))
    assert len(history.recent(3)) == 3
    assert history.recent(3)[-1].exit_code == 4


def test_max_entries_bounded():
    h = JobHistory(max_entries=3)
    for i in range(6):
        h.record(make_entry(exit_code=i))
    assert h.total() == 3
    assert h.last().exit_code == 5


def test_store_record_creates_history(store):
    store.record(make_entry("deploy"))
    assert "deploy" in store.all_jobs()


def test_store_get_returns_history(store):
    store.record(make_entry("cleanup"))
    h = store.get("cleanup")
    assert h is not None
    assert h.total() == 1


def test_store_get_unknown_returns_none(store):
    assert store.get("nonexistent") is None


def test_store_summary(store):
    store.record(make_entry("jobA"))
    store.record(make_entry("jobA"))
    store.record(make_entry("jobB"))
    summary = store.summary()
    assert summary["jobA"] == 2
    assert summary["jobB"] == 1


def test_unknown_job_name_uses_fallback(store):
    entry = make_entry()
    entry.job_name = None
    store.record(entry)
    assert "unknown" in store.all_jobs()
