"""Optional key-value labels attached to cron job configs for enriching alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class JobLabels:
    labels: Dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: str = "") -> str:
        return self.labels.get(key, default)

    def as_dict(self) -> Dict[str, str]:
        return dict(self.labels)

    def merge(self, other: "JobLabels") -> "JobLabels":
        """Return a new JobLabels with other overriding self."""
        merged = {**self.labels, **other.labels}
        return JobLabels(labels=merged)


def parse_job_labels(raw: Any) -> JobLabels:
    """Parse a labels dict from a job config section.

    Accepts a plain dict of string keys/values.  Any non-string values are
    coerced to str.  Missing or None section returns empty labels.
    """
    if raw is None:
        return JobLabels()

    if not isinstance(raw, dict):
        raise ValueError(f"labels must be a dict, got {type(raw).__name__}")

    coerced: Dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            raise ValueError(f"label key must be a string, got {type(k).__name__}")
        coerced[k] = str(v)

    return JobLabels(labels=coerced)


def enrich_payload(payload: Dict[str, Any], labels: JobLabels) -> Dict[str, Any]:
    """Return a copy of payload with a 'labels' key added (may be empty dict)."""
    enriched = dict(payload)
    enriched["labels"] = labels.as_dict()
    return enriched
