from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mlops.dataset_pipeline import build_dataset_from_database
from mlops.promotion import decide_promotion, load_production_rmse, promote_model
from mlops.training import (
    choose_best_run,
    log_training_to_mlflow,
    run_baseline_models,
    run_xgboost_training,
)

MLFLOW_REGISTERED_MODEL_NAME = os.getenv(
    "MLFLOW_REGISTERED_MODEL_NAME",
    "smart-irrigation-soil-moisture",
)
MODEL_SERVER_REST_URL = os.getenv("MODEL_SERVER_REST_URL", "http://model-server:8501")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CHANNEL_PREDICTIONS_NEW = os.getenv("REDIS_CHANNEL_PREDICTIONS_NEW", "predictions:new")


def _serialize_rows(rows):
    serialized = []
    for row in rows:
        serialized.append(
            {
                key: value.isoformat() if hasattr(value, "isoformat") else value
                for key, value in row.items()
            }
        )
    return serialized


def prepare_dataset(**context):
    import asyncio
    from mlops.dataset_pipeline import build_dataset_from_database, log_dataset_to_mlflow

    dataset = asyncio.run(build_dataset_from_database())
    mlflow_info = log_dataset_to_mlflow(dataset)
    
    context["ti"].xcom_push(key="dataset_run_id", value=mlflow_info["run_id"])
    context["ti"].xcom_push(key="dataset_artifact_path", value=mlflow_info["artifact_path"])
    context["ti"].xcom_push(key="dataset_metadata", value=dataset.metadata)
    context["ti"].xcom_push(key="feature_columns", value=dataset.feature_columns)


def _load_dataset_from_mlflow(run_id: str, artifact_path: str, metadata: dict, feature_columns: list):
    import mlflow
    import json
    from mlops.dataset_pipeline import DatasetBuildResult
    
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    client = mlflow.tracking.MlflowClient()
    local_path = client.download_artifacts(run_id, artifact_path)
    
    with open(local_path, "r") as f:
        rows = json.load(f)
    
    return DatasetBuildResult(rows=rows, feature_columns=feature_columns, metadata=metadata)


def train_candidate_models(**context):
    run_id = context["ti"].xcom_pull(key="dataset_run_id", task_ids="prepare_dataset")
    artifact_path = context["ti"].xcom_pull(key="dataset_artifact_path", task_ids="prepare_dataset")
    metadata = context["ti"].xcom_pull(key="dataset_metadata", task_ids="prepare_dataset")
    feature_columns = context["ti"].xcom_pull(key="feature_columns", task_ids="prepare_dataset")

    dataset = _load_dataset_from_mlflow(run_id, artifact_path, metadata, feature_columns)

    baseline_runs = run_baseline_models(dataset)
    xgboost_run = run_xgboost_training(dataset)
    all_runs = [*baseline_runs, xgboost_run]
    best_run = choose_best_run(all_runs)

    context["ti"].xcom_push(
        key="baseline_runs",
        value=[{"model_name": run.model_name, "metrics": run.metrics.__dict__, "params": run.params} for run in baseline_runs],
    )
    context["ti"].xcom_push(
        key="best_run",
        value={"model_name": best_run.model_name, "metrics": best_run.metrics.__dict__, "params": best_run.params},
    )


def evaluate_and_register(**context):
    from dataclasses import asdict

    import mlflow
    from mlflow import MlflowClient

    from mlops.training import ModelMetrics, ModelRunResult

    run_id = context["ti"].xcom_pull(key="dataset_run_id", task_ids="prepare_dataset")
    artifact_path = context["ti"].xcom_pull(key="dataset_artifact_path", task_ids="prepare_dataset")
    metadata = context["ti"].xcom_pull(key="dataset_metadata", task_ids="prepare_dataset")
    feature_columns = context["ti"].xcom_pull(key="feature_columns", task_ids="prepare_dataset")
    
    baseline_runs_raw = context["ti"].xcom_pull(key="baseline_runs", task_ids="train_candidate_models")
    best_run_raw = context["ti"].xcom_pull(key="best_run", task_ids="train_candidate_models")

    dataset = _load_dataset_from_mlflow(run_id, artifact_path, metadata, feature_columns)
    
    baseline_runs = [
        ModelRunResult(
            model_name=run["model_name"],
            metrics=ModelMetrics(**run["metrics"]),
            params=run["params"],
        )
        for run in baseline_runs_raw
    ]
    best_run = ModelRunResult(
        model_name=best_run_raw["model_name"],
        metrics=ModelMetrics(**best_run_raw["metrics"]),
        params=best_run_raw["params"],
    )

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    client = MlflowClient()
    production_rmse = load_production_rmse(client, MLFLOW_REGISTERED_MODEL_NAME)
    decision = decide_promotion(best_run.metrics.rmse, production_rmse)
    mlflow_result = log_training_to_mlflow(dataset, baseline_runs, best_run)

    if decision.should_promote:
        promote_model(
            client,
            MLFLOW_REGISTERED_MODEL_NAME,
            mlflow_result["version"],
            decision.target_stage,
        )

    result = {
        "decision": asdict(decision),
        "best_run": asdict(best_run),
        "mlflow": mlflow_result,
    }
    context["ti"].xcom_push(key="promotion_result", value=result)


