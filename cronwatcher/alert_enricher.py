"""Enriches alert payloads with additional context before dispatch."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class EnricherConfig:
    add_hostname: bool = True
    add_env: Optional[str] = None
    static_fields: Dict[str, str] = field(default_factory=dict)


def enrich_payload(
    payload: WebhookPayload,
    config: EnricherConfig,
) -> WebhookPayload:
    """Return a new WebhookPayload with enriched extra_fields."""
    extras: Dict[str, Any] = dict(payload.extra_fields or {})

    if config.add_hostname and "hostname" not in extras:
        try:
            extras["hostname"] = socket.gethostname()
        except Exception:  # pragma: no cover
            extras["hostname"] = "unknown"

    if config.add_env is not None:
        extras["env"] = config.add_env

    for key, value in config.static_fields.items():
        if key not in extras:
            extras[key] = value

    return WebhookPayload(
        job_name=payload.job_name,
        exit_code=payload.exit_code,
        timestamp=payload.timestamp,
        log_line=payload.log_line,
        extra_fields=extras,
    )


def parse_alert_enricher(raw: Dict[str, Any]) -> Optional[EnricherConfig]:
    """Parse enricher config from the top-level config dict."""
    section = raw.get("alert_enricher")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_enricher must be a dict")

    add_hostname = section.get("add_hostname", True)
    if not isinstance(add_hostname, bool):
        raise ValueError("alert_enricher.add_hostname must be a boolean")

    add_env = section.get("env", None)
    if add_env is not None and not isinstance(add_env, str):
        raise ValueError("alert_enricher.env must be a string")

    static_fields = section.get("static_fields", {})
    if not isinstance(static_fields, dict):
        raise ValueError("alert_enricher.static_fields must be a dict")
    for k, v in static_fields.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ValueError("alert_enricher.static_fields keys and values must be strings")

    return EnricherConfig(
        add_hostname=add_hostname,
        add_env=add_env,
        static_fields=static_fields,
    )
