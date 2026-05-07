"""Tests for dead letter queue config parsing."""
import pytest

from cronwatcher.dead_letter import DeadLetterQueue
from cronwatcher.dead_letter_config import parse_dead_letter_config


def test_no_section_returns_none():
    result = parse_dead_letter_config({})
    assert result is None


def test_enabled_false_returns_none():
    result = parse_dead_letter_config({"dead_letter": {"enabled": False}})
    assert result is None


def test_default_max_size():
    result = parse_dead_letter_config({"dead_letter": {"enabled": True}})
    assert isinstance(result, DeadLetterQueue)
    assert result.max_size == 500


def test_custom_max_size():
    result = parse_dead_letter_config({"dead_letter": {"enabled": True, "max_size": 100}})
    assert result.max_size == 100


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="JSON object"):
        parse_dead_letter_config({"dead_letter": "yes"})


def test_invalid_max_size_type_raises():
    with pytest.raises(ValueError, match="integer"):
        parse_dead_letter_config({"dead_letter": {"max_size": "big"}})


def test_zero_max_size_raises():
    with pytest.raises(ValueError, match="at least 1"):
        parse_dead_letter_config({"dead_letter": {"max_size": 0}})


def test_enabled_defaults_to_true():
    result = parse_dead_letter_config({"dead_letter": {"max_size": 50}})
    assert isinstance(result, DeadLetterQueue)
    assert result.max_size == 50
