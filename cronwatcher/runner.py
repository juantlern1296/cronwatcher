"""Main run loop wiring together watcher, alerting, and webhook."""

import logging
from typing import Optional

from cronwatcher.alerting import AlertManager
from cronwatcher.config import Config, load_config
from cronwatcher.log_parser import CronLogEntry
from cronwatcher.watcher import LogWatcher
from cronwatcher.webhook import build_payload, send_webhook

logger = logging.getLogger(__name__)


def make_failure_handler(config: Config, alert_manager: AlertManager):
    """Return a closure that handles failure events with deduplication."""

    def on_failure(entry: CronLogEntry) -> None:
        job = entry.job_name or "unknown"

        if not alert_manager.should_alert(job):
            logger.debug("Suppressing duplicate alert for job '%s'", job)
            return

        job_cfg = config.jobs.get(job)
        webhook_cfg = config.webhook
        if job_cfg and job_cfg.webhook_url:
            from cronwatcher.config import WebhookConfig
            webhook_cfg = WebhookConfig(
                url=job_cfg.webhook_url,
                timeout=config.webhook.timeout,
                secret=config.webhook.secret,
            )

        payload = build_payload(entry, webhook_cfg)
        success = send_webhook(webhook_cfg, payload)
        if success:
            alert_manager.record_alert(job)
            logger.info("Alert sent for job '%s'", job)
        else:
            logger.warning("Failed to send alert for job '%s'", job)

    return on_failure


def run(config_path: str = "config.json") -> None:
    """Load config and start the log watcher loop."""
    config = load_config(config_path)

    logging.basicConfig(
        level=logging.DEBUG if config.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cooldown = config.alert_cooldown_seconds
    alert_manager = AlertManager(cooldown_seconds=cooldown)
    handler = make_failure_handler(config, alert_manager)

    watcher = LogWatcher(log_path=config.log_path, on_failure=handler)
    logger.info("cronwatcher started, watching %s", config.log_path)
    watcher.watch()
