"""Tests for cronwatcher.retry."""

from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.retry import RetryConfig, RetryResult, with_retry


@pytest.fixture
def default_cfg() -> RetryConfig:
    return RetryConfig(max_attempts=3, base_delay=0.0, backoff_factor=2.0, max_delay=0.0)


def test_success_on_first_attempt(default_cfg):
    fn = MagicMock(return_value=True)
    result = with_retry(fn, default_cfg, job_name="test_job")
    assert result.success is True
    assert result.attempts == 1
    fn.assert_called_once()


def test_success_on_second_attempt(default_cfg):
    fn = MagicMock(side_effect=[False, True])
    result = with_retry(fn, default_cfg, job_name="test_job")
    assert result.success is True
    assert result.attempts == 2


def test_all_attempts_fail(default_cfg):
    fn = MagicMock(return_value=False)
    result = with_retry(fn, default_cfg, job_name="test_job")
    assert result.success is False
    assert result.attempts == 3
    assert fn.call_count == 3


def test_exception_treated_as_failure(default_cfg):
    exc = ConnectionError("timeout")
    fn = MagicMock(side_effect=exc)
    result = with_retry(fn, default_cfg, job_name="test_job")
    assert result.success is False
    assert result.last_exception is exc
    assert result.attempts == 3


def test_exception_then_success(default_cfg):
    fn = MagicMock(side_effect=[RuntimeError("boom"), True])
    result = with_retry(fn, default_cfg, job_name="test_job")
    assert result.success is True
    assert result.attempts == 2


def test_uses_default_config_when_none_given():
    fn = MagicMock(return_value=True)
    result = with_retry(fn, job_name="test_job")
    assert result.success is True


def test_sleep_called_between_attempts():
    cfg = RetryConfig(max_attempts=2, base_delay=1.5, backoff_factor=1.0, max_delay=30.0)
    fn = MagicMock(side_effect=[False, True])
    with patch("cronwatcher.retry.time.sleep") as mock_sleep:
        result = with_retry(fn, cfg, job_name="test_job")
    mock_sleep.assert_called_once_with(1.5)
    assert result.success is True


def test_delay_capped_at_max_delay():
    cfg = RetryConfig(max_attempts=3, base_delay=100.0, backoff_factor=2.0, max_delay=5.0)
    fn = MagicMock(return_value=False)
    with patch("cronwatcher.retry.time.sleep") as mock_sleep:
        with_retry(fn, cfg, job_name="test_job")
    for call in mock_sleep.call_args_list:
        assert call.args[0] <= 5.0


def test_no_sleep_after_last_attempt():
    """Sleep should only occur between attempts, not after the final one."""
    cfg = RetryConfig(max_attempts=3, base_delay=1.0, backoff_factor=1.0, max_delay=30.0)
    fn = MagicMock(return_value=False)
    with patch("cronwatcher.retry.time.sleep") as mock_sleep:
        with_retry(fn, cfg, job_name="test_job")
    # 3 attempts means 2 sleeps (between attempt 1-2 and 2-3, not after 3)
    assert mock_sleep.call_count == 2
