"""Parse alert inhibition rules from the config dict."""
from __future__ import annotations

from typing import Any, Dict, List

from cronwatcher.alert_inhibition import AlertInhibition, InhibitionRule


def parse_alert_inhibition(config: Dict[str, Any]) -> AlertInhibition:
    """Parse the optional ``inhibition`` section from the top-level config dict.

    Expected shape::

        "inhibition": [
            {"source": "db_backup", "targets": ["db_cleanup", "db_report"]},
            ...
        ]

    Returns an :class:`AlertInhibition` instance (empty rules if section absent).
    """
    raw = config.get("inhibition")
    if raw is None:
        return AlertInhibition()

    if not isinstance(raw, list):
        raise ValueError("'inhibition' must be a list")

    rules: List[InhibitionRule] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"inhibition[{idx}] must be a dict")

        source = item.get("source")
        if not source or not isinstance(source, str):
            raise ValueError(f"inhibition[{idx}] missing or invalid 'source'")

        targets = item.get("targets")
        if not targets or not isinstance(targets, list):
            raise ValueError(f"inhibition[{idx}] missing or invalid 'targets'")
        if not all(isinstance(t, str) for t in targets):
            raise ValueError(f"inhibition[{idx}] 'targets' must be a list of strings")

        rules.append(InhibitionRule(source_job=source, target_jobs=list(targets)))

    return AlertInhibition(rules=rules)
