import json
import os
import pytest
import tempfile

from cronwatcher.config import load_config, Config, WebhookConfig, CronJobConfig


@pytest.fixture
def valid_config_data():
    return {
        "webhook": {
            "url": "https://hooks.example.com/test",
            "secret": "mysecret",
            "timeout": 5,
        },
        "log_level": "DEBUG",
        "check_interval": 30,
        "jobs": [
            {
                "name": "test-job",
                "schedule": "* * * * *",
                "command": "/bin/true",
                "max_retries": 2,
                "alert_on_failure": True,
            }
        ],
    }


@pytest.fixture
def config_file(valid_config_data):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(valid_config_data, f)
        path = f.name
    yield path
    os.unlink(path)


def test_load_config_success(config_file):
    config = load_config(config_file)
    assert isinstance(config, Config)
    assert config.webhook.url == "https://hooks.example.com/test"
    assert config.webhook.secret == "mysecret"
    assert config.webhook.timeout == 5
    assert config.log_level == "DEBUG"
    assert config.check_interval == 30
    assert len(config.jobs) == 1
    assert config.jobs[0].name == "test-job"
    assert config.jobs[0].max_retries == 2


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.json")


def test_load_config_missing_webhook_url():
    data = {"webhook": {}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        with pytest.raises(ValueError, match="webhook.url is required"):
            load_config(path)
    finally:
        os.unlink(path)


def test_load_config_defaults():
    data = {"webhook": {"url": "https://example.com/hook"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        config = load_config(path)
        assert config.log_level == "INFO"
        assert config.check_interval == 60
        assert config.jobs == []
        assert config.log_file is None
        assert config.webhook.timeout == 10
        assert config.webhook.secret is None
    finally:
        os.unlink(path)
