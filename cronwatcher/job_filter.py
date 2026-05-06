"""Filter cron log entries based on job name include/exclude patterns."""

import fnmatch
from dataclasses import dataclass, field
from typing import List

from cronwatcher.log_parser import CronLogEntry, job_name


@dataclass
class JobFilter:
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)

    def matches(self, entry: CronLogEntry) -> bool:
        """Return True if the entry should be processed."""
        name = job_name(entry) or ""

        if self.exclude_patterns:
            for pattern in self.exclude_patterns:
                if fnmatch.fnmatch(name, pattern):
                    return False

        if self.include_patterns:
            for pattern in self.include_patterns:
                if fnmatch.fnmatch(name, pattern):
                    return True
            return False

        return True


def parse_job_filter(config_data: dict) -> JobFilter:
    """Build a JobFilter from the top-level config dict."""
    section = config_data.get("job_filter", {})
    if not isinstance(section, dict):
        raise ValueError("'job_filter' must be a JSON object")

    include = section.get("include", [])
    exclude = section.get("exclude", [])

    if not isinstance(include, list):
        raise ValueError("'job_filter.include' must be a list")
    if not isinstance(exclude, list):
        raise ValueError("'job_filter.exclude' must be a list")

    return JobFilter(
        include_patterns=[str(p) for p in include],
        exclude_patterns=[str(p) for p in exclude],
    )
