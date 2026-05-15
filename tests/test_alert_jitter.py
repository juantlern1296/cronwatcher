"""Tests for cronwatcher.alert_jitter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_jitter import AlertJitter, JitterConfig, wrap_with_jitter
from cronwatcher.webhook import WebhookPayload


def make_payload(job_name: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job_name,
        message="failed",
        hostname="host1",
        timestamp="2024-01-01T00:00:00Z",
        extra={"job_name": job_name},
    )


def test_invalid_min_delay_raises():
    with pytest.raises(ValueError, match="min_delay"):
        JitterConfig(min_delay=-1.0, max_delay=2.0)


def test_max_less_than_min_raises():
    with pytest.raises(ValueError, match="max_delay"):
        JitterConfig(min_delay=3.0, max_delay=1.0)


def test_per_job_negative_min_raises():
    with pytest.raises(ValueError, match="per_job min_delay"):
        JitterConfig(min_delay=0.0, max_delay=1.0, per_job={"backup": (-1.0, 2.0)})


def test_per_job_max_less_than_min_raises():
    with pytest.raises(ValueError, match="per_job max_delay"):
        JitterConfig(min_delay=0.0, max_delay=1.0, per_job={"backup": (3.0, 1.0)})


def test_valid_config_created():
    cfg = JitterConfig(min_delay=0.5, max_delay=2.0)
    assert cfg.min_delay == 0.5
    assert cfg.max_delay == 2.0


def test_range_for_unknown_job_returns_global():
    cfg = JitterConfig(min_delay=1.0, max_delay=3.0)
    assert cfg.range_for("unknown") == (1.0, 3.0)


def test_range_for_none_returns_global():
    cfg = JitterConfig(min_delay=0.5, max_delay=1.5)
    assert cfg.range_for(None) == (0.5, 1.5)


def test_range_for_per_job_override():
    cfg = JitterConfig(min_delay=1.0, max_delay=5.0, per_job={"backup": (0.1, 0.5)})
    assert cfg.range_for("backup") == (0.1, 0.5)


def test_dispatch_sleeps_and_calls_handler():
    cfg = JitterConfig(min_delay=1.0, max_delay=2.0)
    handler = MagicMock()
    slept = []
    jitter = AlertJitter(cfg, handler, _sleep=slept.append, _random=lambda lo, hi: 1.5)
    payload = make_payload()
    jitter.dispatch(payload)
    assert slept == [1.5]
    handler.assert_called_once_with(payload)


def test_dispatch_zero_delay_skips_sleep():
    cfg = JitterConfig(min_delay=0.0, max_delay=0.0)
    handler = MagicMock()
    slept = []
    jitter = AlertJitter(cfg, handler, _sleep=slept.append, _random=lambda lo, hi: 0.0)
    jitter.dispatch(make_payload())
    assert slept == []
    handler.assert_called_once()


def test_dispatch_uses_per_job_range():
    cfg = JitterConfig(min_delay=5.0, max_delay=10.0, per_job={"backup": (0.1, 0.2)})
    recorded = []
    jitter = AlertJitter(
        cfg,
        MagicMock(),
        _sleep=lambda d: None,
        _random=lambda lo, hi: recorded.append((lo, hi)) or lo,
    )
    jitter.dispatch(make_payload("backup"))
    assert recorded == [(0.1, 0.2)]


def test_wrap_with_jitter_returns_alertjitter():
    cfg = JitterConfig(min_delay=0.0, max_delay=0.5)
    handler = MagicMock()
    result = wrap_with_jitter(cfg, handler, _sleep=lambda d: None)
    assert isinstance(result, AlertJitter)
