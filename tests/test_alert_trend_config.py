"""Tests for alert trend config parsing."""

import pytest
from unittest.mock import MagicMock

from cronwatcher.alert_trend_config import parse_trend_config, trend_handler, wrap_with_trend
from cronwatcher.alert_trend import AlertTrend, TrendConfig
from cronwatcher.webhook import WebhookPayload


def make_payload() -> WebhookPayload:
    return WebhookPayload(
        job_name="job1",
        exit_code=1,
        timestamp="2024-01-01T00:00:00Z",
        hostname="host",
        extra={},
    )


def test_no_section_returns_none():
    assert parse_trend_config({}) is None


def test_enabled_false_returns_none():
    assert parse_trend_config({"alert_trend": {"enabled": False}}) is None


def test_defaults_applied():
    cfg = parse_trend_config({"alert_trend": {}})
    assert cfg is not None
    assert cfg.window_size == 20
    assert cfg.min_samples == 6
    assert cfg.spike_ratio == 2.0


def test_custom_values():
    cfg = parse_trend_config({
        "alert_trend": {
            "window_size": 30,
            "min_samples": 8,
            "spike_ratio": 3.5,
        }
    })
    assert cfg.window_size == 30
    assert cfg.min_samples == 8
    assert cfg.spike_ratio == 3.5


def test_invalid_spike_ratio_raises():
    with pytest.raises(ValueError):
        parse_trend_config({"alert_trend": {"spike_ratio": 0.5}})


def test_wrap_with_trend_calls_handler():
    cfg = TrendConfig(window_size=10, min_samples=2, spike_ratio=2.0)
    on_trend = MagicMock()
    trend = AlertTrend(cfg, on_trend)
    handler = MagicMock()
    wrapped = wrap_with_trend(trend, handler)
    p = make_payload()
    wrapped(p)
    handler.assert_called_once_with(p)


def test_trend_handler_no_section_returns_original():
    handler = MagicMock()
    on_trend = MagicMock()
    result = trend_handler({}, handler, on_trend)
    assert result is handler


def test_trend_handler_with_section_wraps():
    handler = MagicMock()
    on_trend = MagicMock()
    raw = {"alert_trend": {"window_size": 10, "min_samples": 2, "spike_ratio": 2.0}}
    result = trend_handler(raw, handler, on_trend)
    assert result is not handler
    p = make_payload()
    result(p)
    handler.assert_called_once_with(p)
