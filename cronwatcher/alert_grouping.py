"""Groups alerts by a configurable key before dispatching them together."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class GroupingConfig:
    group_by: str  # field name: "job", "host", "severity"
    window_seconds: float
    max_group_size: int = 20

    def __post_init__(self) -> None:
        allowed = {"job", "host", "severity"}
        if self.group_by not in allowed:
            raise ValueError(f"group_by must be one of {allowed}, got {self.group_by!r}")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.max_group_size < 1:
            raise ValueError("max_group_size must be at least 1")


@dataclass
class _Group:
    key: str
    payloads: List[WebhookPayload] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)

    def is_expired(self, window: float) -> bool:
        return (time.monotonic() - self.created_at) >= window


class AlertGrouper:
    def __init__(
        self,
        config: GroupingConfig,
        callback: Callable[[str, List[WebhookPayload]], None],
    ) -> None:
        self._config = config
        self._callback = callback
        self._groups: Dict[str, _Group] = {}

    def _extract_key(self, payload: WebhookPayload) -> str:
        field = self._config.group_by
        if field == "job":
            return payload.job_name or "unknown"
        if field == "host":
            return payload.hostname or "unknown"
        if field == "severity":
            return (payload.extra or {}).get("severity", "info")
        return "default"

    def add(self, payload: WebhookPayload) -> None:
        self.flush_expired()
        key = self._extract_key(payload)
        if key not in self._groups:
            self._groups[key] = _Group(key=key)
        group = self._groups[key]
        group.payloads.append(payload)
        if len(group.payloads) >= self._config.max_group_size:
            self._flush_group(key)

    def flush_expired(self) -> None:
        expired = [
            k for k, g in self._groups.items()
            if g.is_expired(self._config.window_seconds)
        ]
        for k in expired:
            self._flush_group(k)

    def flush_all(self) -> None:
        for key in list(self._groups):
            self._flush_group(key)

    def _flush_group(self, key: str) -> None:
        group = self._groups.pop(key, None)
        if group and group.payloads:
            self._callback(key, group.payloads)

    def group_count(self) -> int:
        return len(self._groups)
