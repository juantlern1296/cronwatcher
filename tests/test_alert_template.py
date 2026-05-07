"""Tests for cronwatcher.alert_template."""

import pytest

from cronwatcher.alert_template import (
    AlertTemplate,
    _render,
    parse_alert_template,
    render_template,
)


# ---------------------------------------------------------------------------
# _render
# ---------------------------------------------------------------------------

def test_render_replaces_known_placeholder():
    result = _render("Hello {name}!", {"name": "world"})
    assert result == "Hello world!"


def test_render_leaves_unknown_placeholder():
    result = _render("Hello {name}!", {})
    assert result == "Hello {name}!"


def test_render_multiple_placeholders():
    result = _render("{a} and {b}", {"a": "foo", "b": "bar"})
    assert result == "foo and bar"


# ---------------------------------------------------------------------------
# render_template
# ---------------------------------------------------------------------------

def test_render_template_defaults():
    tmpl = AlertTemplate()
    ctx = {
        "job_name": "backup",
        "hostname": "myhost",
        "timestamp": "2024-01-01T00:00:00",
        "exit_code": "1",
    }
    out = render_template(tmpl, ctx)
    assert out["title"] == "Cron job failure: backup"
    assert "backup" in out["body"]
    assert "myhost" in out["body"]


def test_render_template_extra_fields():
    tmpl = AlertTemplate(extra_fields={"channel": "#{job_name}-alerts"})
    ctx = {"job_name": "cleanup"}
    out = render_template(tmpl, ctx)
    assert out["channel"] == "#cleanup-alerts"


def test_render_template_returns_all_keys():
    tmpl = AlertTemplate()
    out = render_template(tmpl, {})
    assert "title" in out
    assert "body" in out


# ---------------------------------------------------------------------------
# parse_alert_template
# ---------------------------------------------------------------------------

def test_parse_none_returns_none():
    assert parse_alert_template(None) is None


def test_parse_empty_dict_returns_none():
    assert parse_alert_template({}) is None


def test_parse_not_dict_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        parse_alert_template("bad")


def test_parse_custom_title_and_body():
    raw = {"title": "ALERT: {job_name}", "body": "Something broke."}
    tmpl = parse_alert_template(raw)
    assert tmpl is not None
    assert tmpl.title == "ALERT: {job_name}"
    assert tmpl.body == "Something broke."


def test_parse_extra_field_included():
    raw = {"severity": "critical"}
    tmpl = parse_alert_template(raw)
    assert tmpl is not None
    assert tmpl.extra_fields["severity"] == "critical"


def test_parse_non_string_title_raises():
    with pytest.raises(ValueError, match="title must be a string"):
        parse_alert_template({"title": 123})


def test_parse_non_string_extra_raises():
    with pytest.raises(ValueError, match="must be a string"):
        parse_alert_template({"custom_field": ["bad"]})
