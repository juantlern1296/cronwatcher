"""Parse alert mute windows from config."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from cronwatcher.alert_mute import AlertMute, MuteWindow


def _parse_window(raw: Any, idx: int) -> MuteWindow:
    if not isinstance(raw, dict):
        raise ValueError(f"mute_windows[{idx}] must be a dict")

    job_name = raw.get("job", "*")
    if not isinstance(job_name, str):
        raise ValueError(f"mute_windows[{idx}].job must be a string")

    start = raw.get("start")
    end = raw.get("end")
    if start is None or end is None:
        raise ValueError(f"mute_windows[{idx}] must have 'start' and 'end' (unix timestamps)")

    try:
        start = float(start)
        end = float(end)
    except (TypeError, ValueError):
        raise ValueError(f"mute_windows[{idx}] 'start' and 'end' must be numeric timestamps")

    if end <= start:
        raise ValueError(f"mute_windows[{idx}] 'end' must be greater than 'start'")

    reason = str(raw.get("reason", ""))
    return MuteWindow(job_name=job_name, start=start, end=end, reason=reason)


def parse_alert_mute(config: Dict[str, Any]) -> AlertMute:
    """Parse 'mute_windows' section from config dict. Returns an AlertMute instance."""
    mute = AlertMute()
    raw_list = config.get("mute_windows")
    if raw_list is None:
        return mute
    if not isinstance(raw_list, list):
        raise ValueError("'mute_windows' must be a list")
    for idx, item in enumerate(raw_list):
        mute.add_window(_parse_window(item, idx))
    return mute
