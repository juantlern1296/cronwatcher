"""Tests for EscalationManager."""
import pytest

from cronwatcher.escalation import EscalationManager, EscalationPolicy


@pytest.fixture()
def policy() -> EscalationPolicy:
    return EscalationPolicy(threshold=3, webhook_url="https://hooks.example.com/esc")


@pytest.fixture()
def manager(policy: EscalationPolicy) -> EscalationManager:
    return EscalationManager(policy)


def test_invalid_threshold_raises():
    with pytest.raises(ValueError, match="threshold"):
        EscalationManager(EscalationPolicy(threshold=0, webhook_url="http://x"))


def test_no_escalation_below_threshold(manager):
    assert manager.record_failure("backup") is False
    assert manager.record_failure("backup") is False
    assert manager.consecutive_count("backup") == 2


def test_escalation_at_threshold(manager):
    manager.record_failure("backup")
    manager.record_failure("backup")
    result = manager.record_failure("backup")
    assert result is True
    assert manager.is_escalated("backup")


def test_escalation_stays_active_beyond_threshold(manager):
    for _ in range(5):
        manager.record_failure("backup")
    assert manager.is_escalated("backup")
    assert manager.consecutive_count("backup") == 5


def test_success_resets_state(manager):
    manager.record_failure("backup")
    manager.record_failure("backup")
    manager.record_failure("backup")
    assert manager.is_escalated("backup")
    manager.record_success("backup")
    assert not manager.is_escalated("backup")
    assert manager.consecutive_count("backup") == 0


def test_independent_jobs(manager):
    manager.record_failure("job_a")
    manager.record_failure("job_a")
    manager.record_failure("job_a")  # escalates job_a
    assert manager.is_escalated("job_a")
    assert not manager.is_escalated("job_b")
    assert manager.consecutive_count("job_b") == 0


def test_unknown_job_not_escalated(manager):
    assert not manager.is_escalated("unknown")
    assert manager.consecutive_count("unknown") == 0
