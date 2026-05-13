"""Tests for parse_escalation_chain."""

from __future__ import annotations

import pytest

from cronwatcher.alert_escalation_chain_config import parse_escalation_chain


def test_no_section_returns_none():
    assert parse_escalation_chain({}) is None


def test_not_a_list_raises():
    with pytest.raises(ValueError, match="must be a list"):
        parse_escalation_chain({"escalation_chain": {"channel": "x"}})


def test_item_not_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_escalation_chain({"escalation_chain": ["bad"]})


def test_missing_min_failures_raises():
    with pytest.raises(ValueError, match="missing 'min_failures'"):
        parse_escalation_chain({"escalation_chain": [{"channel": "default"}]})


def test_invalid_min_failures_raises():
    with pytest.raises(ValueError, match="positive integer"):
        parse_escalation_chain({
            "escalation_chain": [{"min_failures": 0, "channel": "default"}]
        })


def test_missing_channel_raises():
    with pytest.raises(ValueError, match="missing or invalid 'channel'"):
        parse_escalation_chain({
            "escalation_chain": [{"min_failures": 1}]
        })


def test_valid_single_step():
    cfg = parse_escalation_chain({
        "escalation_chain": [{"min_failures": 1, "channel": "default"}]
    })
    assert cfg is not None
    assert len(cfg.steps) == 1
    assert cfg.steps[0].channel_name == "default"
    assert cfg.steps[0].min_failures == 1


def test_multiple_steps_parsed():
    cfg = parse_escalation_chain({
        "escalation_chain": [
            {"min_failures": 1, "channel": "default", "label": "low"},
            {"min_failures": 5, "channel": "pagerduty", "label": "critical"},
        ]
    })
    assert cfg is not None
    assert len(cfg.steps) == 2
    assert cfg.steps[1].channel_name == "pagerduty"
    assert cfg.steps[1].label == "critical"


def test_label_defaults_to_empty_string():
    cfg = parse_escalation_chain({
        "escalation_chain": [{"min_failures": 2, "channel": "ops"}]
    })
    assert cfg.steps[0].label == ""
