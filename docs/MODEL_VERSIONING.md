# Model & Data Versioning with MinIO

## Overview

MinIO provides S3-compatible object storage for the Smart Irrigation System's MLOps pipeline. It serves as the backend for:
- **MLflow** - Stores model artifacts, datasets, and experiment files
- **Versioning** - Maintains history of all models and datasets

**Location:** Docker container `minio`

**Access:**
- API: http://localhost:9000
- Console: http://localhost:9001

---

## Architecture

### System Integration

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MINIO STORAGE                                     │
│                                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐   │
│  │   ml-artifacts/     │  │   datasets/         │  │   exports/          │   │
│  │                     │  │                     │  │                     │   │
│  │  - model versions   │  │  - training data    │  │  - summaries        │   │
│  │  - sklearn models   │  │  - dataset JSON     │  │  - reports          │   │
│  │  - model cards      │  │  - metadata         │  │                     │   │
│  │                     │  │                     │  │                     │   │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘   │
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
         ┌──────────────────┐      ┌──────────────────┐
         │     MLFLOW       │      │   OTHER SERVICES │
         │                  │      │                  │
         │ - Experiment     │      │ - Model Server   │
         │   tracking      │      │ - Airflow DAG    │
         │ - Model         │      │ - Dashboard      │
         │   registry      │      │                  │
         │ - Version       │      │                  │
         │   management    │      │                  │
         └──────────────────┘      └──────────────────┘
```

### MLflow with MinIO

**MLflow Configuration (docker-compose.yml):**
```yaml
mlflow:
  environment:
    MLFLOW_S3_ENDPOINT_URL: ${MLFLOW_S3_ENDPOINT_URL}
    AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
    AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
  command: >
    mlflow server
    --backend-store-uri ${DATABASE_URL}
    --default-artifact-root s3://${MLFLOW_ARTIFACT_BUCKET}/
```

**Environment Variables (from .env):**
```
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
MLFLOW_ARTIFACT_BUCKET=ml-artifacts
```

---

## Storage Structure

### Buckets

| Bucket | Purpose | Contents |
|--------|---------|----------|
| `ml-artifacts` | ML model storage | Trained models, sklearn/XGBoost artifacts |
| `datasets` | Training datasets | Versioned training data |
| `exports` | Export artifacts | Training summaries, reports |

### Artifacts Path Structure

```
ml-artifacts/
├── smart-irrigation-soil-moisture/
│   ├── <run_id>/
│   │   ├── model/
│   │   │   ├── model.pkl
│   │   │   ├── conda.yaml
│   │   │   ├── requirements.txt
│   │   │   └── MLmodel
│   │   ├── best_run.json
│   │   └── model_card.md
│   └── ...
│
datasets/
├── smart-irrigation-training-dataset/
│   ├── <run_id>/
│   │   └── dataset.json
│   └── ...

exports/
└── training-summaries/
    └── ...
```

> **Note:** Both MLflow and MinIO are involved in storing artifacts. When `mlflow.log_artifact()` is called, MLflow acts as the interface/manager while MinIO serves as the actual S3-compatible storage backend. All files (models, datasets, summaries) flow through MLflow APIs but are physically stored in MinIO buckets.

---

## Versioning Mechanism

### Model Versioning

#### 1. Training Creates New Version

When `log_training_to_mlflow()` runs in Airflow DAG:

```python
# mlops/training.py
mlflow.sklearn.log_model(
    sk_model=pipeline,
    artifact_path="model",
    registered_model_name=settings.mlflow_registered_model_name,
    registered_model_version={"version": mlflow_result["version"]},
)
```

#### 2. Version Stages

Models can be promoted through stages:

| Stage | Description | Use Case |
|-------|-------------|----------|
| `None` | Staging | New training, not yet deployed |
| `Staging` | Testing | Validating before production |
| `Production` | Live | Currently serving predictions |
| `Archived` | Retired | Old models kept for rollback |

#### 3. Promotion Decision

```python
# mlops/promotion.py
def decide_promotion(new_rmse: float, production_rmse: float) -> PromotionDecision:
    if new_rmse < production_rmse:
        return PromotionDecision(should_promote=True, target_stage="Production")
    elif new_rmse < production_rmse * 1.1:
        return PromotionDecision(should_promote=True, target_stage="Staging")
    else:
        return PromotionDecision(should_promote=False, target_stage=None)
