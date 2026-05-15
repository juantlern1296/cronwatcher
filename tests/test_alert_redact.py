"""Tests for alert_redact and alert_redact_config."""
import pytest

from cronwatcher.alert_redact import (
    RedactConfig,
    redact_payload,
    AlertRedactor,
)
from cronwatcher.alert_redact_config import parse_redact_config, redacted_handler
from cronwatcher.webhook import WebhookPayload


def make_payload(**extra) -> WebhookPayload:
    return WebhookPayload(
        job_name="backup",
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        message="failed",
        extra_fields=extra or None,
    )


# --- RedactConfig validation ---

def test_empty_mask_raises():
    with pytest.raises(ValueError, match="mask"):
        RedactConfig(mask="")


def test_default_mask_is_stars():
    cfg = RedactConfig()
    assert cfg.mask == "***"


# --- redact_payload ---

def test_password_field_is_masked():
    cfg = RedactConfig()
    p = make_payload(password="s3cr3t", user="alice")
    result = redact_payload(p, cfg)
    assert result.extra_fields["password"] == "***"
    assert result.extra_fields["user"] == "alice"


def test_token_field_is_masked():
    cfg = RedactConfig()
    p = make_payload(api_token="tok123")
    result = redact_payload(p, cfg)
    assert result.extra_fields["api_token"] == "***"


def test_secret_field_is_masked():
    cfg = RedactConfig()
    p = make_payload(my_secret="abc")
    result = redact_payload(p, cfg)
    assert result.extra_fields["my_secret"] == "***"


def test_extra_field_in_config_is_masked():
    cfg = RedactConfig(extra_fields=["internal_id"])
    p = make_payload(internal_id="42", name="job")
    result = redact_payload(p, cfg)
    assert result.extra_fields["internal_id"] == "***"
    assert result.extra_fields["name"] == "job"


def test_custom_mask_used():
    cfg = RedactConfig(mask="[REDACTED]")
    p = make_payload(password="pw")
    result = redact_payload(p, cfg)
    assert result.extra_fields["password"] == "[REDACTED]"


def test_no_extra_fields_returns_unchanged():
    cfg = RedactConfig()
    p = make_payload()
    result = redact_payload(p, cfg)
    assert result is p


def test_original_payload_not_mutated():
    cfg = RedactConfig()
    p = make_payload(password="pw", user="alice")
    redact_payload(p, cfg)
    assert p.extra_fields["password"] == "pw"


# --- AlertRedactor ---

def test_redactor_calls_handler_with_redacted_payload():
    calls = []
    cfg = RedactConfig()
    redactor = AlertRedactor(cfg, calls.append)
    p = make_payload(api_key="secret123", region="us-east")
    redactor.handle(p)
    assert len(calls) == 1
    assert calls[0].extra_fields["api_key"] == "***"
    assert calls[0].extra_fields["region"] == "us-east"


# --- parse_redact_config ---

def test_no_section_returns_none():
    assert parse_redact_config({}) is None


def test_enabled_false_returns_none():
    assert parse_redact_config({"alert_redact": {"enabled": False}}) is None


def test_not_a_dict_raises():
    with pytest.raises(ValueError):
        parse_redact_config({"alert_redact": ["oops"]})


def test_invalid_mask_raises():
    with pytest.raises(ValueError, match="mask"):
        parse_redact_config({"alert_redact": {"mask": ""}})


def test_extra_fields_not_list_raises():
    with pytest.raises(ValueError, match="extra_fields"):
        parse_redact_config({"alert_redact": {"extra_fields": "bad"}})


def test_valid_config_parsed():
    cfg = parse_redact_config({"alert_redact": {"mask": "XXXX", "extra_fields": ["env"]}})
    assert cfg is not None
    assert cfg.mask == "XXXX"
    assert "env" in cfg.extra_fields


# --- redacted_handler ---

def test_redacted_handler_no_section_returns_original():
    handler = lambda p: None
    result = redacted_handler({}, handler)
    assert result is handler


def test_redacted_handler_wraps_when_configured():
    calls = []
    raw = {"alert_redact": {"enabled": True}}
    wrapped = redacted_handler(raw, calls.append)
    p = make_payload(password="pw")
    wrapped(p)
    assert calls[0].extra_fields["password"] == "***"
