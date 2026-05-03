# Drift Monitoring Documentation

## Overview

The Drift Monitoring service detects when the ML model's predictions drift from expected behavior. It monitors:
1. **Data Drift** - Changes in input data distribution
2. **Concept Drift** - Changes in the relationship between inputs and outputs
3. **Model Performance** - Prediction error increases

When drift is detected, the service automatically triggers Airflow to retrain the model.

**Location:** `services/drift-monitor/src/`

**Port:** 8502

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DRIFT MONITOR SERVICE                                 │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Application                              │   │
│  │                                                                          │   │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                  │   │
│  │  │   /health   │   │  /metrics   │   │/v1/drift/   │                  │   │
│  │  │             │   │             │   │   status    │                  │   │
│  │  └─────────────┘   └─────────────┘   └──────┬──────┘                  │   │
│  │                                           │                           │   │
│  │                                           ▼                           │   │
│  │  ┌──────────────────────────────────────────────────────────────┐      │   │
│  │  │                    DriftMonitor Class                         │      │   │
│  │  │                                                              │      │   │
│  │  │  - scan()       : Detects drift                              │      │   │
│  │  │  - _fetch_prediction_window() : Gets prediction data        │      │   │
│  │  │  - summarize_drift() : Calculates drift metrics            │      │   │
│  │  │  - trigger_retraining_dag() : Triggers Airflow             │      │   │
│  │  └──────────────────────────────────────────────────────────────┘      │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                   Background Scan Loop (every 60 sec)                    │   │
│  │                                                                          │   │
│  │  while running:                                                          │   │
│  │    1. Fetch last 200 predictions (100 current, 100 reference)          │   │
│  │    2. Run drift detection algorithms                                   │   │
│  │    3. If drift detected:                                                │   │
│  │       - Publish to alerts:anomaly                                       │   │   │
│  │       - Trigger Airflow retraining                                      │   │
│  │    4. Sleep 60 seconds                                                  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            DATA SOURCES                                         │
│                                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                                │
│  │   TimescaleDB    │    │      Redis       │                                │
│  │                  │    │                  │                                │
│  │ model_predictions│    │  alerts:anomaly  │                                │
│  │ (last 24 hours) │    │    (output)       │                                │
│  └──────────────────┘    └──────────────────┘                                │
└───────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT                                                │
│                                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐        │
│  │   Redis Pub/Sub  │    │   Prometheus     │    │     Airflow      │        │
│  │                  │    │     Metrics      │    │   (retraining)   │        │
│  │ alerts:anomaly   │    │                  │    │                  │        │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘        │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Drift Detection Algorithms

### 1. Page-Hinkley Test

Used for detecting abrupt changes in the mean of a sequence.

```python
def page_hinkley(values: list[float], delta: float = 0.005, threshold: float = 0.5) -> tuple[float, bool]:
    """
    Page-Hinkley change detection test.

    Args:
        values: Sequence of values to test
        delta: Minor change allowance (default: 0.005)
        threshold: Detection threshold (default: 0.5)

    Returns:
        (score, detected): Score and whether drift was detected
    """
    mean_value = 0.0
    cumulative = 0.0
    min_cumulative = 0.0
    best_score = 0.0

    for index, value in enumerate(values, start=1):
        mean_value += (value - mean_value) / index
        cumulative += value - mean_value - delta
        min_cumulative = min(min_cumulative, cumulative)
        best_score = max(best_score, cumulative - min_cumulative)

    return best_score, best_score > threshold
```

**How it works:**
- Tracks cumulative sum of deviations from the running mean
- Detects when cumulative deviation exceeds threshold
- Returns score and boolean (drift detected if score > 0.5)

### 2. KL Divergence

Used for detecting distribution changes between reference and current data.

```python
def kl_divergence(reference: list[float], current: list[float], bins: int = 10) -> float:
    """
    Kullback-Leibler divergence between two distributions.

    Args:
        reference: Reference distribution (historical data)
        current: Current distribution to compare
        bins: Number of histogram bins (default: 10)

    Returns:
        KL divergence score (higher = more different)
    """
    # Create histograms
    ref_hist = [1e-6] * bins
    cur_hist = [1e-6] * bins

    # Fill histograms
    for value in reference:
        index = min(bins - 1, int((value - minimum) / bucket_width))
        ref_hist[index] += 1
    ...

    # Calculate KL divergence
    return sum(
        (cur / cur_total) * math.log((cur / cur_total) / (ref / ref_total))
        for ref, cur in zip(ref_hist, cur_hist)
    )
```

