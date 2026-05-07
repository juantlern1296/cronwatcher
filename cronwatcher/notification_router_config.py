"""Parses notification routing rules from config dict."""

from typing import Any, Dict, List, Optional

from cronwatcher.config import WebhookConfig
from cronwatcher.notification_router import RouteRule, NotificationRouter, build_router


def _parse_webhook_config(data: Dict[str, Any]) -> WebhookConfig:
    url = data.get("url")
    if not url:
        raise ValueError("Route webhook missing 'url'")
    return WebhookConfig(
        url=url,
        secret=data.get("secret"),
        timeout=int(data.get("timeout", 10)),
        headers=data.get("headers", {}),
    )


def parse_notification_router(
    config: Dict[str, Any],
    default_webhook: WebhookConfig,
) -> NotificationRouter:
    """Parse 'notification_routes' section from config dict.

    Each route entry must have: label_key, label_value, webhook.url.
    Falls back to default_webhook when no routes are defined or matched.
    """
    raw_routes = config.get("notification_routes", [])
    if not isinstance(raw_routes, list):
        raise ValueError("'notification_routes' must be a list")

    rules: List[RouteRule] = []
    for i, entry in enumerate(raw_routes):
        if not isinstance(entry, dict):
            raise ValueError(f"Route entry {i} must be a dict")
        key = entry.get("label_key")
        value = entry.get("label_value")
        webhook_data = entry.get("webhook")
        if not key:
            raise ValueError(f"Route entry {i} missing 'label_key'")
        if value is None:
            raise ValueError(f"Route entry {i} missing 'label_value'")
        if not isinstance(webhook_data, dict):
            raise ValueError(f"Route entry {i} missing 'webhook' dict")
        rules.append(RouteRule(
            label_key=key,
            label_value=str(value),
            webhook=_parse_webhook_config(webhook_data),
        ))

    return build_router(default_webhook=default_webhook, routes=rules)
