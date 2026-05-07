"""Parse circuit-breaker settings from the config dict."""

from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.circuit_breaker import CircuitBreaker

_DEFAULT_THRESHOLD = 5
_DEFAULT_RESET_TIMEOUT = 300.0


def parse_circuit_breaker(config: Dict[str, Any]) -> Optional[CircuitBreaker]:
    """Return a CircuitBreaker from the ``circuit_breaker`` config section.

    Returns *None* if the section is absent (feature disabled).

    Example JSON::

        "circuit_breaker": {
            "threshold": 5,
            "reset_timeout": 300
        }
    """
    section = config.get("circuit_breaker")
    if section is None:
        return None

    if not isinstance(section, dict):
        raise ValueError("circuit_breaker config must be a JSON object")

    threshold = section.get("threshold", _DEFAULT_THRESHOLD)
    reset_timeout = section.get("reset_timeout", _DEFAULT_RESET_TIMEOUT)

    if not isinstance(threshold, int) or threshold < 1:
        raise ValueError("circuit_breaker.threshold must be an integer >= 1")
    if not isinstance(reset_timeout, (int, float)) or reset_timeout <= 0:
        raise ValueError("circuit_breaker.reset_timeout must be a positive number")

    return CircuitBreaker(threshold=threshold, reset_timeout=float(reset_timeout))
