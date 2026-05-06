"""Tests for parse_job_timeout_configs."""

import pytest

from cronwatcher.job_timeout_config import parse_job_timeout_configs


def test_empty_section_returns_empty_list():
    result = parse_job_timeout_configs({})
    assert result == []


def test_valid_single_entry():
    raw = {
        "job_timeouts": [
            {"job_name": "backup", "expected_interval_seconds": 3600}
        ]
    }
    result = parse_job_timeout_configs(raw)
    assert len(result) == 1
    assert result[0].job_name == "backup"
    assert result[0].expected_interval_seconds == 3600
    assert result[0].grace_period_seconds == 60  # default


def test_custom_grace_period():
    raw = {
        "job_timeouts": [
            {"job_name": "cleanup", "expected_interval_seconds": 1800, "grace_period_seconds": 120}
        ]
    }
    result = parse_job_timeout_configs(raw)
    assert result[0].grace_period_seconds == 120


def test_multiple_entries():
    raw = {
        "job_timeouts": [
            {"job_name": "a", "expected_interval_seconds": 60},
            {"job_name": "b", "expected_interval_seconds": 3600},
        ]
    }
    result = parse_job_timeout_configs(raw)
    assert len(result) == 2
    assert {r.job_name for r in result} == {"a", "b"}


def test_not_a_list_raises():
    with pytest.raises(ValueError, match="must be a list"):
        parse_job_timeout_configs({"job_timeouts": {"job_name": "x"}})


def test_missing_job_name_raises():
    raw = {"job_timeouts": [{"expected_interval_seconds": 60}]}
    with pytest.raises(ValueError, match="job_name"):
        parse_job_timeout_configs(raw)


def test_invalid_interval_raises():
    raw = {"job_timeouts": [{"job_name": "x", "expected_interval_seconds": -1}]}
    with pytest.raises(ValueError, match="expected_interval_seconds"):
        parse_job_timeout_configs(raw)


def test_zero_interval_raises():
    raw = {"job_timeouts": [{"job_name": "x", "expected_interval_seconds": 0}]}
    with pytest.raises(ValueError, match="expected_interval_seconds"):
        parse_job_timeout_configs(raw)


def test_negative_grace_raises():
    raw = {
        "job_timeouts": [
            {"job_name": "x", "expected_interval_seconds": 60, "grace_period_seconds": -5}
        ]
    }
    with pytest.raises(ValueError, match="grace_period_seconds"):
        parse_job_timeout_configs(raw)


def test_zero_grace_is_valid():
    raw = {
        "job_timeouts": [
            {"job_name": "x", "expected_interval_seconds": 60, "grace_period_seconds": 0}
        ]
    }
    result = parse_job_timeout_configs(raw)
    assert result[0].grace_period_seconds == 0
