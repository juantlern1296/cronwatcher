"""Parse shadow mode configuration."""
from __future__ import annotations

from typing import Optional

from cronwatcher.alert_shadow import ShadowConfig
from cronwatcher.config import WebhookConfig


def parse_shadow_config(config: dict) -> Optional[ShadowConfig]:
    """Return ShadowConfig from the top-level config dict, or None if absent/disabled."""
    section = config.get("shadow")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("'shadow' must be a dict")
    if not section.get("enabled", True):
        return None
    url = section.get("webhook_url")
    if not url:
        raise ValueError("shadow.webhook_url is required")
    headers = section.get("headers", {})
    if not isinstance(headers, dict):
        raise ValueError("shadow.headers must be a dict")
    webhook = WebhookConfig(url=url, headers=headers)
    return ShadowConfig(webhook=webhook, enabled=True)
