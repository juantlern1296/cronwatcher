"""Parse replay configuration from the top-level config dict."""

from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.alert_replay import ReplayConfig

_SECTION = "replay"
_DEFAULT_MAX_REPLAYS = 50


def parse_replay_config(raw: Dict[str, Any]) -> Optional[ReplayConfig]:
    """Return a ReplayConfig from *raw* config dict, or None if section absent.

    Expected JSON shape::

        "replay": {
            "max_replays": 100,
            "dry_run": false
        }
    """
    section = raw.get(_SECTION)
    if section is None:
        return None

    if not isinstance(section, dict):
        raise ValueError(f"'{_SECTION}' must be a JSON object")

    max_replays = section.get("max_replays", _DEFAULT_MAX_REPLAYS)
    if not isinstance(max_replays, int) or max_replays < 1:
        raise ValueError("replay.max_replays must be a positive integer")

    dry_run = section.get("dry_run", False)
    if not isinstance(dry_run, bool):
        raise ValueError("replay.dry_run must be a boolean")

    return ReplayConfig(max_replays=max_replays, dry_run=dry_run)
