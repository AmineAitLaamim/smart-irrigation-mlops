from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from .dataset_pipeline import (
    DatasetBuildResult,
    build_dataset_from_database,
    chronological_split,
    time_aware_cv_slices,
)
from .evaluation import summarize_evaluation, write_evaluation_report
from .metrics import ModelMetrics, compute_metrics
from .settings import settings

MODEL_CARD_PATH = Path("docs/model_cards/soil_moisture_model.md")


@dataclass(frozen=True)
class ModelRunResult:
    model_name: str
    metrics: ModelMetrics
    params: dict[str, Any]


def _require_training_stack() -> dict[str, Any]:
    try:
        import mlflow
        import numpy as np
        import pandas as pd
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        from xgboost import XGBRegressor
    except ImportError as exc:
        raise RuntimeError(
            "Training requires mlflow, numpy, pandas, scikit-learn, and xgboost."
        ) from exc

    return {
        "mlflow": mlflow,
        "np": np,
        "pd": pd,
        "LinearRegression": LinearRegression,
        "RandomForestRegressor": RandomForestRegressor,
        "XGBRegressor": XGBRegressor,
        "mean_absolute_error": mean_absolute_error,
        "mean_squared_error": mean_squared_error,
        "r2_score": r2_score,
    }


def select_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    excluded = {
        "zone_id",
        "sensor_id",
        "timestamp",
        "target_timestamp",
        "target_moisture",
        "model_version",
    }
    numeric_features = sorted(
        key
        for key, value in rows[0].items()
        if key not in excluded and isinstance(value, (float, int))
    )
    scaled = [column for column in numeric_features if column.endswith("_scaled")]
    return scaled or numeric_features


def _rows_to_matrix(
    rows: list[dict[str, Any]],
    feature_columns: list[str],
) -> tuple[list[list[float]], list[float]]:
    matrix: list[list[float]] = []
    target: list[float] = []
    for row in rows:
        if any(row.get(column) is None for column in feature_columns):
            continue
        matrix.append([float(row[column]) for column in feature_columns])
        target.append(float(row["target_moisture"]))
    return matrix, target


def fit_estimator_on_rows(
    model_name: str,
    params: dict[str, Any],
    rows: list[dict[str, Any]],
    feature_columns: list[str],
) -> Any:
    estimator = build_estimator(model_name, params)
    train_x, train_y = _rows_to_matrix(rows, feature_columns)
    estimator.fit(train_x, train_y)
    return estimator


def evaluate_regressor(
    model_name: str,
    estimator: Any,
    rows: list[dict[str, Any]],
    feature_columns: list[str],
) -> ModelRunResult:
    folds = time_aware_cv_slices(rows, folds=3)
    if not folds:
        raise RuntimeError("Not enough rows to run time-aware cross-validation.")

    fold_metrics: list[ModelMetrics] = []
    for fold in folds:
        train_x, train_y = _rows_to_matrix(fold["train"], feature_columns)
        valid_x, valid_y = _rows_to_matrix(fold["validation"], feature_columns)
        if not train_x or not valid_x:
            continue
        estimator.fit(train_x, train_y)
        predictions = estimator.predict(valid_x)
        fold_metrics.append(compute_metrics(valid_y, list(predictions)))

    if not fold_metrics:
        raise RuntimeError("Unable to compute fold metrics for the selected model.")

    metrics = ModelMetrics(
        rmse=mean(metric.rmse for metric in fold_metrics),
        mae=mean(metric.mae for metric in fold_metrics),
        r2=mean(metric.r2 for metric in fold_metrics),
    )
    return ModelRunResult(
        model_name=model_name,
        metrics=metrics,
        params=estimator.get_params(),
    )


def run_baseline_models(dataset: DatasetBuildResult) -> list[ModelRunResult]:
    imports = _require_training_stack()
    feature_columns = select_feature_columns(dataset.rows)
    models = [
        ("linear_regression", imports["LinearRegression"]()),
        (
            "random_forest",
            imports["RandomForestRegressor"](
                n_estimators=200,
                random_state=42,
                min_samples_leaf=2,
            ),
        ),
    ]
    return [
        evaluate_regressor(name, estimator, dataset.rows, feature_columns)
        for name, estimator in models
    ]


