"""Alert TTL: automatically expire/suppress alerts that have been firing too long."""
from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Callable, Dict, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class TTLConfig:
    default_ttl: float  # seconds
    per_job: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.default_ttl <= 0:
            raise ValueError("default_ttl must be positive")
        for job, ttl in self.per_job.items():
            if ttl <= 0:
                raise ValueError(f"TTL for job '{job}' must be positive")

    def ttl_for(self, job_name: str) -> float:
        return self.per_job.get(job_name, self.default_ttl)


@dataclass
class _TTLRecord:
    first_seen: float
    last_seen: float


class AlertTTL:
    """Suppress alerts for a job once it has been continuously firing beyond its TTL."""

    def __init__(self, config: TTLConfig, on_expire: Optional[Callable[[str], None]] = None) -> None:
        self._config = config
        self._on_expire = on_expire
        self._records: Dict[str, _TTLRecord] = {}

    def is_expired(self, job_name: str, now: Optional[float] = None) -> bool:
        now = now if now is not None else time()
        record = self._records.get(job_name)
        if record is None:
            return False
        ttl = self._config.ttl_for(job_name)
        return (now - record.first_seen) >= ttl

    def record(self, job_name: str, now: Optional[float] = None) -> None:
        now = now if now is not None else time()
        if job_name not in self._records:
            self._records[job_name] = _TTLRecord(first_seen=now, last_seen=now)
        else:
            self._records[job_name].last_seen = now

    def clear(self, job_name: str) -> None:
        self._records.pop(job_name, None)

    def check(self, payload: WebhookPayload, handler: Callable[[WebhookPayload], None],
              now: Optional[float] = None) -> None:
        job = payload.job_name or "unknown"
        now = now if now is not None else time()
        self.record(job, now=now)
        if self.is_expired(job, now=now):
            if self._on_expire is not None:
                self._on_expire(job)
            return
        handler(payload)


def parse_ttl_config(raw: dict) -> Optional[TTLConfig]:
    section = raw.get("alert_ttl")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_ttl must be a dict")
    default_ttl = float(section.get("default_ttl", 3600))
    per_job_raw = section.get("per_job", {})
    if not isinstance(per_job_raw, dict):
        raise ValueError("alert_ttl.per_job must be a dict")
    per_job = {k: float(v) for k, v in per_job_raw.items()}
    return TTLConfig(default_ttl=default_ttl, per_job=per_job)
