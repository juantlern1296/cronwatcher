"""Tests for cronwatcher.alert_tag."""
from __future__ import annotations

import pytest

from cronwatcher.alert_tag import AlertTagger, TagConfig, parse_tag_config
from cronwatcher.webhook import WebhookPayload


def make_payload(job_name="backup", exit_code=1, extra=None) -> WebhookPayload:
    return WebhookPayload(
        job_name=job_name,
        exit_code=exit_code,
        timestamp="2024-01-01T00:00:00Z",
        hostname="host1",
        log_line="FAILED",
        extra_fields=extra or {},
    )


# --- TagConfig ---

def test_tags_for_returns_global_only_when_no_per_job():
    cfg = TagConfig(global_tags={"infra", "prod"})
    assert cfg.tags_for("backup") == {"infra", "prod"}


def test_tags_for_merges_per_job():
    cfg = TagConfig(global_tags={"infra"}, per_job_tags={"backup": {"storage"}})
    assert cfg.tags_for("backup") == {"infra", "storage"}


def test_tags_for_unknown_job_returns_global():
    cfg = TagConfig(global_tags={"infra"}, per_job_tags={"backup": {"storage"}})
    assert cfg.tags_for("other") == {"infra"}


# --- AlertTagger ---

def test_tag_adds_tags_to_payload():
    cfg = TagConfig(global_tags={"env:prod"})
    tagger = AlertTagger(cfg)
    result = tagger.tag(make_payload())
    assert "env:prod" in result.extra_fields["tags"]


def test_tag_merges_existing_tags():
    cfg = TagConfig(global_tags={"infra"})
    tagger = AlertTagger(cfg)
    payload = make_payload(extra={"tags": ["custom"]})
    result = tagger.tag(payload)
    assert "infra" in result.extra_fields["tags"]
    assert "custom" in result.extra_fields["tags"]


def test_tag_deduplicates():
    cfg = TagConfig(global_tags={"dup"})
    tagger = AlertTagger(cfg)
    payload = make_payload(extra={"tags": ["dup"]})
    result = tagger.tag(payload)
    assert result.extra_fields["tags"].count("dup") == 1


def test_tag_does_not_mutate_original():
    cfg = TagConfig(global_tags={"infra"})
    tagger = AlertTagger(cfg)
    original = make_payload()
    tagger.tag(original)
    assert "tags" not in original.extra_fields


# --- parse_tag_config ---

def test_no_section_returns_none():
    assert parse_tag_config({}) is None


def test_valid_global_tags():
    raw = {"alert_tags": {"global": ["prod", "infra"]}}
    cfg = parse_tag_config(raw)
    assert cfg is not None
    assert "prod" in cfg.global_tags


def test_valid_per_job_tags():
    raw = {"alert_tags": {"per_job": {"backup": ["storage"]}}}
    cfg = parse_tag_config(raw)
    assert cfg is not None
    assert "storage" in cfg.per_job_tags["backup"]


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="must be a JSON object"):
        parse_tag_config({"alert_tags": ["oops"]})


def test_non_string_tag_raises():
    with pytest.raises(ValueError, match="Tag must be a string"):
        parse_tag_config({"alert_tags": {"global": [123]}})


def test_per_job_not_list_raises():
    with pytest.raises(ValueError, match="must be a list"):
        parse_tag_config({"alert_tags": {"per_job": {"backup": "oops"}}})
