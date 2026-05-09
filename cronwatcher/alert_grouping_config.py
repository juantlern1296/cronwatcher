"""Parses alert grouping configuration from the config dict."""

from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.alert_grouping import AlertGrouper, GroupingConfig

_DEFAULTS = {
    "group_by": "job",
    "window_seconds": 60.0,
    "max_group_size": 20,
}


def parse_alert_grouping(raw: Dict[str, Any]) -> Optional[GroupingConfig]:
    """Return a GroupingConfig if 'alert_grouping' section is present, else None."""
    section = raw.get("alert_grouping")
    if section is None:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_grouping must be a JSON object")

    group_by = section.get("group_by", _DEFAULTS["group_by"])
    window_seconds = section.get("window_seconds", _DEFAULTS["window_seconds"])
    max_group_size = section.get("max_group_size", _DEFAULTS["max_group_size"])

    try:
        window_seconds = float(window_seconds)
    except (TypeError, ValueError):
        raise ValueError("alert_grouping.window_seconds must be a number")

    try:
        max_group_size = int(max_group_size)
    except (TypeError, ValueError):
        raise ValueError("alert_grouping.max_group_size must be an integer")

    return GroupingConfig(
        group_by=str(group_by),
        window_seconds=window_seconds,
        max_group_size=max_group_size,
    )
