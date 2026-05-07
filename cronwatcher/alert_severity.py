"""Alert severity levels and classification based on failure counts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class SeverityConfig:
    warning_threshold: int  # failures before WARNING
    critical_threshold: int  # failures before CRITICAL

    def __post_init__(self) -> None:
        if self.warning_threshold < 1:
            raise ValueError("warning_threshold must be >= 1")
        if self.critical_threshold <= self.warning_threshold:
            raise ValueError(
                "critical_threshold must be greater than warning_threshold"
            )


def classify(failure_count: int, cfg: SeverityConfig) -> Severity:
    """Return the severity level for a given failure count."""
    if failure_count >= cfg.critical_threshold:
        return Severity.CRITICAL
    if failure_count >= cfg.warning_threshold:
        return Severity.WARNING
    return Severity.INFO


def parse_severity_config(raw: Dict[str, Any]) -> Optional[SeverityConfig]:
    """Parse severity config from the 'severity' section of config JSON.

    Returns None if the section is absent or disabled.
    """
    section = raw.get("severity")
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("'severity' must be a JSON object")
    warning = int(section.get("warning_threshold", 1))
    critical = int(section.get("critical_threshold", 3))
    return SeverityConfig(warning_threshold=warning, critical_threshold=critical)
