"""Token-bucket rate limiter to cap webhook calls per job per time window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BucketState:
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)


class RateLimiter:
    """Per-job token bucket rate limiter.

    Args:
        max_tokens: Maximum burst size (also the initial token count).
        refill_rate: Tokens added per second.
    """

    def __init__(self, max_tokens: int = 5, refill_rate: float = 1.0) -> None:
        if max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be > 0")
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self._buckets: Dict[str, BucketState] = {}

    def _refill(self, bucket: BucketState) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(
            float(self.max_tokens),
            bucket.tokens + elapsed * self.refill_rate,
        )
        bucket.last_refill = now

    def allow(self, job_name: str) -> bool:
        """Return True and consume a token if the request is allowed."""
        if job_name not in self._buckets:
            self._buckets[job_name] = BucketState(tokens=float(self.max_tokens))
        bucket = self._buckets[job_name]
        self._refill(bucket)
        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True
        return False

    def available_tokens(self, job_name: str) -> float:
        """Return current token count for *job_name* (after refill)."""
        if job_name not in self._buckets:
            return float(self.max_tokens)
        bucket = self._buckets[job_name]
        self._refill(bucket)
        return bucket.tokens

    def reset(self, job_name: str) -> None:
        """Remove the bucket for *job_name*, restoring it to full tokens."""
        self._buckets.pop(job_name, None)
