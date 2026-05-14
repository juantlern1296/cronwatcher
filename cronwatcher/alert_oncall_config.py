"""Parse on-call schedule configuration from the config dict."""

from __future__ import annotations

from datetime import time
from typing import Any, Dict, Optional

from cronwatcher.alert_oncall import AlertOnCall, OnCallSchedule, OnCallSlot
from cronwatcher.webhook import WebhookPayload, send_webhook
from cronwatcher.config import WebhookConfig


def _parse_time(value: str, key: str) -> time:
    try:
        h, m = value.split(":")
        return time(int(h), int(m))
    except Exception:
        raise ValueError(f"on_call: '{key}' must be HH:MM, got {value!r}")


def _parse_slot(raw: Any, index: int) -> OnCallSlot:
    if not isinstance(raw, dict):
        raise TypeError(f"on_call.slots[{index}] must be a dict")
    name = raw.get("name", f"slot-{index}")
    url = raw.get("webhook_url")
    if not url:
        raise ValueError(f"on_call.slots[{index}] missing 'webhook_url'")
    weekdays = raw.get("weekdays", list(range(7)))
    if not isinstance(weekdays, list):
        raise TypeError(f"on_call.slots[{index}].weekdays must be a list")
    start = _parse_time(raw.get("start_time", "00:00"), "start_time")
    end = _parse_time(raw.get("end_time", "23:59"), "end_time")
    return OnCallSlot(name=name, webhook_url=url, weekdays=weekdays, start_time=start, end_time=end)


def parse_oncall_schedule(config: Dict[str, Any]) -> Optional[OnCallSchedule]:
    section = config.get("on_call")
    if not section:
        return None
    if not isinstance(section, dict):
        raise TypeError("on_call must be a dict")
    raw_slots = section.get("slots", [])
    if not isinstance(raw_slots, list):
        raise TypeError("on_call.slots must be a list")
    slots = [_parse_slot(s, i) for i, s in enumerate(raw_slots)]
    fallback = section.get("fallback_url")
    return OnCallSchedule(slots=slots, fallback_url=fallback)


def build_oncall_alerter(config: Dict[str, Any]) -> Optional[AlertOnCall]:
    schedule = parse_oncall_schedule(config)
    if schedule is None:
        return None

    def _send(url: str, payload: WebhookPayload) -> bool:
        cfg = WebhookConfig(url=url, headers={}, timeout=10)
        ok, _ = send_webhook(cfg, payload)
        return ok

    return AlertOnCall(schedule=schedule, send_fn=_send)
