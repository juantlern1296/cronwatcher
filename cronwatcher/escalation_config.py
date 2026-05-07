"""Parse escalation policy from config dict."""
from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.escalation import EscalationPolicy

_DEFAULT_THRESHOLD = 3


def parse_escalation_policy(config: Dict[str, Any]) -> Optional[EscalationPolicy]:
    """Return an EscalationPolicy if the config contains an 'escalation' section.

    Expected shape::

        "escalation": {
            "threshold": 3,
            "webhook_url": "https://hooks.example.com/escalate",
            "headers": {"X-Token": "secret"}   # optional
        }

    Returns None when the section is absent.
    """
    section = config.get("escalation")
    if section is None:
        return None

    if not isinstance(section, dict):
        raise ValueError("'escalation' config must be a JSON object")

    url = section.get("webhook_url", "").strip()
    if not url:
        raise ValueError("escalation.webhook_url is required")

    threshold = section.get("threshold", _DEFAULT_THRESHOLD)
    if not isinstance(threshold, int) or threshold < 1:
        raise ValueError("escalation.threshold must be a positive integer")

    headers = section.get("headers", {})
    if not isinstance(headers, dict):
        raise ValueError("escalation.headers must be a JSON object")
    headers = {str(k): str(v) for k, v in headers.items()}

    return EscalationPolicy(
        threshold=threshold,
        webhook_url=url,
        headers=headers,
    )
