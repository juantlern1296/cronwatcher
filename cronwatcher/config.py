"""Configuration loading and validation for cronwatcher."""

import json
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class WebhookConfig:
    url: str
    timeout: int = 10
    secret: Optional[str] = None


@dataclass
class CronJobConfig:
    name: str
    webhook_url: Optional[str] = None
    enabled: bool = True


@dataclass
class Config:
    log_path: str
    webhook: WebhookConfig
    jobs: Dict[str, CronJobConfig] = field(default_factory=dict)
    alert_cooldown_seconds: int = 300
    debug: bool = False


def _parse_webhook(data: dict) -> WebhookConfig:
    if "url" not in data:
        raise ValueError("webhook config missing required field 'url'")
    return WebhookConfig(
        url=data["url"],
        timeout=data.get("timeout", 10),
        secret=data.get("secret"),
    )


def _parse_jobs(data: list) -> Dict[str, CronJobConfig]:
    jobs: Dict[str, CronJobConfig] = {}
    for item in data:
        if "name" not in item:
            raise ValueError("job entry missing required field 'name'")
        name = item["name"]
        jobs[name] = CronJobConfig(
            name=name,
            webhook_url=item.get("webhook_url"),
            enabled=item.get("enabled", True),
        )
    return jobs


def load_config(path: str) -> Config:
    """Load and parse configuration from a JSON file."""
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path}")

    if "webhook" not in data:
        raise ValueError("Config missing required section 'webhook'")
    if "log_path" not in data:
        raise ValueError("Config missing required field 'log_path'")

    return Config(
        log_path=data["log_path"],
        webhook=_parse_webhook(data["webhook"]),
        jobs=_parse_jobs(data.get("jobs", [])),
        alert_cooldown_seconds=data.get("alert_cooldown_seconds", 300),
        debug=data.get("debug", False),
    )
