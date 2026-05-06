"""Tests for cronwatcher.metrics_reporter module."""

import logging
import pytest
from unittest.mock import patch, MagicMock

from cronwatcher.metrics import MetricsStore
from cronwatcher.metrics_reporter import MetricsReporter


@pytest.fixture
def store():
    s = MetricsStore()
    s.record_failure("job_a")
    s.record_alert("job_a")
    return s


@pytest.fixture
def reporter(store):
    return MetricsReporter(store, interval_seconds=60)


def test_invalid_interval_raises():
    with pytest.raises(ValueError):
        MetricsReporter(MetricsStore(), interval_seconds=0)


def test_report_now_logs_json(reporter, caplog):
    with caplog.at_level(logging.INFO, logger="cronwatcher.metrics_reporter"):
        reporter.report_now()
    assert any("[metrics]" in r.message for r in caplog.records)
    assert any("job_a" in r.message for r in caplog.records)


def test_start_schedules_timer(reporter):
    with patch("cronwatcher.metrics_reporter.threading.Timer") as mock_timer_cls:
        mock_timer = MagicMock()
        mock_timer_cls.return_value = mock_timer
        reporter.start()
        mock_timer_cls.assert_called_once_with(60, reporter._tick)
        mock_timer.start.assert_called_once()
        reporter.stop()


def test_stop_cancels_timer(reporter):
    with patch("cronwatcher.metrics_reporter.threading.Timer") as mock_timer_cls:
        mock_timer = MagicMock()
        mock_timer_cls.return_value = mock_timer
        reporter.start()
        reporter.stop()
        mock_timer.cancel.assert_called_once()


def test_tick_calls_report_and_reschedules(reporter):
    reporter.report_now = MagicMock()
    reporter._schedule = MagicMock()
    reporter._tick()
    reporter.report_now.assert_called_once()
    reporter._schedule.assert_called_once()


def test_schedule_does_nothing_when_stopped(reporter):
    reporter._stopped.set()
    reporter._schedule()  # should not raise or create a timer
    assert reporter._timer is None
