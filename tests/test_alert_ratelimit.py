"""Tests for alert_ratelimit and alert_ratelimit_config."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cronwatcher.alert_ratelimit import AlertRateLimiter, RateLimitConfig
from cronwatcher.alert_ratelimit_config import (
    parse_ratelimit_config,
    ratelimited_handler,
    wrap_with_ratelimiter,
)
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(job_name=job, exit_code=1, timestamp="2024-01-01T00:00:00Z")


# --- RateLimitConfig validation ---

def test_invalid_max_alerts_raises():
    with pytest.raises(ValueError):
        RateLimitConfig(max_alerts=0, window_seconds=60.0)


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        RateLimitConfig(max_alerts=3, window_seconds=0)


def test_invalid_per_job_raises():
    with pytest.raises(ValueError):
        RateLimitConfig(max_alerts=3, window_seconds=60.0, per_job={"backup": 0})


def test_limit_for_returns_per_job_override():
    cfg = RateLimitConfig(max_alerts=5, window_seconds=60.0, per_job={"backup": 2})
    assert cfg.limit_for("backup") == 2
    assert cfg.limit_for("other") == 5


# --- AlertRateLimiter behaviour ---

@pytest.fixture
def limiter():
    cfg = RateLimitConfig(max_alerts=3, window_seconds=60.0)
    t = [0.0]
    return AlertRateLimiter(cfg, now_fn=lambda: t[0]), t


def test_new_job_is_allowed(limiter):
    rl, _ = limiter
    assert rl.is_allowed("backup") is True


def test_allow_up_to_max(limiter):
    rl, _ = limiter
    for _ in range(3):
        assert rl.check_and_record("backup") is True
    assert rl.check_and_record("backup") is False


def test_window_expiry_resets_count(limiter):
    rl, t = limiter
    for _ in range(3):
        rl.record("backup")
    t[0] = 61.0  # advance past window
    assert rl.is_allowed("backup") is True


def test_independent_jobs(limiter):
    rl, _ = limiter
    for _ in range(3):
        rl.record("job_a")
    assert rl.is_allowed("job_b") is True


def test_window_boundary_not_yet_expired(limiter):
    """Alerts exactly at the window boundary should still be blocked."""
    rl, t = limiter
    for _ in range(3):
        rl.record("backup")
    t[0] = 60.0  # exactly at window edge, not past it
    assert rl.is_allowed("backup") is False


# --- parse_ratelimit_config ---

def test_no_section_returns_none():
    assert parse_ratelimit_config({}) is None


def test_enabled_false_returns_none():
    assert parse_ratelimit_config({"alert_ratelimit": {"enabled": False}}) is None


def test_valid_config_parsed():
    cfg = parse_ratelimit_config({"alert_ratelimit": {"max_alerts": 2, "window_seconds": 30}})
    assert cfg is not None
    assert cfg.max_alerts == 2
    assert cfg.window_seconds == 30.0


def test_not_a_dict_raises():
    with pytest.raises(ValueError):
        parse_ratelimit_config({"alert_ratelimit": "bad"})


# --- ratelimited_handler integration ---

def test_ratelimited_handler_no_section_passes_through():
    handler = MagicMock()
    wrapped = ratelimited_handler({}, handler)
    p = make_payload()
    wrapped(p)
    handler.assert_called_once_with(p)


def test_ratelimited_handler_blocks_after_limit():
    handler = MagicMock()
    raw = {"alert_ratelimit": {"max_alerts": 2, "window_seconds": 60}}
    wrapped = ratelimited_handler(raw, handler)
    p = make_payload()
    wrapped(p)
    wrapped(p)
    wrapped(p)  # this third call should be blocked
    assert handler.call_count == 2
