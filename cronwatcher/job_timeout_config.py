"""Parse job timeout configuration from the config dict."""

from typing import Any

from cronwatcher.job_timeout import JobTimeoutConfig

_DEFAULT_GRACE_PERIOD = 60


def parse_job_timeout_configs(raw: dict[str, Any]) -> list[JobTimeoutConfig]:
    """Parse the 'job_timeouts' section of the config dict.

    Expected format:
        {
            "job_timeouts": [
                {"job_name": "backup", "expected_interval_seconds": 86400},
                {"job_name": "cleanup", "expected_interval_seconds": 3600, "grace_period_seconds": 120}
            ]
        }
    """
    entries = raw.get("job_timeouts", [])
    if not isinstance(entries, list):
        raise ValueError("'job_timeouts' must be a list")

    configs: list[JobTimeoutConfig] = []
    for i, item in enumerate(entries):
        job_name = item.get("job_name")
        if not job_name or not isinstance(job_name, str):
            raise ValueError(f"job_timeouts[{i}] missing or invalid 'job_name'")

        interval = item.get("expected_interval_seconds")
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError(
                f"job_timeouts[{i}] 'expected_interval_seconds' must be a positive int"
            )

        grace = item.get("grace_period_seconds", _DEFAULT_GRACE_PERIOD)
        if not isinstance(grace, int) or grace < 0:
            raise ValueError(
                f"job_timeouts[{i}] 'grace_period_seconds' must be a non-negative int"
            )

        configs.append(
            JobTimeoutConfig(
                job_name=job_name,
                expected_interval_seconds=interval,
                grace_period_seconds=grace,
            )
        )

    return configs
