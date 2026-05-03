# Prometheus Monitoring

## Overview

Prometheus collects metrics from all Smart Irrigation services, stores them time-series, and triggers alerts based on configurable rules. It integrates with Grafana for visualization and Alertmanager for alert routing.

**Port:** 9090

**Config:** `configs/monitoring/prometheus.yml`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SERVICES (Metrics Producers)                          │
│                                                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐   │
│  │ API Gateway  │ │User Service │ │Notification │ │   Data Ingestion   │   │
│  │   :8080      │ │   :5005     │ │  Service    │ │      :8001         │   │
│  │   /metrics   │ │   /metrics   │ │   :8505     │ │     /metrics       │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────┘   │
│                                                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐   │
│  │Feature Eng.  │ │ Data Quality │ │ Model Server │ │  Irrigation Ctrl   │   │
│  │   :8004      │ │   :8005      │ │   :8501      │ │      :8503         │   │
│  │   /metrics   │ │   /metrics   │ │   /metrics   │ │     /metrics       │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      PROMETHEUS (:9090)                                        │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Scrape Configuration                                 │   │
│  │                                                                          │   │
│  │  scrape_interval: 15s                                                   │   │
│  │  evaluation_interval: 15s                                               │   │
│  │  10 jobs (one per service)                                             │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Alert Rules                                          │   │
│  │                                                                          │   │
│  │  - service-availability  (service down)                               │   │
│  │  - application-health    (latency, errors, drift)                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Storage                                              │   │
│  │                                                                          │   │
│  │  retention: 15 days                                                    │   │
│  │  TSDB path: /prometheus                                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      ALERTMANAGER (:9093)                                      │
│                                                                                 │
│  Routes alerts based on severity and dispatches via email/webhook            │
└────────────────────────────────────────────────┬────────────────────────────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      GRAFANA (:3001)                                          │
│                                                                                 │
│  Dashboards for system health, sensor metrics, ML performance                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Scrape Configuration

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    project: smart-irrigation

rule_files:
  - /etc/prometheus/alert_rules.yml

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: [prometheus:9090]

  - job_name: api-gateway
    metrics_path: /metrics
    static_configs:
      - targets: [api-gateway:8080]

  - job_name: user-service
    metrics_path: /metrics
    static_configs:
      - targets: [user-service:5005]

  # ... (one job per service)
```

### Service Targets

| Service | Port | Metrics Path |
|---------|------|--------------|
| api-gateway | 8080 | /metrics |
| user-service | 5005 | /metrics |
| notification-service | 8505 | /metrics |
| data-ingestion | 8001 | /metrics |
| feature-engineering | 8004 | /metrics |
| data-quality | 8005 | /metrics |
| model-server | 8501 | /metrics |
| drift-monitor | 8502 | /metrics |
| irrigation-controller | 8503 | /metrics |

---

## Alert Rules

### alert_rules.yml

#### Service Availability

```yaml
- alert: SmartIrrigationServiceDown
  expr: up{job=~"api-gateway|user-service|..."} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Service {{ $labels.job }} is down"
    description: "Prometheus cannot scrape..."
```

#### Application Health

| Alert | Expression | For | Severity |
|-------|------------|-----|----------|
| ApiGatewayHigh5xxRate | 5xx ratio > 5% | 10m | warning |
| UserServiceHighLatency | p95 > 1s | 10m | warning |
| DataIngestionProcessingStalled | no new readings in 15m | 15m | critical |
| FeatureEngineeringErrorsIncreasing | errors > 0 | 5m | warning |
| ModelServerErrorRateHigh | errors > 5 | 10m | warning |
| DriftSignalExceeded | KL > 0.5 or PH > 50 | 10m | warning |
| UnhealthySensorsDetected | max health status >= 2 | 10m | warning |

---

## Query Examples

### Service Uptime

```promql
up{job="api-gateway"}
```

### Request Rate (API Gateway)

```promql
rate(api_gateway_http_requests_total[5m])
```

### Error Rate (Data Ingestion)

```promql
rate(data_ingestion_errors_total[5m])
```

### Sensor Health Status

```promql
data_quality_sensor_health_status
```

### Model Prediction Latency

```promql
histogram_quantile(0.95, rate(model_server_prediction_duration_seconds_bucket[5m]))
```

---

## Docker Compose

```yaml
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  command:
    - "--config.file=/etc/prometheus/prometheus.yml"
    - "--storage.tsdb.path=/prometheus"
    - "--storage.tsdb.retention.time=15d"
    - "--web.enable-lifecycle"
  volumes:
    - ../configs/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - ../configs/monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml:ro
    - prometheus_data:/prometheus
  networks:
    - irrigation_net
```

---

## Environment Variables

From `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMETHEUS_SCRAPE_INTERVAL` | 15s | Scrape interval |

---

## Accessing Prometheus

**Web UI:** http://localhost:9090

**Graph queries:** http://localhost:9090/graph

**Alerts page:** http://localhost:9090/alerts

---

## Integration

### Alertmanager

Prometheus sends firing alerts to Alertmanager:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

### Grafana

Grafana connects to Prometheus as a datasource:

```yaml
# configs/monitoring/grafana/datasources.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    access: proxy
```

---

## Metrics by Service

### API Gateway

- `api_gateway_http_requests_total` (counter)
- `api_gateway_request_duration_seconds` (histogram)

### User Service

- `user_service_request_duration_seconds` (histogram)
- `user_service_login_attempts_total` (counter)

### Data Ingestion

- `data_ingestion_total_processed` (gauge)
- `data_ingestion_valid_readings` (gauge)
- `data_ingestion_anomalies_flagged` (gauge)
- `data_ingestion_errors_total` (counter)

### Data Quality

- `data_quality_readings_checked_total` (counter)
- `data_quality_anomalies_detected_total` (counter)
- `data_quality_active_rules` (gauge)
- `data_quality_sensor_health_status` (gauge)

### Model Server

- `model_server_predictions_total` (counter)
- `model_server_prediction_duration_seconds` (histogram)
- `model_server_errors_total` (counter)

### Irrigation Controller

- `irrigation_triggers_total` (counter)
- `irrigation_events_active` (gauge)

### Drift Monitor

- `drift_monitor_kl_divergence` (gauge)
- `drift_monitor_page_hinkley_score` (gauge)

---

## Summary

| Aspect | Value |
|--------|-------|
| Port | 9090 |
| Scrape Interval | 15s |
| Evaluation Interval | 15s |
| Retention | 15 days |
| Alert Rules | `configs/monitoring/alert_rules.yml` |
| Targets | 10 services |
| Integration | Grafana, Alertmanager |

Prometheus provides centralized metrics collection and alerting for all Smart Irrigation services.