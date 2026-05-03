# Alertmanager

## Overview

Alertmanager handles alerts sent by Prometheus, manages routing and deduplication, and dispatches notifications via webhooks. In the Smart Irrigation System, it forwards alerts to the notification-service which then sends email/webhook notifications.

**Port:** 9093

**Config:** `configs/monitoring/alertmanager.yml`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       PROMETHEUS (:9090)                                       │
│                                                                                 │
│  Evaluates alert_rules.yml                                                     │
│  Fires alerts to Alertmanager                                                  │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ALERTMANAGER (:9093)                                       │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Routing Tree                                       │   │
│  │                                                                          │   │
│  │  All alerts ──────────────────────────────────────────────────────────┐   │   │
│  │                              │                                        │   │
│  │              ┌───────────────┴───────────────┐                        │   │
│  │              │                               │                        │   │
│  │         critical (10s wait)           warning (30s wait)             │   │
│  │              │                               │                        │   │
│  │              └───────────────┬───────────────┘                        │   │
│  │                              │                                        │   │
│  └──────────────────────────────┼───────────────────────────────────────┘   │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Receivers                                         │   │
│  │                                                                          │   │
│  │  - notification-service (webhook)                                      │   │
│  │  - email (via notification-service)                                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     Inhibit Rules                                      │   │
│  │                                                                          │   │
│  │  critical alerts inhibit warning alerts for same alertname/job        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                  NOTIFICATION SERVICE (:8505)                                 │
│                                                                                 │
│  Receives alerts via webhook → sends email/webhook to end users               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration

### alertmanager.yml

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: notification-service
  group_by:
    - alertname
    - job
    - severity
  group_wait: 15s
  group_interval: 1m
  repeat_interval: 4h
  routes:
    - matchers:
        - severity="critical"
      receiver: notification-service
      group_wait: 10s
      repeat_interval: 30m
    - matchers:
        - severity="warning"
      receiver: notification-service
      group_wait: 30s
      repeat_interval: 2h

receivers:
  - name: notification-service
    webhook_configs:
      - url: http://notification-service:8505/alerts/webhook
        send_resolved: true

inhibit_rules:
  - source_matchers:
      - severity="critical"
    target_matchers:
      - severity="warning"
    equal:
      - alertname
      - job
```

### Configuration Explained

| Setting | Value | Description |
|---------|-------|-------------|
| `group_by` | alertname, job, severity | How to group alerts |
| `group_wait` | 15s | Wait before sending first notification |
| `group_interval` | 1m | Interval between grouped alerts |
| `repeat_interval` | 4h | Repeat alert if still firing |
| `group_wait` (critical) | 10s | Faster notification for critical |
| `repeat_interval` (critical) | 30m | More frequent repeats for critical |
| `group_wait` (warning) | 30s | Slower for warnings |
| `repeat_interval` (warning) | 2h | Less frequent for warnings |

---

## Routing

### Severity-Based Routing

```yaml
routes:
  # Critical alerts - faster notifications
  - matchers:
      - severity="critical"
    receiver: notification-service
    group_wait: 10s
    repeat_interval: 30m

  # Warning alerts - slower notifications
  - matchers:
      - severity="warning"
    receiver: notification-service
    group_wait: 30s
    repeat_interval: 2h
```

### Grouping

Alerts are grouped by `alertname`, `job`, and `severity`. Multiple alerts matching the same group are sent together to reduce notification spam.

---

## Inhibit Rules

Prevents warning alerts from firing when a critical alert for the same issue exists:

```yaml
inhibit_rules:
  - source_matchers:
      - severity="critical"
    target_matchers:
      - severity="warning"
    equal:
      - alertname
      - job
```

**Logic:** If a `critical` alert for `HighTemperature` on `irrigation-controller` is firing, suppress any `warning` alerts for `HighTemperature` on `irrigation-controller`.

---

## Receivers

### Webhook (Primary)

```yaml
- name: notification-service
  webhook_configs:
    - url: http://notification-service:8505/alerts/webhook
      send_resolved: true
```

**Endpoint:** `POST http://notification-service:8505/alerts/webhook`

**Payload:**
```json
{
  "receiver": "notification-service",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {"alertname": "SmartIrrigationServiceDown", "severity": "critical", "job": "data-ingestion"},
      "annotations": {"summary": "Service data-ingestion is down", "description": "..."},
      "startsAt": "2026-05-03T10:00:00Z"
    }
  ],
  "groupLabels": {"alertname": "SmartIrrigationServiceDown"},
  "commonLabels": {"severity": "critical"},
  "commonAnnotations": {}
}
```

---

## Docker Compose

```yaml
alertmanager:
  image: prom/alertmanager:latest
  ports:
    - "9093:9093"
  command:
    - "--config.file=/etc/alertmanager/alertmanager.yml"
    - "--storage.path=/alertmanager"
  volumes:
    - ../configs/monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
  networks:
    - irrigation_net
```

---

## Environment Variables

From `.env` (for notification-service email):

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERTMANAGER_SMTP_HOST` | smtp.example.com | SMTP server |
| `ALERTMANAGER_SMTP_PORT` | 587 | SMTP port |
| `ALERTMANAGER_SMTP_FROM` | alerts@smart-irrigation.local | Sender email |
| `ALERTMANAGER_SMTP_USERNAME` | dev_alerts | SMTP username |
| `ALERTMANAGER_SMTP_PASSWORD` | smtp_dev_pass | SMTP password |
| `ALERTMANAGER_EMAIL_TO` | team@smart-irrigation.local | Recipient email |

---

## Accessing Alertmanager

**Web UI:** http://localhost:9093

**Silent alert:** http://localhost:9093/#/silences

**Status:** http://localhost:9093/api/v1/status

---

## Integration with Prometheus

Prometheus sends alerts to Alertmanager via configuration:

```yaml
# prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

---

## Alert Flow

```
1. Prometheus evaluates alert_rules.yml every 15s
2. If alert condition met → fires alert to Alertmanager
3. Alertmanager:
   - Groups alerts by alertname/job/severity
   - Waits group_wait before sending
   - Sends to notification-service webhook
4. Notification-service:
   - Receives alert at /alerts/webhook
   - Checks ALERT_SEVERITY_THRESHOLD
   - Sends email (if SMTP configured)
   - Sends webhook (if webhook URL configured)
```

---

## Testing Alerts

### Manually trigger via Prometheus

```bash
# In Prometheus UI: http://localhost:9090/graph
# Execute: up{job="data-ingestion"} = 0
```

### Check Alertmanager status

```bash
curl http://localhost:9093/api/v1/alerts
```

### Check silences

```bash
curl http://localhost:9093/api/v1/silences
```

---

## Summary

| Aspect | Value |
|--------|-------|
| Port | 9093 |
| Config | configs/monitoring/alertmanager.yml |
| Receiver | notification-service webhook |
| Group wait | 15s (default), 10s (critical), 30s (warning) |
| Repeat interval | 4h (default), 30m (critical), 2h (warning) |
| Inhibit rules | Critical suppresses warning for same alert/job |

Alertmanager provides centralized alert routing with intelligent grouping and deduplication before forwarding to the notification-service for delivery.