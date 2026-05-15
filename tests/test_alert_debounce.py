"""Tests for cronwatcher.alert_debounce."""
import pytest

from cronwatcher.alert_debounce import AlertDebounce, DebounceConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        message="failed",
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
    )


# --- DebounceConfig validation ---

def test_invalid_min_failures_raises():
    with pytest.raises(ValueError, match="min_failures"):
        DebounceConfig(min_failures=0)


def test_invalid_per_job_min_failures_raises():
    with pytest.raises(ValueError, match="per_job"):
        DebounceConfig(min_failures=2, per_job={"backup": 0})


def test_valid_config_created():
    cfg = DebounceConfig(min_failures=3, per_job={"sync": 5})
    assert cfg.threshold_for("sync") == 5
    assert cfg.threshold_for("other") == 3


def test_threshold_for_unknown_job_returns_default():
    cfg = DebounceConfig(min_failures=2)
    assert cfg.threshold_for("unknown") == 2


# --- AlertDebounce behaviour ---

@pytest.fixture
def calls():
    return []


@pytest.fixture
def debounce(calls):
    cfg = DebounceConfig(min_failures=3)
    return AlertDebounce(cfg, lambda p: calls.append(p))


def test_below_threshold_does_not_forward(debounce, calls):
    p = make_payload()
    debounce.process(p)
    debounce.process(p)
    assert calls == []


def test_at_threshold_forwards(debounce, calls):
    p = make_payload()
    for _ in range(3):
        debounce.process(p)
    assert len(calls) == 1


def test_above_threshold_continues_forwarding(debounce, calls):
    p = make_payload()
    for _ in range(5):
        debounce.process(p)
    assert len(calls) == 3


def test_success_resets_counter(debounce, calls):
    p = make_payload()
    debounce.process(p)
    debounce.process(p)
    debounce.record_success("backup")
    assert debounce.consecutive_count("backup") == 0
    debounce.process(p)
    debounce.process(p)
    # still only 2 after reset, threshold is 3
    assert calls == []


def test_per_job_threshold_respected(calls):
    cfg = DebounceConfig(min_failures=3, per_job={"sync": 1})
    debounce = AlertDebounce(cfg, lambda p: calls.append(p))
    p = make_payload(job="sync")
    result = debounce.process(p)
    assert result is True
    assert len(calls) == 1


def test_consecutive_count_tracked(debounce):
    p = make_payload()
    debounce.process(p)
    debounce.process(p)
    assert debounce.consecutive_count("backup") == 2


def test_process_returns_false_below_threshold(debounce):
    p = make_payload()
    assert debounce.process(p) is False


def test_process_returns_true_at_threshold(debounce):
    p = make_payload()
    debounce.process(p)
    debounce.process(p)
    assert debounce.process(p) is True
