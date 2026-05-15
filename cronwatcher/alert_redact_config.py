"""Config parsing for alert redaction."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from cronwatcher.alert_redact import AlertRedactor, RedactConfig
from cronwatcher.webhook import WebhookPayload


def parse_redact_config(raw: Dict[str, Any]) -> Optional[RedactConfig]:
    section = raw.get("alert_redact")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_redact must be a JSON object")
    if section.get("enabled") is False:
        return None

    mask = section.get("mask", "***")
    if not isinstance(mask, str) or not mask:
        raise ValueError("alert_redact.mask must be a non-empty string")

    extra = section.get("extra_fields", [])
    if not isinstance(extra, list):
        raise ValueError("alert_redact.extra_fields must be a list")
    if not all(isinstance(f, str) for f in extra):
        raise ValueError("alert_redact.extra_fields entries must be strings")

    return RedactConfig(mask=mask, extra_fields=extra)


def wrap_with_redactor(
    cfg: RedactConfig, handler: Callable[[WebhookPayload], None]
) -> Callable[[WebhookPayload], None]:
    redactor = AlertRedactor(cfg, handler)
    return redactor.handle


def redacted_handler(
    raw: Dict[str, Any], handler: Callable[[WebhookPayload], None]
) -> Callable[[WebhookPayload], None]:
    cfg = parse_redact_config(raw)
    if cfg is None:
        return handler
    return wrap_with_redactor(cfg, handler)
