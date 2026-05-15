"""Tests for cronwatcher.alert_sequence."""
import pytest

from cronwatcher.alert_sequence import AlertSequence, SequenceConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        message="failed",
        hostname="host1",
        timestamp="2024-01-01T00:00:00",
        extra={},
    )


# --- SequenceConfig validation ---

def test_invalid_min_consecutive_raises():
    with pytest.raises(ValueError, match="min_consecutive"):
        SequenceConfig(min_consecutive=0)


def test_invalid_per_job_raises():
    with pytest.raises(ValueError, match="per_job"):
        SequenceConfig(per_job={"backup": 0})


def test_valid_config_created():
    cfg = SequenceConfig(min_consecutive=2, per_job={"sync": 5})
    assert cfg.threshold_for("sync") == 5
    assert cfg.threshold_for("other") == 2


# --- AlertSequence behaviour ---

@pytest.fixture
def calls():
    return []


@pytest.fixture
def seq(calls):
    cfg = SequenceConfig(min_consecutive=3)
    return AlertSequence(cfg, calls.append)


def test_below_threshold_does_not_fire(seq, calls):
    p = make_payload()
    seq.record(p)
    seq.record(p)
    assert calls == []


def test_at_threshold_fires(seq, calls):
    p = make_payload()
    for _ in range(3):
        seq.record(p)
    assert len(calls) == 1


def test_counter_resets_after_fire(seq, calls):
    p = make_payload()
    for _ in range(3):
        seq.record(p)
    # one more cycle
    for _ in range(3):
        seq.record(p)
    assert len(calls) == 2


def test_partial_count_after_fire(seq, calls):
    p = make_payload()
    for _ in range(3):
        seq.record(p)
    seq.record(p)
    assert seq.consecutive_count("backup") == 1


def test_per_job_threshold_respected(calls):
    cfg = SequenceConfig(min_consecutive=3, per_job={"sync": 2})
    seq = AlertSequence(cfg, calls.append)
    p = make_payload("sync")
    seq.record(p)
    assert calls == []
    seq.record(p)
    assert len(calls) == 1


def test_reset_clears_counter(seq, calls):
    p = make_payload()
    seq.record(p)
    seq.record(p)
    seq.reset("backup")
    assert seq.consecutive_count("backup") == 0
    # need full 3 again
    seq.record(p)
    seq.record(p)
    assert calls == []


def test_unknown_job_count_is_zero(seq):
    assert seq.consecutive_count("nonexistent") == 0


def test_none_job_name_uses_fallback(calls):
    cfg = SequenceConfig(min_consecutive=2)
    seq = AlertSequence(cfg, calls.append)
    p = WebhookPayload(
        job_name=None,
        exit_code=1,
        message="oops",
        hostname="h",
        timestamp="t",
        extra={},
    )
    seq.record(p)
    seq.record(p)
    assert len(calls) == 1
