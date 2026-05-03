# MLOps Pipeline: Smart Irrigation

## Overview
The Smart Irrigation System integrates MLOps best practices to ensure models are trained on high-quality data, served reliably, and monitored for performance degradation.

## 1. Feature Store Architecture
We use a **Versioned Feature Store** implemented in TimescaleDB (`feature_references`).
- **Engine**: The `feature-engineering` service computes rolling metrics across windows (30m, 1h, 3h, 24h).
- **Versioning**: Each feature record is tagged with a `model_version` (e.g., `v1`, `v2_candidate`).
- **Consistency**: The same engineering logic is used for both training (batch) and inference (streaming), preventing training-serving skew.

## 2. Model Lifecycle

### Dataset Versioning & Storage
To ensure that models can always be traced back to the data they were trained on, we store every training dataset in **MinIO** (Object Storage).
- **Versioning**: Each training run gets its own unique dataset version stored in the `mlflow-artifacts` bucket.
- **Traceability**: The system automatically tracks which dataset version was used for each model. This allows you to "time travel" and retrain or audit models with the exact same data later.
- **Efficiency**: Downstream tasks pull data directly from MinIO, which is more stable and scalable for large datasets than passing data through temporary memory or databases.

### Scalable Pipeline
The training pipeline is designed to handle large volumes of sensor data without slowing down:
- **Fast Data Preparation**: The logic for building training datasets is optimized to process millions of records efficiently.
- **Traceable Experiments**: We use **MLflow** to track every training attempt, including the exact features used and the resulting performance metrics.
- **Automated Retraining**: Airflow manages the end-to-end flow from data gathering to model registration.

### Experiment Tracking
...

## 3. Data Quality & Malfunction Detection
Before data is used for inference or training, it passes through the **Data Quality Framework**:
- **Plausibility Check**: Hard physical limits (e.g., moisture cannot be > 100%).
- **Malfunction detection**: Identifies stuck sensors or unrealistic jumps that would corrupt ML predictions.
- **Health Filtering**: The system can be configured to ignore readings from sensors marked as `unhealthy` in `v_sensor_health`.

## 4. Monitoring & Drift
- **Shadow Deployment**: New model versions can be deployed in "shadow mode," where they run alongside the champion model. Results are stored in `shadow_predictions` for comparison without affecting irrigation logic.
- **Shadow Comparison**: The `v_shadow_comparison` view calculates deltas between models to validate new candidates.
- **Drift Monitoring**: The `drift-monitor` service (implementation ongoing) tracks statistical changes in input distributions (Moisture Mean Shift) and output residuals.

## 5. Feature Dictionary (Agricultural)
| Feature | Logic | Use Case |
| :--- | :--- | :--- |
| `mean_moisture` | Rolling average | Baseline soil hydration. |
| `roc_moisture` | Rate of change | How fast the soil is drying (evapotranspiration). |
| `std_moisture` | Standard deviation | Sensor stability / noisy data detection. |
| `mean_temp` | Rolling average | Thermal load on crops. |