```

### Dataset Versioning

Dataset versioning follows the same MLflow → MinIO pattern as model versioning.

#### 1. Dataset Creation

```python
# mlops/dataset_pipeline.py
def log_dataset_to_mlflow(dataset: DatasetBuildResult) -> dict[str, Any]:
    mlflow_dataset = mlflow.data.from_pandas(
        df,
        name=settings.mlflow_dataset_name,
    )

    with mlflow.start_run(run_name="dataset-build") as run:
        # Log dataset as MLflow input (tracks lineage)
        mlflow.log_input(mlflow_dataset, context="training")

        # Log metadata (query params, time range, source)
        mlflow.log_params(dataset.metadata)

        # Log dataset metrics
        mlflow.log_metric("dataset_rows", len(dataset.rows))
        mlflow.log_metric("dataset_features", len(dataset.feature_columns))

        # Save and log dataset JSON to MinIO (via MLflow API)
        tmp_path = Path(tmpdir) / "dataset.json"
        dataset.to_json(tmp_path)
        mlflow.log_artifact(str(tmp_path))  # → Physically stored in MinIO

    return {
        "run_id": run.info.run_id,
        "artifact_path": "dataset.json",
    }
```

**Data Flow:**
```
mlflow.log_artifact(str(tmp_path))
         │
         ▼
    ┌────────────┐
    │  MLflow    │  (manages the interface)
    │   API      │
    └─────┬──────┘
          │ Stores to (via S3 protocol)
          ▼
    ┌────────────┐
    │   MinIO    │  (actual storage: s3://datasets/...)
    │  Storage   │
    └────────────┘
```

#### 2. Dataset Metadata

Each dataset version captures:
- Number of rows
- Feature columns
- Time range
- Source query parameters
- Full raw data (dataset.json)

#### 3. Dataset Lineage

Every model version in MLflow is linked to its dataset version through MLflow's **dataset input tracking**:

- When you train a model, MLflow records which dataset was used
- You can trace back: `Model v5` → `was trained on` → `Dataset from run <run_id>`
- This enables full reproducibility

To view in MLflow UI:
1. Go to **Experiments** → Select an experiment
2. Click on a run
3. Look at **Datasets** section (shows input datasets with version)
4. Look at **Artifacts** → `dataset.json` (actual data stored in MinIO)

---

## Usage in Pipeline

### Airflow DAG Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          AIRFLOW DAG                                           │
│                                                                                 │
│  1. prepare_dataset                                                            │
│     └─► Calls build_dataset_from_database()                                     │
│     └─► Calls log_dataset_to_mlflow() ──► MinIO: datasets/                     │
│     └─► Pushes run_id to XCom                                                  │
│                                                                                 │
│  2. train_candidate_models                                                     │
│     └─► Pulls dataset from MinIO (via run_id)                                  │
│     └─► Trains XGBoost model                                                   │
│     └─► Calls log_training_to_mlflow() ──► MinIO: ml-artifacts/                │
│                                                                                 │
│  3. evaluate_and_register                                                      │
│     └─► Compares with production model                                         │
│     └─► Promotes if better (updates version stage)                             │
│                                                                                 │
│  4. scheduled_zone_predictions                                                 │
│     └─► Loads model from MLflow (from MinIO)                                   │
│     └─► Runs inference                                                         │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         MINIO STORAGE                                           │
│                                                                                 │
│  Bucket: ml-artifacts                                                          │
│  ├── smart-irrigation-soil-moisture/                                          │
│  │   └── <run_id>/                                                             │
│  │       ├── model/  (sklearn model + metadata)                               │
│  │       ├── best_run.json                                                    │
│  │       └── model_card.md                                                    │
│  └── ...                                                                       │
│                                                                                 │
│  Bucket: datasets                                                              │
│  └── smart-irrigation-training-dataset/                                        │
│      └── <run_id>/                                                             │
│          └── dataset.json                                                      │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       MODEL SERVER                                             │
│                                                                                 │
│  At startup:                                                                   │
│  1. Loads production model from MLflow (from MinIO)                           │
│  2. Serves predictions via REST API                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Accessing MinIO

### Via Console (Web UI)

1. Open http://localhost:9001
2. Login with credentials from `.env`:
   - Username: `minioadmin` (or from `MINIO_ROOT_USER`)
   - Password: `minioadmin` (or from `MINIO_ROOT_PASSWORD`)

### Via AWS CLI

```bash
# Configure AWS CLI for MinIO
aws configure set aws_access_key_id minioadmin
aws configure set aws_secret_access_key minioadmin
aws configure set region us-east-1

# List buckets
aws --endpoint-url http://localhost:9000 s3 ls

# List objects in bucket
aws --endpoint-url http://localhost:9000 s3 ls s3://ml-artifacts/

# Download model artifact
aws --endpoint-url http://localhost:9000 s3 cp s3://ml-artifacts/smart-irrigation-soil-moisture/<run_id>/model/ ./model/ --recursive
```

### Via Python (boto3)

```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin',
)

