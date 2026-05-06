"""Tests for the health check HTTP server."""

import json
import time
import urllib.request
from unittest.mock import MagicMock

import pytest

from cronwatcher.health import HealthServer
from cronwatcher.metrics import MetricsStore


TEST_PORT = 18765


@pytest.fixture
def store():
    return MetricsStore()


@pytest.fixture
def server(store):
    s = HealthServer(port=TEST_PORT, metrics_store=store)
    s.start()
    time.sleep(0.05)  # let the thread spin up
    yield s
    s.stop()


def test_invalid_port_raises():
    with pytest.raises(ValueError):
        HealthServer(port=0)

    with pytest.raises(ValueError):
        HealthServer(port=99999)


def test_health_endpoint_returns_ok(server):
    with urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT}/health") as resp:
        assert resp.status == 200
        body = json.loads(resp.read())
    assert body["status"] == "ok"


def test_unknown_path_returns_404(server):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT}/unknown")
        pytest.fail("Expected HTTPError")
    except urllib.error.HTTPError as e:
        assert e.code == 404


def test_metrics_endpoint_empty(server):
    with urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT}/metrics") as resp:
        assert resp.status == 200
        body = json.loads(resp.read())
    assert body == {}


def test_metrics_endpoint_with_data(server, store):
    store.record_failure("backup_job")
    store.record_failure("backup_job")
    store.record_alert("backup_job")

    with urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT}/metrics") as resp:
        body = json.loads(resp.read())

    assert "backup_job" in body
    assert body["backup_job"]["failures"] == 2
    assert body["backup_job"]["alerts_sent"] == 1


def test_metrics_unavailable_when_no_store():
    s = HealthServer(port=TEST_PORT + 1, metrics_store=None)
    s.start()
    time.sleep(0.05)
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT + 1}/metrics")
        pytest.fail("Expected HTTPError")
    except urllib.error.HTTPError as e:
        assert e.code == 503
    finally:
        s.stop()
