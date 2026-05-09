"""Tests for alert inhibition."""
import pytest

from cronwatcher.alert_inhibition import AlertInhibition, InhibitionRule
from cronwatcher.alert_inhibition_config import parse_alert_inhibition


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def inhibition():
    rules = [
        InhibitionRule(source_job="db_backup", target_jobs=["db_cleanup", "db_report"]),
    ]
    return AlertInhibition(rules=rules)


# ---------------------------------------------------------------------------
# AlertInhibition unit tests
# ---------------------------------------------------------------------------

def test_not_inhibited_when_source_not_firing(inhibition):
    assert not inhibition.is_inhibited("db_cleanup")


def test_inhibited_when_source_is_firing(inhibition):
    inhibition.mark_firing("db_backup")
    assert inhibition.is_inhibited("db_cleanup")
    assert inhibition.is_inhibited("db_report")


def test_non_target_not_inhibited_even_when_source_fires(inhibition):
    inhibition.mark_firing("db_backup")
    assert not inhibition.is_inhibited("some_other_job")


def test_mark_resolved_clears_inhibition(inhibition):
    inhibition.mark_firing("db_backup")
    inhibition.mark_resolved("db_backup")
    assert not inhibition.is_inhibited("db_cleanup")


def test_inhibited_by_returns_source(inhibition):
    inhibition.mark_firing("db_backup")
    assert inhibition.inhibited_by("db_cleanup") == "db_backup"


def test_inhibited_by_returns_none_when_not_inhibited(inhibition):
    assert inhibition.inhibited_by("db_cleanup") is None


def test_active_sources_reflects_state(inhibition):
    inhibition.mark_firing("db_backup")
    assert "db_backup" in inhibition.active_sources()
    inhibition.mark_resolved("db_backup")
    assert "db_backup" not in inhibition.active_sources()


# ---------------------------------------------------------------------------
# parse_alert_inhibition tests
# ---------------------------------------------------------------------------

def test_no_section_returns_empty():
    result = parse_alert_inhibition({})
    assert result.rules == []


def test_valid_single_rule():
    cfg = {"inhibition": [{"source": "db_backup", "targets": ["db_cleanup"]}]}
    result = parse_alert_inhibition(cfg)
    assert len(result.rules) == 1
    assert result.rules[0].source_job == "db_backup"
    assert result.rules[0].target_jobs == ["db_cleanup"]


def test_multiple_rules():
    cfg = {
        "inhibition": [
            {"source": "a", "targets": ["b", "c"]},
            {"source": "x", "targets": ["y"]},
        ]
    }
    result = parse_alert_inhibition(cfg)
    assert len(result.rules) == 2


def test_not_a_list_raises():
    with pytest.raises(ValueError, match="must be a list"):
        parse_alert_inhibition({"inhibition": {"source": "a", "targets": ["b"]}})


def test_missing_source_raises():
    with pytest.raises(ValueError, match="missing or invalid 'source'"):
        parse_alert_inhibition({"inhibition": [{"targets": ["b"]}]})


def test_missing_targets_raises():
    with pytest.raises(ValueError, match="missing or invalid 'targets'"):
        parse_alert_inhibition({"inhibition": [{"source": "a"}]})


def test_non_string_target_raises():
    with pytest.raises(ValueError, match="list of strings"):
        parse_alert_inhibition({"inhibition": [{"source": "a", "targets": [1, 2]}]})
