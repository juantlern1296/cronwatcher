"""Parse alert_correlation section from config dict."""
from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.alert_correlation import CorrelationConfig

_DEFAULTS: Dict[str, Any] = {
    "window_seconds": 60.0,
    "group_by": "job",
    "min_count": 2,
    "pattern": None,
}


def parse_alert_correlation(raw: Dict[str, Any]) -> Optional[CorrelationConfig]:
    """Return a CorrelationConfig if 'alert_correlation' key exists, else None."""
    section = raw.get("alert_correlation")
    if section is None:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_correlation must be a JSON object")

    window = section.get("window_seconds", _DEFAULTS["window_seconds"])
    group_by = section.get("group_by", _DEFAULTS["group_by"])
    min_count = section.get("min_count", _DEFAULTS["min_count"])
    pattern = section.get("pattern", _DEFAULTS["pattern"])

    try:
        window = float(window)
    except (TypeError, ValueError):
        raise ValueError("alert_correlation.window_seconds must be a number")

    try:
        min_count = int(min_count)
    except (TypeError, ValueError):
        raise ValueError("alert_correlation.min_count must be an integer")

    if not isinstance(group_by, str):
        raise ValueError("alert_correlation.group_by must be a string")

    if pattern is not None and not isinstance(pattern, str):
        raise ValueError("alert_correlation.pattern must be a string or null")

    return CorrelationConfig(
        window_seconds=window,
        group_by=group_by,
        min_count=min_count,
        pattern=pattern,
    )
