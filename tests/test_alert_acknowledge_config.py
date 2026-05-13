"""Tests for alert_acknowledge_config.py"""
from __future__ import annotations

import pytest

from cronwatcher.alert_acknowledge import AlertAcknowledge
from cronwatcher.alert_acknowledge_config import (
    parse_alert_acknowledge,
    wrap_with_acknowledge,
)


# --- parse_alert_acknowledge ---

def test_no_section_returns_none():
    assert parse_alert_acknowledge({}) is None


def test_enabled_false_returns_none():
    cfg = {"alert_acknowledge": {"enabled": False}}
    assert parse_alert_acknowledge(cfg) is None


def test_enabled_returns_instance():
    cfg = {"alert_acknowledge": {"enabled": True}}
    result = parse_alert_acknowledge(cfg)
    assert isinstance(result, AlertAcknowledge)


def test_defaults_applied_when_keys_absent():
    cfg = {"alert_acknowledge": {}}
    result = parse_alert_acknowledge(cfg)
    assert isinstance(result, AlertAcknowledge)


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_alert_acknowledge({"alert_acknowledge": "yes"})


def test_negative_duration_raises():
    cfg = {"alert_acknowledge": {"enabled": True, "default_duration_seconds": -5}}
    with pytest.raises(ValueError, match="non-negative"):
        parse_alert_acknowledge(cfg)


# --- wrap_with_acknowledge ---

class _FakePayload:
    def __init__(self, job_name):
        self.job_name = job_name


def test_wrap_calls_handler_when_not_acked():
    ack = AlertAcknowledge()
    calls = []
    handler = wrap_with_acknowledge(ack, calls.append)
    handler(_FakePayload("backup"))
    assert len(calls) == 1


def test_wrap_skips_handler_when_acked():
    import time
    ack = AlertAcknowledge()
    ack.acknowledge("backup", "alice", duration_seconds=300)
    calls = []
    handler = wrap_with_acknowledge(ack, calls.append)
    handler(_FakePayload("backup"))
    assert len(calls) == 0


def test_wrap_calls_handler_after_ack_expires():
    import time
    ack = AlertAcknowledge()
    now = time.time()
    ack.acknowledge("backup", "alice", duration_seconds=1, now=now - 10)
    calls = []
    handler = wrap_with_acknowledge(ack, calls.append)
    handler(_FakePayload("backup"))
    assert len(calls) == 1
