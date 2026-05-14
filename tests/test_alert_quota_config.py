"""Tests for alert_quota_config parsing and handler wrapping."""

from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_quota_config import parse_quota_config, quota_handler, wrap_with_quota
from cronwatcher.alert_quota import AlertQuota, QuotaConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "myjob") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=2,
        timestamp="2024-06-01T12:00:00",
        hostname="testhost",
        raw_line="cron error",
    )


def test_no_section_returns_none():
    assert parse_quota_config({}) is None


def test_enabled_false_returns_none():
    assert parse_quota_config({"alert_quota": {"enabled": False}}) is None


def test_not_a_dict_raises():
    with pytest.raises((ValueError, AttributeError)):
        parse_quota_config({"alert_quota": "bad"})


def test_defaults_applied():
    quota = parse_quota_config({"alert_quota": {"enabled": True}})
    assert quota is not None
    assert isinstance(quota, AlertQuota)


def test_custom_values_parsed():
    raw = {
        "alert_quota": {
            "max_per_job": 5,
            "max_global": 20,
            "window_seconds": 1800,
        }
    }
    quota = parse_quota_config(raw)
    assert quota is not None
    assert quota._cfg.max_per_job == 5
    assert quota._cfg.max_global == 20
    assert quota._cfg.window_seconds == 1800.0


def test_wrap_with_quota_calls_handler_when_allowed():
    cfg = QuotaConfig(max_per_job=5, max_global=10, window_seconds=60.0)
    quota = AlertQuota(cfg)
    handler = MagicMock()
    wrapped = wrap_with_quota(quota, handler)
    p = make_payload()
    wrapped(p)
    handler.assert_called_once_with(p)


def test_wrap_with_quota_blocks_handler_when_exceeded():
    cfg = QuotaConfig(max_per_job=1, max_global=10, window_seconds=60.0)
    quota = AlertQuota(cfg)
    handler = MagicMock()
    wrapped = wrap_with_quota(quota, handler)
    p = make_payload()
    wrapped(p)  # allowed
    wrapped(p)  # blocked
    assert handler.call_count == 1


def test_quota_handler_no_section_returns_original():
    handler = MagicMock()
    result = quota_handler({}, handler)
    assert result is handler


def test_quota_handler_with_section_wraps():
    handler = MagicMock()
    raw = {"alert_quota": {"max_per_job": 2, "max_global": 5, "window_seconds": 60}}
    result = quota_handler(raw, handler)
    assert result is not handler
