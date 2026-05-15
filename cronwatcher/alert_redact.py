"""Alert payload redaction — strips or masks sensitive fields before dispatch."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List

from cronwatcher.webhook import WebhookPayload


_DEFAULT_MASK = "***"
_SENSITIVE_PATTERNS = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
]


@dataclass
class RedactConfig:
    mask: str = _DEFAULT_MASK
    extra_fields: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.mask:
            raise ValueError("mask must be a non-empty string")


def _is_sensitive(key: str, extra_fields: List[str]) -> bool:
    if key in extra_fields:
        return True
    return any(p.search(key) for p in _SENSITIVE_PATTERNS)


def redact_payload(payload: WebhookPayload, cfg: RedactConfig) -> WebhookPayload:
    """Return a new payload with sensitive extra_fields values masked."""
    if not payload.extra_fields:
        return payload

    redacted = {
        k: (cfg.mask if _is_sensitive(k, cfg.extra_fields) else v)
        for k, v in payload.extra_fields.items()
    }
    return WebhookPayload(
        job_name=payload.job_name,
        exit_code=payload.exit_code,
        timestamp=payload.timestamp,
        hostname=payload.hostname,
        message=payload.message,
        extra_fields=redacted,
    )


class AlertRedactor:
    def __init__(self, cfg: RedactConfig, handler: Callable[[WebhookPayload], None]) -> None:
        self._cfg = cfg
        self._handler = handler

    def handle(self, payload: WebhookPayload) -> None:
        self._handler(redact_payload(payload, self._cfg))
