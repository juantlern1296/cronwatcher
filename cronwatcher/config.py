import os
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WebhookConfig:
    url: str
    secret: Optional[str] = None
    timeout: int = 10


@dataclass
class CronJobConfig:
    name: str
    schedule: str
    command: str
    max_retries: int = 0
    alert_on_failure: bool = True


@dataclass
class Config:
    webhook: WebhookConfig
    jobs: List[CronJobConfig] = field(default_factory=list)
    log_level: str = "INFO"
    log_file: Optional[str] = None
    check_interval: int = 60


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        data = json.load(f)

    webhook_data = data.get("webhook", {})
    if not webhook_data.get("url"):
        raise ValueError("webhook.url is required in config")

    webhook = WebhookConfig(
        url=webhook_data["url"],
        secret=webhook_data.get("secret"),
        timeout=webhook_data.get("timeout", 10),
    )

    jobs = [
        CronJobConfig(
            name=j["name"],
            schedule=j["schedule"],
            command=j["command"],
            max_retries=j.get("max_retries", 0),
            alert_on_failure=j.get("alert_on_failure", True),
        )
        for j in data.get("jobs", [])
    ]

    return Config(
        webhook=webhook,
        jobs=jobs,
        log_level=data.get("log_level", "INFO"),
        log_file=data.get("log_file"),
        check_interval=data.get("check_interval", 60),
    )
