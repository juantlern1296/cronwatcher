"""Tests for alert_severity and alert_severity_config."""
import pytest

from cronwatcher.alert_severity import (
    Severity,
    SeverityConfig,
    classify,
    parse_severity_config,
)
from cronwatcher.alert_severity_config import enrich_payload_with_severity
from cronwatcher.metrics import MetricsStore
from cronwatcher.webhook import WebhookPayload


# ---------------------------------------------------------------------------
# SeverityConfig validation
# ---------------------------------------------------------------------------

def test_invalid_warning_threshold_raises():
    with pytest.raises(ValueError, match="warning_threshold"):
        SeverityConfig(warning_threshold=0, critical_threshold=3)


def test_critical_must_exceed_warning():
    with pytest.raises(ValueError, match="critical_threshold"):
        SeverityConfig(warning_threshold=3, critical_threshold=3)


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

@pytest.fixture
def cfg():
    return SeverityConfig(warning_threshold=2, critical_threshold=5)


def test_below_warning_is_info(cfg):
    assert classify(0, cfg) == Severity.INFO
    assert classify(1, cfg) == Severity.INFO


def test_at_warning_threshold(cfg):
    assert classify(2, cfg) == Severity.WARNING
    assert classify(4, cfg) == Severity.WARNING


def test_at_critical_threshold(cfg):
    assert classify(5, cfg) == Severity.CRITICAL
    assert classify(99, cfg) == Severity.CRITICAL


# ---------------------------------------------------------------------------
# parse_severity_config
# ---------------------------------------------------------------------------

def test_no_section_returns_none():
    assert parse_severity_config({}) is None


def test_valid_section_parsed():
    result = parse_severity_config({"severity": {"warning_threshold": 2, "critical_threshold": 6}})
    assert result is not None
    assert result.warning_threshold == 2
    assert result.critical_threshold == 6


def test_defaults_applied():
    result = parse_severity_config({"severity": {}})
    assert result.warning_threshold == 1
    assert result.critical_threshold == 3


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="JSON object"):
        parse_severity_config({"severity": "high"})


# ---------------------------------------------------------------------------
# enrich_payload_with_severity
# ---------------------------------------------------------------------------

@pytest.fixture
def base_payload():
    return WebhookPayload(
        job_name="backup",
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        log_line="FAILED",
    )


def test_enrich_no_config_defaults_to_info(base_payload):
    store = MetricsStore()
    result = enrich_payload_with_severity(base_payload, store, None)
    assert result.extra_fields["severity"] == "info"


def test_enrich_uses_failure_count(base_payload):
    store = MetricsStore()
    store.record_failure("backup")
    store.record_failure("backup")
    cfg = SeverityConfig(warning_threshold=2, critical_threshold=5)
    result = enrich_payload_with_severity(base_payload, store, cfg)
    assert result.extra_fields["severity"] == "warning"


def test_enrich_preserves_existing_extra_fields(base_payload):
    store = MetricsStore()
    payload = WebhookPayload(
        job_name="backup",
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        log_line="FAILED",
        extra_fields={"env": "prod"},
    )
    result = enrich_payload_with_severity(payload, store, None)
    assert result.extra_fields["env"] == "prod"
    assert "severity" in result.extra_fields
