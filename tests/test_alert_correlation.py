"""Tests for alert_correlation and alert_correlation_config."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cronwatcher.alert_correlation import AlertCorrelator, CorrelationConfig
from cronwatcher.alert_correlation_config import parse_alert_correlation
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str, labels: dict | None = None) -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        timestamp="2024-01-01T00:00:00Z",
        hostname="host",
        extra_fields=labels or {},
    )


@pytest.fixture
def callback():
    return MagicMock()


@pytest.fixture
def correlator(callback):
    cfg = CorrelationConfig(window_seconds=30.0, group_by="job", min_count=2)
    return AlertCorrelator(cfg, callback)


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        CorrelationConfig(window_seconds=0, group_by="job")


def test_invalid_min_count_raises():
    with pytest.raises(ValueError, match="min_count"):
        CorrelationConfig(window_seconds=10, group_by="job", min_count=0)


def test_invalid_group_by_raises():
    with pytest.raises(ValueError, match="group_by"):
        CorrelationConfig(window_seconds=10, group_by="unknown_field")


def test_single_event_does_not_fire(correlator, callback):
    correlator.add(make_payload("backup"))
    callback.assert_not_called()


def test_two_events_fires_correlated(correlator, callback):
    correlator.add(make_payload("backup"))
    correlator.add(make_payload("backup"))
    callback.assert_called_once()
    key, events = callback.call_args[0]
    assert key == "backup"
    assert len(events) == 2


def test_different_jobs_do_not_correlate(correlator, callback):
    correlator.add(make_payload("backup"))
    correlator.add(make_payload("cleanup"))
    callback.assert_not_called()


def test_pattern_filters_non_matching(callback):
    cfg = CorrelationConfig(window_seconds=30, group_by="job", min_count=2, pattern=r"^backup")
    c = AlertCorrelator(cfg, callback)
    c.add(make_payload("backup_daily"))
    c.add(make_payload("cleanup"))  # doesn't match pattern
    callback.assert_not_called()


def test_group_by_label(callback):
    cfg = CorrelationConfig(window_seconds=30, group_by="label:env", min_count=2)
    c = AlertCorrelator(cfg, callback)
    c.add(make_payload("job1", labels={"env": "prod"}))
    c.add(make_payload("job2", labels={"env": "prod"}))
    callback.assert_called_once()
    key, events = callback.call_args[0]
    assert key == "prod"
    assert len(events) == 2


def test_flush_all_fires_if_min_met(callback):
    cfg = CorrelationConfig(window_seconds=60, group_by="job", min_count=2)
    c = AlertCorrelator(cfg, callback)
    c.add(make_payload("deploy"))
    c.add(make_payload("deploy"))
    # already fired; flush_all on empty should be fine
    c.flush_all()
    assert callback.call_count == 1


# --- config parsing ---

def test_no_section_returns_none():
    assert parse_alert_correlation({}) is None


def test_valid_minimal_config():
    cfg = parse_alert_correlation({"alert_correlation": {"window_seconds": 45, "group_by": "job"}})
    assert cfg is not None
    assert cfg.window_seconds == 45.0
    assert cfg.group_by == "job"
    assert cfg.min_count == 2


def test_custom_min_count():
    cfg = parse_alert_correlation({"alert_correlation": {"window_seconds": 10, "group_by": "job", "min_count": 3}})
    assert cfg.min_count == 3


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="JSON object"):
        parse_alert_correlation({"alert_correlation": "bad"})


def test_invalid_window_in_config_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        parse_alert_correlation({"alert_correlation": {"window_seconds": "nope", "group_by": "job"}})
