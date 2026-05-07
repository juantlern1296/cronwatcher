"""Tests for parse_notification_router config parsing."""

import pytest

from cronwatcher.config import WebhookConfig
from cronwatcher.notification_router_config import parse_notification_router


@pytest.fixture
def default_webhook():
    return WebhookConfig(url="https://default.example.com/hook", secret=None, timeout=10, headers={})


def test_no_section_returns_router_with_no_routes(default_webhook):
    router = parse_notification_router({}, default_webhook)
    assert router.routes == []
    assert router.default_webhook == default_webhook


def test_valid_single_route(default_webhook):
    cfg = {
        "notification_routes": [
            {"label_key": "team", "label_value": "ops", "webhook": {"url": "https://ops.example.com"}}
        ]
    }
    router = parse_notification_router(cfg, default_webhook)
    assert len(router.routes) == 1
    assert router.routes[0].label_key == "team"
    assert router.routes[0].label_value == "ops"
    assert router.routes[0].webhook.url == "https://ops.example.com"


def test_multiple_routes(default_webhook):
    cfg = {
        "notification_routes": [
            {"label_key": "env", "label_value": "prod", "webhook": {"url": "https://prod.example.com"}},
            {"label_key": "env", "label_value": "staging", "webhook": {"url": "https://staging.example.com"}},
        ]
    }
    router = parse_notification_router(cfg, default_webhook)
    assert len(router.routes) == 2


def test_not_a_list_raises(default_webhook):
    with pytest.raises(ValueError, match="must be a list"):
        parse_notification_router({"notification_routes": "bad"}, default_webhook)


def test_entry_not_a_dict_raises(default_webhook):
    with pytest.raises(ValueError, match="must be a dict"):
        parse_notification_router({"notification_routes": ["not-a-dict"]}, default_webhook)


def test_missing_label_key_raises(default_webhook):
    entry = {"label_value": "ops", "webhook": {"url": "https://x.com"}}
    with pytest.raises(ValueError, match="label_key"):
        parse_notification_router({"notification_routes": [entry]}, default_webhook)


def test_missing_webhook_url_raises(default_webhook):
    entry = {"label_key": "team", "label_value": "ops", "webhook": {"timeout": 5}}
    with pytest.raises(ValueError, match="url"):
        parse_notification_router({"notification_routes": [entry]}, default_webhook)


def test_route_webhook_timeout_parsed(default_webhook):
    cfg = {
        "notification_routes": [
            {"label_key": "k", "label_value": "v", "webhook": {"url": "https://x.com", "timeout": 30}}
        ]
    }
    router = parse_notification_router(cfg, default_webhook)
    assert router.routes[0].webhook.timeout == 30
