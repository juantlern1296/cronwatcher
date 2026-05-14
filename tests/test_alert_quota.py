"""Tests for alert quota enforcement."""

import time
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_quota import AlertQuota, QuotaConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        raw_line=f"CRON error for {job}",
    )


@pytest.fixture
def quota():
    cfg = QuotaConfig(max_per_job=3, max_global=5, window_seconds=60.0)
    return AlertQuota(cfg)


def test_invalid_max_per_job_raises():
    with pytest.raises(ValueError, match="max_per_job"):
        QuotaConfig(max_per_job=0, max_global=10, window_seconds=60.0)


def test_invalid_max_global_raises():
    with pytest.raises(ValueError, match="max_global"):
        QuotaConfig(max_per_job=5, max_global=0, window_seconds=60.0)


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        QuotaConfig(max_per_job=5, max_global=10, window_seconds=0.0)


def test_new_job_is_allowed(quota):
    assert quota.is_allowed(make_payload("backup")) is True


def test_allow_up_to_max_per_job(quota):
    p = make_payload("backup")
    for _ in range(3):
        assert quota.check_and_record(p) is True
    assert quota.check_and_record(p) is False


def test_global_limit_across_jobs(quota):
    jobs = ["job1", "job2", "job3", "job4", "job5"]
    for job in jobs:
        assert quota.check_and_record(make_payload(job)) is True
    # global exhausted
    assert quota.check_and_record(make_payload("job6")) is False


def test_per_job_independent_of_other_jobs(quota):
    # exhaust job1 quota
    for _ in range(3):
        quota.check_and_record(make_payload("job1"))
    # job2 should still be allowed (global not exhausted yet)
    assert quota.is_allowed(make_payload("job2")) is True


def test_window_reset_allows_again():
    tick = [0.0]
    now = lambda: tick[0]
    cfg = QuotaConfig(max_per_job=2, max_global=10, window_seconds=30.0)
    q = AlertQuota(cfg, now=now)
    p = make_payload("job")
    q.check_and_record(p)
    q.check_and_record(p)
    assert q.is_allowed(p) is False
    tick[0] = 31.0
    assert q.is_allowed(p) is True


def test_unknown_job_name_uses_fallback():
    cfg = QuotaConfig(max_per_job=2, max_global=10, window_seconds=60.0)
    q = AlertQuota(cfg)
    p = WebhookPayload(
        job_name=None,
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host",
        raw_line="error",
    )
    assert q.check_and_record(p) is True
