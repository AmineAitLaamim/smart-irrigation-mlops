from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MlopsSettings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db",
    )
    mlflow_tracking_uri: str = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    mlflow_experiment_name: str = os.getenv(
        "MLFLOW_EXPERIMENT_NAME",
        "smart-irrigation-soil-moisture",
    )
    mlflow_registered_model_name: str = os.getenv(
        "MLFLOW_REGISTERED_MODEL_NAME",
        "smart-irrigation-soil-moisture",
    )
    mlflow_dataset_name: str = os.getenv(
        "MLFLOW_DATASET_NAME",
        "smart-irrigation-training-dataset",
    )
    feature_model_version: str = os.getenv("FEATURE_MODEL_VERSION", "v1")
    target_horizon_minutes: int = int(os.getenv("ML_TARGET_HORIZON_MINUTES", "60"))
    outlier_zscore_threshold: float = float(
        os.getenv("OUTLIER_ZSCORE_THRESHOLD", "3.0")
    )


settings = MlopsSettings()

