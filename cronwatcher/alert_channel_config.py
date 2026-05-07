"""Parse alert channel definitions from config dict."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from cronwatcher.config import WebhookConfig
from cronwatcher.alert_channel import AlertChannel, AlertChannelRegistry


def _parse_single_channel(raw: Any, index: int) -> AlertChannel:
    if not isinstance(raw, dict):
        raise ValueError(f"alert_channels[{index}] must be a dict")

    name = raw.get("name", "")
    if not name or not isinstance(name, str):
        raise ValueError(f"alert_channels[{index}] missing required 'name'")

    url = raw.get("url", "")
    if not url or not isinstance(url, str):
        raise ValueError(f"alert_channels[{index}] missing required 'url'")

    headers: Dict[str, str] = {}
    raw_headers = raw.get("headers", {})
    if isinstance(raw_headers, dict):
        headers = {str(k): str(v) for k, v in raw_headers.items()}

    tags: list = []
    raw_tags = raw.get("tags", [])
    if isinstance(raw_tags, list):
        tags = [str(t) for t in raw_tags]

    cfg = WebhookConfig(url=url, headers=headers)
    return AlertChannel(name=name, webhook_config=cfg, tags=tags)


def parse_alert_channels(config: Dict[str, Any]) -> AlertChannelRegistry:
    registry = AlertChannelRegistry()
    raw_list = config.get("alert_channels")
    if raw_list is None:
        return registry
    if not isinstance(raw_list, list):
        raise ValueError("'alert_channels' must be a list")
    for i, item in enumerate(raw_list):
        channel = _parse_single_channel(item, i)
        registry.register(channel)
    return registry
