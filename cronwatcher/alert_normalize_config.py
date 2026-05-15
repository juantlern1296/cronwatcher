"""Config parsing and handler wiring for alert_normalize."""

from __future__ import annotations

from typing import Callable, Optional

from cronwatcher.alert_normalize import AlertNormalizer, NormalizeConfig
from cronwatcher.webhook import WebhookPayload


def parse_normalize_config(raw: dict) -> Optional[NormalizeConfig]:
    """Parse the 'normalize' section of the config dict.

    Returns None if the section is absent or disabled.
    """
    section = raw.get("normalize")
    if section is None:
        return None
    if not isinstance(section, dict):
        raise ValueError("'normalize' must be a dict")
    if not section.get("enabled", True):
        return None

    max_len = section.get("max_message_length")
    if max_len is not None:
        max_len = int(max_len)

    return NormalizeConfig(
        lowercase_job_name=bool(section.get("lowercase_job_name", True)),
        strip_whitespace=bool(section.get("strip_whitespace", True)),
        max_message_length=max_len,
    )


def wrap_with_normalizer(
    config: NormalizeConfig, handler: Callable[[WebhookPayload], None]
) -> AlertNormalizer:
    return AlertNormalizer(config=config, handler=handler)


def normalized_handler(
    raw: dict, handler: Callable[[WebhookPayload], None]
) -> Callable[[WebhookPayload], None]:
    """Return handler wrapped with normalization if configured, else return as-is."""
    config = parse_normalize_config(raw)
    if config is None:
        return handler
    normalizer = wrap_with_normalizer(config, handler)
    return normalizer.handle
