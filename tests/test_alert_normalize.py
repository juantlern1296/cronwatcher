"""Tests for alert_normalize and alert_normalize_config."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatcher.alert_normalize import AlertNormalizer, NormalizeConfig, normalize_payload
from cronwatcher.alert_normalize_config import normalized_handler, parse_normalize_config
from cronwatcher.webhook import WebhookPayload


def make_payload(**kwargs) -> WebhookPayload:
    defaults = dict(
        job_name="BackupJob",
        exit_code=1,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        hostname="host1",
        message="  Some error  ",
        extra={"env": "  prod  "},
    )
    defaults.update(kwargs)
    return WebhookPayload(**defaults)


# --- NormalizeConfig validation ---

def test_invalid_max_message_length_raises():
    with pytest.raises(ValueError):
        NormalizeConfig(max_message_length=0)


def test_negative_max_message_length_raises():
    with pytest.raises(ValueError):
        NormalizeConfig(max_message_length=-5)


# --- normalize_payload ---

def test_strip_whitespace_strips_message():
    cfg = NormalizeConfig(strip_whitespace=True, lowercase_job_name=False)
    result = normalize_payload(make_payload(), cfg)
    assert result.message == "Some error"


def test_strip_whitespace_strips_hostname():
    cfg = NormalizeConfig(strip_whitespace=True, lowercase_job_name=False)
    p = make_payload(hostname="  myhost  ")
    result = normalize_payload(p, cfg)
    assert result.hostname == "myhost"


def test_strip_whitespace_strips_extra_values():
    cfg = NormalizeConfig(strip_whitespace=True, lowercase_job_name=False)
    result = normalize_payload(make_payload(), cfg)
    assert result.extra["env"] == "prod"


def test_lowercase_job_name():
    cfg = NormalizeConfig(lowercase_job_name=True, strip_whitespace=False)
    result = normalize_payload(make_payload(), cfg)
    assert result.job_name == "backupjob"


def test_no_lowercase_preserves_case():
    cfg = NormalizeConfig(lowercase_job_name=False, strip_whitespace=False)
    result = normalize_payload(make_payload(), cfg)
    assert result.job_name == "BackupJob"


def test_max_message_length_truncates():
    cfg = NormalizeConfig(strip_whitespace=False, lowercase_job_name=False, max_message_length=4)
    p = make_payload(message="toolong")
    result = normalize_payload(p, cfg)
    assert result.message == "tool"


def test_none_job_name_handled():
    cfg = NormalizeConfig(lowercase_job_name=True, strip_whitespace=True)
    result = normalize_payload(make_payload(job_name=None), cfg)
    assert result.job_name is None


# --- AlertNormalizer ---

def test_normalizer_calls_handler():
    received = []
    cfg = NormalizeConfig()
    normalizer = AlertNormalizer(config=cfg, handler=received.append)
    normalizer.handle(make_payload())
    assert len(received) == 1
    assert received[0].job_name == "backupjob"


# --- parse_normalize_config ---

def test_no_section_returns_none():
    assert parse_normalize_config({}) is None


def test_enabled_false_returns_none():
    assert parse_normalize_config({"normalize": {"enabled": False}}) is None


def test_not_a_dict_raises():
    with pytest.raises((ValueError, AttributeError)):
        parse_normalize_config({"normalize": "yes"})


def test_defaults_applied():
    cfg = parse_normalize_config({"normalize": {"enabled": True}})
    assert cfg is not None
    assert cfg.lowercase_job_name is True
    assert cfg.strip_whitespace is True
    assert cfg.max_message_length is None


def test_custom_values():
    cfg = parse_normalize_config({
        "normalize": {
            "enabled": True,
            "lowercase_job_name": False,
            "strip_whitespace": False,
            "max_message_length": 200,
        }
    })
    assert cfg.lowercase_job_name is False
    assert cfg.strip_whitespace is False
    assert cfg.max_message_length == 200


# --- normalized_handler ---

def test_normalized_handler_no_section_returns_original():
    handler = lambda p: None
    result = normalized_handler({}, handler)
    assert result is handler


def test_normalized_handler_with_section_wraps():
    received = []
    raw = {"normalize": {"enabled": True}}
    wrapped = normalized_handler(raw, received.append)
    wrapped(make_payload(job_name="  MyJob  "))
    assert received[0].job_name == "myjob"
