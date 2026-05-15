"""Tests for parse_circuit_log_config."""
import pytest
from cronwatcher.alert_circuit_log import CircuitTransitionLog
from cronwatcher.alert_circuit_log_config import parse_circuit_log_config


def test_no_section_returns_none():
    assert parse_circuit_log_config({}) is None


def test_enabled_false_returns_none():
    cfg = {"circuit_log": {"enabled": False}}
    assert parse_circuit_log_config(cfg) is None


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_circuit_log_config({"circuit_log": ["bad"]})


def test_defaults_applied():
    cfg = {"circuit_log": {"enabled": True}}
    result = parse_circuit_log_config(cfg)
    assert isinstance(result, CircuitTransitionLog)
    assert result.max_entries == 200


def test_custom_max_entries():
    cfg = {"circuit_log": {"enabled": True, "max_entries": 50}}
    result = parse_circuit_log_config(cfg)
    assert result.max_entries == 50


def test_invalid_max_entries_raises():
    cfg = {"circuit_log": {"enabled": True, "max_entries": 0}}
    with pytest.raises(ValueError, match="max_entries"):
        parse_circuit_log_config(cfg)


def test_non_integer_max_entries_raises():
    cfg = {"circuit_log": {"enabled": True, "max_entries": "lots"}}
    with pytest.raises(ValueError, match="max_entries"):
        parse_circuit_log_config(cfg)
