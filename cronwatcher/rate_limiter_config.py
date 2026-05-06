"""Parse rate-limiter settings from the config dict."""

from __future__ import annotations

from typing import Any, Dict

from cronwatcher.rate_limiter import RateLimiter

_DEFAULT_MAX_TOKENS = 5
_DEFAULT_REFILL_RATE = 1.0


def parse_rate_limiter(raw: Dict[str, Any]) -> RateLimiter:
    """Build a :class:`RateLimiter` from the ``rate_limiter`` section of config.

    Accepts an optional ``rate_limiter`` key with ``max_tokens`` and
    ``refill_rate`` sub-keys.  Missing keys fall back to defaults.

    Raises:
        ValueError: If provided values are out of range.
    """
    section = raw.get("rate_limiter", {})

    max_tokens = section.get("max_tokens", _DEFAULT_MAX_TOKENS)
    refill_rate = section.get("refill_rate", _DEFAULT_REFILL_RATE)

    if not isinstance(max_tokens, int) or max_tokens < 1:
        raise ValueError(
            f"rate_limiter.max_tokens must be a positive integer, got {max_tokens!r}"
        )
    if not isinstance(refill_rate, (int, float)) or refill_rate <= 0:
        raise ValueError(
            f"rate_limiter.refill_rate must be a positive number, got {refill_rate!r}"
        )

    return RateLimiter(max_tokens=max_tokens, refill_rate=float(refill_rate))
