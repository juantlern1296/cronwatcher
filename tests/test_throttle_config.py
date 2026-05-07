"""Tests for cronwatcher.throttle_config."""

import pytest

from cronwatcher.throttle import AlertThrottle
from cronwatcher.throttle_config import parse_throttle_config


def test_no_section_returns_none():
    assert parse_throttle_config({}) is None


def test_valid_minimal_config():
    result = parse_throttle_config({"throttle": {"max_alerts": 2, "window_seconds": 120}})
    assert isinstance(result, AlertThrottle)


def test_defaults_applied_when_keys_absent():
    result = parse_throttle_config({"throttle": {}})
    assert isinstance(result, AlertThrottle)
    # default window is 300 s — job should be allowed fresh
    assert result.is_allowed("x", now=0.0) is True


def test_custom_max_and_window():
    result = parse_throttle_config({"throttle": {"max_alerts": 1, "window_seconds": 10}})
    result.record("j", now=0.0)
    assert result.is_allowed("j", now=1.0) is False
    assert result.is_allowed("j", now=15.0) is True


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="JSON object"):
        parse_throttle_config({"throttle": "bad"})


def test_invalid_max_alerts_raises():
    with pytest.raises(ValueError, match="max_alerts"):
        parse_throttle_config({"throttle": {"max_alerts": 0}})


def test_invalid_window_seconds_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        parse_throttle_config({"throttle": {"window_seconds": -5}})


def test_float_window_accepted():
    result = parse_throttle_config({"throttle": {"max_alerts": 2, "window_seconds": 30.5}})
    assert isinstance(result, AlertThrottle)
