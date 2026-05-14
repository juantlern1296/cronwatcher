"""Tests for alert_baseline module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_baseline import AlertBaseline, BaselineConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job_name: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job_name,
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        extra={},
    )


@pytest.fixture
def callback():
    return MagicMock()


@pytest.fixture
def cfg():
    return BaselineConfig(window_size=3, deviation_factor=2.0)


@pytest.fixture
def baseline(cfg, callback):
    return AlertBaseline(config=cfg, on_deviation=callback)


def test_invalid_window_size_raises():
    with pytest.raises(ValueError, match="window_size"):
        BaselineConfig(window_size=0, deviation_factor=2.0)


def test_invalid_deviation_factor_raises():
    with pytest.raises(ValueError, match="deviation_factor"):
        BaselineConfig(window_size=5, deviation_factor=1.0)


def test_no_alert_on_first_flush(baseline, callback):
    p = make_payload()
    baseline.record_failure(p)
    baseline.flush(p)
    callback.assert_not_called()


def test_no_alert_within_factor(baseline, callback):
    p = make_payload()
    # build history: avg = 2
    for _ in range(2):
        baseline.record_failure(p)
    baseline.flush(p)

    # current = 3, avg = 2, factor = 2.0 → 3 <= 4, no alert
    for _ in range(3):
        baseline.record_failure(p)
    baseline.flush(p)
    callback.assert_not_called()


def test_alert_when_deviation_exceeded(baseline, callback):
    p = make_payload()
    # build history: avg = 1
    baseline.record_failure(p)
    baseline.flush(p)

    # current = 5, avg = 1, factor = 2.0 → 5 > 2, alert
    for _ in range(5):
        baseline.record_failure(p)
    baseline.flush(p)
    callback.assert_called_once_with(p)


def test_current_count_resets_after_flush(baseline):
    p = make_payload()
    baseline.record_failure(p)
    baseline.record_failure(p)
    assert baseline.current_count("backup") == 2
    baseline.flush(p)
    assert baseline.current_count("backup") == 0


def test_average_updates_over_time(baseline):
    p = make_payload()
    for _ in range(4):
        baseline.record_failure(p)
    baseline.flush(p)
    assert baseline.average_for("backup") == 4.0

    for _ in range(2):
        baseline.record_failure(p)
    baseline.flush(p)
    # window_size=3, history=[4, 2]
    assert baseline.average_for("backup") == pytest.approx(3.0)


def test_window_size_limits_history(baseline):
    p = make_payload()
    for count in [10, 10, 10]:
        for _ in range(count):
            baseline.record_failure(p)
        baseline.flush(p)
    # window_size=3, history=[10,10,10]
    assert baseline.average_for("backup") == pytest.approx(10.0)

    # add one more to push oldest out
    for _ in range(1):
        baseline.record_failure(p)
    baseline.flush(p)
    # history=[10,10,1]
    assert baseline.average_for("backup") == pytest.approx(7.0)


def test_independent_job_tracking(baseline, callback):
    p1 = make_payload("job_a")
    p2 = make_payload("job_b")

    baseline.record_failure(p1)
    baseline.flush(p1)

    # job_b has no history yet, no alert
    for _ in range(10):
        baseline.record_failure(p2)
    baseline.flush(p2)
    callback.assert_not_called()
