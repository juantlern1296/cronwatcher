"""Parse alert retention config and build AlertRetention wrapper."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from cronwatcher.alert_retention import AlertRetention, RetentionConfig
from cronwatcher.webhook import WebhookPayload


def parse_retention_config(raw: Dict[str, Any]) -> Optional[RetentionConfig]:
    section = raw.get("alert_retention")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_retention must be a dict")
    if section.get("enabled") is False:
        return None

    max_age = section.get("max_age_seconds", 3600)
    max_records = section.get("max_records", 1000)

    try:
        max_age = float(max_age)
    except (TypeError, ValueError):
        raise ValueError("alert_retention.max_age_seconds must be a number")

    try:
        max_records = int(max_records)
    except (TypeError, ValueError):
        raise ValueError("alert_retention.max_records must be an integer")

    return RetentionConfig(max_age_seconds=max_age, max_records=max_records)


def wrap_with_retention(
    config: RetentionConfig, handler: Callable[[WebhookPayload], None]
) -> AlertRetention:
    return AlertRetention(config=config, handler=handler)


def retention_handler(
    raw: Dict[str, Any], handler: Callable[[WebhookPayload], None]
) -> Callable[[WebhookPayload], None]:
    cfg = parse_retention_config(raw)
    if cfg is None:
        return handler
    retention = wrap_with_retention(cfg, handler)
    return retention.handle
