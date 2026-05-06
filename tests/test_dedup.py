"""Tests for cronwatcher.dedup module."""

import pytest

from cronwatcher.dedup import DedupStore
from cronwatcher.log_parser import CronLogEntry


def make_entry(job_name: str = "backup", exit_code: int = 1) -> CronLogEntry:
    return CronLogEntry(
        raw="some raw line",
        job_name=job_name,
        exit_code=exit_code,
        timestamp=None,
    )


@pytest.fixture
def store() -> DedupStore:
    return DedupStore(window_seconds=60.0)


def test_new_entry_is_not_duplicate(store):
    entry = make_entry()
    assert store.is_duplicate(entry, now=1000.0) is False


def test_entry_is_duplicate_after_record(store):
    entry = make_entry()
    store.record(entry, now=1000.0)
    assert store.is_duplicate(entry, now=1010.0) is True


def test_entry_not_duplicate_after_window_expires(store):
    entry = make_entry()
    store.record(entry, now=1000.0)
    assert store.is_duplicate(entry, now=1061.0) is False


def test_different_jobs_are_independent(store):
    e1 = make_entry(job_name="backup")
    e2 = make_entry(job_name="cleanup")
    store.record(e1, now=1000.0)
    assert store.is_duplicate(e2, now=1010.0) is False


def test_different_exit_codes_are_independent(store):
    e1 = make_entry(exit_code=1)
    e2 = make_entry(exit_code=2)
    store.record(e1, now=1000.0)
    assert store.is_duplicate(e2, now=1010.0) is False


def test_record_increments_count(store):
    entry = make_entry()
    store.record(entry, now=1000.0)
    dedup_entry = store.record(entry, now=1010.0)
    assert dedup_entry.count == 2


def test_record_updates_last_seen(store):
    entry = make_entry()
    store.record(entry, now=1000.0)
    dedup_entry = store.record(entry, now=1020.0)
    assert dedup_entry.last_seen == 1020.0
    assert dedup_entry.first_seen == 1000.0


def test_clear_removes_all_entries(store):
    entry = make_entry()
    store.record(entry, now=1000.0)
    store.clear()
    assert store.is_duplicate(entry, now=1001.0) is False


def test_eviction_on_is_duplicate_check(store):
    entry = make_entry()
    store.record(entry, now=1000.0)
    # advance past window so eviction fires inside is_duplicate
    result = store.is_duplicate(entry, now=2000.0)
    assert result is False
    assert len(store._store) == 0
