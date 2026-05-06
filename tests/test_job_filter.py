"""Tests for cronwatcher.job_filter."""

import pytest
from cronwatcher.job_filter import JobFilter, parse_job_filter
from cronwatcher.log_parser import CronLogEntry


def make_entry(cmd: str) -> CronLogEntry:
    return CronLogEntry(
        raw="Jan  1 00:00:00 host CRON[1]: (root) CMD (" + cmd + ")",
        timestamp=None,
        process="CRON",
        pid="1",
        user="root",
        tag="CMD",
        message=cmd,
    )


# --- matches() ---

def test_no_patterns_allows_all():
    f = JobFilter()
    assert f.matches(make_entry("/usr/bin/backup.sh")) is True


def test_include_pattern_allows_match():
    f = JobFilter(include_patterns=["*backup*"])
    assert f.matches(make_entry("/usr/bin/backup.sh")) is True


def test_include_pattern_blocks_non_match():
    f = JobFilter(include_patterns=["*backup*"])
    assert f.matches(make_entry("/usr/bin/cleanup.sh")) is False


def test_exclude_pattern_blocks_match():
    f = JobFilter(exclude_patterns=["*cleanup*"])
    assert f.matches(make_entry("/usr/bin/cleanup.sh")) is False


def test_exclude_pattern_allows_non_match():
    f = JobFilter(exclude_patterns=["*cleanup*"])
    assert f.matches(make_entry("/usr/bin/backup.sh")) is True


def test_exclude_takes_priority_over_include():
    f = JobFilter(include_patterns=["*backup*"], exclude_patterns=["*backup*"])
    assert f.matches(make_entry("/usr/bin/backup.sh")) is False


def test_multiple_include_patterns():
    f = JobFilter(include_patterns=["*backup*", "*sync*"])
    assert f.matches(make_entry("/usr/bin/sync.sh")) is True
    assert f.matches(make_entry("/usr/bin/other.sh")) is False


# --- parse_job_filter() ---

def test_parse_empty_config_returns_empty_filter():
    f = parse_job_filter({})
    assert f.include_patterns == []
    assert f.exclude_patterns == []


def test_parse_include_and_exclude():
    data = {"job_filter": {"include": ["*backup*"], "exclude": ["*test*"]}}
    f = parse_job_filter(data)
    assert f.include_patterns == ["*backup*"]
    assert f.exclude_patterns == ["*test*"]


def test_parse_invalid_section_raises():
    with pytest.raises(ValueError, match="job_filter"):
        parse_job_filter({"job_filter": "not-a-dict"})


def test_parse_invalid_include_type_raises():
    with pytest.raises(ValueError, match="include"):
        parse_job_filter({"job_filter": {"include": "*backup*"}})


def test_parse_invalid_exclude_type_raises():
    with pytest.raises(ValueError, match="exclude"):
        parse_job_filter({"job_filter": {"exclude": "*test*"}})
