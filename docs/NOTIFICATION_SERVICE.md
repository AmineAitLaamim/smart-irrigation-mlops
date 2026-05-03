# Notification Service

## Overview

The Notification Service is an alert routing service that consumes events from Redis and Alertmanager webhooks, then dispatches notifications via email and webhooks based on severity thresholds.

**Location:** `services/notification-service/`

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Alert Sources                                              │
│                                                                                 │
│  ┌──────────────────┐                    ┌────────────────────────┐          │
│  │  Redis Channels  │                    │  Alertmanager Webhook  │          │
│  │                   │                    │                        │          │
│  │ - alerts:anomaly  │──┐                 │  POST /alerts/webhook   │──┐       │
│  │ - irrigation:     │  │                 │                        │  │       │
│  │   triggered        │──┼────────────────▶│                        │  │       │
│  └──────────────────┘  │                 └────────────────────────┘  │       │
│                        │                                             │       │
└────────────────────────┼─────────────────────────────────────────────┼───────┘
                         │                                             │
                         ▼                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION SERVICE                                         │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       AlertHandler                                       │   │
│  │                                                                          │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │   │
│  │  │   Severity   │    │    Email     │    │       Webhook           │   │   │
│  │  │   Filter     │    │   (SMTP)     │    │       (HTTP POST)       │   │   │
│  │  │              │    │              │    │                          │   │   │
│  │  │ - info       │    │ - TLS        │    │ - Configurable URL     │   │   │
│  │  │ - warning    │    │ - Auth      │    │ - JSON payload        │   │   │
│  │  │ - critical   │    │ - Template  │    │ - Latency metrics     │   │   │
│  │  └──────────────┘    └──────────────┘    └──────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Input Channels

### Redis Channels

| Channel | Description | Example Payload |
|---------|-------------|-----------------|
| `alerts:anomaly` | Data quality anomalies | `{"zone_id": "zone-001", "severity": "warning", "event_type": "above_max_plausible_moisture"}` |
| `irrigation:triggered` | Irrigation events | `{"zone_id": "zone-001", "action": "start", "duration": 300}` |

### Alertmanager Webhook

```
POST /alerts/webhook
```

```json
{
  "receiver": "notifications",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {"severity": "critical", "alertname": "HighTemperature"},
      "annotations": {"summary": "Temperature exceeded threshold", "description": "Zone 1 at 55°C"},
      "startsAt": "2026-05-03T10:00:00Z"
    }
  ],
  "groupLabels": {},
  "commonLabels": {},
  "commonAnnotations": {}
}
```

---

## Components

### main.py

FastAPI application with Redis listener:

```python
async def redis_listener() -> None:
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message:
            data = json.loads(message["data"])
            severity = str(data.get("severity", "info")).lower()
            if not handler.should_dispatch(severity):
                continue
            asyncio.create_task(handler.dispatch_alert({**data, "channel": channel}, "redis"))
```

**Endpoints:**
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `POST /alerts/webhook` - Alertmanager integration

### alert_handler.py

Handles alert dispatch:

```python
async def dispatch_alert(self, payload: dict[str, Any], source: str) -> dict[str, str]:
    severity = str(payload.get("severity", "warning")).lower()
    ALERTS_RECEIVED.labels(source, severity).inc()
    subject = f"[{severity.upper()}] Smart Irrigation Alert"
    body = json.dumps(payload, indent=2)
    await asyncio.gather(self.send_email(subject, body), self.send_webhook(payload))
    return {"status": "accepted", "source": source, "severity": severity}
```

**Features:**
- Severity-based filtering
- Email via SMTP (async, thread pool)
- Webhook delivery (with latency tracking)
- Alertmanager normalization

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `REDIS_CHANNEL_ALERTS_ANOMALY` | alerts:anomaly | Anomaly alerts channel |
| `REDIS_CHANNEL_IRRIGATION_TRIGGERED` | irrigation:triggered | Irrigation events channel |
| `SMTP_HOST` | - | SMTP server hostname |
| `SMTP_PORT` | 587 | SMTP port (TLS) |
| `SMTP_FROM_ADDRESS` | - | Sender email address |
| `SMTP_PASSWORD` | - | SMTP password |
| `NOTIFICATION_WEBHOOK_URL` | - | Webhook URL for HTTP notifications |
| `ALERT_EMAIL_TO` | admin@smart-irrigation.local | Recipient email |
| `ALERT_SEVERITY_THRESHOLD` | warning | Minimum severity to dispatch |

