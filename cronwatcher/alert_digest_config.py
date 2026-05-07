"""Parse alert digest configuration from the config dict."""

from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.alert_digest import DigestConfig

_DEFAULT_INTERVAL = 300.0  # 5 minutes
_DEFAULT_MIN_ALERTS = 2


def parse_alert_digest(config: Dict[str, Any]) -> Optional[DigestConfig]:
    """Return a DigestConfig if 'alert_digest' section exists and is enabled.

    Expected config shape::

        "alert_digest": {
            "enabled": true,
            "interval_seconds": 300,
            "min_alerts": 2
        }

    Returns None when the section is absent or ``enabled`` is false.
    """
    section = config.get("alert_digest")
    if not section:
        return None
    if not isinstance(section, dict):
        raise TypeError("alert_digest must be a JSON object")
    if not section.get("enabled", True):
        return None

    interval = section.get("interval_seconds", _DEFAULT_INTERVAL)
    if not isinstance(interval, (int, float)) or interval <= 0:
        raise ValueError("alert_digest.interval_seconds must be a positive number")

    min_alerts = section.get("min_alerts", _DEFAULT_MIN_ALERTS)
    if not isinstance(min_alerts, int) or min_alerts < 1:
        raise ValueError("alert_digest.min_alerts must be a positive integer")

    return DigestConfig(
        interval_seconds=float(interval),
        min_alerts=min_alerts,
    )
