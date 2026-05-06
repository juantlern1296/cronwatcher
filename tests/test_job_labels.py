"""Tests for cronwatcher.job_labels."""

import pytest
from cronwatcher.job_labels import JobLabels, parse_job_labels, enrich_payload


# ---------------------------------------------------------------------------
# parse_job_labels
# ---------------------------------------------------------------------------

def test_none_returns_empty():
    labels = parse_job_labels(None)
    assert labels.as_dict() == {}


def test_empty_dict_returns_empty():
    labels = parse_job_labels({})
    assert labels.as_dict() == {}


def test_string_values_parsed():
    labels = parse_job_labels({"env": "prod", "team": "ops"})
    assert labels.get("env") == "prod"
    assert labels.get("team") == "ops"


def test_non_string_value_coerced():
    labels = parse_job_labels({"retries": 3})
    assert labels.get("retries") == "3"


def test_non_dict_raises():
    with pytest.raises(ValueError, match="labels must be a dict"):
        parse_job_labels(["env", "prod"])


def test_non_string_key_raises():
    with pytest.raises(ValueError, match="label key must be a string"):
        parse_job_labels({1: "value"})


# ---------------------------------------------------------------------------
# JobLabels.get
# ---------------------------------------------------------------------------

def test_get_missing_key_returns_default():
    labels = JobLabels(labels={"a": "1"})
    assert labels.get("missing") == ""
    assert labels.get("missing", "fallback") == "fallback"


# ---------------------------------------------------------------------------
# JobLabels.merge
# ---------------------------------------------------------------------------

def test_merge_combines_labels():
    base = JobLabels(labels={"env": "prod", "team": "ops"})
    override = JobLabels(labels={"env": "staging", "owner": "alice"})
    merged = base.merge(override)
    assert merged.get("env") == "staging"   # overridden
    assert merged.get("team") == "ops"       # kept from base
    assert merged.get("owner") == "alice"    # new from override


def test_merge_does_not_mutate_originals():
    base = JobLabels(labels={"env": "prod"})
    override = JobLabels(labels={"env": "dev"})
    base.merge(override)
    assert base.get("env") == "prod"


# ---------------------------------------------------------------------------
# enrich_payload
# ---------------------------------------------------------------------------

def test_enrich_payload_adds_labels_key():
    payload = {"job": "backup", "exit_code": 1}
    labels = JobLabels(labels={"env": "prod"})
    result = enrich_payload(payload, labels)
    assert result["labels"] == {"env": "prod"}
    assert result["job"] == "backup"


def test_enrich_payload_empty_labels():
    payload = {"job": "cleanup"}
    labels = JobLabels()
    result = enrich_payload(payload, labels)
    assert result["labels"] == {}


def test_enrich_payload_does_not_mutate_original():
    payload = {"job": "sync"}
    labels = JobLabels(labels={"env": "dev"})
    enrich_payload(payload, labels)
    assert "labels" not in payload
