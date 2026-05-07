"""Tests for the dead letter queue."""
import time

import pytest

from cronwatcher.dead_letter import DeadLetterQueue
from cronwatcher.webhook import WebhookPayload


def make_payload(job_name: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job_name,
        exit_code=1,
        timestamp="2024-01-01T00:00:00Z",
        hostname="host",
        raw_line="Jan  1 00:00:00 host CRON[1]: CMD (backup)",
    )


@pytest.fixture
def queue() -> DeadLetterQueue:
    return DeadLetterQueue(max_size=10)


def test_invalid_max_size_raises():
    with pytest.raises(ValueError, match="max_size"):
        DeadLetterQueue(max_size=0)


def test_push_increases_size(queue):
    queue.push(make_payload(), attempts=1, error="timeout")
    assert queue.size() == 1


def test_pop_all_clears_queue(queue):
    queue.push(make_payload(), attempts=1, error="err")
    entries = queue.pop_all()
    assert len(entries) == 1
    assert queue.size() == 0


def test_entry_stores_metadata(queue):
    p = make_payload("nightly")
    before = time.time()
    queue.push(p, attempts=2, error="connection refused")
    entry = queue.pop_all()[0]
    assert entry.payload.job_name == "nightly"
    assert entry.attempts == 2
    assert entry.last_error == "connection refused"
    assert entry.failed_at >= before


def test_overflow_drops_oldest(queue):
    q = DeadLetterQueue(max_size=2)
    q.push(make_payload("job1"), attempts=1, error="e")
    q.push(make_payload("job2"), attempts=1, error="e")
    q.push(make_payload("job3"), attempts=1, error="e")  # should drop job1
    entries = q.pop_all()
    names = [e.payload.job_name for e in entries]
    assert "job1" not in names
    assert "job3" in names


def test_flush_retries_and_removes_on_success(queue):
    queue.push(make_payload("ok_job"), attempts=1, error="err")
    count = queue.flush(lambda p: True)
    assert count == 1
    assert queue.size() == 0


def test_flush_keeps_entry_on_failure(queue):
    queue.push(make_payload("bad_job"), attempts=1, error="err")
    count = queue.flush(lambda p: False)
    assert count == 0
    assert queue.size() == 1


def test_flush_increments_attempts_on_failure(queue):
    queue.push(make_payload(), attempts=2, error="err")
    queue.flush(lambda p: False)
    entry = queue.pop_all()[0]
    assert entry.attempts == 3


def test_flush_handles_exception_as_failure(queue):
    def boom(p):
        raise RuntimeError("network down")

    queue.push(make_payload(), attempts=1, error="prev")
    count = queue.flush(boom)
    assert count == 0
    assert queue.size() == 1
    entry = queue.pop_all()[0]
    assert "network down" in entry.last_error
