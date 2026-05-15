"""Tests for alert_retention module."""

import time
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_retention import AlertRetention, RetentionConfig
from cronwatcher.alert_retention_config import parse_retention_config, retention_handler
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        timestamp="2024-01-01T00:00:00Z",
        hostname="host1",
        raw_line=f"{job} failed",
    )


# --- RetentionConfig validation ---

def test_invalid_max_age_raises():
    with pytest.raises(ValueError, match="max_age_seconds"):
        RetentionConfig(max_age_seconds=0)


def test_negative_max_age_raises():
    with pytest.raises(ValueError, match="max_age_seconds"):
        RetentionConfig(max_age_seconds=-10)


def test_invalid_max_records_raises():
    with pytest.raises(ValueError, match="max_records"):
        RetentionConfig(max_age_seconds=60, max_records=0)


# --- AlertRetention behaviour ---

@pytest.fixture
def handler():
    return MagicMock()


@pytest.fixture
def retention(handler):
    cfg = RetentionConfig(max_age_seconds=60, max_records=100)
    return AlertRetention(config=cfg, handler=handler)


def test_handle_calls_downstream(retention, handler):
    p = make_payload()
    retention.handle(p)
    handler.assert_called_once_with(p)


def test_record_count_increments(retention):
    retention.handle(make_payload("job1"))
    retention.handle(make_payload("job2"))
    assert retention.record_count() == 2


def test_recent_returns_payloads(retention):
    p1, p2 = make_payload("j1"), make_payload("j2")
    retention.handle(p1)
    retention.handle(p2)
    recent = retention.recent()
    assert p1 in recent
    assert p2 in recent


def test_max_records_cap(handler):
    cfg = RetentionConfig(max_age_seconds=60, max_records=3)
    r = AlertRetention(config=cfg, handler=handler)
    for i in range(5):
        r.handle(make_payload(f"job{i}"))
    assert r.record_count() == 3


def test_eviction_removes_old_records(handler):
    cfg = RetentionConfig(max_age_seconds=1, max_records=100)
    r = AlertRetention(config=cfg, handler=handler)
    now = time.monotonic()
    r._records.append(__import__('cronwatcher.alert_retention', fromlist=['_RetentionRecord'])._RetentionRecord(
        payload=make_payload(), recorded_at=now - 120
    ))
    assert r.record_count() == 0  # eviction triggered by record_count


# --- parse_retention_config ---

def test_no_section_returns_none():
    assert parse_retention_config({}) is None


def test_enabled_false_returns_none():
    assert parse_retention_config({"alert_retention": {"enabled": False}}) is None


def test_not_a_dict_raises():
    with pytest.raises(ValueError):
        parse_retention_config({"alert_retention": "bad"})


def test_defaults_applied():
    cfg = parse_retention_config({"alert_retention": {}})
    assert cfg is not None
    assert cfg.max_age_seconds == 3600
    assert cfg.max_records == 1000


def test_custom_values():
    cfg = parse_retention_config({"alert_retention": {"max_age_seconds": 120, "max_records": 50}})
    assert cfg.max_age_seconds == 120
    assert cfg.max_records == 50


# --- retention_handler ---

def test_retention_handler_no_section_returns_original():
    h = MagicMock()
    result = retention_handler({}, h)
    assert result is h


def test_retention_handler_with_section_wraps():
    h = MagicMock()
    result = retention_handler({"alert_retention": {"max_age_seconds": 300}}, h)
    assert result is not h
    result(make_payload())
    h.assert_called_once()
