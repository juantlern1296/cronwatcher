"""Simple in-memory metrics collector for cronwatcher."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class JobMetrics:
    job_name: str
    total_failures: int = 0
    total_alerts_sent: int = 0
    last_failure_at: Optional[datetime] = None
    last_alert_at: Optional[datetime] = None


@dataclass
class MetricsStore:
    _jobs: Dict[str, JobMetrics] = field(default_factory=dict)
    _started_at: datetime = field(default_factory=datetime.utcnow)

    def record_failure(self, job_name: str) -> None:
        """Record a cron job failure."""
        if job_name not in self._jobs:
            self._jobs[job_name] = JobMetrics(job_name=job_name)
        m = self._jobs[job_name]
        m.total_failures += 1
        m.last_failure_at = datetime.utcnow()

    def record_alert(self, job_name: str) -> None:
        """Record that an alert was sent for a job."""
        if job_name not in self._jobs:
            self._jobs[job_name] = JobMetrics(job_name=job_name)
        m = self._jobs[job_name]
        m.total_alerts_sent += 1
        m.last_alert_at = datetime.utcnow()

    def get(self, job_name: str) -> Optional[JobMetrics]:
        return self._jobs.get(job_name)

    def all_jobs(self) -> List[JobMetrics]:
        return list(self._jobs.values())

    def summary(self) -> Dict:
        return {
            "started_at": self._started_at.isoformat(),
            "jobs": [
                {
                    "job_name": m.job_name,
                    "total_failures": m.total_failures,
                    "total_alerts_sent": m.total_alerts_sent,
                    "last_failure_at": m.last_failure_at.isoformat() if m.last_failure_at else None,
                    "last_alert_at": m.last_alert_at.isoformat() if m.last_alert_at else None,
                }
                for m in self.all_jobs()
            ],
        }
