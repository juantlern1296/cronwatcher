"""Tests for cronwatcher.throttle."""

import pytest

from cronwatcher.throttle import AlertThrottle, ThrottleConfig


@pytest.fixture
def throttle() -> AlertThrottle:
    cfg = ThrottleConfig(max_alerts=3, window_seconds=60.0)
    return AlertThrottle(cfg)


def test_invalid_max_alerts_raises():
    with pytest.raises(ValueError, match="max_alerts"):
        AlertThrottle(ThrottleConfig(max_alerts=0, window_seconds=60.0))


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        AlertThrottle(ThrottleConfig(max_alerts=1, window_seconds=0.0))


def test_new_job_is_allowed(throttle):
    assert throttle.is_allowed("backup", now=0.0) is True


def test_allow_up_to_max(throttle):
    for i in range(3):
        assert throttle.is_allowed("backup", now=float(i)) is True
        throttle.record("backup", now=float(i))


def test_blocked_after_max(throttle):
    for i in range(3):
        throttle.record("backup", now=float(i))
    assert throttle.is_allowed("backup", now=3.0) is False


def test_allowed_again_after_window_expires(throttle):
    for i in range(3):
        throttle.record("backup", now=float(i))
    # advance past the 60-second window
    assert throttle.is_allowed("backup", now=65.0) is True


def test_current_count_is_zero_for_new_job(throttle):
    assert throttle.current_count("nightly", now=0.0) == 0


def test_current_count_increments_on_record(throttle):
    throttle.record("nightly", now=0.0)
    throttle.record("nightly", now=1.0)
    assert throttle.current_count("nightly", now=2.0) == 2


def test_current_count_drops_after_window(throttle):
    throttle.record("nightly", now=0.0)
    throttle.record("nightly", now=1.0)
    assert throttle.current_count("nightly", now=62.0) == 0


def test_independent_jobs_tracked_separately(throttle):
    for i in range(3):
        throttle.record("jobA", now=float(i))
    assert throttle.is_allowed("jobA", now=3.0) is False
    assert throttle.is_allowed("jobB", now=3.0) is True
