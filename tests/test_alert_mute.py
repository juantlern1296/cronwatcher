"""Tests for alert_mute and alert_mute_config."""

from __future__ import annotations

import time
import pytest

from cronwatcher.alert_mute import AlertMute, MuteWindow
from cronwatcher.alert_mute_config import parse_alert_mute


NOW = 1_700_000_000.0


@pytest.fixture
def mute() -> AlertMute:
    return AlertMute()


def make_window(job="backup", offset_start=-60, offset_end=60, reason="") -> MuteWindow:
    return MuteWindow(
        job_name=job,
        start=NOW + offset_start,
        end=NOW + offset_end,
        reason=reason,
    )


def test_window_is_active(mute):
    w = make_window()
    assert w.is_active(NOW) is True


def test_window_not_active_before_start(mute):
    w = make_window(offset_start=100, offset_end=200)
    assert w.is_active(NOW) is False


def test_window_not_active_after_end(mute):
    w = make_window(offset_start=-200, offset_end=-100)
    assert w.is_active(NOW) is False


def test_is_muted_specific_job(mute):
    mute.add_window(make_window(job="backup"))
    assert mute.is_muted("backup", NOW) is True
    assert mute.is_muted("sync", NOW) is False


def test_is_muted_wildcard(mute):
    mute.add_window(make_window(job="*"))
    assert mute.is_muted("backup", NOW) is True
    assert mute.is_muted("anything", NOW) is True


def test_inactive_window_does_not_mute(mute):
    mute.add_window(make_window(offset_start=100, offset_end=200))
    assert mute.is_muted("backup", NOW) is False


def test_remove_window(mute):
    mute.add_window(make_window(job="backup"))
    removed = mute.remove_window("backup")
    assert removed == 1
    assert mute.is_muted("backup", NOW) is False


def test_evict_expired(mute):
    mute.add_window(make_window(offset_start=-200, offset_end=-100))  # expired
    mute.add_window(make_window(offset_start=-10, offset_end=100))    # active
    removed = mute.evict_expired(NOW)
    assert removed == 1
    assert len(mute.active_windows(NOW)) == 1


def test_active_windows_returns_only_active(mute):
    mute.add_window(make_window(offset_start=-200, offset_end=-100))
    mute.add_window(make_window(offset_start=-10, offset_end=100))
    assert len(mute.active_windows(NOW)) == 1


# --- config parsing ---

def test_no_section_returns_empty():
    m = parse_alert_mute({})
    assert m.is_muted("backup", NOW) is False


def test_valid_window_parsed():
    cfg = {"mute_windows": [{"job": "backup", "start": NOW - 60, "end": NOW + 60}]}
    m = parse_alert_mute(cfg)
    assert m.is_muted("backup", NOW) is True


def test_not_a_list_raises():
    with pytest.raises(ValueError, match="must be a list"):
        parse_alert_mute({"mute_windows": {}})


def test_missing_end_raises():
    with pytest.raises(ValueError, match="must have 'start' and 'end'"):
        parse_alert_mute({"mute_windows": [{"job": "backup", "start": NOW}]})


def test_end_before_start_raises():
    with pytest.raises(ValueError, match="'end' must be greater than 'start'"):
        parse_alert_mute({"mute_windows": [{"start": NOW + 100, "end": NOW}]})
