"""Parse snooze rules from config (optional section)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.alert_snooze import AlertSnooze


def parse_alert_snooze(config: Dict[str, Any]) -> Optional[AlertSnooze]:
    """Return an AlertSnooze pre-loaded with any static snooze rules.

    Config section example::

        "alert_snooze": [
            {"job": "backup", "duration": 3600, "reason": "maintenance"},
            {"job": "report", "duration": 1800}
        ]

    Returns None if the section is absent.
    """
    section = config.get("alert_snooze")
    if section is None:
        return None

    if not isinstance(section, list):
        raise ValueError("alert_snooze must be a list")

    snooze = AlertSnooze()
    for i, item in enumerate(section):
        if not isinstance(item, dict):
            raise ValueError(f"alert_snooze[{i}] must be a dict")
        job = item.get("job")
        if not job or not isinstance(job, str):
            raise ValueError(f"alert_snooze[{i}] missing required string 'job'")
        duration = item.get("duration")
        if duration is None:
            raise ValueError(f"alert_snooze[{i}] missing required 'duration'")
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            raise ValueError(f"alert_snooze[{i}] 'duration' must be a number")
        reason = item.get("reason", "")
        snooze.snooze(job, duration, reason=reason)

    return snooze
