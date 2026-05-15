"""Normalize alert payloads before dispatch — trim whitespace, lowercase job names, etc."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class NormalizeConfig:
    lowercase_job_name: bool = True
    strip_whitespace: bool = True
    max_message_length: Optional[int] = None

    def __post_init__(self) -> None:
        if self.max_message_length is not None and self.max_message_length < 1:
            raise ValueError("max_message_length must be a positive integer")


def normalize_payload(payload: WebhookPayload, config: NormalizeConfig) -> WebhookPayload:
    """Return a new WebhookPayload with fields normalized according to config."""
    job_name = payload.job_name
    message = payload.message
    hostname = payload.hostname
    extra = dict(payload.extra) if payload.extra else {}

    if config.strip_whitespace:
        if job_name is not None:
            job_name = job_name.strip()
        if message is not None:
            message = message.strip()
        if hostname is not None:
            hostname = hostname.strip()
        extra = {k: v.strip() if isinstance(v, str) else v for k, v in extra.items()}

    if config.lowercase_job_name and job_name is not None:
        job_name = job_name.lower()

    if config.max_message_length is not None and message is not None:
        message = message[: config.max_message_length]

    return WebhookPayload(
        job_name=job_name,
        exit_code=payload.exit_code,
        timestamp=payload.timestamp,
        hostname=hostname,
        message=message,
        extra=extra,
    )


class AlertNormalizer:
    def __init__(self, config: NormalizeConfig, handler: Callable[[WebhookPayload], None]) -> None:
        self._config = config
        self._handler = handler

    def handle(self, payload: WebhookPayload) -> None:
        normalized = normalize_payload(payload, self._config)
        self._handler(normalized)
