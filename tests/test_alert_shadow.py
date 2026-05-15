"""Tests for alert shadow mode."""
from unittest.mock import MagicMock, patch
import pytest

from cronwatcher.alert_shadow import AlertShadow, ShadowConfig, wrap_with_shadow
from cronwatcher.config import WebhookConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        raw_line="error",
    )


@pytest.fixture
def webhook_cfg():
    return WebhookConfig(url="http://shadow.example.com/hook", headers={})


@pytest.fixture
def shadow(webhook_cfg):
    return AlertShadow(config=ShadowConfig(webhook=webhook_cfg))


def test_dispatch_calls_send_webhook(shadow):
    with patch("cronwatcher.alert_shadow.send_webhook") as mock_send:
        result = shadow.dispatch(make_payload())
    assert result is True
    mock_send.assert_called_once()


def test_dispatch_increments_count(shadow):
    with patch("cronwatcher.alert_shadow.send_webhook"):
        shadow.dispatch(make_payload())
        shadow.dispatch(make_payload())
    assert shadow.dispatch_count() == 2


def test_dispatch_disabled_returns_false(webhook_cfg):
    s = AlertShadow(config=ShadowConfig(webhook=webhook_cfg, enabled=False))
    with patch("cronwatcher.alert_shadow.send_webhook") as mock_send:
        result = s.dispatch(make_payload())
    assert result is False
    mock_send.assert_not_called()


def test_dispatch_exception_returns_false(shadow):
    with patch("cronwatcher.alert_shadow.send_webhook", side_effect=RuntimeError("boom")):
        result = shadow.dispatch(make_payload())
    assert result is False
    assert shadow.dispatch_count() == 0


def test_wrap_with_shadow_calls_both(shadow):
    primary = MagicMock()
    wrapped = wrap_with_shadow(primary, shadow)
    payload = make_payload()
    with patch("cronwatcher.alert_shadow.send_webhook"):
        wrapped(payload)
    primary.assert_called_once_with(payload)
    assert shadow.dispatch_count() == 1


def test_wrap_with_shadow_primary_still_called_on_shadow_error(shadow):
    primary = MagicMock()
    wrapped = wrap_with_shadow(primary, shadow)
    payload = make_payload()
    with patch("cronwatcher.alert_shadow.send_webhook", side_effect=Exception("net")):
        wrapped(payload)
    primary.assert_called_once_with(payload)


def test_dispatch_count_starts_at_zero(shadow):
    assert shadow.dispatch_count() == 0
