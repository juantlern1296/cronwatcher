"""Parse escalation chain configuration from a config dict."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cronwatcher.alert_escalation_chain import ChainStep, EscalationChainConfig

_SECTION = "escalation_chain"


def parse_escalation_chain(config: Dict[str, Any]) -> Optional[EscalationChainConfig]:
    """Return an EscalationChainConfig if the section exists, else None."""
    section = config.get(_SECTION)
    if section is None:
        return None

    if not isinstance(section, list):
        raise ValueError(f"'{_SECTION}' must be a list")

    steps: List[ChainStep] = []
    for idx, item in enumerate(section):
        if not isinstance(item, dict):
            raise ValueError(f"'{_SECTION}[{idx}]' must be a dict")

        min_failures = item.get("min_failures")
        if min_failures is None:
            raise ValueError(f"'{_SECTION}[{idx}]' missing 'min_failures'")
        if not isinstance(min_failures, int) or min_failures < 1:
            raise ValueError(
                f"'{_SECTION}[{idx}].min_failures' must be a positive integer"
            )

        channel_name = item.get("channel")
        if not channel_name or not isinstance(channel_name, str):
            raise ValueError(
                f"'{_SECTION}[{idx}]' missing or invalid 'channel'"
            )

        label = item.get("label", "")
        steps.append(ChainStep(
            min_failures=min_failures,
            channel_name=channel_name,
            label=str(label),
        ))

    return EscalationChainConfig(steps=steps)
