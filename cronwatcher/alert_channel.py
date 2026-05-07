"""Alert channel abstraction — route alerts to different output targets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from cronwatcher.webhook import WebhookPayload, send_webhook
from cronwatcher.config import WebhookConfig


@dataclass
class ChannelResult:
    channel_name: str
    success: bool
    error: Optional[str] = None


@dataclass
class AlertChannel:
    name: str
    webhook_config: WebhookConfig
    tags: List[str] = field(default_factory=list)

    def send(self, payload: WebhookPayload) -> ChannelResult:
        ok, err = send_webhook(self.webhook_config, payload)
        return ChannelResult(channel_name=self.name, success=ok, error=err)


class AlertChannelRegistry:
    def __init__(self) -> None:
        self._channels: Dict[str, AlertChannel] = {}

    def register(self, channel: AlertChannel) -> None:
        if not channel.name:
            raise ValueError("Channel name must not be empty")
        self._channels[channel.name] = channel

    def get(self, name: str) -> Optional[AlertChannel]:
        return self._channels.get(name)

    def all(self) -> List[AlertChannel]:
        return list(self._channels.values())

    def by_tag(self, tag: str) -> List[AlertChannel]:
        return [c for c in self._channels.values() if tag in c.tags]

    def send_all(self, payload: WebhookPayload) -> List[ChannelResult]:
        return [ch.send(payload) for ch in self._channels.values()]

    def send_by_tag(self, tag: str, payload: WebhookPayload) -> List[ChannelResult]:
        return [ch.send(payload) for ch in self.by_tag(tag)]
