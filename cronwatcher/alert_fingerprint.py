"""Fingerprinting for alert deduplication and grouping."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cronwatcher.webhook import WebhookPayload


@dataclass
class FingerprintConfig:
    """Controls which fields contribute to the alert fingerprint."""
    fields: List[str] = field(default_factory=lambda: ["job", "exit_code", "hostname"])
    include_labels: bool = False

    def __post_init__(self) -> None:
        if not self.fields:
            raise ValueError("fingerprint fields list must not be empty")
        allowed = {"job", "exit_code", "hostname", "command"}
        unknown = set(self.fields) - allowed
        if unknown:
            raise ValueError(f"unknown fingerprint fields: {sorted(unknown)}")


def _extract_fields(payload: WebhookPayload, fields: List[str]) -> Dict[str, Any]:
    mapping: Dict[str, Any] = {
        "job": payload.job_name,
        "exit_code": payload.exit_code,
        "hostname": payload.hostname,
        "command": payload.command,
    }
    return {f: mapping.get(f) for f in fields}


def compute_fingerprint(payload: WebhookPayload, config: FingerprintConfig) -> str:
    """Return a stable hex fingerprint string for the given payload."""
    data = _extract_fields(payload, config.fields)
    if config.include_labels:
        data["__labels"] = payload.labels or {}
    serialised = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()


def parse_fingerprint_config(raw: Optional[Dict[str, Any]]) -> FingerprintConfig:
    """Build a FingerprintConfig from the 'fingerprint' section of config JSON."""
    if not raw:
        return FingerprintConfig()
    if not isinstance(raw, dict):
        raise ValueError("'fingerprint' config must be a dict")
    kwargs: Dict[str, Any] = {}
    if "fields" in raw:
        fields = raw["fields"]
        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
            raise ValueError("'fingerprint.fields' must be a list of strings")
        kwargs["fields"] = fields
    if "include_labels" in raw:
        kwargs["include_labels"] = bool(raw["include_labels"])
    return FingerprintConfig(**kwargs)