**How it works:**
- Creates histogram of reference and current distributions
- Measures information loss when using reference to encode current
- KL > 0.1 indicates significant distribution change

### 3. Prediction Error

Monitors the mean absolute error between predictions and actual values (if available).

```python
mean_error = sum(abs(a - c) for a, c in zip(actual, current)) / len(actual)
```

**How it works:**
- Compares predicted vs actual values
- If mean_error > 0.15 (15%), indicates model degradation

---

## Drift Summary

Combines all metrics into a single summary:

```python
def summarize_drift(reference: list[float], current: list[float], actual: list[float] | None = None) -> DriftSummary:
    score, detected = page_hinkley(current)
    divergence = kl_divergence(reference, current)
    mean_error = ...

    drift_detected = detected or divergence > 0.1 or mean_error > 0.15

    return DriftSummary(
        page_hinkley_score=score,
        kl_divergence=divergence,
        mean_error=mean_error,
        drift_detected=drift_detected,
    )
```

**Drift Detection Logic:**
```
Drift detected if ANY of:
├── Page-Hinkley score > 0.5 (detected)
├── KL divergence > 0.1 (distribution change)
└── Mean error > 0.15 (prediction degradation)
```

---

## Scan Process

### 1. Fetch Data Window

```python
async def _fetch_prediction_window(self) -> tuple[list[float], list[float]]:
    # Get last 24 hours of predictions
    rows = await conn.fetch("""
        SELECT prediction, confidence
        FROM model_predictions
        WHERE predicted_at >= $1
        ORDER BY predicted_at DESC
        LIMIT 200
    """, since)

    # Split into:
    # - current: most recent 100 predictions
    # - reference: previous 100 predictions
    current = [float(row["prediction"]) for row in rows[:100]]
    reference = [float(row["prediction"]) for row in rows[100:200]]
    return reference, current
```

### 2. Run Detection

```python
async def scan(self) -> DriftSummary:
    reference, current = await self._fetch_prediction_window()
    summary = summarize_drift(reference, current)

    # Update Prometheus metrics
    PAGE_HINKLEY_GAUGE.set(summary.page_hinkley_score)
    KL_GAUGE.set(summary.kl_divergence)
    ERROR_GAUGE.set(summary.mean_error)

    # If drift detected, take action
    if summary.drift_detected:
        # Publish to Redis
        await self.redis_client.publish(REDIS_CHANNEL_ALERTS_ANOMALY, json.dumps(...))
        # Trigger retraining
        await self.trigger_retraining_dag()

    return summary
```

### 3. Trigger Retraining

```python
async def trigger_retraining_dag(self) -> None:
    # Cooldown: don't trigger more than once per hour
    if (now - self._last_triggered_at) < timedelta(hours=1):
        return

    # Call Airflow API
    response = await client.post(
        f"{AIRFLOW_URL}/api/v1/dags/smart_irrigation_model_training/dagRuns",
        json={"conf": {}},
        auth=(AIRFLOW_ADMIN_USER, AIRFLOW_ADMIN_PASSWORD),
    )
```

---

## API Endpoints

### GET /health

Health check.

```bash
curl http://localhost:8502/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "drift-monitor"
}
```

### GET /metrics

Prometheus metrics.

```bash
curl http://localhost:8502/metrics
```

**Metrics:**
- `drift_monitor_page_hinkley_score` - Latest Page-Hinkley score
- `drift_monitor_kl_divergence` - Latest KL divergence
- `drift_monitor_mean_error` - Latest mean error

### GET /v1/drift/status

Get current drift status.

```bash
curl http://localhost:8502/v1/drift/status
```

**Response (No drift):**
```json
{
  "page_hinkley_score": 0.12,
  "kl_divergence": 0.03,
  "mean_error": 0.05,
  "drift_detected": false
}
```

