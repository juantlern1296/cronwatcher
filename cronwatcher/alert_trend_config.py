"""Config parsing for alert trend detection."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from cronwatcher.alert_trend import AlertTrend, TrendConfig
from cronwatcher.webhook import WebhookPayload

_DEFAULTS = {
    "window_size": 20,
    "min_samples": 6,
    "spike_ratio": 2.0,
}


def parse_trend_config(raw: Dict[str, Any]) -> Optional[TrendConfig]:
    section = raw.get("alert_trend")
    if not section:
        return None
    if section.get("enabled") is False:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_trend must be a dict")

    window_size = int(section.get("window_size", _DEFAULTS["window_size"]))
    min_samples = int(section.get("min_samples", _DEFAULTS["min_samples"]))
    spike_ratio = float(section.get("spike_ratio", _DEFAULTS["spike_ratio"]))

    return TrendConfig(
        window_size=window_size,
        min_samples=min_samples,
        spike_ratio=spike_ratio,
    )


def wrap_with_trend(
    trend: AlertTrend,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    def _inner(payload: WebhookPayload) -> None:
        trend.record(payload)
        handler(payload)

    return _inner


def trend_handler(
    raw: Dict[str, Any],
    handler: Callable[[WebhookPayload], None],
    on_trend: Callable[[WebhookPayload, float], None],
) -> Callable[[WebhookPayload], None]:
    cfg = parse_trend_config(raw)
    if cfg is None:
        return handler
    trend = AlertTrend(cfg, on_trend)
    return wrap_with_trend(trend, handler)
