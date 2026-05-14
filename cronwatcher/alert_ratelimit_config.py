"""Config parsing and handler wrapping for alert rate limiting."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from cronwatcher.alert_ratelimit import AlertRateLimiter, RateLimitConfig
from cronwatcher.webhook import WebhookPayload


def parse_ratelimit_config(raw: Dict[str, Any]) -> Optional[RateLimitConfig]:
    """Parse 'alert_ratelimit' section from config dict. Returns None if absent or disabled."""
    section = raw.get("alert_ratelimit")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_ratelimit must be a dict")
    if not section.get("enabled", True):
        return None

    max_alerts = int(section.get("max_alerts", 5))
    window_seconds = float(section.get("window_seconds", 60.0))

    per_job_raw = section.get("per_job", {})
    if not isinstance(per_job_raw, dict):
        raise ValueError("alert_ratelimit.per_job must be a dict")
    per_job = {k: int(v) for k, v in per_job_raw.items()}

    return RateLimitConfig(
        max_alerts=max_alerts,
        window_seconds=window_seconds,
        per_job=per_job,
    )


def wrap_with_ratelimiter(
    limiter: AlertRateLimiter,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    def _handler(payload: WebhookPayload) -> None:
        job = payload.job_name or "__unknown__"
        if limiter.check_and_record(job):
            handler(payload)

    return _handler


def ratelimited_handler(
    raw_config: Dict[str, Any],
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    """Return handler wrapped with rate limiter if configured, else original handler."""
    cfg = parse_ratelimit_config(raw_config)
    if cfg is None:
        return handler
    limiter = AlertRateLimiter(cfg)
    return wrap_with_ratelimiter(limiter, handler)
