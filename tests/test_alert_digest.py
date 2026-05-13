"""Tests for AlertDigest and parse_alert_digest."""

from __future__ import annotations

import time
from typing import List
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_digest import AlertDigest, DigestConfig
from cronwatcher.alert_digest_config import parse_alert_digest
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host",
        raw_line="cron error",
    )


@pytest.fixture
def callback():
    return MagicMock()


@pytest.fixture
def cfg():
    return DigestConfig(interval_seconds=60, min_alerts=2)


@pytest.fixture
def digest(cfg, callback):
    return AlertDigest(cfg, on_flush=callback)


def test_invalid_interval_raises():
    with pytest.raises(ValueError, match="interval_seconds"):
        AlertDigest(DigestConfig(interval_seconds=0, min_alerts=1), on_flush=lambda j, p: None)


def test_invalid_min_alerts_raises():
    with pytest.raises(ValueError, match="min_alerts"):
        AlertDigest(DigestConfig(interval_seconds=10, min_alerts=0), on_flush=lambda j, p: None)


def test_flush_calls_callback_when_min_met(digest, callback):
    digest.add(make_payload("backup"))
    digest.add(make_payload("backup"))
    digest.flush()
    callback.assert_called_once()
    job, payloads = callback.call_args[0]
    assert job == "backup"
    assert len(payloads) == 2


def test_flush_skips_when_below_min(digest, callback):
    digest.add(make_payload("backup"))
    digest.flush()
    callback.assert_not_called()


def test_flush_clears_buckets(digest, callback):
    digest.add(make_payload("backup"))
    digest.add(make_payload("backup"))
    digest.flush()
    digest.flush()  # second flush should have nothing
    assert callback.call_count == 1


def test_multiple_jobs_flushed_separately(digest, callback):
    for _ in range(2):
        digest.add(make_payload("backup"))
        digest.add(make_payload("cleanup"))
    digest.flush()
    assert callback.call_count == 2
    jobs_notified = {call[0][0] for call in callback.call_args_list}
    assert jobs_notified == {"backup", "cleanup"}


def test_start_and_stop_do_not_raise(digest):
    digest.start()
    digest.stop()


# --- parse_alert_digest ---

def test_no_section_returns_none():
    assert parse_alert_digest({}) is None


def test_enabled_false_returns_none():
    assert parse_alert_digest({"alert_digest": {"enabled": False}}) is None


def test_defaults_applied():
    result = parse_alert_digest({"alert_digest": {"enabled": True}})
    assert result is not None
    assert result.interval_seconds == 300.0
    assert result.min_alerts == 2


def test_custom_values():
    result = parse_alert_digest({"alert_digest": {"enabled": True, "interval_seconds": 120, "min_alerts": 5}})
    assert result.interval_seconds == 120.0
    assert result.min_alerts == 5


def test_invalid_interval_in_config_raises():
    """parse_alert_digest should propagate ValueError for bad interval_seconds."""
    with pytest.raises(ValueError, match="interval_seconds"):
        parse_alert_digest({"alert_digest": {"enabled": True, "interval_seconds": 0}})


def test_invalid_min_alerts_in_config_raises():
    """parse_alert_digest should propagate ValueError for bad min_alerts."""
    with pytest.raises(ValueError, match="min_alerts"):
        parse_alert_digest({"alert_digest": {"enabled": True, "min_alerts": 0}})
