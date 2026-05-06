"""Helpers to extract JobLabels from the top-level Config and per-job sections."""

from __future__ import annotations

from typing import Any, Dict

from cronwatcher.job_labels import JobLabels, parse_job_labels


# Key used in both the top-level config and per-job config dicts.
_LABELS_KEY = "labels"


def global_labels_from_config(raw_config: Dict[str, Any]) -> JobLabels:
    """Extract optional top-level labels that apply to every job."""
    return parse_job_labels(raw_config.get(_LABELS_KEY))


def job_labels_from_config(raw_job: Dict[str, Any]) -> JobLabels:
    """Extract optional per-job labels from a single job config dict."""
    return parse_job_labels(raw_job.get(_LABELS_KEY))


def effective_labels(
    raw_config: Dict[str, Any],
    raw_job: Dict[str, Any],
) -> JobLabels:
    """Return merged labels: global labels overridden by per-job labels.

    Per-job labels take precedence over global ones, allowing teams to set
    shared defaults at the top level while individual jobs can override them.
    """
    g = global_labels_from_config(raw_config)
    j = job_labels_from_config(raw_job)
    return g.merge(j)
