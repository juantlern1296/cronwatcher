"""Tests for alert_baseline_config module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_baseline_config import (
    baseline_handler,
    parse_baseline_config,
    wrap_with_baseline,
)
from cronwatcher.alert_baseline import AlertBaseline, BaselineConfig


def test_no_section_returns_none():
    assert parse_baseline_config({}) is None


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_baseline_config({"alert_baseline": "bad"})


def test_defaults_applied():
    cfg = parse_baseline_config({"alert_baseline": {}})
    assert cfg is not None
    assert cfg.window_size == 10
    assert cfg.deviation_factor == 2.0


def test_custom_values():
    cfg = parse_baseline_config({"alert_baseline": {"window_size": 5, "deviation_factor": 3.0}})
    assert cfg.window_size == 5
    assert cfg.deviation_factor == 3.0


def test_invalid_window_size_raises():
    with pytest.raises(ValueError, match="window_size"):
        parse_baseline_config({"alert_baseline": {"window_size": 0}})


def test_invalid_deviation_factor_raises():
    with pytest.raises(ValueError, match="deviation_factor"):
        parse_baseline_config({"alert_baseline": {"deviation_factor": 0.5}})


def test_wrap_with_baseline_returns_instance():
    cfg = BaselineConfig(window_size=5, deviation_factor=2.0)
    cb = MagicMock()
    instance = wrap_with_baseline(cfg, cb)
    assert isinstance(instance, AlertBaseline)


def test_baseline_handler_no_section_returns_none():
    cb = MagicMock()
    assert baseline_handler({}, cb) is None


def test_baseline_handler_returns_instance():
    cb = MagicMock()
    raw = {"alert_baseline": {"window_size": 4, "deviation_factor": 1.5}}
    result = baseline_handler(raw, cb)
    assert isinstance(result, AlertBaseline)
