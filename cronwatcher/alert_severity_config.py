"""Helpers to attach severity to webhook payloads."""
from __future__ import annotations

from typing import Optional

from cronwatcher.alert_severity import Severity, SeverityConfig, classify
from cronwatcher.metrics import MetricsStore
from cronwatcher.webhook import WebhookPayload


def enrich_payload_with_severity(
    payload: WebhookPayload,
    metrics: MetricsStore,
    cfg: Optional[SeverityConfig],
) -> WebhookPayload:
    """Return a new WebhookPayload with 'severity' injected into extra_fields.

    If cfg is None the severity defaults to INFO and is still attached so
    downstream consumers always have the field available.
    """
    job = payload.job_name or "unknown"

    if cfg is not None:
        job_metrics = metrics.get(job)
        count = job_metrics.failure_count if job_metrics else 0
        level = classify(count, cfg)
    else:
        level = Severity.INFO

    extra = dict(payload.extra_fields) if payload.extra_fields else {}
    extra["severity"] = level.value

    return WebhookPayload(
        job_name=payload.job_name,
        exit_code=payload.exit_code,
        timestamp=payload.timestamp,
        hostname=payload.hostname,
        log_line=payload.log_line,
        extra_fields=extra,
    )
