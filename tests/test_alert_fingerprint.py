"""Tests for cronwatcher.alert_fingerprint."""
import pytest

from cronwatcher.alert_fingerprint import (
    FingerprintConfig,
    compute_fingerprint,
    parse_fingerprint_config,
)
from cronwatcher.webhook import WebhookPayload


def make_payload(**kwargs) -> WebhookPayload:
    defaults = dict(
        job_name="backup",
        exit_code=1,
        hostname="host1",
        command="/usr/bin/backup.sh",
        timestamp="2024-01-01T00:00:00Z",
        labels={},
    )
    defaults.update(kwargs)
    return WebhookPayload(**defaults)


# --- FingerprintConfig validation ---

def test_empty_fields_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        FingerprintConfig(fields=[])


def test_unknown_field_raises():
    with pytest.raises(ValueError, match="unknown fingerprint fields"):
        FingerprintConfig(fields=["job", "nonexistent"])


def test_valid_config_created():
    cfg = FingerprintConfig(fields=["job", "exit_code"])
    assert cfg.fields == ["job", "exit_code"]
    assert cfg.include_labels is False


# --- compute_fingerprint ---

def test_same_payload_same_fingerprint():
    cfg = FingerprintConfig()
    p = make_payload()
    assert compute_fingerprint(p, cfg) == compute_fingerprint(p, cfg)


def test_different_job_different_fingerprint():
    cfg = FingerprintConfig()
    p1 = make_payload(job_name="backup")
    p2 = make_payload(job_name="cleanup")
    assert compute_fingerprint(p1, cfg) != compute_fingerprint(p2, cfg)


def test_different_exit_code_different_fingerprint():
    cfg = FingerprintConfig()
    p1 = make_payload(exit_code=1)
    p2 = make_payload(exit_code=2)
    assert compute_fingerprint(p1, cfg) != compute_fingerprint(p2, cfg)


def test_fingerprint_excludes_unlisted_field():
    cfg = FingerprintConfig(fields=["job"])
    p1 = make_payload(exit_code=1, hostname="host1")
    p2 = make_payload(exit_code=99, hostname="host2")
    assert compute_fingerprint(p1, cfg) == compute_fingerprint(p2, cfg)


def test_include_labels_changes_fingerprint():
    cfg_no = FingerprintConfig(fields=["job"], include_labels=False)
    cfg_yes = FingerprintConfig(fields=["job"], include_labels=True)
    p1 = make_payload(labels={"env": "prod"})
    p2 = make_payload(labels={"env": "staging"})
    assert compute_fingerprint(p1, cfg_no) == compute_fingerprint(p2, cfg_no)
    assert compute_fingerprint(p1, cfg_yes) != compute_fingerprint(p2, cfg_yes)


def test_fingerprint_is_hex_string():
    cfg = FingerprintConfig()
    fp = compute_fingerprint(make_payload(), cfg)
    assert isinstance(fp, str)
    assert len(fp) == 64
    int(fp, 16)  # should not raise


# --- parse_fingerprint_config ---

def test_none_returns_defaults():
    cfg = parse_fingerprint_config(None)
    assert cfg.fields == ["job", "exit_code", "hostname"]
    assert cfg.include_labels is False


def test_custom_fields_parsed():
    cfg = parse_fingerprint_config({"fields": ["job", "command"]})
    assert cfg.fields == ["job", "command"]


def test_include_labels_parsed():
    cfg = parse_fingerprint_config({"include_labels": True})
    assert cfg.include_labels is True


def test_not_a_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_fingerprint_config(["job"])


def test_fields_not_a_list_raises():
    with pytest.raises(ValueError, match="list of strings"):
        parse_fingerprint_config({"fields": "job"})
