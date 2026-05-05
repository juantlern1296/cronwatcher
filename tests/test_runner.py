"""Tests for cronwatcher.runner module."""

import pytest
from unittest.mock import MagicMock, patch, call
from cronwatcher.alerting import AlertManager
from cronwatcher.runner import make_failure_handler
from cronwatcher.log_parser import CronLogEntry
from cronwatcher.config import Config, WebhookConfig


@pytest.fixture
def webhook_cfg():
    return WebhookConfig(url="https://hooks.example.com/alert", timeout=5)


@pytest.fixture
def config(webhook_cfg):
    return Config(
        log_path="/var/log/syslog",
        webhook=webhook_cfg,
        jobs={},
        alert_cooldown_seconds=300,
        debug=False,
    )


@pytest.fixture
def entry():
    e = MagicMock(spec=CronLogEntry)
    e.job_name = "backup"
    return e


def test_on_failure_sends_webhook(config, entry):
    manager = AlertManager(cooldown_seconds=0)
    handler = make_failure_handler(config, manager)

    with patch("cronwatcher.runner.build_payload", return_value={}) as bp, \
         patch("cronwatcher.runner.send_webhook", return_value=True) as sw:
        handler(entry)
        bp.assert_called_once()
        sw.assert_called_once()


def test_on_failure_records_alert_on_success(config, entry):
    manager = AlertManager(cooldown_seconds=300)
    handler = make_failure_handler(config, manager)

    with patch("cronwatcher.runner.build_payload", return_value={}), \
         patch("cronwatcher.runner.send_webhook", return_value=True):
        handler(entry)

    assert manager.alert_count("backup") == 1


def test_on_failure_suppresses_duplicate(config, entry):
    manager = AlertManager(cooldown_seconds=300)
    manager.record_alert("backup")
    handler = make_failure_handler(config, manager)

    with patch("cronwatcher.runner.send_webhook") as sw:
        handler(entry)
        sw.assert_not_called()


def test_on_failure_no_record_on_send_failure(config, entry):
    manager = AlertManager(cooldown_seconds=0)
    handler = make_failure_handler(config, manager)

    with patch("cronwatcher.runner.build_payload", return_value={}), \
         patch("cronwatcher.runner.send_webhook", return_value=False):
        handler(entry)

    assert manager.alert_count("backup") == 0


def test_on_failure_unknown_job_name(config):
    manager = AlertManager(cooldown_seconds=0)
    handler = make_failure_handler(config, manager)
    entry = MagicMock(spec=CronLogEntry)
    entry.job_name = None

    with patch("cronwatcher.runner.build_payload", return_value={}), \
         patch("cronwatcher.runner.send_webhook", return_value=True):
        handler(entry)

    assert manager.alert_count("unknown") == 1
