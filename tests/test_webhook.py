import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.config import WebhookConfig
from cronwatcher.log_parser import CronLogEntry
from cronwatcher.webhook import WebhookPayload, build_payload, send_webhook


@pytest.fixture
def webhook_config():
    return WebhookConfig(url="https://example.com/hook", timeout_seconds=5, secret=None)


@pytest.fixture
def sample_entry():
    return CronLogEntry(
        timestamp="2024-01-15T10:30:00",
        job_name="backup-job",
        exit_code=1,
        raw_line="Jan 15 10:30:00 CROND[1234]: (root) CMD (backup.sh) EXIT CODE 1",
    )


def test_build_payload(sample_entry):
    payload = build_payload(sample_entry, hostname="myserver")
    assert payload.job_name == "backup-job"
    assert payload.exit_code == 1
    assert payload.hostname == "myserver"
    assert payload.timestamp == sample_entry.timestamp


def test_build_payload_no_hostname(sample_entry):
    payload = build_payload(sample_entry)
    assert payload.hostname is None


def test_build_payload_missing_job_name():
    entry = CronLogEntry(timestamp="2024-01-15T10:30:00", job_name=None, exit_code=2, raw_line="raw")
    payload = build_payload(entry)
    assert payload.job_name == "unknown"
    assert payload.exit_code == 2


def test_payload_to_dict():
    payload = WebhookPayload(
        job_name="test-job", exit_code=1, timestamp="2024-01-15", raw_line="raw", hostname="host"
    )
    d = payload.to_dict()
    assert d["job_name"] == "test-job"
    assert d["exit_code"] == 1
    assert d["hostname"] == "host"


def _make_mock_response(status: int) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_send_webhook_success(webhook_config):
    payload = WebhookPayload(job_name="job", exit_code=1, timestamp="ts", raw_line="raw")
    with patch("urllib.request.urlopen", return_value=_make_mock_response(200)) as mock_open:
        result = send_webhook(webhook_config, payload)
    assert result is True
    mock_open.assert_called_once()


def test_send_webhook_non_2xx(webhook_config):
    payload = WebhookPayload(job_name="job", exit_code=1, timestamp="ts", raw_line="raw")
    with patch("urllib.request.urlopen", return_value=_make_mock_response(500)):
        result = send_webhook(webhook_config, payload)
    assert result is False


def test_send_webhook_includes_secret():
    config = WebhookConfig(url="https://example.com/hook", timeout_seconds=5, secret="mysecret")
    payload = WebhookPayload(job_name="job", exit_code=1, timestamp="ts", raw_line="raw")
    captured = {}

    def fake_urlopen(req, timeout):
        captured["headers"] = req.headers
        return _make_mock_response(200)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        send_webhook(config, payload)

    assert captured["headers"].get("X-webhook-secret") == "mysecret"


def test_send_webhook_url_error(webhook_config):
    import urllib.error
    payload = WebhookPayload(job_name="job", exit_code=1, timestamp="ts", raw_line="raw")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        result = send_webhook(webhook_config, payload)
    assert result is False
