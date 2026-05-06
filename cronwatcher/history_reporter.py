"""Formats and logs job failure history summaries."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from cronwatcher.job_history import FailureRecord, JobHistoryStore

logger = logging.getLogger(__name__)


def _record_to_dict(record: FailureRecord) -> Dict[str, Any]:
    return {
        "job_name": record.job_name,
        "timestamp": record.timestamp.isoformat(),
        "exit_code": record.exit_code,
        "raw_line": record.raw_line,
    }


def build_history_report(
    store: JobHistoryStore, recent_n: int = 5
) -> Dict[str, Any]:
    """Build a serialisable report of recent failures per job."""
    report: Dict[str, Any] = {}
    for job_name in store.all_jobs():
        history = store.get(job_name)
        if history is None:
            continue
        recent: List[Dict[str, Any]] = [
            _record_to_dict(r) for r in history.recent(recent_n)
        ]
        report[job_name] = {
            "total_recorded": history.total(),
            "recent_failures": recent,
        }
    return report


def log_history_report(store: JobHistoryStore, recent_n: int = 5) -> None:
    """Emit the history report as a single JSON log line at INFO level."""
    report = build_history_report(store, recent_n=recent_n)
    if not report:
        logger.info("job_history report={}")
        return
    logger.info("job_history %s", json.dumps(report))


def history_as_json(store: JobHistoryStore, recent_n: int = 5) -> str:
    """Return the history report serialised as a JSON string."""
    return json.dumps(build_history_report(store, recent_n=recent_n))
