"""Tests for JobTimeoutMonitor."""

from datetime import datetime, timedelta

import pytest

from cronwatcher.job_timeout import JobTimeoutConfig, JobTimeoutMonitor


@pytest.fixture
def cfg_backup():
    return JobTimeoutConfig(
        job_name="backup",
        expected_interval_seconds=3600,
        grace_period_seconds=60,
    )


@pytest.fixture
def monitor(cfg_backup):
    return JobTimeoutMonitor(configs=[cfg_backup])


def test_no_configs_raises():
    with pytest.raises(ValueError, match="At least one"):
        JobTimeoutMonitor(configs=[])


def test_never_seen_job_not_overdue(monitor):
    # A job that was never seen is skipped (not reported as overdue)
    result = monitor.overdue_jobs(now=datetime.utcnow())
    assert result == []


def test_recently_seen_job_not_overdue(monitor):
    now = datetime.utcnow()
    monitor.record_seen("backup", at=now - timedelta(seconds=100))
    result = monitor.overdue_jobs(now=now)
    assert "backup" not in result


def test_overdue_job_reported(monitor):
    now = datetime.utcnow()
    # Last seen 2 hours ago; interval=3600 + grace=60 => overdue after 3660s
    monitor.record_seen("backup", at=now - timedelta(seconds=7200))
    result = monitor.overdue_jobs(now=now)
    assert "backup" in result


def test_exactly_at_deadline_is_overdue(monitor):
    now = datetime.utcnow()
    monitor.record_seen("backup", at=now - timedelta(seconds=3660))
    result = monitor.overdue_jobs(now=now)
    assert "backup" in result


def test_just_before_deadline_not_overdue(monitor):
    now = datetime.utcnow()
    monitor.record_seen("backup", at=now - timedelta(seconds=3659))
    result = monitor.overdue_jobs(now=now)
    assert result == []


def test_record_seen_updates_last_seen(monitor):
    t1 = datetime(2024, 1, 1, 12, 0, 0)
    t2 = datetime(2024, 1, 1, 13, 0, 0)
    monitor.record_seen("backup", at=t1)
    monitor.record_seen("backup", at=t2)
    assert monitor.last_seen("backup") == t2


def test_last_seen_returns_none_for_unknown(monitor):
    assert monitor.last_seen("nonexistent") is None


def test_multiple_jobs_only_overdue_reported():
    configs = [
        JobTimeoutConfig("fast", expected_interval_seconds=60, grace_period_seconds=0),
        JobTimeoutConfig("slow", expected_interval_seconds=86400, grace_period_seconds=0),
    ]
    m = JobTimeoutMonitor(configs=configs)
    now = datetime.utcnow()
    m.record_seen("fast", at=now - timedelta(seconds=200))
    m.record_seen("slow", at=now - timedelta(seconds=200))
    result = m.overdue_jobs(now=now)
    assert "fast" in result
    assert "slow" not in result
