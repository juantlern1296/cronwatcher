"""Tests for cronwatcher.alert_ttl."""
import pytest
from unittest.mock import MagicMock
from cronwatcher.alert_ttl import TTLConfig, AlertTTL, parse_ttl_config
from cronwatcher.webhook import WebhookPayload


def make_payload(job_name: str = "backup") -> WebhookPayload:
    return WebhookPayload(job_name=job_name, exit_code=1, message="failed", timestamp="2024-01-01T00:00:00Z")


# --- TTLConfig ---

def test_invalid_default_ttl_raises():
    with pytest.raises(ValueError, match="default_ttl must be positive"):
        TTLConfig(default_ttl=0)


def test_negative_default_ttl_raises():
    with pytest.raises(ValueError, match="default_ttl must be positive"):
        TTLConfig(default_ttl=-10)


def test_invalid_per_job_ttl_raises():
    with pytest.raises(ValueError, match="TTL for job 'sync'"):
        TTLConfig(default_ttl=60, per_job={"sync": -5})


def test_ttl_for_returns_per_job_override():
    cfg = TTLConfig(default_ttl=3600, per_job={"backup": 600})
    assert cfg.ttl_for("backup") == 600


def test_ttl_for_returns_default_for_unknown_job():
    cfg = TTLConfig(default_ttl=3600)
    assert cfg.ttl_for("unknown") == 3600


# --- AlertTTL ---

@pytest.fixture
def cfg():
    return TTLConfig(default_ttl=300)


@pytest.fixture
def ttl(cfg):
    return AlertTTL(cfg)


def test_unknown_job_is_not_expired(ttl):
    assert not ttl.is_expired("backup", now=1000)


def test_job_not_expired_within_ttl(ttl):
    ttl.record("backup", now=1000)
    assert not ttl.is_expired("backup", now=1200)


def test_job_expired_after_ttl(ttl):
    ttl.record("backup", now=1000)
    assert ttl.is_expired("backup", now=1301)


def test_clear_removes_record(ttl):
    ttl.record("backup", now=1000)
    ttl.clear("backup")
    assert not ttl.is_expired("backup", now=9999)


def test_check_calls_handler_when_not_expired(ttl):
    handler = MagicMock()
    payload = make_payload("backup")
    ttl.check(payload, handler, now=1000)
    handler.assert_called_once_with(payload)


def test_check_suppresses_handler_when_expired(ttl):
    handler = MagicMock()
    payload = make_payload("backup")
    ttl.record("backup", now=0)
    ttl.check(payload, handler, now=400)
    handler.assert_not_called()


def test_check_calls_on_expire_callback_when_expired():
    cfg = TTLConfig(default_ttl=100)
    on_expire = MagicMock()
    alerter = AlertTTL(cfg, on_expire=on_expire)
    alerter.record("sync", now=0)
    alerter.check(make_payload("sync"), MagicMock(), now=200)
    on_expire.assert_called_once_with("sync")


# --- parse_ttl_config ---

def test_no_section_returns_none():
    assert parse_ttl_config({}) is None


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_ttl_config({"alert_ttl": "bad"})


def test_defaults_applied():
    result = parse_ttl_config({"alert_ttl": {}})
    assert result is not None
    assert result.default_ttl == 3600


def test_custom_values():
    result = parse_ttl_config({"alert_ttl": {"default_ttl": 600, "per_job": {"backup": 120}}})
    assert result.default_ttl == 600
    assert result.per_job["backup"] == 120


def test_per_job_not_dict_raises():
    with pytest.raises(ValueError, match="per_job must be a dict"):
        parse_ttl_config({"alert_ttl": {"default_ttl": 60, "per_job": "bad"}})
