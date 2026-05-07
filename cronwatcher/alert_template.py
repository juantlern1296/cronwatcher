"""Simple templating support for webhook alert messages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AlertTemplate:
    """Holds a title and body template string."""

    title: str = "Cron job failure: {job_name}"
    body: str = "Job '{job_name}' failed on {hostname} at {timestamp}. Exit code: {exit_code}."
    extra_fields: Dict[str, str] = field(default_factory=dict)


_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _render(template: str, context: Dict[str, str]) -> str:
    """Replace {key} placeholders with values from context.

    Unknown placeholders are left as-is.
    """

    def replacer(match: re.Match) -> str:  # type: ignore[type-arg]
        key = match.group(1)
        return context.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(replacer, template)


def render_template(
    template: AlertTemplate,
    context: Dict[str, str],
) -> Dict[str, str]:
    """Return a dict with rendered title, body, and any extra fields."""
    result: Dict[str, str] = {
        "title": _render(template.title, context),
        "body": _render(template.body, context),
    }
    for key, value in template.extra_fields.items():
        result[key] = _render(value, context)
    return result


def parse_alert_template(raw: object) -> Optional[AlertTemplate]:
    """Parse an AlertTemplate from a config dict section.

    Returns None if *raw* is None or an empty dict.
    Raises ValueError on invalid input.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("alert_template config must be a dict")
    if not raw:
        return None

    kwargs: Dict[str, object] = {}
    for key in ("title", "body"):
        if key in raw:
            if not isinstance(raw[key], str):
                raise ValueError(f"alert_template.{key} must be a string")
            kwargs[key] = raw[key]

    extra: Dict[str, str] = {}
    for key, value in raw.items():
        if key in ("title", "body"):
            continue
        if not isinstance(value, str):
            raise ValueError(f"alert_template extra field '{key}' must be a string")
        extra[key] = value

    if extra:
        kwargs["extra_fields"] = extra

    return AlertTemplate(**kwargs)  # type: ignore[arg-type]
