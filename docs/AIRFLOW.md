# Airflow DAG Documentation

## Overview

Apache Airflow orchestrates the MLOps pipeline for the Smart Irrigation System. It handles:
1. Dataset preparation from sensor data
2. Model training (baseline + XGBoost)
3. Model evaluation and promotion to production
4. **Prediction generation** (scheduled, not real-time)

**Location:** `airflow/dags/smart_irrigation_dags.py`

---

## Two Prediction Paths

The system has **two ways** to generate predictions:

### 1. Real-Time Predictions (Primary)

```
Feature Engineering → [features:computed] → Model Server → [predictions:new] → Irrigation Controller
```

- Triggered when new sensor data arrives
- Model Server subscribes to Redis `features:computed`
- Runs inference immediately
- Publishes to `predictions:new` channel

### 2. Scheduled Predictions (Airflow)

```
Airflow DAG: scheduled_zone_predictions → model-server API → [predictions:new] → Irrigation Controller
```

- Runs daily at 2:00 AM UTC
- Queries all active zones from database
- Calls model-server REST API (`/v1/predict`)
- Stores predictions in `model_predictions` table
- Publishes to `predictions:new` channel

| Aspect | Real-Time | Scheduled (Airflow) |
|--------|-----------|---------------------|
| Trigger | New sensor data | Cron (daily 2am) |
| Latency | ~10-15 seconds | Minutes |
| Use Case | Immediate irrigation | Batch predictions |
| Method | Redis subscription | REST API call |

---

## DAG Configuration

```python
with DAG(
    dag_id="smart_irrigation_model_training",
    description="Feature refresh, model training, evaluation, and MLflow promotion.",
    schedule="0 2 * * *",  # Runs daily at 2:00 AM UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["mlops", "training"],
) as dag:
```

| Property | Value | Description |
|----------|-------|-------------|
| dag_id | `smart_irrigation_model_training` | Unique identifier |
| schedule | `0 2 * * *` | Cron: Daily at 2:00 AM UTC |
| catchup | `false` | Don't run missed DAGs |
| retries | 1 | Retry failed tasks once |
| retry_delay | 5 minutes | Wait between retries |

---

## Task Flow

```
┌─────────────────────────┐
│   prepare_dataset       │  ← Build dataset from TimescaleDB sensor data
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  train_candidate_models │  ← Train baseline + XGBoost models
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ evaluate_and_register   │  ← Evaluate, compare with production, promote
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ export_training_summary │  ← Save training results to JSON
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ scheduled_zone_predictions│ ← Generate predictions, publish to Redis
└─────────────────────────┘
```

---

## Task Details

### 1. prepare_dataset

**Purpose:** Fetch sensor data from TimescaleDB and create a training dataset.

```python
def prepare_dataset(**context):
    dataset = asyncio.run(build_dataset_from_database())
    mlflow_info = log_dataset_to_mlflow(dataset)
    
    # Push to XCom for downstream tasks
    context["ti"].xcom_push(key="dataset_run_id", value=mlflow_info["run_id"])
    context["ti"].xcom_push(key="dataset_artifact_path", value=mlflow_info["artifact_path"])
    context["ti"].xcom_push(key="dataset_metadata", value=dataset.metadata)
    context["ti"].xcom_push(key="feature_columns", value=dataset.feature_columns)
```

**What it does:**
1. Calls `build_dataset_from_database()` from `mlops/dataset_pipeline.py`
2. Fetches sensor readings, feature references, and predictions
3. Creates a structured dataset with features and labels
4. Logs the dataset to MLflow as an artifact
5. Passes dataset info via XCom to next task

**Outputs (XCom):**
- `dataset_run_id`: MLflow run ID for the dataset
- `dataset_artifact_path`: Path to dataset artifact
- `dataset_metadata`: Dataset metadata
- `feature_columns`: List of feature column names

---

### 2. train_candidate_models

**Purpose:** Train multiple models and select the best one.

```python
def train_candidate_models(**context):
    dataset = _load_dataset_from_mlflow(run_id, artifact_path, metadata, feature_columns)
    
    baseline_runs = run_baseline_models(dataset)
    xgboost_run = run_xgboost_training(dataset)
    all_runs = [*baseline_runs, xgboost_run]
    best_run = choose_best_run(all_runs)
    
    context["ti"].xcom_push(key="baseline_runs", value=...)
    context["ti"].xcom_push(key="best_run", value=...)
```

**What it does:**
1. Loads dataset from MLflow (created by previous task)
2. Trains baseline models (simple heuristics for comparison)
3. Trains XGBoost model with hyperparameter tuning
4. Compares all models using RMSE metric
5. Selects the best performing model

**Models trained:**
- Baseline models (simple heuristics)
- XGBoost (gradient boosted decision trees)

**Outputs (XCom):**
- `baseline_runs`: Results from all baseline models
- `best_run`: The best performing model result

---

### 3. evaluate_and_register

**Purpose:** Evaluate model against production and promote if better.

```python
def evaluate_and_register(**context):
    production_rmse = load_production_rmse(client, MLFLOW_REGISTERED_MODEL_NAME)
    decision = decide_promotion(best_run.metrics.rmse, production_rmse)
    mlflow_result = log_training_to_mlflow(dataset, baseline_runs, best_run)
    
    if decision.should_promote:
        promote_model(client, MLFLOW_REGISTERED_MODEL_NAME, mlflow_result["version"], decision.target_stage)
```

**What it does:**
1. Loads current production model RMSE from MLflow
2. Compares new model RMSE with production RMSE
3. Decides whether to promote (if new model is better)
4. Logs training results to MLflow
5. Promotes model to appropriate stage (Staging/Production)

