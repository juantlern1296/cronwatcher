"""Tests for cronwatcher.metrics module."""

import pytest
from datetime import datetime
from cronwatcher.metrics import MetricsStore, JobMetrics


@pytest.fixture
def store():
    return MetricsStore()


def test_record_failure_creates_entry(store):
    store.record_failure("backup")
    m = store.get("backup")
    assert m is not None
    assert m.total_failures == 1
    assert m.last_failure_at is not None


def test_record_failure_increments(store):
    store.record_failure("backup")
    store.record_failure("backup")
    assert store.get("backup").total_failures == 2


def test_record_alert_creates_entry(store):
    store.record_alert("cleanup")
    m = store.get("cleanup")
    assert m is not None
    assert m.total_alerts_sent == 1
    assert m.last_alert_at is not None


def test_record_alert_increments(store):
    store.record_alert("cleanup")
    store.record_alert("cleanup")
    assert store.get("cleanup").total_alerts_sent == 2


def test_get_unknown_job_returns_none(store):
    assert store.get("nonexistent") is None


def test_all_jobs_empty(store):
    assert store.all_jobs() == []


def test_all_jobs_returns_all(store):
    store.record_failure("job_a")
    store.record_failure("job_b")
    names = {m.job_name for m in store.all_jobs()}
    assert names == {"job_a", "job_b"}


def test_summary_structure(store):
    store.record_failure("job_a")
    store.record_alert("job_a")
    summary = store.summary()
    assert "started_at" in summary
    assert len(summary["jobs"]) == 1
    job = summary["jobs"][0]
    assert job["job_name"] == "job_a"
    assert job["total_failures"] == 1
    assert job["total_alerts_sent"] == 1
    assert job["last_failure_at"] is not None
    assert job["last_alert_at"] is not None


def test_summary_no_alert_sent(store):
    store.record_failure("job_b")
    summary = store.summary()
    job = summary["jobs"][0]
    assert job["last_alert_at"] is None
    assert job["total_alerts_sent"] == 0
