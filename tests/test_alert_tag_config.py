"""Tests for cronwatcher.alert_tag_config."""
from __future__ import annotations

from cronwatcher.alert_tag_config import tagged_handler, wrap_with_tagger
from cronwatcher.alert_tag import AlertTagger, TagConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job_name="backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job_name,
        exit_code=1,
        timestamp="2024-01-01T00:00:00Z",
        hostname="host1",
        log_line="FAILED",
        extra_fields={},
    )


def test_wrap_with_tagger_calls_handler():
    received = []
    cfg = TagConfig(global_tags={"prod"})
    tagger = AlertTagger(cfg)
    wrapped = wrap_with_tagger(lambda p: received.append(p), tagger)
    wrapped(make_payload())
    assert len(received) == 1
    assert "prod" in received[0].extra_fields["tags"]


def test_tagged_handler_no_section_returns_original():
    calls = []
    original = lambda p: calls.append(p)
    result = tagged_handler({}, original)
    assert result is original


def test_tagged_handler_with_section_wraps():
    received = []
    raw = {"alert_tags": {"global": ["env:test"]}}
    handler = tagged_handler(raw, lambda p: received.append(p))
    handler(make_payload())
    assert "env:test" in received[0].extra_fields["tags"]


def test_tagged_handler_per_job_tags_applied():
    received = []
    raw = {"alert_tags": {"per_job": {"backup": ["storage"]}}}
    handler = tagged_handler(raw, lambda p: received.append(p))
    handler(make_payload(job_name="backup"))
    assert "storage" in received[0].extra_fields["tags"]


def test_tagged_handler_per_job_not_applied_to_other_job():
    received = []
    raw = {"alert_tags": {"per_job": {"backup": ["storage"]}}}
    handler = tagged_handler(raw, lambda p: received.append(p))
    handler(make_payload(job_name="other"))
    assert "storage" not in received[0].extra_fields.get("tags", [])
