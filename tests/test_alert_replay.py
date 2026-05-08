"""Tests for alert_replay and alert_replay_config."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_replay import AlertReplayer, ReplayConfig
from cronwatcher.alert_replay_config import parse_replay_config
from cronwatcher.config import WebhookConfig
from cronwatcher.dead_letter import DeadLetterQueue
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        timestamp=datetime.now(timezone.utc).isoformat(),
        hostname="host1",
        log_line="error",
    )


@pytest.fixture()
def webhook_cfg() -> WebhookConfig:
    return WebhookConfig(url="https://hooks.example.com/alert", headers={})


@pytest.fixture()
def queue() -> DeadLetterQueue:
    return DeadLetterQueue(max_size=20)


# --- ReplayConfig ---

def test_invalid_max_replays_raises():
    with pytest.raises(ValueError):
        ReplayConfig(max_replays=0)


def test_defaults_are_sane():
    cfg = ReplayConfig()
    assert cfg.max_replays == 50
    assert cfg.dry_run is False


# --- AlertReplayer ---

def test_empty_queue_returns_zero(queue, webhook_cfg):
    replayer = AlertReplayer(queue, webhook_cfg)
    assert replayer.replay() == 0


def test_successful_replay_returns_count(queue, webhook_cfg):
    queue.push(make_payload("job1"))
    queue.push(make_payload("job2"))
    send_fn = MagicMock(return_value=True)
    replayer = AlertReplayer(queue, webhook_cfg, send_fn=send_fn)
    result = replayer.replay()
    assert result == 2
    assert send_fn.call_count == 2


def test_failed_replay_requeues(queue, webhook_cfg):
    queue.push(make_payload("flaky"))
    send_fn = MagicMock(return_value=False)
    replayer = AlertReplayer(queue, webhook_cfg, send_fn=send_fn)
    result = replayer.replay()
    assert result == 0
    assert queue.size == 1


def test_dry_run_does_not_call_send(queue, webhook_cfg):
    queue.push(make_payload("job"))
    send_fn = MagicMock()
    cfg = ReplayConfig(dry_run=True)
    replayer = AlertReplayer(queue, webhook_cfg, config=cfg, send_fn=send_fn)
    result = replayer.replay()
    assert result == 1
    send_fn.assert_not_called()


def test_max_replays_limits_processing(queue, webhook_cfg):
    for i in range(10):
        queue.push(make_payload(f"job{i}"))
    send_fn = MagicMock(return_value=True)
    cfg = ReplayConfig(max_replays=3)
    replayer = AlertReplayer(queue, webhook_cfg, config=cfg, send_fn=send_fn)
    result = replayer.replay()
    assert result == 3
    assert send_fn.call_count == 3


# --- parse_replay_config ---

def test_no_section_returns_none():
    assert parse_replay_config({}) is None


def test_valid_config_parsed():
    cfg = parse_replay_config({"replay": {"max_replays": 10, "dry_run": True}})
    assert cfg is not None
    assert cfg.max_replays == 10
    assert cfg.dry_run is True


def test_defaults_when_keys_absent():
    cfg = parse_replay_config({"replay": {}})
    assert cfg.max_replays == 50
    assert cfg.dry_run is False


def test_not_a_dict_raises():
    with pytest.raises(ValueError):
        parse_replay_config({"replay": ["bad"]})


def test_invalid_max_replays_in_config_raises():
    with pytest.raises(ValueError):
        parse_replay_config({"replay": {"max_replays": -1}})
