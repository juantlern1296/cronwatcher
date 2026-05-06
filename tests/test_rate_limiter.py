"""Tests for RateLimiter and parse_rate_limiter."""

from __future__ import annotations

import time

import pytest

from cronwatcher.rate_limiter import RateLimiter
from cronwatcher.rate_limiter_config import parse_rate_limiter


# ---------------------------------------------------------------------------
# RateLimiter unit tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def limiter() -> RateLimiter:
    return RateLimiter(max_tokens=3, refill_rate=10.0)


def test_invalid_max_tokens_raises():
    with pytest.raises(ValueError, match="max_tokens"):
        RateLimiter(max_tokens=0)


def test_invalid_refill_rate_raises():
    with pytest.raises(ValueError, match="refill_rate"):
        RateLimiter(refill_rate=0)


def test_new_job_has_full_tokens(limiter: RateLimiter):
    assert limiter.available_tokens("backup") == 3.0


def test_allow_consumes_token(limiter: RateLimiter):
    assert limiter.allow("backup") is True
    assert limiter.available_tokens("backup") == pytest.approx(2.0, abs=0.05)


def test_allow_exhausts_bucket(limiter: RateLimiter):
    for _ in range(3):
        limiter.allow("backup")
    assert limiter.allow("backup") is False


def test_tokens_refill_over_time(limiter: RateLimiter):
    for _ in range(3):
        limiter.allow("backup")
    time.sleep(0.15)  # 10 tokens/s → ~1.5 tokens after 0.15 s
    assert limiter.available_tokens("backup") >= 1.0


def test_tokens_capped_at_max(limiter: RateLimiter):
    # Even after a long wait tokens should not exceed max_tokens
    time.sleep(0.05)
    assert limiter.available_tokens("backup") <= 3.0


def test_reset_restores_full_tokens(limiter: RateLimiter):
    limiter.allow("backup")
    limiter.allow("backup")
    limiter.reset("backup")
    assert limiter.available_tokens("backup") == 3.0


def test_independent_buckets_per_job(limiter: RateLimiter):
    for _ in range(3):
        limiter.allow("job_a")
    assert limiter.allow("job_b") is True


# ---------------------------------------------------------------------------
# parse_rate_limiter tests
# ---------------------------------------------------------------------------


def test_defaults_when_no_section():
    rl = parse_rate_limiter({})
    assert rl.max_tokens == 5
    assert rl.refill_rate == 1.0


def test_custom_values():
    rl = parse_rate_limiter({"rate_limiter": {"max_tokens": 10, "refill_rate": 2.5}})
    assert rl.max_tokens == 10
    assert rl.refill_rate == pytest.approx(2.5)


def test_invalid_max_tokens_in_config_raises():
    with pytest.raises(ValueError, match="max_tokens"):
        parse_rate_limiter({"rate_limiter": {"max_tokens": 0}})


def test_invalid_refill_rate_in_config_raises():
    with pytest.raises(ValueError, match="refill_rate"):
        parse_rate_limiter({"rate_limiter": {"refill_rate": -1}})
