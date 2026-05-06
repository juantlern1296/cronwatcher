"""Load retry configuration from the main config dict."""

from __future__ import annotations

from typing import Any, Dict

from cronwatcher.retry import RetryConfig

_DEFAULTS = {
    "max_attempts": 3,
    "base_delay": 1.0,
    "backoff_factor": 2.0,
    "max_delay": 30.0,
}


def parse_retry_config(data: Dict[str, Any]) -> RetryConfig:
    """Parse a 'retry' block from the top-level config dict.

    Missing keys fall back to sensible defaults so the section is optional.
    """
    retry_data = data.get("retry", {})

    max_attempts = int(retry_data.get("max_attempts", _DEFAULTS["max_attempts"]))
    if max_attempts < 1:
        raise ValueError("retry.max_attempts must be >= 1")

    base_delay = float(retry_data.get("base_delay", _DEFAULTS["base_delay"]))
    if base_delay < 0:
        raise ValueError("retry.base_delay must be >= 0")

    backoff_factor = float(
        retry_data.get("backoff_factor", _DEFAULTS["backoff_factor"])
    )
    if backoff_factor < 1.0:
        raise ValueError("retry.backoff_factor must be >= 1.0")

    max_delay = float(retry_data.get("max_delay", _DEFAULTS["max_delay"]))
    if max_delay < base_delay:
        raise ValueError("retry.max_delay must be >= retry.base_delay")

    return RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        backoff_factor=backoff_factor,
        max_delay=max_delay,
    )
