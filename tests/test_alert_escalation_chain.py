"""Tests for EscalationChain."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_escalation_chain import (
    ChainStep,
    EscalationChain,
    EscalationChainConfig,
)
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup", failures: int = 1) -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        command="/usr/bin/backup",
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        failure_count=failures,
    )


@pytest.fixture
def cfg() -> EscalationChainConfig:
    return EscalationChainConfig(steps=[
        ChainStep(min_failures=1, channel_name="default"),
        ChainStep(min_failures=3, channel_name="oncall"),
        ChainStep(min_failures=5, channel_name="pagerduty"),
    ])


@pytest.fixture
def dispatch():
    return MagicMock()


@pytest.fixture
def chain(cfg, dispatch) -> EscalationChain:
    return EscalationChain(config=cfg, dispatch=dispatch)


def test_empty_steps_raises():
    with pytest.raises(ValueError, match="at least one step"):
        EscalationChainConfig(steps=[])


def test_invalid_min_failures_raises():
    with pytest.raises(ValueError, match="min_failures"):
        EscalationChainConfig(steps=[ChainStep(min_failures=0, channel_name="x")])


def test_first_failure_uses_default_channel(chain, dispatch):
    p = make_payload()
    channel = chain.record_failure(p)
    assert channel == "default"
    dispatch.assert_called_once_with("default", p)


def test_third_failure_escalates_to_oncall(chain, dispatch):
    p = make_payload()
    for _ in range(3):
        chain.record_failure(p)
    assert dispatch.call_args[0][0] == "oncall"


def test_fifth_failure_escalates_to_pagerduty(chain, dispatch):
    p = make_payload()
    for _ in range(5):
        chain.record_failure(p)
    assert dispatch.call_args[0][0] == "pagerduty"


def test_success_resets_count(chain):
    p = make_payload()
    chain.record_failure(p)
    chain.record_failure(p)
    chain.record_success("backup")
    assert chain.failure_count("backup") == 0


def test_different_jobs_tracked_independently(chain, dispatch):
    chain.record_failure(make_payload(job="job_a"))
    chain.record_failure(make_payload(job="job_a"))
    chain.record_failure(make_payload(job="job_b"))
    assert chain.failure_count("job_a") == 2
    assert chain.failure_count("job_b") == 1


def test_no_matching_step_returns_none():
    cfg = EscalationChainConfig(steps=[
        ChainStep(min_failures=10, channel_name="high"),
    ])
    dispatch = MagicMock()
    c = EscalationChain(config=cfg, dispatch=dispatch)
    result = c.record_failure(make_payload())
    assert result is None
    dispatch.assert_not_called()
