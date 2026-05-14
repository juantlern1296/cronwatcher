"""Config parsing and handler wrapping for alert quota."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from cronwatcher.alert_quota import AlertQuota, QuotaConfig
from cronwatcher.webhook import WebhookPayload

logger = logging.getLogger(__name__)

_DEFAULT_MAX_PER_JOB = 10
_DEFAULT_MAX_GLOBAL = 50
_DEFAULT_WINDOW_SECONDS = 3600.0


def parse_quota_config(raw: Dict[str, Any]) -> Optional[AlertQuota]:
    """Parse 'alert_quota' section from config dict. Returns None if absent or disabled."""
    section = raw.get("alert_quota")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_quota must be a JSON object")
    if not section.get("enabled", True):
        return None

    cfg = QuotaConfig(
        max_per_job=int(section.get("max_per_job", _DEFAULT_MAX_PER_JOB)),
        max_global=int(section.get("max_global", _DEFAULT_MAX_GLOBAL)),
        window_seconds=float(section.get("window_seconds", _DEFAULT_WINDOW_SECONDS)),
    )
    return AlertQuota(cfg)


def wrap_with_quota(
    quota: AlertQuota,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    def _handler(payload: WebhookPayload) -> None:
        if quota.check_and_record(payload):
            handler(payload)
        else:
            logger.warning(
                "alert_quota: dropping alert for job %r — quota exceeded",
                payload.job_name,
            )

    return _handler


def quota_handler(
    raw: Dict[str, Any],
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    """Return handler wrapped with quota enforcement if configured, else original."""
    quota = parse_quota_config(raw)
    if quota is None:
        return handler
    return wrap_with_quota(quota, handler)