### Severity Levels

| Level | Value | Description |
|-------|-------|-------------|
| `info` | 0 | Informational only |
| `warning` | 1 | Warnings, requires attention |
| `critical` | 2 | Critical alerts, immediate action |

The `ALERT_SEVERITY_THRESHOLD` setting controls which alerts are dispatched:
- `"info"` → dispatch all alerts
- `"warning"` → dispatch warning + critical
- `"critical"` → dispatch only critical

---

## Metrics

Prometheus metrics at `/metrics`:

| Metric | Labels | Description |
|--------|--------|-------------|
| `notification_service_alerts_received_total` | source, severity | Alerts received |
| `notification_service_deliveries_total` | channel, status | Delivery attempts (success/failed/skipped) |
| `notification_service_webhook_delivery_seconds` | - | Webhook latency histogram |

---

## Notification Channels

### Email (SMTP)

- **Transport:** TLS (port 587)
- **Authentication:** Username + password
- **Template:** JSON dump of alert payload as body

```python
def _send_smtp_sync(self, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = ALERT_EMAIL_TO
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_FROM, SMTP_PASSWORD)
        server.send_message(msg)
```

### Webhook (HTTP POST)

- **Method:** POST
- **Content-Type:** application/json
- **Timeout:** 10 seconds
- **Payload:** Full alert data as JSON

```python
async def send_webhook(self, payload: dict[str, Any]) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
```

---

## Alertmanager Integration

The service normalizes Alertmanager alerts to internal format:

```python
def normalize_alertmanager_alert(self, alert, payload_status):
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    return {
        "source": "alertmanager",
        "status": alert.get("status", payload_status),
        "severity": labels.get("severity", "warning"),
        "alertname": labels.get("alertname", "unknown"),
        "service": labels.get("job") or labels.get("service", "unknown"),
        "summary": annotations.get("summary", ""),
        "description": annotations.get("description", ""),
        "startsAt": alert.get("startsAt"),
        "endsAt": alert.get("endsAt"),
    }
```

---

## Docker Compose

```yaml
notification-service:
  image: notification-service:latest
  ports:
    - "8002:8002"
  environment:
    - REDIS_URL=redis://redis:6379/0
    - REDIS_CHANNEL_ALERTS_ANOMALY=alerts:anomaly
    - REDIS_CHANNEL_IRRIGATION_TRIGGERED=irrigation:triggered
    - SMTP_HOST=smtp.example.com
    - SMTP_PORT=587
    - SMTP_FROM_ADDRESS=alerts@smart-irrigation.local
    - SMTP_PASSWORD=${SMTP_PASSWORD}
    - NOTIFICATION_WEBHOOK_URL=https://hooks.example.com/notify
    - ALERT_EMAIL_TO=admin@example.com
    - ALERT_SEVERITY_THRESHOLD=warning
  depends_on:
    - redis
```

---

## Usage Examples

### Sending a test alert via Redis

```bash
redis-cli PUBLISH alerts:anomaly '{"zone_id": "zone-001", "severity": "warning", "event_type": "high_moisture", "value": 95}'
```

### Alertmanager rule

```yaml
groups:
- name: irrigation
  rules:
  - alert: HighTemperature
    expr: temperature > 45
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High temperature in {{ $labels.zone_id }}"
      description: "Temperature is {{ $value }}°C"
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + asyncio |
| Language | Python |
| Input | Redis pubsub + Alertmanager webhook |
| Output | Email (SMTP) + Webhook (HTTP) |
| Filtering | Severity-based threshold |
| Port | 8002 |
| Dependencies | Redis |

The Notification Service provides centralized alerting with configurable thresholds, supporting both real-time Redis events and Prometheus Alertmanager integration.