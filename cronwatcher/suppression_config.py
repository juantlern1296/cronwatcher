"""Parse job suppression configuration from the config dict."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SuppressionRule:
    job_name: str
    duration_seconds: float
    reason: str = ""


def parse_suppression_rules(config: Dict[str, Any]) -> List[SuppressionRule]:
    """Parse 'suppression' section from the top-level config dict.

    Example config section::

        "suppression": [
            {"job": "backup", "duration_seconds": 3600, "reason": "planned maintenance"},
            {"job": "report", "duration_seconds": 600}
        ]
    """
    raw = config.get("suppression")
    if raw is None:
        return []

    if not isinstance(raw, list):
        raise ValueError("'suppression' config section must be a list")

    rules: List[SuppressionRule] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"suppression entry {i} must be a dict")

        job_name = item.get("job")
        if not isinstance(job_name, str) or not job_name.strip():
            raise ValueError(f"suppression entry {i} missing valid 'job' field")

        duration = item.get("duration_seconds")
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise ValueError(
                f"suppression entry {i} 'duration_seconds' must be a positive number"
            )

        reason = item.get("reason", "")
        if not isinstance(reason, str):
            reason = str(reason)

        rules.append(SuppressionRule(job_name=job_name.strip(), duration_seconds=float(duration), reason=reason))

    return rules
