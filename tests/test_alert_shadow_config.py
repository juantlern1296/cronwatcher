"""Tests for shadow config parsing."""
import pytest

from cronwatcher.alert_shadow_config import parse_shadow_config


def test_no_section_returns_none():
    assert parse_shadow_config({}) is None


def test_enabled_false_returns_none():
    cfg = {"shadow": {"enabled": False, "webhook_url": "http://x.com"}}
    assert parse_shadow_config(cfg) is None


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_shadow_config({"shadow": "http://x.com"})


def test_missing_webhook_url_raises():
    with pytest.raises(ValueError, match="webhook_url is required"):
        parse_shadow_config({"shadow": {"enabled": True}})


def test_valid_config_returns_shadow_config():
    cfg = {"shadow": {"webhook_url": "http://shadow.example.com/hook"}}
    result = parse_shadow_config(cfg)
    assert result is not None
    assert result.webhook.url == "http://shadow.example.com/hook"
    assert result.enabled is True


def test_custom_headers_parsed():
    cfg = {
        "shadow": {
            "webhook_url": "http://shadow.example.com/hook",
            "headers": {"X-Token": "abc"},
        }
    }
    result = parse_shadow_config(cfg)
    assert result.webhook.headers == {"X-Token": "abc"}


def test_invalid_headers_raises():
    cfg = {
        "shadow": {
            "webhook_url": "http://shadow.example.com/hook",
            "headers": "bad",
        }
    }
    with pytest.raises(ValueError, match="headers must be a dict"):
        parse_shadow_config(cfg)


def test_enabled_true_explicit():
    cfg = {"shadow": {"enabled": True, "webhook_url": "http://x.com/h"}}
    result = parse_shadow_config(cfg)
    assert result is not None
    assert result.enabled is True
