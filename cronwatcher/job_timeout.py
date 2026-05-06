"""Detects cron jobs that haven't been seen within an expected interval."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional


@dataclass
class JobTimeoutConfig:
    job_name: str
    expected_interval_seconds: int
    grace_period_seconds: int = 60


@dataclass
class JobSeen:
    job_name: str
    last_seen: datetime = field(default_factory=datetime.utcnow)


class JobTimeoutMonitor:
    """Tracks the last time each job was seen and reports overdue jobs."""

    def __init__(self, configs: list[JobTimeoutConfig]) -> None:
        if not configs:
            raise ValueError("At least one JobTimeoutConfig is required")
        self._configs: Dict[str, JobTimeoutConfig] = {
            c.job_name: c for c in configs
        }
        self._seen: Dict[str, JobSeen] = {}

    def record_seen(self, job_name: str, at: Optional[datetime] = None) -> None:
        """Mark a job as seen at the given time (defaults to now)."""
        ts = at if at is not None else datetime.utcnow()
        self._seen[job_name] = JobSeen(job_name=job_name, last_seen=ts)

    def overdue_jobs(self, now: Optional[datetime] = None) -> list[str]:
        """Return names of jobs that are past their expected interval + grace period."""
        check_time = now if now is not None else datetime.utcnow()
        overdue = []
        for job_name, cfg in self._configs.items():
            seen = self._seen.get(job_name)
            if seen is None:
                # Never seen — treat start of monitoring as epoch; skip for now
                continue
            deadline = seen.last_seen + timedelta(
                seconds=cfg.expected_interval_seconds + cfg.grace_period_seconds
            )
            if check_time >= deadline:
                overdue.append(job_name)
        return overdue

    def last_seen(self, job_name: str) -> Optional[datetime]:
        entry = self._seen.get(job_name)
        return entry.last_seen if entry else None
