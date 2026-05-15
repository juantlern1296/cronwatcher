"""Shadow mode: dispatch alerts to a secondary webhook without affecting primary flow."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from cronwatcher.webhook import WebhookPayload, send_webhook
from cronwatcher.config import WebhookConfig


@dataclass
class ShadowConfig:
    webhook: WebhookConfig
    enabled: bool = True


@dataclass
class AlertShadow:
    config: ShadowConfig
    _dispatched: list = field(default_factory=list, init=False, repr=False)

    def dispatch(self, payload: WebhookPayload, now: Optional[float] = None) -> bool:
        """Send payload to shadow webhook. Returns True if sent, False if disabled."""
        if not self.config.enabled:
            return False
        try:
            send_webhook(self.config.webhook, payload)
            self._dispatched.append(payload)
            return True
        except Exception:
            return False

    def dispatch_count(self) -> int:
        return len(self._dispatched)


def wrap_with_shadow(
    handler: Callable[[WebhookPayload], None],
    shadow: AlertShadow,
) -> Callable[[WebhookPayload], None]:
    """Wrap a handler so the payload is also forwarded to the shadow webhook."""
    def _inner(payload: WebhookPayload) -> None:
        handler(payload)
        shadow.dispatch(payload)
    return _inner


def shadow_handler(
    config: dict,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    """Build a shadow-wrapped handler from raw config dict."""
    from cronwatcher.alert_shadow_config import parse_shadow_config
    shadow_cfg = parse_shadow_config(config)
    if shadow_cfg is None:
        return handler
    shadow = AlertShadow(config=shadow_cfg)
    return wrap_with_shadow(handler, shadow)
