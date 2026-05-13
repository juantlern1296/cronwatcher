"""Parse acknowledgement configuration from the config dict."""
from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatcher.alert_acknowledge import AlertAcknowledge


_DEFAULT_DURATION = 3600  # 1 hour


def parse_alert_acknowledge(config: Dict[str, Any]) -> Optional[AlertAcknowledge]:
    """Return an AlertAcknowledge instance if the section is present and enabled.

    Expected config shape::

        "alert_acknowledge": {
            "enabled": true,
            "default_duration_seconds": 3600
        }

    Returns ``None`` if the section is absent or ``enabled`` is ``false``.
    """
    section = config.get("alert_acknowledge")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_acknowledge must be a dict")
    if not section.get("enabled", True):
        return None

    duration = section.get("default_duration_seconds", _DEFAULT_DURATION)
    if not isinstance(duration, (int, float)) or duration < 0:
        raise ValueError(
            "alert_acknowledge.default_duration_seconds must be a non-negative number"
        )

    return AlertAcknowledge()


def wrap_with_acknowledge(
    ack: AlertAcknowledge,
    handler,
    default_duration: float = _DEFAULT_DURATION,
):
    """Return a handler that skips sending if the job is acknowledged."""

    def _handler(payload) -> None:  # type: ignore[override]
        job_name = payload.job_name if hasattr(payload, "job_name") else ""
        if ack.is_acknowledged(job_name):
            return
        handler(payload)

    return _handler