# List buckets
response = s3.list_buckets()
print([b['Name'] for b in response['Buckets']])

# List objects
response = s3.list_objects_v2(Bucket='ml-artifacts')
print([o['Key'] for o in response.get('Contents', [])])
```

---

## MLflow UI

Access MLflow at http://localhost:5000

### Features

1. **Experiments** - View all training runs
2. **Runs** - Individual run details with metrics
3. **Models** - Registered model versions with stages
4. **Artifacts** - Browse stored files in MinIO

### Model Registry

```
smart-irrigation-soil-moisture
├── Version 1 (Production)
│   - Created: 2026-01-01
│   - RMSE: 5.2
│   - Stage: Production
├── Version 2 (Staging)
│   - Created: 2026-01-15
│   - RMSE: 4.8
│   - Stage: Staging
└── Version 3 (None)
    - Created: 2026-02-01
    - RMSE: 4.5
    - Stage: None
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ROOT_USER` | `minioadmin` | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO admin password |
| `MLFLOW_S3_ENDPOINT_URL` | `http://minio:9000` | MLflow → MinIO connection |
| `AWS_ACCESS_KEY_ID` | `minioadmin` | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | `minioadmin` | S3 secret key |
| `MLFLOW_ARTIFACT_BUCKET` | `ml-artifacts` | Default artifact bucket |

### Docker Compose Service

```yaml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  ports:
    - "9000:9000"    # API
    - "9001:9001"    # Console
  volumes:
    - minio_data:/data
```

---

## Cleanup & Maintenance

### Pruning Old Runs

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Delete runs older than 30 days
for exp in client.list_experiments():
    for run in client.list_run_infos(exp.experiment_id):
        if run.end_time < (datetime.now() - timedelta(days=30)):
            client.delete_run(run.run_id)
```

### Deleting Old Model Versions

```python
client = MlflowClient()

# Delete old versions (keep last 5)
for version in client.get_model_version_download_links("smart-irrigation-soil-moisture"):
    if version.version < 5:
        client.delete_model_version("smart-irrigation-soil-moisture", version.version)
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Storage Backend | MinIO (S3-compatible) |
| ML Integration | MLflow artifact storage |
| Model Versioning | MLflow Model Registry |
| Dataset Versioning | MLflow dataset inputs |
| Access | MinIO Console (9001), MLflow UI (5000) |
| API | AWS S3 API via boto3 |

MinIO provides the foundation for reproducible MLOps by storing all model and dataset artifacts with full versioning support. MLflow manages the lifecycle from training to production deployment.