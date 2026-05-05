# cronwatcher

Lightweight daemon that monitors cron job failures and sends alerts via webhook.

## Installation

```bash
pip install cronwatcher
```

## Usage

Start the daemon and point it at your cron log:

```bash
cronwatcher --log /var/log/syslog --webhook https://hooks.example.com/alerts
```

You can also use a config file:

```yaml
# cronwatcher.yml
log: /var/log/syslog
webhook: https://hooks.example.com/alerts
jobs:
  - name: backup
    pattern: "backup.sh"
    notify_on: failure
```

```bash
cronwatcher --config cronwatcher.yml
```

cronwatcher will watch for non-zero exit codes and missed schedules, then POST a JSON payload to your webhook when something goes wrong.

### Example Alert Payload

```json
{
  "job": "backup",
  "status": "failed",
  "exit_code": 1,
  "timestamp": "2024-03-15T02:30:01Z",
  "message": "backup.sh exited with code 1"
}
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--log` | Path to cron log file | `/var/log/syslog` |
| `--webhook` | Webhook URL for alerts | required |
| `--config` | Path to config file | none |
| `--interval` | Poll interval in seconds | `60` |

## License

MIT © [cronwatcher contributors](LICENSE)