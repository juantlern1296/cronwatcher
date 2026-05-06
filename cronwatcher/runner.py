"""Wires together config, log watching, alerting, dedup, and webhook dispatch."""

from __future__ import annotations

import logging
from typing import Optional

from cronwatcher.alerting import AlertManager
from cronwatcher.config import Config
from cronwatcher.dedup import DedupStore
from cronwatcher.log_parser import CronLogEntry
from cronwatcher.watcher import LogWatcher
from cronwatcher.webhook import build_payload, send_webhook

logger = logging.getLogger(__name__)


def make_failure_handler(
    config: Config,
    alert_manager: Optional[AlertManager] = None,
    dedup_store: Optional[DedupStore] = None,
):
    """Return a closure that handles a CronLogEntry failure event."""
    if alert_manager is None:
        alert_manager = AlertManager(cooldown_seconds=config.alert_cooldown_seconds)
    if dedup_store is None:
        dedup_store = DedupStore(window_seconds=config.dedup_window_seconds)

    def on_failure(entry: CronLogEntry) -> None:
        job_name = entry.job_name or "unknown"

        if dedup_store.is_duplicate(entry):
            logger.debug("Suppressing duplicate alert for job '%s'", job_name)
            return

        if not alert_manager.should_alert(job_name):
            logger.debug("Alert cooldown active for job '%s'", job_name)
            return

        dedup_store.record(entry)

        payload = build_payload(entry, config.webhook)
        success = send_webhook(config.webhook, payload)

        if success:
            alert_manager.record_alert(job_name)
            logger.info("Alert sent for job '%s'", job_name)
        else:
            logger.warning("Webhook delivery failed for job '%s'", job_name)

    return on_failure


def run(config: Config) -> None:
    """Start the log watcher and block until interrupted."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting cronwatcher, watching %s", config.log_path)

    on_failure = make_failure_handler(config)
    watcher = LogWatcher(log_path=config.log_path, on_failure=on_failure)
    watcher.watch()
