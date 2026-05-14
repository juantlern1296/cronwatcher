"""Tests for alert_oncall module."""

from datetime import datetime, time
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_oncall import AlertOnCall, OnCallSchedule, OnCallSlot
from cronwatcher.webhook import WebhookPayload


def make_payload() -> WebhookPayload:
    return WebhookPayload(
        job_name="backup",
        exit_code=1,
        timestamp="2024-01-01T00:00:00Z",
        hostname="host1",
        extra={},
    )


def make_slot(url="http://pager", weekdays=None, start="09:00", end="17:00") -> OnCallSlot:
    if weekdays is None:
        weekdays = list(range(7))
    h_s, m_s = start.split(":")
    h_e, m_e = end.split(":")
    return OnCallSlot(
        name="day",
        webhook_url=url,
        weekdays=weekdays,
        start_time=time(int(h_s), int(m_s)),
        end_time=time(int(h_e), int(m_e)),
    )


def test_slot_active_within_window():
    slot = make_slot(weekdays=[0, 1, 2, 3, 4], start="09:00", end="17:00")
    # Monday 10:00
    now = datetime(2024, 1, 1, 10, 0)  # Monday
    assert slot.is_active(now) is True


def test_slot_inactive_outside_window():
    slot = make_slot(weekdays=[0, 1, 2, 3, 4], start="09:00", end="17:00")
    now = datetime(2024, 1, 1, 8, 0)
    assert slot.is_active(now) is False


def test_slot_inactive_wrong_weekday():
    slot = make_slot(weekdays=[0, 1, 2, 3, 4], start="09:00", end="17:00")
    # Saturday = 5
    now = datetime(2024, 1, 6, 12, 0)
    assert slot.is_active(now) is False


def test_schedule_returns_first_active_slot():
    s1 = make_slot(url="http://primary", start="08:00", end="12:00")
    s2 = make_slot(url="http://secondary", start="12:00", end="20:00")
    schedule = OnCallSchedule(slots=[s1, s2], fallback_url="http://fallback")
    now = datetime(2024, 1, 1, 9, 0)
    assert schedule.current_url(now) == "http://primary"


def test_schedule_falls_back_when_no_slot_active():
    slot = make_slot(start="09:00", end="10:00")
    schedule = OnCallSchedule(slots=[slot], fallback_url="http://fallback")
    now = datetime(2024, 1, 1, 22, 0)
    assert schedule.current_url(now) == "http://fallback"


def test_schedule_returns_none_when_no_fallback():
    slot = make_slot(start="09:00", end="10:00")
    schedule = OnCallSchedule(slots=[slot], fallback_url=None)
    now = datetime(2024, 1, 1, 22, 0)
    assert schedule.current_url(now) is None


def test_dispatch_calls_send_with_active_url():
    slot = make_slot(url="http://oncall")
    schedule = OnCallSchedule(slots=[slot])
    send_fn = MagicMock(return_value=True)
    alerter = AlertOnCall(schedule=schedule, send_fn=send_fn)
    payload = make_payload()
    now = datetime(2024, 1, 1, 12, 0)
    result = alerter.dispatch(payload, now=now)
    assert result is True
    send_fn.assert_called_once_with("http://oncall", payload)


def test_dispatch_returns_false_when_no_url():
    schedule = OnCallSchedule(slots=[], fallback_url=None)
    send_fn = MagicMock()
    alerter = AlertOnCall(schedule=schedule, send_fn=send_fn)
    result = alerter.dispatch(make_payload())
    assert result is False
    send_fn.assert_not_called()
