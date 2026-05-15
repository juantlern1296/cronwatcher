from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from cronwatcher.alert_counter import AlertCounter, CounterConfig, wrap_with_counter
from cronwatcher.webhook import WebhookPayload

_DEFAULTS: Dict[str, Any] = {
    "window": 300.0,
    "max_count": 10,
}


def parse_counter_config(raw: Dict[str, Any]) -> Optional[CounterConfig]:
    """Parse alert_counter section from config dict.

    Returns None if the section is absent or disabled.
    """
    section = raw.get("alert_counter")
    if section is None:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_counter must be a dict")
    if not section.get("enabled", True):
        return None

    window = float(section.get("window", _DEFAULTS["window"]))
    max_count = int(section.get("max_count", _DEFAULTS["max_count"]))
    return CounterConfig(window=window, max_count=max_count)


def counter_handler(
    raw: Dict[str, Any],
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    """Wrap handler with AlertCounter if config section present, else pass through."""
    config = parse_counter_config(raw)
    if config is None:
        return handler
    return wrap_with_counter(config, handler)
