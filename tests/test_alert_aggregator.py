"""Tests for cronwatcher.alert_aggregator."""

import time
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_aggregator import (
    AggregatorConfig,
    AlertAggregator,
    parse_alert_aggregator,
)
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        raw_line=f"{job} failed",
    )


@pytest.fixture
def callback():
    return MagicMock()


@pytest.fixture
def aggregator(callback):
    cfg = AggregatorConfig(window_seconds=60, min_count=3)
    return AlertAggregator(cfg, callback)


def test_invalid_window_raises(callback):
    with pytest.raises(ValueError, match="window_seconds"):
        AlertAggregator(AggregatorConfig(window_seconds=0, min_count=1), callback)


def test_invalid_min_count_raises(callback):
    with pytest.raises(ValueError, match="min_count"):
        AlertAggregator(AggregatorConfig(window_seconds=10, min_count=0), callback)


def test_pending_count_starts_at_zero(aggregator):
    assert aggregator.pending_count("backup") == 0


def test_add_increments_pending(aggregator):
    aggregator.add("backup", make_payload())
    assert aggregator.pending_count("backup") == 1


def test_flush_triggered_at_min_count(callback, aggregator):
    for _ in range(3):
        aggregator.add("backup", make_payload())
    callback.assert_called_once()
    name, payloads = callback.call_args[0]
    assert name == "backup"
    assert len(payloads) == 3


def test_flush_resets_bucket(aggregator, callback):
    for _ in range(3):
        aggregator.add("backup", make_payload())
    assert aggregator.pending_count("backup") == 0


def test_flush_all_dispatches_pending(callback):
    cfg = AggregatorConfig(window_seconds=9999, min_count=100)
    agg = AlertAggregator(cfg, callback)
    agg.add("nightly", make_payload("nightly"))
    agg.add("nightly", make_payload("nightly"))
    callback.assert_not_called()
    agg.flush_all()
    callback.assert_called_once()
    assert callback.call_args[0][0] == "nightly"


def test_flush_all_clears_all_jobs(callback):
    cfg = AggregatorConfig(window_seconds=9999, min_count=100)
    agg = AlertAggregator(cfg, callback)
    agg.add("job_a", make_payload("job_a"))
    agg.add("job_b", make_payload("job_b"))
    agg.flush_all()
    assert callback.call_count == 2
    assert agg.pending_count("job_a") == 0
    assert agg.pending_count("job_b") == 0


def test_parse_no_section_returns_none(callback):
    assert parse_alert_aggregator({}, callback) is None


def test_parse_valid_section(callback):
    cfg = {"alert_aggregator": {"window_seconds": 15, "min_count": 2}}
    agg = parse_alert_aggregator(cfg, callback)
    assert isinstance(agg, AlertAggregator)


def test_parse_not_dict_raises(callback):
    with pytest.raises(ValueError):
        parse_alert_aggregator({"alert_aggregator": "bad"}, callback)
