"""Integration helpers for alert deduplication in the handler pipeline."""

from __future__ import annotations

from typing import Callable, Optional

from cronwatcher.alert_dedup import AlertDedup
from cronwatcher.webhook import WebhookPayload

Handler = Callable[[WebhookPayload], None]


def wrap_with_dedup(dedup: AlertDedup, handler: Handler) -> Handler:
    """Return a handler that skips duplicates within the configured window."""

    def _handler(payload: WebhookPayload) -> None:
        if dedup.is_duplicate(payload):
            return
        dedup.record(payload)
        handler(payload)

    return _handler


def deduped_handler(
    config: dict,
    handler: Handler,
) -> Handler:
    """Convenience wrapper: parse config and wrap handler if section present."""
    from cronwatcher.alert_dedup import parse_alert_dedup

    dedup: Optional[AlertDedup] = parse_alert_dedup(config)
    if dedup is None:
        return handler
    return wrap_with_dedup(dedup, handler)
