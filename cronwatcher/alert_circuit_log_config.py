"""Config parsing for CircuitTransitionLog."""
from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.alert_circuit_log import CircuitTransitionLog

_DEFAULT_MAX_ENTRIES = 200


def parse_circuit_log_config(raw: Dict[str, Any]) -> Optional[CircuitTransitionLog]:
    """Parse 'circuit_log' section from config dict.

    Returns None if the section is absent or disabled.
    """
    section = raw.get("circuit_log")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("'circuit_log' must be a dict")
    if not section.get("enabled", True):
        return None

    max_entries = section.get("max_entries", _DEFAULT_MAX_ENTRIES)
    if not isinstance(max_entries, int) or max_entries < 1:
        raise ValueError("circuit_log.max_entries must be a positive integer")

    return CircuitTransitionLog(max_entries=max_entries)
