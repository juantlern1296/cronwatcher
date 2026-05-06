"""Tests for job_suppression and suppression_config."""

import time
import pytest

from cronwatcher.job_suppression import JobSuppression, SuppressionEntry
from cronwatcher.suppression_config import parse_suppression_rules


# ---------------------------------------------------------------------------
# JobSuppression tests
# ---------------------------------------------------------------------------

@pytest.fixture
def sup():
    return JobSuppression()


def test_new_job_not_suppressed(sup):
    assert sup.is_suppressed("backup") is False


def test_suppress_makes_job_suppressed(sup):
    sup.suppress("backup", 60)
    assert sup.is_suppressed("backup") is True


def test_suppression_expires(sup):
    sup.suppress("backup", 1)
    future = time.time() + 2
    assert sup.is_suppressed("backup", now=future) is False


def test_lift_removes_suppression(sup):
    sup.suppress("backup", 60)
    result = sup.lift("backup")
    assert result is True
    assert sup.is_suppressed("backup") is False


def test_lift_nonexistent_returns_false(sup):
    assert sup.lift("nonexistent") is False


def test_invalid_duration_raises(sup):
    with pytest.raises(ValueError):
        sup.suppress("backup", 0)
    with pytest.raises(ValueError):
        sup.suppress("backup", -5)


def test_active_suppressions_filters_expired(sup):
    sup.suppress("backup", 100)
    sup.suppress("report", 1)
    future = time.time() + 2
    active = sup.active_suppressions(now=future)
    names = [e.job_name for e in active]
    assert "backup" in names
    assert "report" not in names


def test_suppression_entry_is_active():
    now = time.time()
    entry = SuppressionEntry(job_name="x", expires_at=now + 10)
    assert entry.is_active(now=now) is True
    assert entry.is_active(now=now + 20) is False


def test_len_reflects_stored_entries(sup):
    assert len(sup) == 0
    sup.suppress("a", 60)
    sup.suppress("b", 60)
    assert len(sup) == 2


# ---------------------------------------------------------------------------
# parse_suppression_rules tests
# ---------------------------------------------------------------------------

def test_no_suppression_section_returns_empty():
    assert parse_suppression_rules({}) == []


def test_valid_rules_parsed():
    cfg = {"suppression": [{"job": "backup", "duration_seconds": 3600, "reason": "maint"}]}
    rules = parse_suppression_rules(cfg)
    assert len(rules) == 1
    assert rules[0].job_name == "backup"
    assert rules[0].duration_seconds == 3600.0
    assert rules[0].reason == "maint"


def test_reason_defaults_to_empty_string():
    cfg = {"suppression": [{"job": "report", "duration_seconds": 60}]}
    rules = parse_suppression_rules(cfg)
    assert rules[0].reason == ""


def test_not_a_list_raises():
    with pytest.raises(ValueError, match="must be a list"):
        parse_suppression_rules({"suppression": {"job": "x", "duration_seconds": 10}})


def test_missing_job_field_raises():
    with pytest.raises(ValueError, match="'job'"):
        parse_suppression_rules({"suppression": [{"duration_seconds": 60}]})


def test_invalid_duration_raises_in_config():
    with pytest.raises(ValueError, match="duration_seconds"):
        parse_suppression_rules({"suppression": [{"job": "backup", "duration_seconds": -1}]})


def test_multiple_rules_parsed():
    cfg = {
        "suppression": [
            {"job": "a", "duration_seconds": 100},
            {"job": "b", "duration_seconds": 200},
        ]
    }
    rules = parse_suppression_rules(cfg)
    assert len(rules) == 2
    assert rules[1].job_name == "b"
