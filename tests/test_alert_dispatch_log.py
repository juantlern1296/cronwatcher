"""Tests for cronwatcher.alert_dispatch_log."""

import pytest
from cronwatcher.alert_dispatch_log import DispatchLog, DispatchRecord


@pytest.fixture
def log():
    return DispatchLog(max_entries=100)


def test_invalid_max_entries_raises():
    with pytest.raises(ValueError):
        DispatchLog(max_entries=0)


def test_record_adds_entry(log):
    log.record("backup", "slack", success=True, status_code=200)
    assert len(log) == 1


def test_record_stores_fields(log):
    log.record("backup", "slack", success=False, status_code=500, error="timeout", now=1000.0)
    r = log.recent(1)[0]
    assert r.job_name == "backup"
    assert r.channel == "slack"
    assert r.success is False
    assert r.status_code == 500
    assert r.error == "timeout"
    assert r.timestamp == 1000.0


def test_recent_returns_last_n(log):
    for i in range(10):
        log.record(f"job{i}", "webhook", success=True)
    result = log.recent(3)
    assert len(result) == 3
    assert result[-1].job_name == "job9"


def test_failures_filters_only_failed(log):
    log.record("jobA", "slack", success=True)
    log.record("jobB", "slack", success=False, error="connection refused")
    log.record("jobC", "slack", success=False, error="timeout")
    failures = log.failures()
    assert len(failures) == 2
    assert all(not r.success for r in failures)


def test_for_job_filters_by_name(log):
    log.record("alpha", "ch1", success=True)
    log.record("beta", "ch1", success=True)
    log.record("alpha", "ch2", success=False)
    result = log.for_job("alpha")
    assert len(result) == 2
    assert all(r.job_name == "alpha" for r in result)


def test_max_entries_evicts_oldest():
    log = DispatchLog(max_entries=3)
    for i in range(5):
        log.record(f"job{i}", "ch", success=True, now=float(i))
    assert len(log) == 3
    names = [r.job_name for r in log.recent()]
    assert names == ["job2", "job3", "job4"]


def test_clear_empties_log(log):
    log.record("backup", "slack", success=True)
    log.clear()
    assert len(log) == 0


def test_no_error_defaults_to_none(log):
    log.record("myjob", "webhook", success=True, status_code=200)
    r = log.recent(1)[0]
    assert r.error is None


def test_timestamp_auto_set_when_not_provided(log):
    import time
    before = time.time()
    log.record("myjob", "webhook", success=True)
    after = time.time()
    r = log.recent(1)[0]
    assert before <= r.timestamp <= after
