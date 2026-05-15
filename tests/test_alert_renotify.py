import pytest
from cronwatcher.alert_renotify import AlertRenotifier, RenotifyConfig
from cronwatcher.webhook import WebhookPayload


def make_payload(job: str = "backup") -> WebhookPayload:
    return WebhookPayload(
        job_name=job,
        exit_code=1,
        timestamp="2024-01-01T00:00:00",
        hostname="host1",
        extra={},
    )


def test_invalid_interval_raises():
    with pytest.raises(ValueError, match="interval must be positive"):
        RenotifyConfig(interval=0)


def test_negative_max_renotifies_raises():
    with pytest.raises(ValueError, match="max_renotifies"):
        RenotifyConfig(interval=60, max_renotifies=-1)


@pytest.fixture
def calls():
    return []


@pytest.fixture
def renotifier(calls):
    cfg = RenotifyConfig(interval=60.0, max_renotifies=0)
    return AlertRenotifier(cfg, lambda p: calls.append(p))


def test_check_before_mark_firing_returns_false(renotifier):
    p = make_payload()
    assert renotifier.check(p, now=0.0) is False


def test_check_within_interval_returns_false(renotifier, calls):
    p = make_payload()
    renotifier.mark_firing(p, now=0.0)
    assert renotifier.check(p, now=30.0) is False
    assert calls == []


def test_check_after_interval_triggers_handler(renotifier, calls):
    p = make_payload()
    renotifier.mark_firing(p, now=0.0)
    result = renotifier.check(p, now=61.0)
    assert result is True
    assert len(calls) == 1


def test_renotify_count_increments(renotifier):
    p = make_payload()
    renotifier.mark_firing(p, now=0.0)
    renotifier.check(p, now=61.0)
    renotifier.check(p, now=122.0)
    assert renotifier.renotify_count("backup") == 2


def test_max_renotifies_respected(calls):
    cfg = RenotifyConfig(interval=10.0, max_renotifies=2)
    r = AlertRenotifier(cfg, lambda p: calls.append(p))
    p = make_payload()
    r.mark_firing(p, now=0.0)
    r.check(p, now=11.0)   # count=1
    r.check(p, now=22.0)   # count=2
    r.check(p, now=33.0)   # blocked
    assert len(calls) == 2


def test_mark_resolved_stops_renotification(renotifier, calls):
    p = make_payload()
    renotifier.mark_firing(p, now=0.0)
    renotifier.mark_resolved("backup")
    result = renotifier.check(p, now=120.0)
    assert result is False
    assert calls == []


def test_renotify_count_unknown_job_returns_zero(renotifier):
    assert renotifier.renotify_count("nonexistent") == 0


def test_mark_firing_twice_does_not_reset_state(renotifier, calls):
    p = make_payload()
    renotifier.mark_firing(p, now=0.0)
    renotifier.check(p, now=61.0)  # triggers, count=1
    renotifier.mark_firing(p, now=70.0)  # should not reset
    assert renotifier.renotify_count("backup") == 1
