from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from .metrics import ModelMetrics, compute_metrics

EVALUATION_REPORT_PATH = Path("docs/model_reports/model_evaluation.json")


@dataclass(frozen=True)
class EvaluationSummary:
    candidate_metrics: ModelMetrics
    production_metrics: ModelMetrics | None
    holdout_metrics: ModelMetrics
    confidence_interval_low: float
    confidence_interval_high: float
    mean_prediction_delta: float
    paired_t_like_score: float
    diebold_mariano_like_score: float
    promoted: bool


def split_holdout(rows: list[dict[str, Any]], holdout_ratio: float = 0.2) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda item: item["timestamp"])
    cutoff = max(1, int(len(ordered) * (1 - holdout_ratio)))
    return ordered[:cutoff], ordered[cutoff:]


def confidence_interval(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    sorted_values = sorted(values)
    lower_index = max(0, int(len(sorted_values) * 0.05) - 1)
    upper_index = min(len(sorted_values) - 1, int(len(sorted_values) * 0.95))
    return sorted_values[lower_index], sorted_values[upper_index]


def compare_prediction_streams(
    actual: list[float],
    candidate: list[float],
    production: list[float] | None,
) -> dict[str, float]:
    candidate_errors = [abs(a - b) for a, b in zip(actual, candidate)]
    production_errors = [abs(a - b) for a, b in zip(actual, production)] if production else []
    mean_delta = mean(candidate_errors) - mean(production_errors) if production_errors else 0.0
    paired_score = mean_delta / (mean(production_errors) + 1e-6) if production_errors else 0.0

    dm_like = 0.0
    if production_errors:
        differential = [c - p for c, p in zip(candidate_errors, production_errors)]
        dm_like = mean(differential)

    return {
        "mean_prediction_delta": mean_delta,
        "paired_t_like_score": paired_score,
        "diebold_mariano_like_score": dm_like,
    }


def summarize_evaluation(
    actual: list[float],
    candidate_predictions: list[float],
    production_predictions: list[float] | None = None,
) -> EvaluationSummary:
    candidate_metrics = compute_metrics(actual, candidate_predictions)
    production_metrics = (
        compute_metrics(actual, production_predictions) if production_predictions else None
    )
    low, high = confidence_interval(candidate_predictions)
    comparison = compare_prediction_streams(actual, candidate_predictions, production_predictions)
    promoted = (
        production_metrics is None or candidate_metrics.rmse < production_metrics.rmse
    )
    return EvaluationSummary(
        candidate_metrics=candidate_metrics,
        production_metrics=production_metrics,
        holdout_metrics=candidate_metrics,
        confidence_interval_low=low,
        confidence_interval_high=high,
        mean_prediction_delta=comparison["mean_prediction_delta"],
        paired_t_like_score=comparison["paired_t_like_score"],
        diebold_mariano_like_score=comparison["diebold_mariano_like_score"],
        promoted=promoted,
    )


def write_evaluation_report(summary: EvaluationSummary, output_path: Path = EVALUATION_REPORT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    return output_path
