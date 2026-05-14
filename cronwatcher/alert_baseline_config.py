"""Config parsing for alert baseline deviation detection."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from cronwatcher.alert_baseline import AlertBaseline, BaselineConfig
from cronwatcher.webhook import WebhookPayload

_DEFAULT_WINDOW_SIZE = 10
_DEFAULT_DEVIATION_FACTOR = 2.0


def parse_baseline_config(raw: Dict[str, Any]) -> Optional[BaselineConfig]:
    section = raw.get("alert_baseline")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_baseline must be a dict")

    window_size = section.get("window_size", _DEFAULT_WINDOW_SIZE)
    deviation_factor = section.get("deviation_factor", _DEFAULT_DEVIATION_FACTOR)

    if not isinstance(window_size, int) or window_size < 1:
        raise ValueError("alert_baseline.window_size must be a positive integer")
    if not isinstance(deviation_factor, (int, float)) or deviation_factor <= 1.0:
        raise ValueError("alert_baseline.deviation_factor must be a float greater than 1.0")

    return BaselineConfig(window_size=window_size, deviation_factor=float(deviation_factor))


def wrap_with_baseline(
    config: BaselineConfig,
    on_deviation: Callable[[WebhookPayload], None],
) -> AlertBaseline:
    return AlertBaseline(config=config, on_deviation=on_deviation)


def baseline_handler(
    raw: Dict[str, Any],
    on_deviation: Callable[[WebhookPayload], None],
) -> Optional[AlertBaseline]:
    cfg = parse_baseline_config(raw)
    if cfg is None:
        return None
    return wrap_with_baseline(cfg, on_deviation)
