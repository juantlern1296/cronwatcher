"""Parse throttle configuration from the config dict."""

from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.throttle import AlertThrottle, ThrottleConfig

_DEFAULT_MAX_ALERTS = 5
_DEFAULT_WINDOW_SECONDS = 300.0  # 5 minutes


def parse_throttle_config(config: Dict[str, Any]) -> Optional[AlertThrottle]:
    """Return an AlertThrottle built from *config*, or None if the section is absent.

    Expected config shape::

        {
          "throttle": {
            "max_alerts": 3,
            "window_seconds": 120
          }
        }
    """
    section = config.get("throttle")
    if section is None:
        return None

    if not isinstance(section, dict):
        raise ValueError("'throttle' must be a JSON object")

    max_alerts = section.get("max_alerts", _DEFAULT_MAX_ALERTS)
    window_seconds = section.get("window_seconds", _DEFAULT_WINDOW_SECONDS)

    if not isinstance(max_alerts, int) or max_alerts < 1:
        raise ValueError("throttle.max_alerts must be an integer >= 1")
    if not isinstance(window_seconds, (int, float)) or window_seconds <= 0:
        raise ValueError("throttle.window_seconds must be a positive number")

    cfg = ThrottleConfig(max_alerts=max_alerts, window_seconds=float(window_seconds))
    return AlertThrottle(cfg)