def export_training_summary(**context):
    result = context["ti"].xcom_pull(key="promotion_result", task_ids="evaluate_and_register")
    summary_dir = ROOT_DIR / "airflow" / "artifacts"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "latest_training_summary.json"
    summary_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return str(summary_path)


def scheduled_zone_predictions(**context):
    import asyncio
    import asyncpg
    import httpx
    import redis.asyncio as redis

    async def _run():
        conn = await asyncpg.connect(os.getenv("DATABASE_URL", "postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db"))
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        try:
            zones = await conn.fetch("SELECT DISTINCT zone_id, sensor_id FROM sensor_metadata WHERE active = TRUE")
            async with httpx.AsyncClient(timeout=30.0) as client:
                for row in zones:
                    async with conn.transaction():
                        # Get latest sensor reading
                        latest_reading = await conn.fetchrow(
                            "SELECT moisture FROM sensor_readings WHERE zone_id = $1 AND sensor_id = $2 ORDER BY timestamp DESC LIMIT 1",
                            row["zone_id"],
                            row["sensor_id"],
                        )
                        if not latest_reading:
                            continue

                        # Get latest feature references
                        feature_rows = await conn.fetch(
                            """
                            SELECT feature_name, window_size, feature_value
                            FROM feature_references
                            WHERE zone_id = $1 AND sensor_id = $2
                            ORDER BY computed_at DESC
                            """,
                            row["zone_id"],
                            row["sensor_id"],
                        )

                        # Assemble feature vector: [current_moisture, current_temperature]
                        # Matches current model version 3 expected features
                        features = [
                            float(latest_reading["moisture"]),
                            0.0 # Default temperature for now
                        ]

                        response = await client.post(
                            f"{MODEL_SERVER_REST_URL}/v1/predict",
                            json={
                                "zone_id": row["zone_id"],
                                "sensor_id": row["sensor_id"],
                                "features": features,
                            },
                        )

                        response.raise_for_status()
                        payload = response.json()
                        await conn.execute(
                            """
                            INSERT INTO model_predictions (predicted_at, zone_id, model_version, prediction, confidence)
                            VALUES ($1, $2, $3, $4, $5)
                            """,
                            datetime.utcnow(),
                            row["zone_id"],
                            payload["model_version"],
                            payload["predicted_moisture"],
                            payload["confidence_interval"][1] - payload["confidence_interval"][0],
                        )
                        await redis_client.publish(
                            REDIS_CHANNEL_PREDICTIONS_NEW,
                            json.dumps(
                                {
                                    "zone_id": row["zone_id"],
                                    "sensor_id": row["sensor_id"],
                                    "prediction": payload["predicted_moisture"],
                                    "model_version": payload["model_version"],
                                    "predicted_at": datetime.utcnow().isoformat(),
                                }
                            ),
                        )
        finally:
            await conn.close()
            await redis_client.close()

    asyncio.run(_run())


default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="smart_irrigation_model_training",
    default_args=default_args,
    description="Feature refresh, model training, evaluation, and MLflow promotion.",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["mlops", "training"],
) as dag:
    prepare_dataset_task = PythonOperator(
        task_id="prepare_dataset",
        python_callable=prepare_dataset,
    )

    train_candidate_models_task = PythonOperator(
        task_id="train_candidate_models",
        python_callable=train_candidate_models,
    )

    evaluate_and_register_task = PythonOperator(
        task_id="evaluate_and_register",
        python_callable=evaluate_and_register,
    )

    export_training_summary_task = PythonOperator(
        task_id="export_training_summary",
        python_callable=export_training_summary,
    )

    scheduled_zone_predictions_task = PythonOperator(
        task_id="scheduled_zone_predictions",
        python_callable=scheduled_zone_predictions,
    )

    prepare_dataset_task >> train_candidate_models_task >> evaluate_and_register_task >> export_training_summary_task >> scheduled_zone_predictions_task
