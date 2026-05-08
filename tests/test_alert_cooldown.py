"""Tests for cronwatcher.alert_cooldown."""

import pytest

from cronwatcher.alert_cooldown import AlertCooldown, CooldownConfig, parse_cooldown_config


@pytest.fixture
def cfg() -> CooldownConfig:
    return CooldownConfig(default_seconds=60.0, per_job={"backup": 120.0})


@pytest.fixture
def cooldown(cfg: CooldownConfig) -> AlertCooldown:
    return AlertCooldown(cfg)


# --- CooldownConfig validation ---

def test_negative_default_raises():
    with pytest.raises(ValueError, match="default_seconds"):
        CooldownConfig(default_seconds=-1.0)


def test_negative_per_job_raises():
    with pytest.raises(ValueError, match="backup"):
        CooldownConfig(default_seconds=30.0, per_job={"backup": -5.0})


def test_cooldown_for_known_job(cfg):
    assert cfg.cooldown_for("backup") == 120.0


def test_cooldown_for_unknown_job_uses_default(cfg):
    assert cfg.cooldown_for("deploy") == 60.0


# --- AlertCooldown.is_allowed ---

def test_new_job_is_allowed(cooldown):
    assert cooldown.is_allowed("deploy", now=1000.0) is True


def test_not_allowed_immediately_after_record(cooldown):
    cooldown.record("deploy", now=1000.0)
    assert cooldown.is_allowed("deploy", now=1001.0) is False


def test_allowed_after_cooldown_expires(cooldown):
    cooldown.record("deploy", now=1000.0)
    assert cooldown.is_allowed("deploy", now=1061.0) is True


def test_per_job_cooldown_respected(cooldown):
    cooldown.record("backup", now=1000.0)
    # 60 s later — inside 120 s backup window
    assert cooldown.is_allowed("backup", now=1060.0) is False
    # 121 s later — outside
    assert cooldown.is_allowed("backup", now=1121.0) is True


# --- AlertCooldown.reset ---

def test_reset_clears_state(cooldown):
    cooldown.record("deploy", now=1000.0)
    cooldown.reset("deploy")
    assert cooldown.is_allowed("deploy", now=1001.0) is True


def test_reset_unknown_job_is_noop(cooldown):
    cooldown.reset("nonexistent")  # should not raise


# --- AlertCooldown.remaining ---

def test_remaining_zero_for_new_job(cooldown):
    assert cooldown.remaining("deploy", now=1000.0) == 0.0


def test_remaining_positive_within_window(cooldown):
    cooldown.record("deploy", now=1000.0)
    rem = cooldown.remaining("deploy", now=1010.0)
    assert rem == pytest.approx(50.0)


def test_remaining_zero_after_expiry(cooldown):
    cooldown.record("deploy", now=1000.0)
    assert cooldown.remaining("deploy", now=1100.0) == 0.0


# --- parse_cooldown_config ---

def test_no_section_returns_zero_default():
    cfg = parse_cooldown_config({})
    assert cfg.default_seconds == 0.0
    assert cfg.per_job == {}


def test_valid_config_parsed():
    raw = {"cooldown": {"default_seconds": 90, "per_job": {"backup": 300}}}
    cfg = parse_cooldown_config(raw)
    assert cfg.default_seconds == 90.0
    assert cfg.cooldown_for("backup") == 300.0


def test_per_job_not_dict_raises():
    raw = {"cooldown": {"default_seconds": 30, "per_job": "bad"}}
    with pytest.raises(ValueError, match="per_job"):
        parse_cooldown_config(raw)
