from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class ModelMetrics:
    rmse: float
    mae: float
    r2: float


def compute_metrics(y_true: list[float], y_pred: list[float]) -> ModelMetrics:
    if not y_true or len(y_true) != len(y_pred):
        raise ValueError("Metric computation requires non-empty equal-length arrays.")

    residuals = [actual - predicted for actual, predicted in zip(y_true, y_pred)]
    mae = float(mean(abs(residual) for residual in residuals))
    mse = mean(residual ** 2 for residual in residuals)
    rmse = float(mse ** 0.5)

    actual_mean = mean(y_true)
    total_variance = sum((actual - actual_mean) ** 2 for actual in y_true)
    if total_variance == 0:
        r2 = 1.0 if mse == 0 else 0.0
    else:
        residual_variance = sum(residual ** 2 for residual in residuals)
        r2 = float(1 - (residual_variance / total_variance))

    return ModelMetrics(rmse=rmse, mae=mae, r2=r2)
