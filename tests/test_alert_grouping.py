"""Tests for alert grouping feature."""

from __future__ import annotations

import time
from typing import List, Tuple
from unittest.mock import patch

import pytest

from cronwatcher.alert_grouping import AlertGrouper, GroupingConfig
from cronwatcher.alert_grouping_config import parse_alert_grouping
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup", host: str = "srv1", severity: str = "info") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        hostname=host,
        exit_code=1,
        timestamp="2024-01-01T00:00:00Z",
        extra={"severity": severity},
    )


@pytest.fixture
def callback() -> Tuple[List, callable]:
    received = []

    def cb(key, payloads):
        received.append((key, list(payloads)))

    return received, cb


@pytest.fixture
def cfg() -> GroupingConfig:
    return GroupingConfig(group_by="job", window_seconds=60.0, max_group_size=5)


@pytest.fixture
def grouper(cfg, callback):
    _, cb = callback
    return AlertGrouper(cfg, cb)


def test_invalid_group_by_raises():
    with pytest.raises(ValueError, match="group_by"):
        GroupingConfig(group_by="region", window_seconds=30.0)


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        GroupingConfig(group_by="job", window_seconds=0)


def test_invalid_max_size_raises():
    with pytest.raises(ValueError, match="max_group_size"):
        GroupingConfig(group_by="job", window_seconds=10.0, max_group_size=0)


def test_add_creates_group(grouper, callback):
    received, _ = callback
    grouper.add(make_payload("backup"))
    assert grouper.group_count() == 1
    assert len(received) == 0


def test_flush_all_dispatches(grouper, callback):
    received, _ = callback
    grouper.add(make_payload("backup"))
    grouper.add(make_payload("sync"))
    grouper.flush_all()
    assert grouper.group_count() == 0
    assert len(received) == 2


def test_max_size_triggers_flush(callback, cfg):
    received, cb = callback
    cfg = GroupingConfig(group_by="job", window_seconds=60.0, max_group_size=3)
    g = AlertGrouper(cfg, cb)
    for _ in range(3):
        g.add(make_payload("backup"))
    assert len(received) == 1
    key, payloads = received[0]
    assert key == "backup"
    assert len(payloads) == 3


def test_group_by_host(callback):
    received, cb = callback
    cfg = GroupingConfig(group_by="host", window_seconds=60.0)
    g = AlertGrouper(cfg, cb)
    g.add(make_payload(host="srv1"))
    g.add(make_payload(host="srv2"))
    g.flush_all()
    keys = {r[0] for r in received}
    assert keys == {"srv1", "srv2"}


def test_flush_expired_dispatches(callback):
    received, cb = callback
    cfg = GroupingConfig(group_by="job", window_seconds=0.05)
    g = AlertGrouper(cfg, cb)
    g.add(make_payload("backup"))
    time.sleep(0.1)
    g.flush_expired()
    assert len(received) == 1


# --- config parsing ---

def test_no_section_returns_none():
    assert parse_alert_grouping({}) is None


def test_valid_config_parsed():
    raw = {"alert_grouping": {"group_by": "host", "window_seconds": 30, "max_group_size": 10}}
    cfg = parse_alert_grouping(raw)
    assert cfg is not None
    assert cfg.group_by == "host"
    assert cfg.window_seconds == 30.0
    assert cfg.max_group_size == 10


def test_defaults_applied():
    cfg = parse_alert_grouping({"alert_grouping": {}})
    assert cfg.group_by == "job"
    assert cfg.window_seconds == 60.0
    assert cfg.max_group_size == 20


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="JSON object"):
        parse_alert_grouping({"alert_grouping": "bad"})
