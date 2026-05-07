"""Tests for parse_alert_channels config parser."""
import pytest

from cronwatcher.alert_channel_config import parse_alert_channels


def test_no_section_returns_empty_registry():
    registry = parse_alert_channels({})
    assert registry.all() == []


def test_not_a_list_raises():
    with pytest.raises(ValueError, match="must be a list"):
        parse_alert_channels({"alert_channels": {"name": "bad"}})


def test_item_not_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_alert_channels({"alert_channels": ["not-a-dict"]})


def test_missing_name_raises():
    with pytest.raises(ValueError, match="missing required 'name'"):
        parse_alert_channels({"alert_channels": [{"url": "https://example.com"}]})


def test_missing_url_raises():
    with pytest.raises(ValueError, match="missing required 'url'"):
        parse_alert_channels({"alert_channels": [{"name": "ops"}]})


def test_valid_single_channel():
    data = {"alert_channels": [{"name": "ops", "url": "https://hooks.example.com/ops"}]}
    registry = parse_alert_channels(data)
    assert len(registry.all()) == 1
    ch = registry.get("ops")
    assert ch is not None
    assert ch.webhook_config.url == "https://hooks.example.com/ops"


def test_tags_parsed_correctly():
    data = {
        "alert_channels": [
            {"name": "pagerduty", "url": "https://pd.example.com", "tags": ["critical", "ops"]}
        ]
    }
    registry = parse_alert_channels(data)
    ch = registry.get("pagerduty")
    assert "critical" in ch.tags
    assert "ops" in ch.tags


def test_headers_parsed_correctly():
    data = {
        "alert_channels": [
            {"name": "secure", "url": "https://secure.example.com", "headers": {"Authorization": "Bearer xyz"}}
        ]
    }
    registry = parse_alert_channels(data)
    ch = registry.get("secure")
    assert ch.webhook_config.headers["Authorization"] == "Bearer xyz"


def test_multiple_channels_registered():
    data = {
        "alert_channels": [
            {"name": "a", "url": "https://a.example.com"},
            {"name": "b", "url": "https://b.example.com", "tags": ["slack"]},
        ]
    }
    registry = parse_alert_channels(data)
    assert len(registry.all()) == 2
    assert registry.get("a") is not None
    assert registry.get("b") is not None
