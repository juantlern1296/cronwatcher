"""Tests for cronwatcher.batch_alert."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.batch_alert import AlertBatch, BatchAlerter, BatchConfig
from cronwatcher.log_parser import CronLogEntry


def make_entry(job: str = "backup") -> CronLogEntry:
    return CronLogEntry(
        raw="CRON[1]: (root) CMD (backup.sh)",
        timestamp=None,
        pid="1",
        user="root",
        tag="CMD",
        message=f"({job}.sh)",
    )


@pytest.fixture
def callback():
    return MagicMock()


@pytest.fixture
def cfg():
    return BatchConfig(window_seconds=60.0, max_size=5)


@pytest.fixture
def alerter(cfg, callback):
    a = BatchAlerter(cfg, callback)
    yield a
    a.stop()


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        BatchAlerter(BatchConfig(window_seconds=0), lambda e: None)


def test_invalid_max_size_raises():
    with pytest.raises(ValueError, match="max_size"):
        BatchAlerter(BatchConfig(max_size=0), lambda e: None)


def test_add_does_not_flush_before_max(alerter, callback):
    alerter.add(make_entry())
    alerter.add(make_entry())
    callback.assert_not_called()


def test_flush_on_max_size(cfg, callback):
    cfg.max_size = 3
    a = BatchAlerter(cfg, callback)
    try:
        a.add(make_entry())
        a.add(make_entry())
        a.add(make_entry())  # triggers flush
        callback.assert_called_once()
        entries = callback.call_args[0][0]
        assert len(entries) == 3
    finally:
        a.stop()


def test_manual_flush_sends_entries(alerter, callback):
    alerter.add(make_entry("db"))
    alerter.add(make_entry("api"))
    alerter.flush()
    callback.assert_called_once()
    assert len(callback.call_args[0][0]) == 2


def test_manual_flush_empty_batch_does_not_call(alerter, callback):
    alerter.flush()
    callback.assert_not_called()


def test_batch_resets_after_flush(alerter, callback):
    alerter.add(make_entry())
    alerter.flush()
    alerter.add(make_entry())
    alerter.flush()
    assert callback.call_count == 2


def test_alert_batch_is_expired():
    b = AlertBatch()
    b.created_at = time.monotonic() - 100
    assert b.is_expired(30.0)


def test_alert_batch_not_expired():
    b = AlertBatch()
    assert not b.is_expired(60.0)


def test_alert_batch_is_full():
    b = AlertBatch()
    for _ in range(3):
        b.add(make_entry())
    assert b.is_full(3)
    assert not b.is_full(4)
