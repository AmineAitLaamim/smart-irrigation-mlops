from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class DriftSummary:
    page_hinkley_score: float
    kl_divergence: float
    mean_error: float
    drift_detected: bool


def page_hinkley(values: list[float], delta: float = 0.005, threshold: float = 0.5) -> tuple[float, bool]:
    if not values:
        return 0.0, False
    mean_value = 0.0
    cumulative = 0.0
    min_cumulative = 0.0
    best_score = 0.0
    for index, value in enumerate(values, start=1):
        mean_value += (value - mean_value) / index
        cumulative += value - mean_value - delta
        min_cumulative = min(min_cumulative, cumulative)
        best_score = max(best_score, cumulative - min_cumulative)
    return best_score, best_score > threshold


def kl_divergence(reference: list[float], current: list[float], bins: int = 10) -> float:
    if not reference or not current:
        return 0.0
    minimum = min(reference + current)
    maximum = max(reference + current)
    if minimum == maximum:
        return 0.0
    bucket_width = (maximum - minimum) / bins
    ref_hist = [1e-6] * bins
    cur_hist = [1e-6] * bins
    for value in reference:
        index = min(bins - 1, int((value - minimum) / bucket_width))
        ref_hist[index] += 1
    for value in current:
        index = min(bins - 1, int((value - minimum) / bucket_width))
        cur_hist[index] += 1
    ref_total = sum(ref_hist)
    cur_total = sum(cur_hist)
    return sum(
        (cur / cur_total) * math.log((cur / cur_total) / (ref / ref_total))
        for ref, cur in zip(ref_hist, cur_hist)
    )


def summarize_drift(reference: list[float], current: list[float], actual: list[float] | None = None) -> DriftSummary:
    score, detected = page_hinkley(current)
    divergence = kl_divergence(reference, current)
    mean_error = 0.0
    if actual and len(actual) == len(current):
        mean_error = sum(abs(a - c) for a, c in zip(actual, current)) / len(actual)
    drift_detected = detected or divergence > 0.1 or mean_error > 0.15
    return DriftSummary(
        page_hinkley_score=score,
        kl_divergence=divergence,
        mean_error=mean_error,
        drift_detected=drift_detected,
    )
