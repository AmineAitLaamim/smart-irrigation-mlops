import math
import os
from dataclasses import dataclass
from datetime import timedelta
from statistics import mean
from typing import Any

ROLLUP_WINDOWS = os.getenv("ROLLUP_WINDOWS", "30m,1h,3h,24h").split(",")
FEATURE_MODEL_VERSION = os.getenv("FEATURE_MODEL_VERSION", "v1")

SOIL_TYPE_FACTORS = {
    "sand": {"water_retention_factor": 0.7, "drainage_factor": 1.3},
    "sandy_loam": {"water_retention_factor": 0.85, "drainage_factor": 1.15},
    "loam": {"water_retention_factor": 1.0, "drainage_factor": 1.0},
    "silty_loam": {"water_retention_factor": 1.05, "drainage_factor": 0.98},
    "silt": {"water_retention_factor": 1.08, "drainage_factor": 0.95},
    "clay_loam": {"water_retention_factor": 1.12, "drainage_factor": 0.9},
    "clay": {"water_retention_factor": 1.2, "drainage_factor": 0.8},
    "peat": {"water_retention_factor": 1.5, "drainage_factor": 0.6},
}
DEFAULT_SOIL_PROFILE = {"water_retention_factor": 1.0, "drainage_factor": 1.0}


@dataclass(frozen=True)
class ComputedFeature:
    window_size: str
    feature_name: str
    feature_value: float
    model_version: str = FEATURE_MODEL_VERSION


def parse_window_to_interval(window: str) -> timedelta:
    window = window.strip()
    if window.endswith("m"):
        return timedelta(minutes=int(window[:-1]))
    if window.endswith("h"):
        return timedelta(hours=int(window[:-1]))
    if window.endswith("d"):
        return timedelta(days=int(window[:-1]))
    raise ValueError(f"Unsupported rolling window: {window}")


def _variance(values: list[float]) -> float:
    if not values:
        return 0.0
    avg = mean(values)
    return sum((value - avg) ** 2 for value in values) / len(values)


def _stddev(values: list[float]) -> float:
    variance = _variance(values)
    return math.sqrt(variance) if variance > 0 else 0.0


def _safe_values(values: list[Any]) -> list[float]:
    return [float(value) for value in values if value is not None and value != -1.0]


def get_soil_profile(soil_type: str | None) -> dict[str, float]:
    if not soil_type:
        return DEFAULT_SOIL_PROFILE
    return SOIL_TYPE_FACTORS.get(soil_type.lower(), DEFAULT_SOIL_PROFILE)


def compute_window_features(
    window: str,
    moisture_values: list[float],
    temperature_values: list[float],
    soil_type: str | None,
) -> list[ComputedFeature]:
    features: list[ComputedFeature] = []
    soil_profile = get_soil_profile(soil_type)

    if moisture_values:
        mean_moisture = mean(moisture_values)
        variance_moisture = _variance(moisture_values)
        std_moisture = _stddev(moisture_values)
        min_moisture = min(moisture_values)
        max_moisture = max(moisture_values)
        moisture_change = (
            moisture_values[-1] - moisture_values[0]
            if len(moisture_values) > 1
            else 0.0
        )
        moisture_range = max_moisture - min_moisture
        dryness_index = (100.0 - mean_moisture) * soil_profile["drainage_factor"]
        retention_index = mean_moisture * soil_profile["water_retention_factor"]

        features.extend(
            [
                ComputedFeature(window, "mean_moisture", mean_moisture),
                ComputedFeature(window, "std_moisture", std_moisture),
                ComputedFeature(window, "min_moisture", min_moisture),
                ComputedFeature(window, "max_moisture", max_moisture),
                ComputedFeature(window, "rate_of_change_moisture", moisture_change),
                ComputedFeature(window, "variance_moisture", variance_moisture),
                ComputedFeature(window, "moisture_range", moisture_range),
                ComputedFeature(window, "soil_water_retention_index", retention_index),
                ComputedFeature(window, "soil_dryness_index", dryness_index),
            ]
        )

    if temperature_values:
        mean_temperature = mean(temperature_values)
        variance_temperature = _variance(temperature_values)
        std_temperature = _stddev(temperature_values)
        min_temperature = min(temperature_values)
        max_temperature = max(temperature_values)
        temperature_change = (
            temperature_values[-1] - temperature_values[0]
            if len(temperature_values) > 1
            else 0.0
        )

        features.extend(
            [
                ComputedFeature(window, "mean_temperature", mean_temperature),
                ComputedFeature(window, "std_temperature", std_temperature),
                ComputedFeature(window, "min_temperature", min_temperature),
                ComputedFeature(window, "max_temperature", max_temperature),
                ComputedFeature(window, "rate_of_change_temperature", temperature_change),
                ComputedFeature(window, "variance_temperature", variance_temperature),
            ]
        )

    if moisture_values and temperature_values:
        evapotranspiration_proxy = max(0.0, mean(temperature_values) * (100.0 - mean(moisture_values)) / 100.0)
        features.append(
            ComputedFeature(window, "evapotranspiration_proxy", evapotranspiration_proxy)
        )

    return features


def serialize_feature_payload(features: list[ComputedFeature]) -> dict[str, float]:
    payload: dict[str, float] = {}
    for feature in features:
        payload[f"{feature.feature_name}_{feature.window_size}"] = feature.feature_value
    return payload


def normalize_sensor_rows(rows: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    moisture_values = _safe_values([row.get("moisture") for row in rows])
    temperature_values = _safe_values([row.get("temperature") for row in rows])
    return moisture_values, temperature_values
