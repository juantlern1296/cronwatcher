import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from cronwatcher.config import WebhookConfig
from cronwatcher.log_parser import CronLogEntry

logger = logging.getLogger(__name__)


@dataclass
class WebhookPayload:
    job_name: str
    exit_code: int
    timestamp: str
    raw_line: str
    hostname: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "exit_code": self.exit_code,
            "timestamp": self.timestamp,
            "raw_line": self.raw_line,
            "hostname": self.hostname,
        }


def build_payload(entry: CronLogEntry, hostname: Optional[str] = None) -> WebhookPayload:
    return WebhookPayload(
        job_name=entry.job_name or "unknown",
        exit_code=entry.exit_code or -1,
        timestamp=entry.timestamp,
        raw_line=entry.raw_line,
        hostname=hostname,
    )


def send_webhook(config: WebhookConfig, payload: WebhookPayload) -> bool:
    """Send a webhook notification. Returns True on success, False on failure."""
    data = json.dumps(payload.to_dict()).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if config.secret:
        headers["X-Webhook-Secret"] = config.secret

    req = urllib.request.Request(
        url=config.url,
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=config.timeout_seconds) as resp:
            status = resp.status
            if 200 <= status < 300:
                logger.info("Webhook sent successfully (status=%d) for job '%s'", status, payload.job_name)
                return True
            logger.warning("Webhook returned non-2xx status %d for job '%s'", status, payload.job_name)
            return False
    except urllib.error.HTTPError as exc:
        logger.error("Webhook HTTP error %d for job '%s': %s", exc.code, payload.job_name, exc.reason)
    except urllib.error.URLError as exc:
        logger.error("Webhook URL error for job '%s': %s", payload.job_name, exc.reason)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Unexpected error sending webhook for job '%s': %s", payload.job_name, exc)
    return False
