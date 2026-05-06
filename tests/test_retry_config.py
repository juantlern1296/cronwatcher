"""Tests for cronwatcher.retry_config."""

import pytest

from cronwatcher.retry_config import parse_retry_config


def test_defaults_when_no_retry_section():
    cfg = parse_retry_config({})
    assert cfg.max_attempts == 3
    assert cfg.base_delay == 1.0
    assert cfg.backoff_factor == 2.0
    assert cfg.max_delay == 30.0


def test_custom_values():
    cfg = parse_retry_config(
        {"retry": {"max_attempts": 5, "base_delay": 0.5, "backoff_factor": 3.0, "max_delay": 60.0}}
    )
    assert cfg.max_attempts == 5
    assert cfg.base_delay == 0.5
    assert cfg.backoff_factor == 3.0
    assert cfg.max_delay == 60.0


def test_partial_override_uses_defaults_for_rest():
    cfg = parse_retry_config({"retry": {"max_attempts": 2}})
    assert cfg.max_attempts == 2
    assert cfg.base_delay == 1.0


def test_invalid_max_attempts_raises():
    with pytest.raises(ValueError, match="max_attempts"):
        parse_retry_config({"retry": {"max_attempts": 0}})


def test_negative_base_delay_raises():
    with pytest.raises(ValueError, match="base_delay"):
        parse_retry_config({"retry": {"base_delay": -1.0}})


def test_backoff_factor_below_one_raises():
    with pytest.raises(ValueError, match="backoff_factor"):
        parse_retry_config({"retry": {"backoff_factor": 0.5}})


def test_max_delay_less_than_base_delay_raises():
    with pytest.raises(ValueError, match="max_delay"):
        parse_retry_config({"retry": {"base_delay": 10.0, "max_delay": 5.0}})


def test_max_attempts_exactly_one_is_valid():
    """max_attempts=1 means no retries, just a single attempt — should be allowed."""
    cfg = parse_retry_config({"retry": {"max_attempts": 1}})
    assert cfg.max_attempts == 1


def test_base_delay_zero_is_valid():
    """A base_delay of 0 disables the initial wait between retries — should be allowed."""
    cfg = parse_retry_config({"retry": {"base_delay": 0.0}})
    assert cfg.base_delay == 0.0


def test_backoff_factor_exactly_one_is_valid():
    """backoff_factor=1.0 means constant delay (no exponential growth) — should be allowed."""
    cfg = parse_retry_config({"retry": {"backoff_factor": 1.0}})
    assert cfg.backoff_factor == 1.0
