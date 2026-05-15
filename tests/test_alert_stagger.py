"""Tests for alert_stagger."""
import time
import threading
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_stagger import StaggerConfig, AlertStagger
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        command="/usr/bin/backup",
        timestamp="2024-01-01T00:00:00Z",
        hostname="host1",
        message="failed",
    )


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window must be positive"):
        StaggerConfig(window=0)


def test_negative_window_raises():
    with pytest.raises(ValueError, match="window must be positive"):
        StaggerConfig(window=-1.0)


def test_per_job_invalid_window_raises():
    with pytest.raises(ValueError, match="backup"):
        StaggerConfig(window=1.0, per_job={"backup": -5.0})


def test_window_for_returns_default():
    cfg = StaggerConfig(window=2.0)
    assert cfg.window_for("unknown_job") == 2.0


def test_window_for_returns_per_job():
    cfg = StaggerConfig(window=2.0, per_job={"backup": 0.5})
    assert cfg.window_for("backup") == 0.5


def test_dispatch_eventually_calls_handler():
    handler = MagicMock()
    cfg = StaggerConfig(window=0.05)
    stagger = AlertStagger(cfg, handler)
    payload = make_payload()
    stagger.dispatch(payload)
    time.sleep(0.2)
    handler.assert_called_once_with(payload)


def test_pending_count_increments_then_clears():
    handler = MagicMock()
    cfg = StaggerConfig(window=0.5)
    stagger = AlertStagger(cfg, handler)
    stagger.dispatch(make_payload("job1"))
    stagger.dispatch(make_payload("job2"))
    assert stagger.pending_count == 2
    stagger.cancel_all()
    assert stagger.pending_count == 0


def test_second_dispatch_same_job_cancels_first():
    calls = []
    event = threading.Event()

    def handler(p):
        calls.append(p)
        event.set()

    cfg = StaggerConfig(window=0.05)
    stagger = AlertStagger(cfg, handler)
    p1 = make_payload("backup")
    p2 = make_payload("backup")
    stagger.dispatch(p1)
    stagger.dispatch(p2)
    event.wait(timeout=0.5)
    assert len(calls) == 1
    assert calls[0] is p2


def test_cancel_all_prevents_handler_call():
    handler = MagicMock()
    cfg = StaggerConfig(window=0.3)
    stagger = AlertStagger(cfg, handler)
    stagger.dispatch(make_payload())
    stagger.cancel_all()
    time.sleep(0.4)
    handler.assert_not_called()
