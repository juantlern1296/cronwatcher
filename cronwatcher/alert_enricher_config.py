"""Helpers to apply enricher config during alert dispatch."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from cronwatcher.alert_enricher import EnricherConfig, enrich_payload
from cronwatcher.webhook import WebhookPayload


def wrap_with_enricher(
    handler: Callable[[WebhookPayload], None],
    config: Optional[EnricherConfig],
) -> Callable[[WebhookPayload], None]:
    """Wrap a payload handler so payloads are enriched before being passed on."""
    if config is None:
        return handler

    def enriched_handler(payload: WebhookPayload) -> None:
        enriched = enrich_payload(payload, config)
        handler(enriched)

    return enriched_handler
