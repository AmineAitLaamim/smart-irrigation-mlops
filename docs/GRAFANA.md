# Grafana Dashboards

## Overview

Grafana provides visualization dashboards for the Smart Irrigation System, connected to Prometheus as the data source. It includes pre-configured dashboards for sensor operations and ML performance monitoring.

**Port:** 3001

**Default credentials:** admin / grafana_dev (from `.env`)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GRAFANA (:3001)                                   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Dashboards                                        │   │
│  │                                                                          │   │
│  │  ┌──────────────────────┐      ┌───────────────────────────────────┐   │   │
│  │  │  Sensor Operations   │      │      ML Performance              │   │   │
│  │  │                      │      │                                   │   │   │
│  │  │ - Sensor health      │      │ - Predictions served            │   │   │
│  │  │ - Ingestion counts   │      │ - Model latency (p95)           │   │   │
│  │  │ - Anomaly detection  │      │ - Drift signals (KL, PH)        │   │   │
│  │  │ - Per-sensor status  │      │ - Irrigation events             │   │   │
│  │  │                      │      │ - Notification deliveries      │   │   │
│  │  └──────────────────────┘      └───────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      PROMETHEUS (:9090)                                        │
│                                                                                 │
│  Datasource: http://prometheus:9090                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Dashboards

### Sensor Operations

**UID:** `smart-irrigation-sensors`

**URL:** http://localhost:3001/d/smart-irrigation-sensors

**Panels:**

| Panel | Metric | Description |
|-------|--------|-------------|
| Worst Sensor Health | `max(data_quality_sensor_health_status)` | 0=healthy, 1=degraded, 2=unhealthy |
| Total Ingested Readings | `data_ingestion_total_processed` | Cumulative readings processed |
| Anomaly Detection Rate | `rate(data_quality_anomalies_detected_total[5m])` | Anomalies per second by type |
| Ingestion Pipeline Counters | `data_ingestion_valid_readings`, `data_ingestion_anomalies_flagged` | Valid vs flagged readings |
| Per-Sensor Health Status | `data_quality_sensor_health_status` | Health per zone/sensor |

**Time range:** Last 24 hours (auto-refresh: 30s)

**Tags:** smart-irrigation, sensors

---

### ML Performance

**UID:** `smart-irrigation-ml`

**URL:** http://localhost:3001/d/smart-irrigation-ml

**Panels:**

| Panel | Metric | Description |
|-------|--------|-------------|
| Predictions Served | `model_server_predictions_total` | Total predictions made |
| Current KL Divergence | `drift_monitor_kl_divergence` | Data drift (threshold: 0.2 warning, 0.5 critical) |
| Current Page-Hinkley Score | `drift_monitor_page_hinkley_score` | Concept drift (threshold: 20 warning, 50 critical) |
| Model Server p95 Latency | `histogram_quantile(0.95, ...)` | Prediction latency |
| Drift Signals | `drift_monitor_kl_divergence`, `drift_monitor_mean_error` | Drift over time |
| Irrigation Events | `irrigation_controller_events_total` | Triggered irrigation events |
| Notification Deliveries | `notification_service_deliveries_total` | Email/webhook delivery status |

**Time range:** Last 24 hours (auto-refresh: 30s)

**Tags:** smart-irrigation, ml

---

## Configuration

### datasources.yml

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### dashboards.yml

```yaml
apiVersion: 1
providers:
  - name: Smart Irrigation Dashboards
    orgId: 1
    folder: Smart Irrigation
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
```

### Dashboard Files

| File | Dashboard |
|------|-----------|
| `dashboard_sensors.json` | Sensor Operations |
| `dashboard_ml.json` | ML Performance |

---

## Docker Compose

```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER}
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    - GF_USERS_ALLOW_SIGN_UP=false
  volumes:
    - grafana_data:/var/lib/grafana
    - ../configs/monitoring/grafana/dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml:ro
    - ../configs/monitoring/grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro
    - ../configs/monitoring/grafana:/var/lib/grafana/dashboards:ro
  networks:
    - irrigation_net
  depends_on:
    prometheus:
      condition: service_healthy
```

---

## Environment Variables

From `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_ADMIN_USER` | admin | Admin username |
| `GRAFANA_ADMIN_PASSWORD` | grafana_dev | Admin password |

---

## Accessing Grafana

**URL:** http://localhost:3001

**Login:** admin / grafana_dev

**Explore queries:** http://localhost:3001/explore

**Alerting:** http://localhost:3001/alerting

---

## Adding Custom Panels

### Query Examples

**Service uptime:**
```promql
up{job="data-ingestion"}
```

**Data ingestion rate:**
```promql
rate(data_ingestion_total_processed[5m])
```

**Error rate by service:**
```promql
sum by (job) (rate(prometheus_target_scrapes_exceeded_target_limit_total[5m]))
```

**Memory usage (if exposed):**
```promql
container_memory_usage_bytes{container_name="irrigation-controller"}
```

### Panel Types

- **Stat** - Single value with thresholds
- **Time series** - Line/area charts over time
- **Table** - Tabular data
- **Gauge** - Numeric with ranges

---

## Alerts Integration

Grafana can trigger alerts based on panel queries:

1. Open a panel → Click alert icon
2. Configure conditions (e.g., `max > 2` for sensor health)
3. Set notification channel (email, Slack, webhook)
4. Save dashboard

**Note:** Prometheus alerts are defined in `alert_rules.yml` and managed via Alertmanager. Grafana alerts are independent.

---

## Summary

| Aspect | Value |
|--------|-------|
| Port | 3001 |
| Default login | admin / grafana_dev |
| Datasource | Prometheus (http://prometheus:9090) |
| Dashboards | 2 (Sensor Operations, ML Performance) |
| Auto-refresh | 30 seconds |
| Time range | 24 hours |

Grafana provides real-time visibility into sensor health, data pipeline performance, and ML model behavior.