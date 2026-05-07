"""Tests for AlertChannel and AlertChannelRegistry."""
from unittest.mock import patch, MagicMock
import pytest

from cronwatcher.config import WebhookConfig
from cronwatcher.alert_channel import AlertChannel, AlertChannelRegistry, ChannelResult
from cronwatcher.webhook import WebhookPayload


@pytest.fixture
def webhook_cfg():
    return WebhookConfig(url="https://hooks.example.com/test", headers={})


@pytest.fixture
def sample_payload():
    return WebhookPayload(
        job_name="backup",
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        raw_line="Jan  1 00:00:00 CRON[123]: backup failed",
        extra_fields={},
    )


@pytest.fixture
def registry(webhook_cfg):
    reg = AlertChannelRegistry()
    reg.register(AlertChannel(name="ops", webhook_config=webhook_cfg, tags=["slack"]))
    reg.register(AlertChannel(name="pagerduty", webhook_config=webhook_cfg, tags=["critical", "slack"]))
    return reg


def test_register_empty_name_raises(webhook_cfg):
    reg = AlertChannelRegistry()
    with pytest.raises(ValueError, match="name must not be empty"):
        reg.register(AlertChannel(name="", webhook_config=webhook_cfg))


def test_get_returns_channel(registry):
    ch = registry.get("ops")
    assert ch is not None
    assert ch.name == "ops"


def test_get_unknown_returns_none(registry):
    assert registry.get("nonexistent") is None


def test_all_returns_all_channels(registry):
    assert len(registry.all()) == 2


def test_by_tag_filters_correctly(registry):
    critical = registry.by_tag("critical")
    assert len(critical) == 1
    assert critical[0].name == "pagerduty"


def test_by_tag_multiple_matches(registry):
    slack_channels = registry.by_tag("slack")
    assert len(slack_channels) == 2


def test_by_tag_no_match_returns_empty(registry):
    assert registry.by_tag("teams") == []


def test_send_all_calls_each_channel(registry, sample_payload):
    with patch("cronwatcher.alert_channel.send_webhook", return_value=(True, None)) as mock_send:
        results = registry.send_all(sample_payload)
    assert len(results) == 2
    assert mock_send.call_count == 2
    assert all(r.success for r in results)


def test_send_by_tag_only_matching(registry, sample_payload):
    with patch("cronwatcher.alert_channel.send_webhook", return_value=(True, None)) as mock_send:
        results = registry.send_by_tag("critical", sample_payload)
    assert len(results) == 1
    assert results[0].channel_name == "pagerduty"
    assert mock_send.call_count == 1


def test_channel_send_failure_captured(webhook_cfg, sample_payload):
    ch = AlertChannel(name="flaky", webhook_config=webhook_cfg)
    with patch("cronwatcher.alert_channel.send_webhook", return_value=(False, "timeout")):
        result = ch.send(sample_payload)
    assert not result.success
    assert result.error == "timeout"
    assert result.channel_name == "flaky"