def build_estimator(model_name: str, params: dict[str, Any]) -> Any:
    imports = _require_training_stack()
    if model_name == "linear_regression":
        return imports["LinearRegression"](**params)
    if model_name == "random_forest":
        return imports["RandomForestRegressor"](**params)
    if model_name == "xgboost":
        return imports["XGBRegressor"](**params)
    raise ValueError(f"Unsupported model name: {model_name}")


def _optuna_best_params(dataset: DatasetBuildResult, feature_columns: list[str]) -> dict[str, Any]:
    try:
        import optuna
        from xgboost import XGBRegressor
    except ImportError:
        return {
            "n_estimators": 300,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
        }

    folds = time_aware_cv_slices(dataset.rows, folds=3)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.7, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.7, 1.0),
            "random_state": 42,
        }
        scores: list[float] = []
        for fold in folds:
            train_x, train_y = _rows_to_matrix(fold["train"], feature_columns)
            valid_x, valid_y = _rows_to_matrix(fold["validation"], feature_columns)
            if not train_x or not valid_x:
                continue
            model = XGBRegressor(**params)
            model.fit(train_x, train_y)
            predictions = model.predict(valid_x)
            scores.append(compute_metrics(valid_y, list(predictions)).rmse)
        return mean(scores) if scores else float("inf")

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=10)
    return {**study.best_params, "random_state": 42}


def run_xgboost_training(dataset: DatasetBuildResult) -> ModelRunResult:
    imports = _require_training_stack()
    feature_columns = select_feature_columns(dataset.rows)
    params = _optuna_best_params(dataset, feature_columns)
    estimator = imports["XGBRegressor"](**params)
    return evaluate_regressor("xgboost", estimator, dataset.rows, feature_columns)


def choose_best_run(runs: list[ModelRunResult]) -> ModelRunResult:
    return min(runs, key=lambda run: run.metrics.rmse)


def render_model_card(best_run: ModelRunResult, dataset: DatasetBuildResult) -> str:
    return f"""# Soil Moisture Model Card

## Model Summary
- Registered model name: `{settings.mlflow_registered_model_name}`
- Selected model: `{best_run.model_name}`
- Dataset rows: `{dataset.metadata['row_count']}`
- Feature count: `{dataset.metadata['feature_count']}`
- Feature logic version: `{dataset.metadata['model_version']}`

## Metrics
- RMSE: `{best_run.metrics.rmse:.4f}`
- MAE: `{best_run.metrics.mae:.4f}`
- R²: `{best_run.metrics.r2:.4f}`

## Features Used
- Training uses the scaled numeric dataset columns derived from `feature_references`.
- Core signals include rolling moisture, rolling temperature, moisture variance, moisture range, soil retention index, dryness index, and evapotranspiration proxy.

## Known Limitations
- Current validation relies on time-aware cross-validation only; shadow mode and holdout reporting are still pending.
- Performance depends on upstream feature freshness and sensor quality filtering.
"""


def write_model_card(best_run: ModelRunResult, dataset: DatasetBuildResult) -> Path:
    MODEL_CARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CARD_PATH.write_text(render_model_card(best_run, dataset), encoding="utf-8")
    return MODEL_CARD_PATH


