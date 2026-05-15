"""Tests for CircuitTransitionLog."""
import pytest
from cronwatcher.alert_circuit_log import CircuitTransition, CircuitTransitionLog
from cronwatcher.circuit_breaker import CircuitState


@pytest.fixture
def log():
    return CircuitTransitionLog(max_entries=50)


def test_invalid_max_entries_raises():
    with pytest.raises(ValueError, match="max_entries"):
        CircuitTransitionLog(max_entries=0)


def test_record_adds_entry(log):
    log.record("backup", CircuitState.CLOSED, CircuitState.OPEN, "threshold reached")
    assert log.size() == 1


def test_record_stores_fields(log):
    log.record("backup", CircuitState.CLOSED, CircuitState.OPEN, "threshold reached")
    entry = log.recent(1)[0]
    assert entry.job_name == "backup"
    assert entry.from_state == CircuitState.CLOSED
    assert entry.to_state == CircuitState.OPEN
    assert entry.reason == "threshold reached"


def test_recent_returns_last_n(log):
    for i in range(5):
        log.record(f"job{i}", CircuitState.CLOSED, CircuitState.OPEN, "x")
    recent = log.recent(3)
    assert len(recent) == 3
    assert recent[-1].job_name == "job4"


def test_evicts_oldest_when_full():
    log = CircuitTransitionLog(max_entries=3)
    for i in range(5):
        log.record(f"job{i}", CircuitState.CLOSED, CircuitState.OPEN, "x")
    assert log.size() == 3
    names = [e.job_name for e in log.recent(3)]
    assert "job0" not in names
    assert "job4" in names


def test_for_job_filters_correctly(log):
    log.record("alpha", CircuitState.CLOSED, CircuitState.OPEN, "a")
    log.record("beta", CircuitState.CLOSED, CircuitState.HALF_OPEN, "b")
    log.record("alpha", CircuitState.OPEN, CircuitState.HALF_OPEN, "c")
    results = log.for_job("alpha")
    assert len(results) == 2
    assert all(e.job_name == "alpha" for e in results)


def test_clear_empties_log(log):
    log.record("job", CircuitState.CLOSED, CircuitState.OPEN, "x")
    log.clear()
    assert log.size() == 0


def test_record_logs_message(log, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="cronwatcher.alert_circuit_log"):
        log.record("myjob", CircuitState.CLOSED, CircuitState.OPEN, "too many failures")
    assert "myjob" in caplog.text
    assert "CLOSED" in caplog.text or "closed" in caplog.text
