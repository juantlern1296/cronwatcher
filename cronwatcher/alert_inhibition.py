"""Alert inhibition: suppress alerts for a job when a higher-priority job is firing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class InhibitionRule:
    """If *source_job* is actively failing, inhibit alerts for *target_jobs*."""
    source_job: str
    target_jobs: List[str]


@dataclass
class AlertInhibition:
    rules: List[InhibitionRule] = field(default_factory=list)
    _active_sources: Set[str] = field(default_factory=set, init=False, repr=False)

    # -- source tracking --------------------------------------------------

    def mark_firing(self, job_name: str) -> None:
        """Record that *job_name* is currently failing."""
        self._active_sources.add(job_name)

    def mark_resolved(self, job_name: str) -> None:
        """Clear the firing state for *job_name*."""
        self._active_sources.discard(job_name)

    # -- inhibition check -------------------------------------------------

    def is_inhibited(self, job_name: str) -> bool:
        """Return True if *job_name* should be suppressed due to an active inhibition rule."""
        for rule in self.rules:
            if rule.source_job in self._active_sources and job_name in rule.target_jobs:
                return True
        return False

    def active_sources(self) -> Set[str]:
        return set(self._active_sources)

    def inhibited_by(self, job_name: str) -> Optional[str]:
        """Return the source job that inhibits *job_name*, or None."""
        for rule in self.rules:
            if rule.source_job in self._active_sources and job_name in rule.target_jobs:
                return rule.source_job
        return None
