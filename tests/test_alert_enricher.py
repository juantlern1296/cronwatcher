"""Tests for alert_enricher module."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from cronwatcher.alert_enricher import (
    EnricherConfig,
    enrich_payload,
    parse_alert_enricher,
)
from cronwatcher.alert_enricher_config import wrap_with_enricher
from cronwatcher.webhook import WebhookPayload


def make_payload(**kwargs) -> WebhookPayload:
    defaults = dict(job_name="backup", exit_code=1, timestamp="2024-01-01T00:00:00", log_line="error")
    defaults.update(kwargs)
    return WebhookPayload(**defaults)


def test_enrich_adds_hostname():
    cfg = EnricherConfig(add_hostname=True)
    result = enrich_payload(make_payload(), cfg)
    assert "hostname" in result.extra_fields


def test_enrich_skips_hostname_if_disabled():
    cfg = EnricherConfig(add_hostname=False)
    result = enrich_payload(make_payload(), cfg)
    assert "hostname" not in (result.extra_fields or {})


def test_enrich_does_not_overwrite_existing_hostname():
    cfg = EnricherConfig(add_hostname=True)
    payload = make_payload(extra_fields={"hostname": "custom-host"})
    result = enrich_payload(payload, cfg)
    assert result.extra_fields["hostname"] == "custom-host"


def test_enrich_adds_env():
    cfg = EnricherConfig(add_hostname=False, add_env="production")
    result = enrich_payload(make_payload(), cfg)
    assert result.extra_fields["env"] == "production"


def test_enrich_adds_static_fields():
    cfg = EnricherConfig(add_hostname=False, static_fields={"team": "ops", "region": "us-east"})
    result = enrich_payload(make_payload(), cfg)
    assert result.extra_fields["team"] == "ops"
    assert result.extra_fields["region"] == "us-east"


def test_enrich_does_not_overwrite_existing_static_field():
    cfg = EnricherConfig(add_hostname=False, static_fields={"team": "ops"})
    payload = make_payload(extra_fields={"team": "infra"})
    result = enrich_payload(payload, cfg)
    assert result.extra_fields["team"] == "infra"


def test_enrich_preserves_original_payload_fields():
    cfg = EnricherConfig(add_hostname=False)
    p = make_payload(exit_code=2)
    result = enrich_payload(p, cfg)
    assert result.job_name == "backup"
    assert result.exit_code == 2


def test_parse_alert_enricher_no_section():
    assert parse_alert_enricher({}) is None


def test_parse_alert_enricher_valid():
    raw = {"alert_enricher": {"add_hostname": False, "env": "staging", "static_fields": {"owner": "alice"}}}
    cfg = parse_alert_enricher(raw)
    assert cfg is not None
    assert cfg.add_hostname is False
    assert cfg.add_env == "staging"
    assert cfg.static_fields == {"owner": "alice"}


def test_parse_alert_enricher_not_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_alert_enricher({"alert_enricher": "bad"})


def test_parse_alert_enricher_invalid_hostname_type_raises():
    with pytest.raises(ValueError, match="boolean"):
        parse_alert_enricher({"alert_enricher": {"add_hostname": "yes"}})


def test_parse_alert_enricher_invalid_env_type_raises():
    with pytest.raises(ValueError, match="string"):
        parse_alert_enricher({"alert_enricher": {"env": 42}})


def test_parse_alert_enricher_invalid_static_fields_raises():
    with pytest.raises(ValueError, match="static_fields"):
        parse_alert_enricher({"alert_enricher": {"static_fields": "bad"}})


def test_wrap_with_enricher_none_returns_same_handler():
    calls = []
    handler = lambda p: calls.append(p)
    wrapped = wrap_with_enricher(handler, None)
    p = make_payload()
    wrapped(p)
    assert calls[0] is p


def test_wrap_with_enricher_enriches_before_dispatch():
    received = []
    handler = lambda p: received.append(p)
    cfg = EnricherConfig(add_hostname=False, add_env="test")
    wrapped = wrap_with_enricher(handler, cfg)
    wrapped(make_payload())
    assert received[0].extra_fields.get("env") == "test"
