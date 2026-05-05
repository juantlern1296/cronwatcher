"""Tests for cronwatcher.alerting module."""

import time
import pytest
from unittest.mock import patch
from cronwatcher.alerting import AlertManager, AlertState


@pytest.fixture
def manager():
    return AlertManager(cooldown_seconds=60)


def test_should_alert_new_job(manager):
    assert manager.should_alert("backup") is True


def test_should_alert_after_record(manager):
    manager.record_alert("backup")
    assert manager.should_alert("backup") is False


def test_should_alert_after_cooldown(manager):
    with patch("cronwatcher.alerting.time.time", return_value=1000.0):
        manager.record_alert("backup")
    with patch("cronwatcher.alerting.time.time", return_value=1061.0):
        assert manager.should_alert("backup") is True


def test_should_not_alert_within_cooldown(manager):
    with patch("cronwatcher.alerting.time.time", return_value=1000.0):
        manager.record_alert("backup")
    with patch("cronwatcher.alerting.time.time", return_value=1059.0):
        assert manager.should_alert("backup") is False


def test_alert_count_increments(manager):
    assert manager.alert_count("backup") == 0
    manager.record_alert("backup")
    manager.record_alert("backup")
    assert manager.alert_count("backup") == 2


def test_alert_count_unknown_job(manager):
    assert manager.alert_count("nonexistent") == 0


def test_reset_specific_job(manager):
    manager.record_alert("backup")
    manager.record_alert("cleanup")
    manager.reset("backup")
    assert manager.should_alert("backup") is True
    assert manager.should_alert("cleanup") is False


def test_reset_all_jobs(manager):
    manager.record_alert("backup")
    manager.record_alert("cleanup")
    manager.reset()
    assert manager.should_alert("backup") is True
    assert manager.should_alert("cleanup") is True


def test_multiple_jobs_independent(manager):
    with patch("cronwatcher.alerting.time.time", return_value=1000.0):
        manager.record_alert("job_a")
    assert manager.should_alert("job_b") is True
    assert manager.should_alert("job_a") is False
