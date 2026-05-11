"""Tests for alert_dedup module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alert_dedup import AlertDedup, DedupConfig, parse_alert_dedup
from cronwatcher.alert_dedup_config import wrap_with_dedup
from cronwatcher.webhook import WebhookPayload


def make_payload(job="backup", exit_code="1", hostname="host1") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=exit_code,
        hostname=hostname,
        timestamp="2024-01-01T00:00:00",
        message="failed",
    )


@pytest.fixture
def dedup() -> AlertDedup:
    return AlertDedup(DedupConfig(window_seconds=60.0))


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        DedupConfig(window_seconds=0)


def test_invalid_negative_window_raises():
    with pytest.raises(ValueError):
        DedupConfig(window_seconds=-5.0)


def test_new_payload_is_not_duplicate(dedup):
    p = make_payload()
    assert dedup.is_duplicate(p) is False


def test_payload_is_duplicate_after_record(dedup):
    p = make_payload()
    dedup.record(p)
    assert dedup.is_duplicate(p) is True


def test_different_job_not_duplicate(dedup):
    p1 = make_payload(job="backup")
    p2 = make_payload(job="cleanup")
    dedup.record(p1)
    assert dedup.is_duplicate(p2) is False


def test_expired_entry_not_duplicate():
    dedup = AlertDedup(DedupConfig(window_seconds=1.0))
    p = make_payload()
    with patch("cronwatcher.alert_dedup.time.monotonic", return_value=1000.0):
        dedup.record(p)
    with patch("cronwatcher.alert_dedup.time.monotonic", return_value=1002.0):
        assert dedup.is_duplicate(p) is False


def test_size_increases_on_record(dedup):
    dedup.record(make_payload(job="a"))
    dedup.record(make_payload(job="b"))
    assert dedup.size() == 2


def test_wrap_with_dedup_blocks_duplicate():
    dedup = AlertDedup(DedupConfig(window_seconds=60.0))
    handler = MagicMock()
    wrapped = wrap_with_dedup(dedup, handler)
    p = make_payload()
    wrapped(p)
    wrapped(p)
    handler.assert_called_once()


def test_wrap_with_dedup_allows_different_payloads():
    dedup = AlertDedup(DedupConfig(window_seconds=60.0))
    handler = MagicMock()
    wrapped = wrap_with_dedup(dedup, handler)
    wrapped(make_payload(job="a"))
    wrapped(make_payload(job="b"))
    assert handler.call_count == 2


def test_parse_alert_dedup_none_when_absent():
    assert parse_alert_dedup({}) is None


def test_parse_alert_dedup_returns_instance():
    cfg = {"alert_dedup": {"window_seconds": 120}}
    result = parse_alert_dedup(cfg)
    assert isinstance(result, AlertDedup)


def test_parse_alert_dedup_invalid_type_raises():
    with pytest.raises(ValueError):
        parse_alert_dedup({"alert_dedup": "bad"})
