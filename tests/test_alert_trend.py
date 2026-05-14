"""Tests for alert trend detection."""

import pytest
from unittest.mock import MagicMock

from cronwatcher.alert_trend import AlertTrend, TrendConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        timestamp="2024-01-01T00:00:00Z",
        hostname="host1",
        extra={},
    )


def test_invalid_window_size_raises():
    with pytest.raises(ValueError, match="window_size"):
        TrendConfig(window_size=1, min_samples=2, spike_ratio=2.0)


def test_invalid_min_samples_raises():
    with pytest.raises(ValueError, match="min_samples"):
        TrendConfig(window_size=10, min_samples=0, spike_ratio=2.0)


def test_spike_ratio_must_exceed_one():
    with pytest.raises(ValueError, match="spike_ratio"):
        TrendConfig(window_size=10, min_samples=2, spike_ratio=1.0)


@pytest.fixture
def cfg():
    return TrendConfig(window_size=20, min_samples=4, spike_ratio=2.0)


@pytest.fixture
def callback():
    return MagicMock()


@pytest.fixture
def trend(cfg, callback):
    return AlertTrend(cfg, callback)


def test_no_trend_below_min_samples(trend, callback):
    p = make_payload()
    for i in range(3):
        trend.record(p, now=float(i))
    callback.assert_not_called()


def test_trend_not_triggered_when_rate_stable(trend, callback):
    p = make_payload()
    # uniform spacing — no spike
    for i in range(10):
        trend.record(p, now=float(i * 10))
    callback.assert_not_called()


def test_trend_triggered_on_spike(trend, callback):
    p = make_payload()
    # baseline: 4 events spread over 40s
    for i in range(4):
        trend.record(p, now=float(i * 10))
    # recent: 6 events crammed into 1s (massive spike)
    base = 40.0
    for i in range(6):
        trend.record(p, now=base + i * 0.1)
    callback.assert_called()
    _, ratio = callback.call_args[0]
    assert ratio >= 2.0


def test_trend_callback_receives_payload(trend, callback):
    p = make_payload("myjob")
    base = 0.0
    for i in range(4):
        trend.record(p, now=base + i * 10)
    for i in range(6):
        trend.record(p, now=40.0 + i * 0.05)
    assert callback.called
    received_payload, _ = callback.call_args[0]
    assert received_payload.job_name == "myjob"


def test_window_evicts_old_samples():
    cfg = TrendConfig(window_size=4, min_samples=2, spike_ratio=2.0)
    cb = MagicMock()
    t = AlertTrend(cfg, cb)
    p = make_payload()
    for i in range(10):
        t.record(p, now=float(i))
    bucket = t._buckets["backup"]
    assert len(bucket.timestamps) <= cfg.window_size


def test_unknown_job_uses_unknown_key(trend):
    p = WebhookPayload(
        job_name=None, exit_code=1, timestamp="t", hostname="h", extra={}
    )
    trend.record(p, now=1.0)
    assert "unknown" in trend._buckets
