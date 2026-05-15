from __future__ import annotations

import time
from typing import List

import pytest

from cronwatcher.alert_counter import AlertCounter, CounterConfig, wrap_with_counter
from cronwatcher.alert_counter_config import counter_handler, parse_counter_config
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup", exit_code: int = 1) -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=exit_code,
        timestamp="2024-01-01T00:00:00Z",
        hostname="host1",
        log_line="FAILED",
    )


def test_invalid_window_raises() -> None:
    with pytest.raises(ValueError, match="window"):
        CounterConfig(window=0, max_count=5)


def test_invalid_max_count_raises() -> None:
    with pytest.raises(ValueError, match="max_count"):
        CounterConfig(window=60.0, max_count=0)


def test_first_increment_count_is_one() -> None:
    cfg = CounterConfig(window=60.0, max_count=5)
    counter = AlertCounter(cfg)
    now = time.monotonic()
    result = counter.increment(make_payload(), now=now)
    assert result.extra_fields["alert_count_in_window"] == 1


def test_second_increment_count_is_two() -> None:
    cfg = CounterConfig(window=60.0, max_count=5)
    counter = AlertCounter(cfg)
    now = time.monotonic()
    counter.increment(make_payload(), now=now)
    result = counter.increment(make_payload(), now=now)
    assert result.extra_fields["alert_count_in_window"] == 2


def test_count_resets_after_window_expires() -> None:
    cfg = CounterConfig(window=10.0, max_count=5)
    counter = AlertCounter(cfg)
    now = time.monotonic()
    counter.increment(make_payload(), now=now)
    counter.increment(make_payload(), now=now)
    result = counter.increment(make_payload(), now=now + 11.0)
    assert result.extra_fields["alert_count_in_window"] == 1


def test_exceeded_flag_false_below_limit() -> None:
    cfg = CounterConfig(window=60.0, max_count=3)
    counter = AlertCounter(cfg)
    now = time.monotonic()
    result = counter.increment(make_payload(), now=now)
    assert result.extra_fields["alert_count_exceeded"] is False


def test_exceeded_flag_true_above_limit() -> None:
    cfg = CounterConfig(window=60.0, max_count=2)
    counter = AlertCounter(cfg)
    now = time.monotonic()
    for _ in range(3):
        result = counter.increment(make_payload(), now=now)
    assert result.extra_fields["alert_count_exceeded"] is True


def test_different_jobs_tracked_independently() -> None:
    cfg = CounterConfig(window=60.0, max_count=5)
    counter = AlertCounter(cfg)
    now = time.monotonic()
    counter.increment(make_payload(job="job_a"), now=now)
    counter.increment(make_payload(job="job_a"), now=now)
    result_b = counter.increment(make_payload(job="job_b"), now=now)
    assert result_b.extra_fields["alert_count_in_window"] == 1


def test_count_for_returns_current_count() -> None:
    cfg = CounterConfig(window=60.0, max_count=5)
    counter = AlertCounter(cfg)
    now = time.monotonic()
    counter.increment(make_payload(), now=now)
    counter.increment(make_payload(), now=now)
    assert counter.count_for("backup", now=now) == 2


def test_wrap_with_counter_calls_handler() -> None:
    cfg = CounterConfig(window=60.0, max_count=5)
    received: List[WebhookPayload] = []
    handler = wrap_with_counter(cfg, received.append)
    handler(make_payload())
    assert len(received) == 1
    assert "alert_count_in_window" in received[0].extra_fields


def test_parse_counter_config_no_section_returns_none() -> None:
    assert parse_counter_config({}) is None


def test_parse_counter_config_disabled_returns_none() -> None:
    assert parse_counter_config({"alert_counter": {"enabled": False}}) is None


def test_parse_counter_config_defaults_applied() -> None:
    cfg = parse_counter_config({"alert_counter": {}})
    assert cfg is not None
    assert cfg.window == 300.0
    assert cfg.max_count == 10


def test_parse_counter_config_custom_values() -> None:
    cfg = parse_counter_config({"alert_counter": {"window": 120, "max_count": 3}})
    assert cfg is not None
    assert cfg.window == 120.0
    assert cfg.max_count == 3


def test_parse_counter_config_not_dict_raises() -> None:
    with pytest.raises(ValueError):
        parse_counter_config({"alert_counter": "bad"})


def test_counter_handler_no_section_passthrough() -> None:
    received: List[WebhookPayload] = []
    handler = counter_handler({}, received.append)
    handler(make_payload())
    assert received[0].extra_fields is None or "alert_count_in_window" not in (received[0].extra_fields or {})
