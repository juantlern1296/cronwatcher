"""Tests for cronwatcher.alert_pause."""
import time
import pytest
from unittest.mock import MagicMock

from cronwatcher.alert_pause import AlertPause, PauseEntry
from cronwatcher.webhook import WebhookPayload


def make_payload(job_name: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job_name,
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host",
        extra={},
    )


@pytest.fixture
def pause() -> AlertPause:
    return AlertPause()


def test_pause_entry_active_within_window():
    entry = PauseEntry(job_name="job", expires_at=time.time() + 60)
    assert entry.is_active()


def test_pause_entry_inactive_after_expiry():
    entry = PauseEntry(job_name="job", expires_at=time.time() - 1)
    assert not entry.is_active()


def test_pause_entry_indefinite_always_active():
    entry = PauseEntry(job_name="job", expires_at=0)
    assert entry.is_active(time.time() + 9999)


def test_new_job_not_paused(pause):
    assert not pause.is_paused("backup")


def test_pause_makes_job_paused(pause):
    pause.pause("backup", duration=60)
    assert pause.is_paused("backup")


def test_pause_expires(pause):
    future = time.time() + 120
    pause.pause("backup", duration=60)
    assert not pause.is_paused("backup", now=future)


def test_resume_clears_pause(pause):
    pause.pause("backup", duration=60)
    pause.resume("backup")
    assert not pause.is_paused("backup")


def test_pause_all_blocks_any_job(pause):
    pause.pause_all(duration=60)
    assert pause.is_paused("backup")
    assert pause.is_paused("deploy")


def test_resume_all_clears_global_pause(pause):
    pause.pause_all(duration=60)
    pause.resume_all()
    assert not pause.is_paused("backup")


def test_negative_duration_raises(pause):
    with pytest.raises(ValueError):
        pause.pause("backup", duration=-1)


def test_wrap_skips_handler_when_paused(pause):
    handler = MagicMock()
    wrapped = pause.wrap(handler)
    pause.pause("backup", duration=60)
    wrapped(make_payload("backup"))
    handler.assert_not_called()


def test_wrap_calls_handler_when_not_paused(pause):
    handler = MagicMock()
    wrapped = pause.wrap(handler)
    wrapped(make_payload("backup"))
    handler.assert_called_once()


def test_wrap_calls_handler_after_resume(pause):
    handler = MagicMock()
    wrapped = pause.wrap(handler)
    pause.pause("backup", duration=60)
    pause.resume("backup")
    wrapped(make_payload("backup"))
    handler.assert_called_once()
