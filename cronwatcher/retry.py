"""Retry logic for webhook delivery with exponential backoff."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 30.0


@dataclass
class RetryResult:
    success: bool
    attempts: int
    last_exception: Optional[Exception] = field(default=None)


def with_retry(
    fn: Callable[[], bool],
    config: Optional[RetryConfig] = None,
    job_name: str = "unknown",
) -> RetryResult:
    """Call fn up to max_attempts times with exponential backoff.

    fn should return True on success, False on failure.
    Exceptions from fn are caught and treated as failure.
    """
    cfg = config or RetryConfig()
    delay = cfg.base_delay
    last_exc: Optional[Exception] = None

    for attempt in range(1, cfg.max_attempts + 1):
        try:
            ok = fn()
            if ok:
                if attempt > 1:
                    logger.info(
                        "Webhook delivered for '%s' on attempt %d", job_name, attempt
                    )
                return RetryResult(success=True, attempts=attempt)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "Attempt %d/%d failed for '%s': %s",
                attempt,
                cfg.max_attempts,
                job_name,
                exc,
            )
        else:
            last_exc = None
            logger.warning(
                "Attempt %d/%d returned failure for '%s'",
                attempt,
                cfg.max_attempts,
                job_name,
            )

        if attempt < cfg.max_attempts:
            sleep_time = min(delay, cfg.max_delay)
            logger.debug("Retrying in %.1fs", sleep_time)
            time.sleep(sleep_time)
            delay *= cfg.backoff_factor

    logger.error(
        "All %d attempts exhausted for '%s'", cfg.max_attempts, job_name
    )
    return RetryResult(success=False, attempts=cfg.max_attempts, last_exception=last_exc)
