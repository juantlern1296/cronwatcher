"""Convenience helpers for wiring AlertWindowFilter into the runner."""

from __future__ import annotations

from typing import Callable, Optional

from cronwatcher.alert_window_filter import AlertWindowFilter, parse_window_filter
from cronwatcher.webhook import WebhookPayload


def wrap_with_window_filter(
    config: dict,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    """Return a wrapped handler that applies time-window filtering, or the
    original handler if no alert_window_filter section is present."""
    wf: Optional[AlertWindowFilter] = parse_window_filter(config, handler)
    if wf is None:
        return handler

    def _handler(payload: WebhookPayload) -> None:
        wf.filter(payload)

    return _handler


def windowed_handler(
    config: dict,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    """Top-level helper used by the runner to optionally apply window filtering.

    Usage::

        send = windowed_handler(raw_config, base_send_fn)
        send(payload)  # silently dropped outside active windows
    """
    return wrap_with_window_filter(config, handler)
