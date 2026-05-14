"""Tests for AlertWindowFilter and parse_window_filter."""

from __future__ import annotations

from datetime import datetime, time
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_window_filter import (
    AlertWindowFilter,
    TimeWindow,
    WindowFilterConfig,
    _parse_time,
    parse_window_filter,
)
from cronwatcher.webhook import WebhookPayload


def make_payload() -> WebhookPayload:
    return WebhookPayload(job_name="backup", exit_code=1, timestamp="2024-01-01T00:00:00")


# --- TimeWindow.is_active ---

def test_window_active_within_range():
    w = TimeWindow(start=time(9, 0), end=time(17, 0))
    assert w.is_active(datetime(2024, 1, 1, 12, 0))  # Monday


def test_window_inactive_before_start():
    w = TimeWindow(start=time(9, 0), end=time(17, 0))
    assert not w.is_active(datetime(2024, 1, 1, 8, 59))


def test_window_inactive_at_end():
    w = TimeWindow(start=time(9, 0), end=time(17, 0))
    assert not w.is_active(datetime(2024, 1, 1, 17, 0))


def test_overnight_window_active_after_start():
    w = TimeWindow(start=time(22, 0), end=time(6, 0))
    assert w.is_active(datetime(2024, 1, 1, 23, 0))


def test_overnight_window_active_before_end():
    w = TimeWindow(start=time(22, 0), end=time(6, 0))
    assert w.is_active(datetime(2024, 1, 2, 5, 30))


def test_window_inactive_wrong_weekday():
    # weekday 0 = Monday; 2024-01-01 is a Monday
    w = TimeWindow(start=time(9, 0), end=time(17, 0), weekdays=[2, 3])  # Wed/Thu only
    assert not w.is_active(datetime(2024, 1, 1, 12, 0))


# --- AlertWindowFilter ---

def test_no_windows_raises():
    with pytest.raises(ValueError, match="at least one time window"):
        AlertWindowFilter(WindowFilterConfig(windows=[]), handler=lambda p: None)


def test_alert_forwarded_within_window():
    cb = MagicMock()
    w = TimeWindow(start=time(0, 0), end=time(23, 59))
    af = AlertWindowFilter(WindowFilterConfig(windows=[w]), handler=cb)
    result = af.filter(make_payload(), now=datetime(2024, 1, 1, 12, 0))
    assert result is True
    cb.assert_called_once()


def test_alert_suppressed_outside_window():
    cb = MagicMock()
    w = TimeWindow(start=time(9, 0), end=time(10, 0))
    af = AlertWindowFilter(WindowFilterConfig(windows=[w]), handler=cb)
    result = af.filter(make_payload(), now=datetime(2024, 1, 1, 23, 0))
    assert result is False
    cb.assert_not_called()


def test_allow_outside_passes_alert_when_no_window_active():
    cb = MagicMock()
    w = TimeWindow(start=time(9, 0), end=time(10, 0))
    cfg = WindowFilterConfig(windows=[w], allow_outside=True)
    af = AlertWindowFilter(cfg, handler=cb)
    result = af.filter(make_payload(), now=datetime(2024, 1, 1, 23, 0))
    assert result is True
    cb.assert_called_once()


# --- _parse_time ---

def test_parse_time_valid():
    assert _parse_time("09:30") == time(9, 30)


def test_parse_time_invalid_raises():
    with pytest.raises(ValueError, match="Invalid time format"):
        _parse_time("9am")


# --- parse_window_filter ---

def test_no_section_returns_none():
    assert parse_window_filter({}, handler=lambda p: None) is None


def test_not_a_dict_raises():
    with pytest.raises(ValueError):
        parse_window_filter({"alert_window_filter": "bad"}, handler=lambda p: None)


def test_valid_config_builds_filter():
    cfg = {
        "alert_window_filter": {
            "windows": [{"start": "08:00", "end": "18:00"}]
        }
    }
    cb = MagicMock()
    wf = parse_window_filter(cfg, cb)
    assert isinstance(wf, AlertWindowFilter)
