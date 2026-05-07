"""Tests for parse_escalation_policy."""
import pytest

from cronwatcher.escalation_config import parse_escalation_policy


def test_no_section_returns_none():
    assert parse_escalation_policy({}) is None


def test_valid_minimal_config():
    cfg = {"escalation": {"webhook_url": "https://hooks.example.com/esc"}}
    policy = parse_escalation_policy(cfg)
    assert policy is not None
    assert policy.webhook_url == "https://hooks.example.com/esc"
    assert policy.threshold == 3  # default
    assert policy.headers == {}


def test_custom_threshold():
    cfg = {"escalation": {"webhook_url": "https://x", "threshold": 5}}
    policy = parse_escalation_policy(cfg)
    assert policy.threshold == 5


def test_custom_headers():
    cfg = {
        "escalation": {
            "webhook_url": "https://x",
            "headers": {"Authorization": "Bearer tok"},
        }
    }
    policy = parse_escalation_policy(cfg)
    assert policy.headers == {"Authorization": "Bearer tok"}


def test_missing_webhook_url_raises():
    with pytest.raises(ValueError, match="webhook_url"):
        parse_escalation_policy({"escalation": {"threshold": 2}})


def test_invalid_threshold_raises():
    cfg = {"escalation": {"webhook_url": "https://x", "threshold": 0}}
    with pytest.raises(ValueError, match="threshold"):
        parse_escalation_policy(cfg)


def test_non_dict_section_raises():
    with pytest.raises(ValueError, match="JSON object"):
        parse_escalation_policy({"escalation": "bad"})


def test_non_dict_headers_raises():
    cfg = {"escalation": {"webhook_url": "https://x", "headers": ["bad"]}}
    with pytest.raises(ValueError, match="headers"):
        parse_escalation_policy(cfg)


def test_header_values_coerced_to_str():
    cfg = {
        "escalation": {
            "webhook_url": "https://x",
            "headers": {"X-Retry": 3},
        }
    }
    policy = parse_escalation_policy(cfg)
    assert policy.headers["X-Retry"] == "3"
