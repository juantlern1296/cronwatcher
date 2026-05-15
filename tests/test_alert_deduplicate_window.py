import time
import pytest
from unittest.mock import MagicMock
from cronwatcher.alert_deduplicate_window import (
    AlertDeduplicateWindow,
    DeduplicateWindowConfig,
    parse_deduplicate_window_config,
)
from cronwatcher.webhook import WebhookPayload


def make_payload(job="backup", exit_code=1, message="failed") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=exit_code,
        message=message,
        hostname="host1",
        timestamp="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def cfg():
    return DeduplicateWindowConfig(window_seconds=60.0)


@pytest.fixture
def dedup(cfg):
    return AlertDeduplicateWindow(cfg)


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds must be positive"):
        DeduplicateWindowConfig(window_seconds=0)


def test_empty_fields_raises():
    with pytest.raises(ValueError, match="fields must not be empty"):
        DeduplicateWindowConfig(window_seconds=10, fields=())


def test_new_payload_is_not_duplicate(dedup):
    p = make_payload()
    assert not dedup.is_duplicate(p)


def test_payload_is_duplicate_after_record(dedup):
    p = make_payload()
    now = time.monotonic()
    dedup.record(p, now=now)
    assert dedup.is_duplicate(p, now=now + 1)


def test_payload_not_duplicate_after_window_expires(dedup):
    p = make_payload()
    now = time.monotonic()
    dedup.record(p, now=now)
    assert not dedup.is_duplicate(p, now=now + 61)


def test_different_exit_code_is_not_duplicate(dedup):
    now = time.monotonic()
    dedup.record(make_payload(exit_code=1), now=now)
    assert not dedup.is_duplicate(make_payload(exit_code=2), now=now + 1)


def test_handle_calls_handler_once_for_duplicates(dedup):
    handler = MagicMock()
    p = make_payload()
    now = time.monotonic()
    dedup.handle(p, handler)
    # second call with same payload should be suppressed
    dedup.handle(p, handler)
    assert handler.call_count == 1


def test_handle_calls_handler_again_after_window_expires():
    cfg = DeduplicateWindowConfig(window_seconds=30)
    d = AlertDeduplicateWindow(cfg)
    handler = MagicMock()
    p = make_payload()
    now = 1000.0
    d.record(p, now=now)
    assert d.is_duplicate(p, now=now + 10)
    assert not d.is_duplicate(p, now=now + 31)


def test_parse_no_section_returns_none():
    assert parse_deduplicate_window_config({}) is None


def test_parse_enabled_false_returns_none():
    assert parse_deduplicate_window_config({"alert_deduplicate_window": {"enabled": False}}) is None


def test_parse_not_dict_raises():
    with pytest.raises(ValueError):
        parse_deduplicate_window_config({"alert_deduplicate_window": "bad"})


def test_parse_defaults_applied():
    cfg = parse_deduplicate_window_config({"alert_deduplicate_window": {}})
    assert cfg is not None
    assert cfg.window_seconds == 60.0
    assert "job" in cfg.fields


def test_parse_custom_values():
    cfg = parse_deduplicate_window_config({
        "alert_deduplicate_window": {
            "window_seconds": 120,
            "fields": ["job", "message"],
        }
    })
    assert cfg.window_seconds == 120.0
    assert cfg.fields == ("job", "message")
