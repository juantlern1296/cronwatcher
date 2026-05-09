"""Alert sampling — only forward a fraction of alerts for noisy jobs."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class SamplingConfig:
    """Configuration for alert sampling."""

    # Fraction of alerts to forward, e.g. 0.1 means 10 %.
    rate: float = 1.0
    # Per-job overrides: job_name -> rate
    per_job: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 < self.rate <= 1.0):
            raise ValueError(f"rate must be in (0, 1], got {self.rate}")
        for job, r in self.per_job.items():
            if not (0.0 < r <= 1.0):
                raise ValueError(
                    f"per_job rate for '{job}' must be in (0, 1], got {r}"
                )

    def rate_for(self, job_name: str) -> float:
        return self.per_job.get(job_name, self.rate)


class AlertSampler:
    """Probabilistically forwards alerts based on a sampling rate."""

    def __init__(
        self,
        config: SamplingConfig,
        handler: Callable[[WebhookPayload], None],
        *,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._config = config
        self._handler = handler
        self._rng = rng or random.Random()

    def add(self, payload: WebhookPayload) -> bool:
        """Forward *payload* to the inner handler if it passes sampling.

        Returns True if the alert was forwarded, False if it was dropped.
        """
        job = payload.job_name or ""
        rate = self._config.rate_for(job)
        if self._rng.random() < rate:
            self._handler(payload)
            return True
        return False


def parse_sampling_config(raw: dict) -> Optional[SamplingConfig]:
    """Build a SamplingConfig from the 'sampling' section of the config dict."""
    section = raw.get("sampling")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("'sampling' must be a JSON object")
    rate = float(section.get("rate", 1.0))
    per_job_raw = section.get("per_job", {})
    if not isinstance(per_job_raw, dict):
        raise ValueError("'sampling.per_job' must be a JSON object")
    per_job = {k: float(v) for k, v in per_job_raw.items()}
    return SamplingConfig(rate=rate, per_job=per_job)
