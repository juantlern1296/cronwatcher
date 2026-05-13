"""Tests for alert_snooze and alert_snooze_config."""

import time

import pytest

from cronwatcher.alert_snooze import AlertSnooze, SnoozeEntry
from cronwatcher.alert_snooze_config import parse_alert_snooze


@pytest.fixture
def snooze() -> AlertSnooze:
    return AlertSnooze()


# --- SnoozeEntry ---

def test_snooze_entry_active_within_window():
    entry = SnoozeEntry(job_name="backup", until=time.time() + 60)
    assert entry.is_active() is True


def test_snooze_entry_inactive_after_expiry():
    entry = SnoozeEntry(job_name="backup", until=time.time() - 1)
    assert entry.is_active() is False


def test_snooze_entry_uses_provided_now():
    entry = SnoozeEntry(job_name="backup", until=1000.0)
    assert entry.is_active(now=999.0) is True
    assert entry.is_active(now=1001.0) is False


# --- AlertSnooze ---

def test_new_job_not_snoozed(snooze):
    assert snooze.is_snoozed("backup") is False


def test_snooze_makes_job_snoozed(snooze):
    snooze.snooze("backup", 300)
    assert snooze.is_snoozed("backup") is True


def test_snooze_expires(snooze):
    future = time.time() + 10
    snooze.snooze("backup", 10)
    assert snooze.is_snoozed("backup", now=future + 1) is False


def test_lift_removes_snooze(snooze):
    snooze.snooze("backup", 300)
    snooze.lift("backup")
    assert snooze.is_snoozed("backup") is False


def test_lift_nonexistent_is_noop(snooze):
    snooze.lift("nonexistent")  # should not raise


def test_invalid_duration_raises(snooze):
    with pytest.raises(ValueError, match="positive"):
        snooze.snooze("backup", 0)


def test_active_snoozes_returns_only_active(snooze):
    now = time.time()
    snooze.snooze("job_a", 300)
    snooze.snooze("job_b", 300)
    # manually expire job_b
    snooze._entries["job_b"].until = now - 1
    active = snooze.active_snoozes(now=now)
    assert "job_a" in active
    assert "job_b" not in active


# --- parse_alert_snooze ---

def test_no_section_returns_none():
    assert parse_alert_snooze({}) is None


def test_valid_section_pre_loads_snoozes():
    cfg = {
        "alert_snooze": [
            {"job": "backup", "duration": 3600, "reason": "maintenance"}
        ]
    }
    result = parse_alert_snooze(cfg)
    assert result is not None
    assert result.is_snoozed("backup") is True


def test_not_a_list_raises():
    with pytest.raises(ValueError, match="list"):
        parse_alert_snooze({"alert_snooze": {"job": "x", "duration": 60}})


def test_item_not_dict_raises():
    with pytest.raises(ValueError, match="dict"):
        parse_alert_snooze({"alert_snooze": ["bad"]})


def test_missing_job_raises():
    with pytest.raises(ValueError, match="job"):
        parse_alert_snooze({"alert_snooze": [{"duration": 60}]})


def test_missing_duration_raises():
    with pytest.raises(ValueError, match="duration"):
        parse_alert_snooze({"alert_snooze": [{"job": "backup"}]})


def test_invalid_duration_type_raises():
    with pytest.raises(ValueError, match="number"):
        parse_alert_snooze({"alert_snooze": [{"job": "backup", "duration": "oops"}]})
