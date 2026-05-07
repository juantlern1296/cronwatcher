"""Tests for NotificationRouter dispatch and label-based routing."""

from unittest.mock import patch, MagicMock
import pytest

from cronwatcher.config import WebhookConfig
from cronwatcher.notification_router import NotificationRouter, RouteRule, build_router
from cronwatcher.webhook import WebhookPayload


@pytest.fixture
def default_cfg():
    return WebhookConfig(url="https://default.example.com/hook", secret=None, timeout=10, headers={})


@pytest.fixture
def alt_cfg():
    return WebhookConfig(url="https://alt.example.com/hook", secret=None, timeout=10, headers={})


@pytest.fixture
def payload():
    return WebhookPayload(job="backup", exit_code=1, timestamp="2024-01-01T00:00:00Z",
                          hostname="host1", log_line="FAILED", labels={})


def test_no_routes_returns_default(default_cfg):
    router = build_router(default_cfg)
    result = router.resolve({"team": "ops"})
    assert result == [default_cfg]


def test_matching_label_returns_route_webhook(default_cfg, alt_cfg):
    rule = RouteRule(label_key="team", label_value="ops", webhook=alt_cfg)
    router = build_router(default_cfg, routes=[rule])
    result = router.resolve({"team": "ops"})
    assert result == [alt_cfg]


def test_non_matching_label_returns_default(default_cfg, alt_cfg):
    rule = RouteRule(label_key="team", label_value="ops", webhook=alt_cfg)
    router = build_router(default_cfg, routes=[rule])
    result = router.resolve({"team": "dev"})
    assert result == [default_cfg]


def test_multiple_matching_routes(default_cfg, alt_cfg):
    cfg2 = WebhookConfig(url="https://second.example.com/hook", secret=None, timeout=5, headers={})
    rules = [
        RouteRule(label_key="env", label_value="prod", webhook=alt_cfg),
        RouteRule(label_key="env", label_value="prod", webhook=cfg2),
    ]
    router = build_router(default_cfg, routes=rules)
    result = router.resolve({"env": "prod"})
    assert alt_cfg in result and cfg2 in result
    assert len(result) == 2


def test_dispatch_calls_send_webhook(default_cfg, payload):
    router = build_router(default_cfg)
    with patch("cronwatcher.notification_router.send_webhook", return_value=True) as mock_send:
        results = router.dispatch(payload, {})
    mock_send.assert_called_once_with(default_cfg, payload)
    assert results == [True]


def test_dispatch_returns_false_on_failure(default_cfg, payload):
    router = build_router(default_cfg)
    with patch("cronwatcher.notification_router.send_webhook", return_value=False):
        results = router.dispatch(payload, {})
    assert results == [False]


def test_empty_labels_uses_default(default_cfg):
    router = build_router(default_cfg)
    assert router.resolve({}) == [default_cfg]
