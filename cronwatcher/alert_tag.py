"""Tag-based filtering for alerts — allows attaching and matching string tags."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from cronwatcher.webhook import WebhookPayload


@dataclass
class TagConfig:
    """Configuration for alert tagging."""
    global_tags: Set[str] = field(default_factory=set)
    # job_name -> extra tags
    per_job_tags: Dict[str, Set[str]] = field(default_factory=dict)

    def tags_for(self, job_name: str) -> Set[str]:
        """Return merged global + per-job tags for a given job."""
        return self.global_tags | self.per_job_tags.get(job_name, set())


class AlertTagger:
    """Enriches a WebhookPayload with tags derived from config."""

    def __init__(self, config: TagConfig) -> None:
        self._config = config

    def tag(self, payload: WebhookPayload) -> WebhookPayload:
        """Return a copy of *payload* with a 'tags' field added/merged."""
        job_name = payload.job_name or ""
        new_tags: Set[str] = self._config.tags_for(job_name)

        existing: List[str] = list(payload.extra_fields.get("tags", []))
        merged = sorted(new_tags | set(existing))

        new_extra = {**payload.extra_fields, "tags": merged}
        return WebhookPayload(
            job_name=payload.job_name,
            exit_code=payload.exit_code,
            timestamp=payload.timestamp,
            hostname=payload.hostname,
            log_line=payload.log_line,
            extra_fields=new_extra,
        )


def parse_tag_config(raw: dict) -> Optional[TagConfig]:
    """Parse 'alert_tags' section from config dict. Returns None if absent."""
    section = raw.get("alert_tags")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("alert_tags must be a JSON object")

    global_tags: Set[str] = set()
    for t in section.get("global", []):
        if not isinstance(t, str):
            raise ValueError(f"Tag must be a string, got {type(t).__name__}")
        global_tags.add(t)

    per_job: Dict[str, Set[str]] = {}
    for job, tags in section.get("per_job", {}).items():
        if not isinstance(tags, list):
            raise ValueError(f"Tags for job '{job}' must be a list")
        per_job[job] = set(tags)

    return TagConfig(global_tags=global_tags, per_job_tags=per_job)