**Response (Drift detected):**
```json
{
  "page_hinkley_score": 0.73,
  "kl_divergence": 0.15,
  "mean_error": 0.22,
  "drift_detected": true
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DRIFT_MONITOR_PORT` | `8502` | Service port |
| `DRIFT_SCAN_INTERVAL_SECONDS` | `60` | Scan every 60 seconds |
| `DATABASE_URL` | `postgresql://...` | Database connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `REDIS_CHANNEL_ALERTS_ANOMALY` | `alerts:anomaly` | Alert output channel |
| `AIRFLOW_URL` | `http://airflow:8080` | Airflow API URL |
| `AIRFLOW_ADMIN_USER` | `admin` | Airflow username |
| `AIRFLOW_ADMIN_PASSWORD` | `airflow_dev` | Airflow password |

### Docker Configuration

```yaml
drift-monitor:
  image: drift-monitor:latest
  ports:
    - "8502:8502"
  environment:
    - DRIFT_SCAN_INTERVAL_SECONDS=60
    - AIRFLOW_URL=http://airflow:8080
  depends_on:
    - timescaledb
    - redis
    - airflow
```

---

## Drift Detection Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Page-Hinkley Score | > 0.5 | Mean shift detected |
| KL Divergence | > 0.1 | Distribution change detected |
| Mean Error | > 0.15 | Prediction accuracy degraded |

---

## Alert Output

When drift is detected, an alert is published to Redis:

```json
{
  "type": "model_drift",
  "detected_at": "2026-05-03T12:00:00+00:00",
  "page_hinkley_score": 0.73,
  "kl_divergence": 0.15,
  "mean_error": 0.22,
  "drift_detected": true
}
```

---

## Integration

### With Airflow

When drift is detected, the service triggers Airflow DAG:

```
Drift Monitor detects drift
        │
        ▼
POST to Airflow API /api/v1/dags/smart_irrigation_model_training/dagRuns
        │
        ▼
Airflow starts new DAG run
        │
        ▼
Model retraining pipeline executes
        │
        ▼
New model promoted to Production (if better)
```

### With Notification Service

The `alerts:anomaly` channel is consumed by the notification service to alert users.

---

## Cooldown Mechanism

To prevent excessive retraining, there's a 1-hour cooldown between triggers:

```python
if self._last_triggered_at and (now - self._last_triggered_at) < timedelta(hours=1):
    self.logger.info("Skipping Airflow trigger (cooldown active).")
    return
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `drift_monitor_page_hinkley_score` | Gauge | Latest Page-Hinkley score |
| `drift_monitor_kl_divergence` | Gauge | Latest KL divergence |
| `drift_monitor_mean_error` | Gauge | Latest mean prediction error |

---

## Monitoring

### Check Drift Status

```bash
curl http://localhost:8502/v1/drift/status | jq
```

### View in Grafana

Import the drift monitoring dashboard to visualize:
- Page-Hinkley score over time
- KL divergence trends
- Mean error history
- Alert frequency

---

## Testing

### Manual Drift Detection Test

```python
from drift_detector import page_hinkley, kl_divergence, summarize_drift

# Test Page-Hinkley
values = [0.1] * 100 + [0.5] * 50  # Sudden shift at index 100
score, detected = page_hinkley(values)
print(f"Score: {score}, Detected: {detected}")

# Test KL divergence
reference = [random.gauss(50, 10) for _ in range(1000)]
current = [random.gauss(60, 15) for _ in range(1000)]  # Different distribution
divergence = kl_divergence(reference, current)
print(f"KL Divergence: {divergence}")

# Test full summary
summary = summarize_drift(reference, current)
print(f"Drift Detected: {summary.drift_detected}")
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + Uvicorn |
| Detection | Page-Hinkley + KL Divergence + Mean Error |
| Scan Interval | Every 60 seconds |
| Data Window | Last 200 predictions (100 current, 100 reference) |
| Triggers | Airflow DAG retraining + Redis alert |
| Cooldown | 1 hour between triggers |
| Port | 8502 |
| Alert Channel | `alerts:anomaly` |

The Drift Monitoring service ensures model quality by automatically detecting when predictions drift from expected behavior and triggering retraining to maintain accuracy.