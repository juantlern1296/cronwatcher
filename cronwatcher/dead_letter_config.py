"""Parse dead letter queue configuration from config dict."""
from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.dead_letter import DeadLetterQueue

_DEFAULT_MAX_SIZE = 500
_MAX_ALLOWED_SIZE = 100_000


def parse_dead_letter_config(config: Dict[str, Any]) -> Optional[DeadLetterQueue]:
    """Return a DeadLetterQueue if 'dead_letter' section is present, else None.

    Expected config shape::

        {
          "dead_letter": {
            "enabled": true,
            "max_size": 200
          }
        }
    """
    section = config.get("dead_letter")
    if section is None:
        return None

    if not isinstance(section, dict):
        raise ValueError("'dead_letter' config must be a JSON object")

    enabled = section.get("enabled", True)
    if not enabled:
        return None

    raw_max = section.get("max_size", _DEFAULT_MAX_SIZE)
    try:
        max_size = int(raw_max)
    except (TypeError, ValueError):
        raise ValueError(f"dead_letter.max_size must be an integer, got {raw_max!r}")

    if max_size < 1:
        raise ValueError("dead_letter.max_size must be at least 1")

    if max_size > _MAX_ALLOWED_SIZE:
        raise ValueError(
            f"dead_letter.max_size must not exceed {_MAX_ALLOWED_SIZE}, got {max_size}"
        )

    return DeadLetterQueue(max_size=max_size)
