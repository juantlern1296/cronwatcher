"""Tests for alert_oncall_config module."""

import pytest

from cronwatcher.alert_oncall_config import parse_oncall_schedule
from cronwatcher.alert_oncall import OnCallSchedule
from datetime import time


def test_no_section_returns_none():
    assert parse_oncall_schedule({}) is None


def test_not_a_dict_raises():
    with pytest.raises(TypeError, match="on_call must be a dict"):
        parse_oncall_schedule({"on_call": "bad"})


def test_slots_not_a_list_raises():
    with pytest.raises(TypeError, match="on_call.slots must be a list"):
        parse_oncall_schedule({"on_call": {"slots": "bad"}})


def test_slot_not_a_dict_raises():
    with pytest.raises(TypeError, match="on_call.slots\\[0\\] must be a dict"):
        parse_oncall_schedule({"on_call": {"slots": ["bad"]}})


def test_slot_missing_webhook_url_raises():
    raw = {"on_call": {"slots": [{"name": "day", "weekdays": [0]}]}}
    with pytest.raises(ValueError, match="missing 'webhook_url'"):
        parse_oncall_schedule(raw)


def test_invalid_time_format_raises():
    raw = {
        "on_call": {
            "slots": [{
                "webhook_url": "http://x",
                "start_time": "9am",
                "end_time": "17:00",
            }]
        }
    }
    with pytest.raises(ValueError, match="start_time"):
        parse_oncall_schedule(raw)


def test_valid_single_slot_parsed():
    raw = {
        "on_call": {
            "slots": [{
                "name": "weekday",
                "webhook_url": "http://pager",
                "weekdays": [0, 1, 2, 3, 4],
                "start_time": "09:00",
                "end_time": "17:00",
            }],
            "fallback_url": "http://fallback",
        }
    }
    schedule = parse_oncall_schedule(raw)
    assert isinstance(schedule, OnCallSchedule)
    assert len(schedule.slots) == 1
    slot = schedule.slots[0]
    assert slot.name == "weekday"
    assert slot.webhook_url == "http://pager"
    assert slot.start_time == time(9, 0)
    assert slot.end_time == time(17, 0)
    assert schedule.fallback_url == "http://fallback"


def test_empty_slots_with_fallback():
    raw = {"on_call": {"slots": [], "fallback_url": "http://always"}}
    schedule = parse_oncall_schedule(raw)
    assert schedule.slots == []
    assert schedule.fallback_url == "http://always"


def test_defaults_applied_when_times_absent():
    raw = {
        "on_call": {
            "slots": [{"webhook_url": "http://x"}]
        }
    }
    schedule = parse_oncall_schedule(raw)
    slot = schedule.slots[0]
    assert slot.start_time == time(0, 0)
    assert slot.end_time == time(23, 59)
    assert slot.weekdays == list(range(7))
