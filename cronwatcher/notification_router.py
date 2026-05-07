"""Routes failure alerts to one or more webhook targets based on job labels."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatcher.webhook import WebhookPayload, send_webhook
from cronwatcher.config import WebhookConfig


@dataclass
class RouteRule:
    """A routing rule that maps a label key/value to a webhook target."""
    label_key: str
    label_value: str
    webhook: WebhookConfig


@dataclass
class NotificationRouter:
    """Routes payloads to webhooks based on job label matching.

    Falls back to the default webhook if no route matches.
    """
    default_webhook: WebhookConfig
    routes: List[RouteRule] = field(default_factory=list)

    def resolve(self, labels: Dict[str, str]) -> List[WebhookConfig]:
        """Return all webhooks that match the given labels.

        If no route matches, returns the default webhook.
        """
        matched: List[WebhookConfig] = []
        for rule in self.routes:
            if labels.get(rule.label_key) == rule.label_value:
                matched.append(rule.webhook)
        return matched if matched else [self.default_webhook]

    def dispatch(self, payload: WebhookPayload, labels: Dict[str, str]) -> List[bool]:
        """Send payload to all resolved webhooks. Returns list of success booleans."""
        targets = self.resolve(labels)
        results = []
        for webhook_cfg in targets:
            ok = send_webhook(webhook_cfg, payload)
            results.append(ok)
        return results


def build_router(
    default_webhook: WebhookConfig,
    routes: Optional[List[RouteRule]] = None,
) -> NotificationRouter:
    """Construct a NotificationRouter with optional route rules."""
    return NotificationRouter(
        default_webhook=default_webhook,
        routes=routes or [],
    )
