"""Tests for cronwatcher.alert_sampling and alert_sampling_config."""
from __future__ import annotations

import random
from unittest.mock import MagicMock

import pytest

from cronwatcher.alert_sampling import AlertSampler, SamplingConfig, parse_sampling_config
from cronwatcher.alert_sampling_config import wrap_with_sampler
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(job_name=job, exit_code=1, timestamp="2024-01-01T00:00:00Z")


# ---------------------------------------------------------------------------
# SamplingConfig validation
# ---------------------------------------------------------------------------

def test_invalid_rate_zero_raises():
    with pytest.raises(ValueError, match="rate"):
        SamplingConfig(rate=0.0)


def test_invalid_rate_above_one_raises():
    with pytest.raises(ValueError, match="rate"):
        SamplingConfig(rate=1.5)


def test_invalid_per_job_rate_raises():
    with pytest.raises(ValueError, match="per_job rate"):
        SamplingConfig(rate=1.0, per_job={"backup": 0.0})


def test_rate_for_returns_per_job_override():
    cfg = SamplingConfig(rate=0.5, per_job={"backup": 0.1})
    assert cfg.rate_for("backup") == 0.1


def test_rate_for_falls_back_to_default():
    cfg = SamplingConfig(rate=0.5, per_job={"backup": 0.1})
    assert cfg.rate_for("other") == 0.5


# ---------------------------------------------------------------------------
# AlertSampler behaviour
# ---------------------------------------------------------------------------

def test_always_forwards_when_rate_is_one():
    handler = MagicMock()
    cfg = SamplingConfig(rate=1.0)
    sampler = AlertSampler(cfg, handler)
    for _ in range(10):
        result = sampler.add(make_payload())
        assert result is True
    assert handler.call_count == 10


def test_never_forwards_when_rng_always_above_rate():
    handler = MagicMock()
    cfg = SamplingConfig(rate=0.1)
    rng = MagicMock()
    rng.random.return_value = 0.99  # always above rate
    sampler = AlertSampler(cfg, handler, rng=rng)
    result = sampler.add(make_payload())
    assert result is False
    handler.assert_not_called()


def test_forwards_when_rng_below_rate():
    handler = MagicMock()
    cfg = SamplingConfig(rate=0.5)
    rng = MagicMock()
    rng.random.return_value = 0.49
    sampler = AlertSampler(cfg, handler, rng=rng)
    result = sampler.add(make_payload())
    assert result is True
    handler.assert_called_once()


def test_per_job_rate_used_for_matching_job():
    handler = MagicMock()
    cfg = SamplingConfig(rate=1.0, per_job={"backup": 0.1})
    rng = MagicMock()
    rng.random.return_value = 0.5  # above per-job rate of 0.1
    sampler = AlertSampler(cfg, handler, rng=rng)
    result = sampler.add(make_payload("backup"))
    assert result is False
    handler.assert_not_called()


# ---------------------------------------------------------------------------
# parse_sampling_config
# ---------------------------------------------------------------------------

def test_no_section_returns_none():
    assert parse_sampling_config({}) is None


def test_valid_minimal_config():
    cfg = parse_sampling_config({"sampling": {"rate": 0.5}})
    assert cfg is not None
    assert cfg.rate == 0.5


def test_per_job_parsed():
    raw = {"sampling": {"rate": 1.0, "per_job": {"backup": "0.2"}}}
    cfg = parse_sampling_config(raw)
    assert cfg.per_job["backup"] == pytest.approx(0.2)


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="object"):
        parse_sampling_config({"sampling": "bad"})


# ---------------------------------------------------------------------------
# wrap_with_sampler
# ---------------------------------------------------------------------------

def test_wrap_returns_handler_unchanged_when_no_section():
    handler = MagicMock()
    wrapped = wrap_with_sampler({}, handler)
    assert wrapped is handler


def test_wrap_returns_callable_when_section_present():
    handler = MagicMock()
    wrapped = wrap_with_sampler({"sampling": {"rate": 1.0}}, handler)
    assert callable(wrapped)
    wrapped(make_payload())
    handler.assert_called_once()