**Promotion Logic:**
```
if new_rmse < production_rmse:
    promote to Production
elif new_rmse < production_rmse * 1.1:
    promote to Staging
else:
    don't promote
```

**Outputs (XCom):**
- `promotion_result`: Contains decision, best_run, and MLflow info

---

### 4. export_training_summary

**Purpose:** Save training summary to a JSON file for external access.

```python
def export_training_summary(**context):
    result = context["ti"].xcom_pull(key="promotion_result", task_ids="evaluate_and_register")
    summary_dir = ROOT_DIR / "airflow" / "artifacts"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "latest_training_summary.json"
    summary_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return str(summary_path)
```

**What it does:**
1. Retrieves promotion result from previous task
2. Creates `airflow/artifacts` directory if not exists
3. Writes summary JSON to `latest_training_summary.json`

**Output file:** `airflow/artifacts/latest_training_summary.json`

---

### 5. scheduled_zone_predictions

**Purpose:** Generate predictions for all zones and publish to Redis for irrigation controller.

```python
def scheduled_zone_predictions(**context):
    async def _run():
        conn = await asyncpg.connect(DATABASE_URL)
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        zones = await conn.fetch("SELECT DISTINCT zone_id, sensor_id FROM sensor_metadata WHERE active = TRUE")
        
        for row in zones:
            # Get latest sensor reading
            latest_reading = await conn.fetchrow(
                "SELECT moisture FROM sensor_readings WHERE zone_id = $1 AND sensor_id = $2 ORDER BY timestamp DESC LIMIT 1",
                row["zone_id"], row["sensor_id"]
            )
            
            # Call model-server for prediction
            response = await client.post(f"{MODEL_SERVER_REST_URL}/v1/predict", json={...})
            payload = response.json()
            
            # Store prediction in database
            await conn.execute("INSERT INTO model_predictions ...")
            
            # PUBLISH to Redis
            await redis_client.publish(REDIS_CHANNEL_PREDICTIONS_NEW, json.dumps({...}))
```

**What it does:**
1. Fetches all active zones and sensors from database
2. For each zone/sensor:
   - Gets latest sensor reading
   - Calls model-server for prediction
   - Stores prediction in `model_predictions` table
   - **Publishes to Redis `predictions:new` channel**

**Key point:** This task bridges ML predictions to the irrigation controller via Redis pub/sub.

**Redis message format:**
```json
{
  "zone_id": "2",
  "sensor_id": "2-s1",
  "prediction": 36.66,
  "model_version": "1",
  "predicted_at": "2026-05-03T02:00:00"
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db` | Database connection |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow server URL |
| `MLFLOW_REGISTERED_MODEL_NAME` | `smart-irrigation-soil-moisture` | Model name in MLflow |
| `MODEL_SERVER_REST_URL` | `http://model-server:8501` | Model server API |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `REDIS_CHANNEL_PREDICTIONS_NEW` | `predictions:new` | Channel for predictions |

---

## Running the DAG

### Manual Trigger

```bash
# Via Airflow CLI
docker exec airflow airflow dags trigger smart_irrigation_model_training

# Via Airflow UI
# 1. Open http://localhost:8082
# 2. Find "smart_irrigation_model_training" DAG
# 3. Click "Play" button to trigger
```

### Check DAG Runs

```bash
docker exec airflow airflow dags list-runs -d smart_irrigation_model_training
```

### Test Individual Task

```bash
# Test the predictions task with a specific execution date
docker exec airflow airflow tasks test smart_irrigation_model_training scheduled_zone_predictions 2026-05-03
```

---

## Output Artifacts

### Training Summary JSON

Location: `airflow/artifacts/latest_training_summary.json`

Example content:
```json
{
  "decision": {
    "should_promote": true,
    "target_stage": "Production",
    "new_rmse": 5.2,
    "production_rmse": 6.1
  },
  "best_run": {
    "model_name": "XGBoost",
    "metrics": {"rmse": 5.2, "mae": 3.1, "r2": 0.89},
    "params": {"max_depth": 6, "learning_rate": 0.1}
  },
  "mlflow": {
    "run_id": "abc123",
    "version": 5
  }
}
```

---

## Integration with Other Components

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         AIRFLOW DAG                                        │
│                                                                        │
│  1. prepare_dataset ──► Pulls from:                                     │
│     - sensor_readings (TimescaleDB)                                     │
│     - feature_references (TimescaleDB)                                 │
│     - model_predictions (TimescaleDB)                                   │
│                                                                        │
│  2. train_candidate_models ──► Uses:                                    │
│     - Dataset from prepare_dataset                                      │
│     - MLflow for experiment tracking                                    │
│                                                                        │
│  3. evaluate_and_register ──► Uses:                                     │
│     - MLflow for model registry                                         │
│     - Compares with current production model                           │
│                                                                        │
│  4. scheduled_zone_predictions ──► Publishes to:                         │
│     - Redis: predictions:new                                           │
│     - TimescaleDB: model_predictions                                   │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 │ Redis: predictions:new
                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                   IRRIGATION-CONTROLLER                                   │
│                                                                        │
│ - Subscribes to predictions:new                                         │
│ - Triggers irrigation based on thresholds                               │
│ - Auto-completes events after 5 seconds                                │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary

| Task | Function | Output |
|------|----------|--------|
| prepare_dataset | Build training dataset from DB | Dataset in MLflow |
| train_candidate_models | Train baseline + XGBoost | Best model selection |
| evaluate_and_register | Compare with production, promote | Model promotion |
| export_training_summary | Save summary JSON | JSON file |
| scheduled_zone_predictions | Generate and publish predictions | Redis message |

The Airflow DAG orchestrates the complete ML lifecycle from data preparation to model serving, with the final task bridging to the irrigation controller via Redis. |