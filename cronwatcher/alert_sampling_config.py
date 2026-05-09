"""Helper that wraps a handler with alert sampling from the top-level config."""
from __future__ import annotations

from typing import Callable, Optional

from cronwatcher.alert_sampling import AlertSampler, SamplingConfig, parse_sampling_config
from cronwatcher.webhook import WebhookPayload


def wrap_with_sampler(
    config: dict,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    """Return *handler* wrapped in an AlertSampler if config contains a
    'sampling' section, otherwise return *handler* unchanged."""
    sampling_cfg: Optional[SamplingConfig] = parse_sampling_config(config)
    if sampling_cfg is None:
        return handler
    sampler = AlertSampler(sampling_cfg, handler)
    return sampler.add


def sampled_handler(
    sampling_cfg: SamplingConfig,
    handler: Callable[[WebhookPayload], None],
) -> Callable[[WebhookPayload], None]:
    """Convenience wrapper — build an AlertSampler and return its *add* method."""
    sampler = AlertSampler(sampling_cfg, handler)
    return sampler.add
