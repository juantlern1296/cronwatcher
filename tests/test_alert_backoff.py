"""Tests for cronwatcher.alert_backoff."""
import pytest
from unittest.mock import MagicMock

from cronwatcher.alert_backoff import AlertBackoff, BackoffConfig, parse_backoff_config
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(job_name=job, exit_code=1, timestamp="2024-01-01T00:00:00Z")


# --- BackoffConfig validation ---

def test_invalid_base_delay_raises():
    with pytest.raises(ValueError, match="base_delay"):
        BackoffConfig(base_delay=0.0)


def test_max_delay_less_than_base_raises():
    with pytest.raises(ValueError, match="max_delay"):
        BackoffConfig(base_delay=10.0, max_delay=5.0)


def test_multiplier_must_exceed_one():
    with pytest.raises(ValueError, match="multiplier"):
        BackoffConfig(multiplier=1.0)


def test_max_attempts_must_be_positive():
    with pytest.raises(ValueError, match="max_attempts"):
        BackoffConfig(max_attempts=0)


def test_delay_for_grows_exponentially():
    cfg = BackoffConfig(base_delay=1.0, max_delay=100.0, multiplier=2.0)
    assert cfg.delay_for(0) == 1.0
    assert cfg.delay_for(1) == 2.0
    assert cfg.delay_for(2) == 4.0


def test_delay_capped_at_max():
    cfg = BackoffConfig(base_delay=1.0, max_delay=5.0, multiplier=2.0)
    assert cfg.delay_for(10) == 5.0


# --- AlertBackoff.send ---

@pytest.fixture
def cfg():
    return BackoffConfig(base_delay=0.1, max_delay=1.0, multiplier=2.0, max_attempts=3)


def test_success_on_first_attempt_no_sleep(cfg):
    handler = MagicMock(return_value=True)
    sleep = MagicMock()
    backoff = AlertBackoff(cfg, handler, sleep_fn=sleep)
    result = backoff.send(make_payload())
    assert result is True
    sleep.assert_not_called()
    handler.assert_called_once()


def test_success_on_second_attempt_sleeps_once(cfg):
    handler = MagicMock(side_effect=[False, True])
    sleep = MagicMock()
    backoff = AlertBackoff(cfg, handler, sleep_fn=sleep)
    result = backoff.send(make_payload())
    assert result is True
    sleep.assert_called_once_with(0.1)


def test_all_attempts_fail_returns_false(cfg):
    handler = MagicMock(return_value=False)
    sleep = MagicMock()
    backoff = AlertBackoff(cfg, handler, sleep_fn=sleep)
    result = backoff.send(make_payload("db_backup"))
    assert result is False
    assert handler.call_count == 3


def test_failure_increments_attempt_count(cfg):
    handler = MagicMock(return_value=False)
    backoff = AlertBackoff(cfg, handler, sleep_fn=lambda _: None)
    backoff.send(make_payload("job_x"))
    assert backoff.attempt_count("job_x") == 1
    backoff.send(make_payload("job_x"))
    assert backoff.attempt_count("job_x") == 2


def test_success_clears_attempt_count(cfg):
    handler = MagicMock(side_effect=[False, False, False, True])
    backoff = AlertBackoff(cfg, handler, sleep_fn=lambda _: None)
    backoff.send(make_payload("job_y"))  # all fail
    assert backoff.attempt_count("job_y") == 1
    handler.reset_mock(side_effect=[True])
    handler.return_value = True
    backoff.send(make_payload("job_y"))  # succeeds
    assert backoff.attempt_count("job_y") == 0


def test_unknown_job_attempt_count_is_zero(cfg):
    backoff = AlertBackoff(cfg, MagicMock(return_value=True), sleep_fn=lambda _: None)
    assert backoff.attempt_count("nonexistent") == 0


# --- parse_backoff_config ---

def test_no_section_returns_none():
    assert parse_backoff_config({}) is None


def test_not_a_dict_raises():
    with pytest.raises(ValueError):
        parse_backoff_config({"alert_backoff": "bad"})


def test_valid_config_parsed():
    raw = {"alert_backoff": {"base_delay": 2.0, "max_delay": 30.0, "multiplier": 3.0, "max_attempts": 4}}
    cfg = parse_backoff_config(raw)
    assert cfg is not None
    assert cfg.base_delay == 2.0
    assert cfg.max_delay == 30.0
    assert cfg.multiplier == 3.0
    assert cfg.max_attempts == 4


def test_defaults_applied_when_keys_absent():
    raw = {"alert_backoff": {}}
    cfg = parse_backoff_config(raw)
    assert cfg.base_delay == 1.0
    assert cfg.max_attempts == 5
