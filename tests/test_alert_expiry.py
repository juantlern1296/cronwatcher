"""Tests for cronwatcher.alert_expiry."""

from __future__ import annotations

import pytest

from cronwatcher.alert_expiry import AlertExpiry, ExpiryConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job_name: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job_name,
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        raw_line="Jan  1 00:00:00 host1 CRON[1]: backup failed",
    )


def test_invalid_window_raises() -> None:
    with pytest.raises(ValueError, match="window_seconds must be positive"):
        ExpiryConfig(window_seconds=0)


def test_negative_window_raises() -> None:
    with pytest.raises(ValueError):
        ExpiryConfig(window_seconds=-5)


@pytest.fixture()
def expiry() -> AlertExpiry:
    return AlertExpiry(ExpiryConfig(window_seconds=60))


def test_unknown_job_is_not_expired(expiry: AlertExpiry) -> None:
    assert expiry.is_expired("ghost") is False


def test_recently_recorded_job_is_not_expired(expiry: AlertExpiry) -> None:
    p = make_payload("backup")
    expiry.record(p, now=1000.0)
    assert expiry.is_expired("backup", now=1050.0) is False


def test_job_expires_after_window(expiry: AlertExpiry) -> None:
    p = make_payload("backup")
    expiry.record(p, now=1000.0)
    assert expiry.is_expired("backup", now=1061.0) is True


def test_job_exactly_at_boundary_is_not_expired(expiry: AlertExpiry) -> None:
    p = make_payload("backup")
    expiry.record(p, now=1000.0)
    # strictly greater-than, so at exactly 60 s it's not yet expired
    assert expiry.is_expired("backup", now=1060.0) is False


def test_sweep_removes_stale_records(expiry: AlertExpiry) -> None:
    expiry.record(make_payload("backup"), now=1000.0)
    expiry.record(make_payload("sync"), now=1000.0)
    expired = expiry.sweep(now=1070.0)
    assert set(expired) == {"backup", "sync"}
    assert expiry.known_jobs() == []


def test_sweep_keeps_fresh_records(expiry: AlertExpiry) -> None:
    expiry.record(make_payload("backup"), now=1000.0)
    expiry.record(make_payload("sync"), now=1050.0)
    expired = expiry.sweep(now=1065.0)  # only backup is older than 60 s
    assert expired == ["backup"]
    assert expiry.known_jobs() == ["sync"]


def test_sweep_calls_on_expire_callback() -> None:
    called: list[str] = []
    cfg = ExpiryConfig(window_seconds=30, on_expire=called.append)
    ex = AlertExpiry(cfg)
    ex.record(make_payload("cleanup"), now=0.0)
    ex.sweep(now=31.0)
    assert called == ["cleanup"]


def test_sweep_empty_store_returns_empty(expiry: AlertExpiry) -> None:
    assert expiry.sweep(now=9999.0) == []


def test_record_updates_last_seen(expiry: AlertExpiry) -> None:
    p = make_payload("backup")
    expiry.record(p, now=1000.0)
    expiry.record(p, now=1100.0)  # refresh
    assert expiry.is_expired("backup", now=1150.0) is False
    assert expiry.is_expired("backup", now=1165.0) is True
