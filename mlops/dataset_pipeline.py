from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import TYPE_CHECKING, Any, Iterable, Sequence

from .settings import settings

if TYPE_CHECKING:
    import asyncpg


def _as_utc(ts: datetime | str) -> datetime:
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


def _safe_mean(values: Sequence[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    if not valid:
        return None
    return mean(valid)


def deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, datetime], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        ts = _as_utc(record["timestamp"])
        grouped[(record["zone_id"], record["sensor_id"], ts)].append(
            {**record, "timestamp": ts}
        )

    deduplicated: list[dict[str, Any]] = []
    for (zone_id, sensor_id, ts), rows in grouped.items():
        deduplicated.append(
            {
                "zone_id": zone_id,
                "sensor_id": sensor_id,
                "timestamp": ts,
                "moisture": mean([row["moisture"] for row in rows]),
                "temperature": _safe_mean([row.get("temperature") for row in rows]),
            }
        )

    deduplicated.sort(key=lambda item: item["timestamp"])
    return deduplicated


def forward_fill_temperature(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    last_temperature: float | None = None
    filled: list[dict[str, Any]] = []
    for record in records:
        updated = dict(record)
        if updated.get("temperature") is None:
            updated["temperature"] = last_temperature
        else:
            last_temperature = updated["temperature"]
        filled.append(updated)
    return filled


def smooth_outliers(
    records: list[dict[str, Any]],
    threshold: float | None = None,
) -> list[dict[str, Any]]:
    if len(records) < 3:
        return [dict(record) for record in records]

    limit = threshold if threshold is not None else settings.outlier_zscore_threshold
    moistures = [record["moisture"] for record in records]
    avg = mean(moistures)
    variance = sum((value - avg) ** 2 for value in moistures) / len(moistures)
    std = math.sqrt(variance)
    if std == 0:
        return [dict(record) for record in records]

    smoothed: list[dict[str, Any]] = []
    for record in records:
        updated = dict(record)
        zscore = abs((updated["moisture"] - avg) / std)
        if zscore > limit:
            updated["moisture"] = avg
        smoothed.append(updated)
    return smoothed


def clean_sensor_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = deduplicate_records(records)
    cleaned = forward_fill_temperature(cleaned)
    cleaned = smooth_outliers(cleaned)
    return cleaned


def build_feature_snapshot(
    feature_rows: Iterable[dict[str, Any]],
    *,
    computed_at: datetime,
    zone_id: str,
    sensor_id: str,
    model_version: str,
) -> dict[str, float]:
    snapshot: dict[str, tuple[datetime, float]] = {}
    for row in feature_rows:
        if row["zone_id"] != zone_id or row.get("sensor_id") != sensor_id:
            continue
        if row.get("model_version", settings.feature_model_version) != model_version:
            continue
        row_time = _as_utc(row["computed_at"])
        if row_time > computed_at:
            continue

        feature_key = f'{row["feature_name"]}_{row["window_size"]}'
        current = snapshot.get(feature_key)
        feature_value = row.get("feature_value")
        if feature_value is None:
            continue
        if current is None or row_time > current[0]:
            snapshot[feature_key] = (row_time, float(feature_value))

    return {key: value for key, (_, value) in snapshot.items()}


@dataclass(frozen=True)
class DatasetBuildResult:
    rows: list[dict[str, Any]]
    feature_columns: list[str]
    metadata: dict[str, Any]


def prepare_training_dataset(
    sensor_rows: list[dict[str, Any]],
    feature_rows: list[dict[str, Any]],
    *,
    target_horizon_minutes: int | None = None,
    model_version: str | None = None,
) -> DatasetBuildResult:
    horizon_minutes = target_horizon_minutes or settings.target_horizon_minutes
    effective_model_version = model_version or settings.feature_model_version
    cleaned = clean_sensor_records(sensor_rows)
    by_sensor: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in cleaned:
        by_sensor[(row["zone_id"], row["sensor_id"])].append(row)

    dataset_rows: list[dict[str, Any]] = []
    feature_names: set[str] = set()

    for (zone_id, sensor_id), rows in by_sensor.items():
        rows.sort(key=lambda item: item["timestamp"])
        future_index = 0
        for row in rows:
            cutoff = row["timestamp"] + timedelta(minutes=horizon_minutes)
            while future_index < len(rows) and rows[future_index]["timestamp"] < cutoff:
                future_index += 1
            if future_index >= len(rows):
                break

            target_row = rows[future_index]
            feature_snapshot = build_feature_snapshot(
                feature_rows,
                computed_at=row["timestamp"],
                zone_id=zone_id,
                sensor_id=sensor_id,
                model_version=effective_model_version,
            )
            feature_names.update(feature_snapshot.keys())

            dataset_rows.append(
                {
                    "zone_id": zone_id,
                    "sensor_id": sensor_id,
                    "timestamp": row["timestamp"],
                    "current_moisture": float(row["moisture"]),
                    "current_temperature": (
                        None
                        if row.get("temperature") is None
                        else float(row["temperature"])
                    ),
                    "target_timestamp": target_row["timestamp"],
                    "target_moisture": float(target_row["moisture"]),
                    "model_version": effective_model_version,
                    **feature_snapshot,
                }
            )

    dataset_rows.sort(key=lambda item: item["timestamp"])
    numeric_columns = [
        "current_moisture",
        "current_temperature",
        *sorted(feature_names),
    ]
    normalized_rows = normalize_numeric_columns(dataset_rows, numeric_columns)
    return DatasetBuildResult(
        rows=normalized_rows,
        feature_columns=sorted(feature_names),
        metadata={
            "row_count": len(normalized_rows),
            "feature_count": len(feature_names),
            "target_horizon_minutes": horizon_minutes,
            "model_version": effective_model_version,
        },
    )


def normalize_numeric_columns(
    rows: list[dict[str, Any]],
    numeric_columns: list[str],
) -> list[dict[str, Any]]:
    stats_map: dict[str, tuple[float, float]] = {}
    for column in numeric_columns:
        values = [row[column] for row in rows if row.get(column) is not None]
        if not values:
            continue
        avg = mean(values)
        variance = sum((value - avg) ** 2 for value in values) / len(values)
        std = math.sqrt(variance)
        stats_map[column] = (avg, std)

    normalized: list[dict[str, Any]] = []
    for row in rows:
        updated = dict(row)
        for column, (avg, std) in stats_map.items():
            value = updated.get(column)
            if value is None:
                continue
            updated[f"{column}_scaled"] = 0.0 if std == 0 else (value - avg) / std
        normalized.append(updated)
    return normalized


def chronological_split(
    rows: list[dict[str, Any]],
    *,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
) -> dict[str, list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda item: item["timestamp"])
    total = len(ordered)
    train_end = int(total * train_ratio)
    validation_end = train_end + int(total * validation_ratio)

    return {
        "train": ordered[:train_end],
        "validation": ordered[train_end:validation_end],
        "test": ordered[validation_end:],
    }


def time_aware_cv_slices(
    rows: list[dict[str, Any]],
    *,
    folds: int = 3,
) -> list[dict[str, list[dict[str, Any]]]]:
    ordered = sorted(rows, key=lambda item: item["timestamp"])
    if len(ordered) < folds + 1:
        return []

    fold_size = max(1, len(ordered) // (folds + 1))
    slices: list[dict[str, list[dict[str, Any]]]] = []
    for fold in range(1, folds + 1):
        train_end = fold * fold_size
        validation_end = min(len(ordered), train_end + fold_size)
        if validation_end <= train_end:
            break
        slices.append(
            {
                "train": ordered[:train_end],
                "validation": ordered[train_end:validation_end],
            }
        )
    return slices


async def fetch_sensor_rows(
    connection: "asyncpg.Connection",
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[dict[str, Any]]:
    rows = await connection.fetch(
        """
        SELECT timestamp, zone_id, sensor_id, moisture, temperature
        FROM sensor_readings
        WHERE ($1::timestamptz IS NULL OR timestamp >= $1)
          AND ($2::timestamptz IS NULL OR timestamp <= $2)
        ORDER BY timestamp
        """,
        start_time,
        end_time,
    )
    return [dict(row) for row in rows]


async def fetch_feature_rows(
    connection: "asyncpg.Connection",
    *,
    model_version: str | None = None,
) -> list[dict[str, Any]]:
    rows = await connection.fetch(
        """
        SELECT computed_at, zone_id, sensor_id, window_size, feature_name, feature_value, model_version
        FROM feature_references
        WHERE ($1::varchar IS NULL OR model_version = $1)
        ORDER BY computed_at
        """,
        model_version,
    )
    return [dict(row) for row in rows]


async def build_dataset_from_database(
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    target_horizon_minutes: int | None = None,
    model_version: str | None = None,
) -> DatasetBuildResult:
    import asyncpg

    connection = await asyncpg.connect(settings.database_url)
    try:
        sensor_rows = await fetch_sensor_rows(
            connection,
            start_time=start_time,
            end_time=end_time,
        )
        feature_rows = await fetch_feature_rows(
            connection,
            model_version=model_version or settings.feature_model_version,
        )
    finally:
        await connection.close()

    return prepare_training_dataset(
        sensor_rows,
        feature_rows,
        target_horizon_minutes=target_horizon_minutes,
        model_version=model_version,
    )


def log_dataset_to_mlflow(dataset: DatasetBuildResult) -> dict[str, Any]:
    try:
        import mlflow
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "MLflow dataset logging requires mlflow and pandas to be installed."
        ) from exc

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)

    frame = pd.DataFrame(dataset.rows)
    mlflow_dataset = mlflow.data.from_pandas(
        frame,
        name=settings.mlflow_dataset_name,
    )

    with mlflow.start_run(run_name="dataset-build"):
        mlflow.log_input(mlflow_dataset, context="training")
        mlflow.log_params(dataset.metadata)
        mlflow.log_metric("dataset_rows", len(dataset.rows))
        mlflow.log_metric("dataset_features", len(dataset.feature_columns))
        return {
            "run_id": mlflow.active_run().info.run_id,
            "rows": len(dataset.rows),
            "features": len(dataset.feature_columns),
        }
