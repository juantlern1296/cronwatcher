"""Helpers to wrap a handler with AlertTagger enrichment."""
from __future__ import annotations

from typing import Callable, Optional

from cronwatcher.alert_tag import AlertTagger, TagConfig, parse_tag_config
from cronwatcher.webhook import WebhookPayload


def wrap_with_tagger(
    handler: Callable[[WebhookPayload], None],
    tagger: AlertTagger,
) -> Callable[[WebhookPayload], None]:
    """Return a new handler that tags the payload before forwarding."""

    def _handler(payload: WebhookPayload) -> None:
        tagged = tagger.tag(payload)
        handler(tagged)

    return _handler


def tagged_handler(
    raw_config: dict,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    """Build a tagging handler from raw config, or return *handler* unchanged."""
    config: Optional[TagConfig] = parse_tag_config(raw_config)
    if config is None:
        return handler
    tagger = AlertTagger(config)
    return wrap_with_tagger(handler, tagger)
