"""Tests for cronwatcher.circuit_breaker."""

import time
import pytest

from cronwatcher.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def breaker() -> CircuitBreaker:
    return CircuitBreaker(threshold=3, reset_timeout=60.0)


def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        CircuitBreaker(threshold=0)


def test_invalid_reset_timeout_raises():
    with pytest.raises(ValueError):
        CircuitBreaker(threshold=3, reset_timeout=-1.0)


def test_new_job_is_closed(breaker):
    assert not breaker.is_open("backup")
    assert breaker.state_of("backup") == CircuitState.CLOSED


def test_below_threshold_stays_closed(breaker):
    breaker.record_failure("backup")
    breaker.record_failure("backup")
    assert breaker.state_of("backup") == CircuitState.CLOSED
    assert not breaker.is_open("backup")


def test_at_threshold_opens(breaker):
    for _ in range(3):
        breaker.record_failure("backup")
    assert breaker.state_of("backup") == CircuitState.OPEN
    assert breaker.is_open("backup")


def test_record_success_resets(breaker):
    for _ in range(3):
        breaker.record_failure("backup")
    assert breaker.is_open("backup")
    breaker.record_success("backup")
    assert not breaker.is_open("backup")
    assert breaker.state_of("backup") == CircuitState.CLOSED


def test_open_transitions_to_half_open_after_timeout(monkeypatch):
    cb = CircuitBreaker(threshold=2, reset_timeout=30.0)
    for _ in range(2):
        cb.record_failure("sync")
    assert cb.is_open("sync")

    # Simulate time passing beyond reset_timeout.
    monkeypatch.setattr(time, "monotonic", lambda: time.monotonic.__wrapped__() + 31)
    assert not cb.is_open("sync")
    assert cb.state_of("sync") == CircuitState.HALF_OPEN


def test_half_open_failure_reopens(monkeypatch):
    cb = CircuitBreaker(threshold=2, reset_timeout=30.0)
    for _ in range(2):
        cb.record_failure("sync")

    real_mono = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: real_mono() + 31)
    cb.is_open("sync")  # triggers HALF_OPEN
    cb.record_failure("sync")
    assert cb.state_of("sync") == CircuitState.OPEN


def test_independent_jobs_do_not_interfere(breaker):
    for _ in range(3):
        breaker.record_failure("job_a")
    assert breaker.is_open("job_a")
    assert not breaker.is_open("job_b")
