"""Main runner — wires together watcher, alerting, dedup, metrics, and webhook."""

import logging
from typing import Optional

from cronwatcher.alerting import AlertManager
from cronwatcher.config import Config
from cronwatcher.dedup import DedupStore
from cronwatcher.log_parser import CronLogEntry
from cronwatcher.metrics import MetricsStore
from cronwatcher.metrics_reporter import MetricsReporter
from cronwatcher.watcher import LogWatcher
from cronwatcher.webhook import build_payload, send_webhook

logger = logging.getLogger(__name__)


def make_failure_handler(
    config: Config,
    alert_manager: AlertManager,
    dedup_store: DedupStore,
    metrics: MetricsStore,
):
    """Return a closure that processes a cron failure entry.

    The handler deduplicates events, records metrics, enforces alert cooldowns,
    and dispatches webhook notifications.
    """
    def on_failure(entry: CronLogEntry) -> None:
        job_name = entry.job_name or "unknown"

        if dedup_store.is_duplicate(entry):
            logger.debug("Duplicate failure ignored for job '%s'", job_name)
            return

        dedup_store.record(entry)
        metrics.record_failure(job_name)

        if not alert_manager.should_alert(job_name):
            logger.debug("Alert suppressed (cooldown) for job '%s'", job_name)
            return

        payload = build_payload(entry, config.webhook)
        success = send_webhook(config.webhook, payload)

        if success:
            alert_manager.record_alert(job_name)
            metrics.record_alert(job_name)
            logger.info("Alert sent for job '%s'", job_name)
        else:
            logger.warning("Failed to send alert for job '%s'", job_name)

    return on_failure


def run(config: Config, metrics: Optional[MetricsStore] = None) -> None:
    """Start the cronwatcher daemon.

    Sets up logging, initialises all subsystems, and blocks on the log watcher.
    The metrics reporter is guaranteed to be stopped on exit.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if metrics is None:
        metrics = MetricsStore()

    alert_manager = AlertManager(cooldown_seconds=config.alert_cooldown_seconds)
    dedup_store = DedupStore()
    reporter = MetricsReporter(metrics, interval_seconds=config.metrics_interval_seconds)

    handler = make_failure_handler(config, alert_manager, dedup_store, metrics)
    watcher = LogWatcher(config.log_path, on_failure=handler)

    reporter.start()
    try:
        logger.info("cronwatcher started, watching %s", config.log_path)
        watcher.run()
    finally:
        reporter.stop()
        logger.info("cronwatcher stopped")
