"""Tests for cronwatcher.circuit_breaker_config."""

import pytest

from cronwatcher.circuit_breaker import CircuitBreaker
from cronwatcher.circuit_breaker_config import parse_circuit_breaker


def test_no_section_returns_none():
    assert parse_circuit_breaker({}) is None


def test_valid_minimal_config():
    cfg = {"circuit_breaker": {}}
    cb = parse_circuit_breaker(cfg)
    assert isinstance(cb, CircuitBreaker)
    assert cb.threshold == 5
    assert cb.reset_timeout == 300.0


def test_custom_threshold_and_timeout():
    cfg = {"circuit_breaker": {"threshold": 10, "reset_timeout": 120}}
    cb = parse_circuit_breaker(cfg)
    assert cb.threshold == 10
    assert cb.reset_timeout == 120.0


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="JSON object"):
        parse_circuit_breaker({"circuit_breaker": "yes"})


def test_invalid_threshold_raises():
    with pytest.raises(ValueError, match="threshold"):
        parse_circuit_breaker({"circuit_breaker": {"threshold": 0}})


def test_threshold_not_int_raises():
    with pytest.raises(ValueError, match="threshold"):
        parse_circuit_breaker({"circuit_breaker": {"threshold": "five"}})


def test_invalid_reset_timeout_raises():
    with pytest.raises(ValueError, match="reset_timeout"):
        parse_circuit_breaker({"circuit_breaker": {"reset_timeout": -10}})


def test_float_reset_timeout_accepted():
    cfg = {"circuit_breaker": {"threshold": 3, "reset_timeout": 45.5}}
    cb = parse_circuit_breaker(cfg)
    assert cb.reset_timeout == 45.5
