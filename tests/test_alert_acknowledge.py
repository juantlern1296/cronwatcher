"""Tests for alert_acknowledge.py"""
from __future__ import annotations

import time
import pytest

from cronwatcher.alert_acknowledge import AckEntry, AlertAcknowledge


@pytest.fixture
def ack():
    return AlertAcknowledge()


# --- AckEntry ---

def test_ack_entry_active_within_window():
    now = time.time()
    entry = AckEntry(job_name="backup", acked_by="alice", expires_at=now + 60)
    assert entry.is_active(now=now) is True


def test_ack_entry_inactive_after_expiry():
    now = time.time()
    entry = AckEntry(job_name="backup", acked_by="alice", expires_at=now - 1)
    assert entry.is_active(now=now) is False


def test_ack_entry_never_expires_when_zero():
    entry = AckEntry(job_name="backup", acked_by="alice", expires_at=0)
    assert entry.is_active(now=time.time() + 9999) is True


# --- AlertAcknowledge.acknowledge ---

def test_acknowledge_creates_entry(ack):
    now = time.time()
    entry = ack.acknowledge("backup", "alice", duration_seconds=300, now=now)
    assert entry.job_name == "backup"
    assert entry.acked_by == "alice"
    assert abs(entry.expires_at - (now + 300)) < 0.01


def test_acknowledge_zero_duration_never_expires(ack):
    entry = ack.acknowledge("backup", "alice", duration_seconds=0)
    assert entry.expires_at == 0


def test_acknowledge_empty_job_name_raises(ack):
    with pytest.raises(ValueError, match="job_name"):
        ack.acknowledge("", "alice")


def test_acknowledge_empty_acked_by_raises(ack):
    with pytest.raises(ValueError, match="acked_by"):
        ack.acknowledge("backup", "")


def test_acknowledge_negative_duration_raises(ack):
    with pytest.raises(ValueError, match="duration_seconds"):
        ack.acknowledge("backup", "alice", duration_seconds=-1)


# --- is_acknowledged ---

def test_new_job_not_acknowledged(ack):
    assert ack.is_acknowledged("unknown") is False


def test_is_acknowledged_returns_true_within_window(ack):
    now = time.time()
    ack.acknowledge("backup", "alice", duration_seconds=300, now=now)
    assert ack.is_acknowledged("backup", now=now + 1) is True


def test_is_acknowledged_returns_false_after_expiry(ack):
    now = time.time()
    ack.acknowledge("backup", "alice", duration_seconds=10, now=now)
    assert ack.is_acknowledged("backup", now=now + 20) is False


def test_expired_ack_evicted_lazily(ack):
    now = time.time()
    ack.acknowledge("backup", "alice", duration_seconds=1, now=now)
    ack.is_acknowledged("backup", now=now + 5)  # triggers eviction
    assert ack.get("backup") is None


# --- clear ---

def test_clear_removes_ack(ack):
    ack.acknowledge("backup", "alice")
    ack.clear("backup")
    assert ack.is_acknowledged("backup") is False


def test_clear_nonexistent_is_noop(ack):
    ack.clear("ghost")  # should not raise


# --- all_active ---

def test_all_active_returns_only_live_entries(ack):
    now = time.time()
    ack.acknowledge("job_a", "alice", duration_seconds=300, now=now)
    ack.acknowledge("job_b", "bob", duration_seconds=1, now=now)
    active = ack.all_active(now=now + 5)
    assert "job_a" in active
    assert "job_b" not in active