def log_training_to_mlflow(
    dataset: DatasetBuildResult,
    baseline_runs: list[ModelRunResult],
    best_run: ModelRunResult,
) -> dict[str, Any]:
    imports = _require_training_stack()
    mlflow = imports["mlflow"]
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)
    feature_columns = select_feature_columns(dataset.rows)
    
    # We want to train on raw features now, because the Pipeline will handle scaling
    # But wait, select_feature_columns currently picks the _scaled ones if they exist.
    # Let's get the raw column names.
    raw_feature_columns = [col.replace("_scaled", "") for col in feature_columns]
    
    train_x, train_y = _rows_to_matrix(dataset.rows, raw_feature_columns)
    
    # Create a pipeline with a scaler and the best estimator
    inner_estimator = build_estimator(best_run.model_name, best_run.params)
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("regressor", inner_estimator)
    ])
    
    pipeline.fit(train_x, train_y)

    with mlflow.start_run(run_name="ml03-model-training"):
        mlflow.log_params(
            {
                "registered_model_name": settings.mlflow_registered_model_name,
                "feature_model_version": dataset.metadata["model_version"],
                "feature_count": len(raw_feature_columns),
                "features": ",".join(raw_feature_columns),
                "target_horizon_minutes": dataset.metadata["target_horizon_minutes"],
            }
        )
        for baseline in baseline_runs:
            mlflow.log_metrics(
                {
                    f"{baseline.model_name}_rmse": baseline.metrics.rmse,
                    f"{baseline.model_name}_mae": baseline.metrics.mae,
                    f"{baseline.model_name}_r2": baseline.metrics.r2,
                }
            )
        mlflow.log_metrics(
            {
                "best_rmse": best_run.metrics.rmse,
                "best_mae": best_run.metrics.mae,
                "best_r2": best_run.metrics.r2,
            }
        )
        mlflow.log_dict(asdict(best_run), "best_run.json")
        model_card_path = write_model_card(best_run, dataset)
        mlflow.log_artifact(str(model_card_path))
        
        input_example = train_x[:5]
        # Note: we use mlflow.sklearn.log_model even for xgboost because it's wrapped in a sklearn Pipeline
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path="model",
            registered_model_name=settings.mlflow_registered_model_name,
            input_example=input_example,
        )

        client = mlflow.tracking.MlflowClient()
        latest_versions = client.get_latest_versions(
            settings.mlflow_registered_model_name, stages=["None"]
        )
        version = latest_versions[0].version if latest_versions else "1"

        return {
            "run_id": mlflow.active_run().info.run_id,
            "best_model": best_run.model_name,
            "model_card_path": str(model_card_path),
            "version": version,
        }


def run_holdout_evaluation(
    dataset: DatasetBuildResult,
    best_run: ModelRunResult,
    production_run: ModelRunResult | None,
) -> dict[str, Any]:
    feature_columns = select_feature_columns(dataset.rows)
    split = chronological_split(dataset.rows)
    train_rows = [*split["train"], *split["validation"]]
    holdout_rows = split["test"]
    if not holdout_rows:
        return {"report_path": None, "summary": None}

    best_estimator = fit_estimator_on_rows(
        best_run.model_name,
        best_run.params,
        train_rows,
        feature_columns,
    )
    holdout_x, holdout_y = _rows_to_matrix(holdout_rows, feature_columns)
    candidate_predictions = [float(value) for value in best_estimator.predict(holdout_x)]

    production_predictions = None
    if production_run:
        production_estimator = fit_estimator_on_rows(
            production_run.model_name,
            production_run.params,
            train_rows,
            feature_columns,
        )
        production_predictions = [
            float(value) for value in production_estimator.predict(holdout_x)
        ]

    summary = summarize_evaluation(
        actual=holdout_y,
        candidate_predictions=candidate_predictions,
        production_predictions=production_predictions,
    )
    report_path = write_evaluation_report(summary)
    return {"report_path": str(report_path), "summary": asdict(summary)}


async def orchestrate_training() -> dict[str, Any]:
    dataset = await build_dataset_from_database()
    baseline_runs = run_baseline_models(dataset)
    xgboost_run = run_xgboost_training(dataset)
    all_runs = [*baseline_runs, xgboost_run]
    best_run = choose_best_run(all_runs)
    production_reference = next(
        (run for run in baseline_runs if run.model_name == "random_forest"),
        None,
    )
    evaluation_result = run_holdout_evaluation(dataset, best_run, production_reference)
    mlflow_result = log_training_to_mlflow(dataset, baseline_runs, best_run)
    return {
        "dataset": dataset.metadata,
        "runs": [asdict(run) for run in all_runs],
        "best_run": asdict(best_run),
        "evaluation": evaluation_result,
        "mlflow": mlflow_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the soil moisture models.")
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to write the training summary JSON.",
    )
    args = parser.parse_args()

    import asyncio

    summary = asyncio.run(orchestrate_training())
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
