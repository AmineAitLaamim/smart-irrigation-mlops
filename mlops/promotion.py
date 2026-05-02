from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


PROMOTION_MARGIN_RMSE = float(os.getenv("MODEL_PROMOTION_MIN_IMPROVEMENT_RMSE", "0.01"))
MLFLOW_STAGING_STAGE = os.getenv("MLFLOW_STAGING_STAGE", "Staging")
MLFLOW_PRODUCTION_STAGE = os.getenv("MLFLOW_PRODUCTION_STAGE", "Production")
MLFLOW_ARCHIVED_STAGE = os.getenv("MLFLOW_ARCHIVED_STAGE", "Archived")


@dataclass(frozen=True)
class PromotionDecision:
    should_promote: bool
    target_stage: str
    reason: str


def decide_promotion(
    candidate_rmse: float,
    production_rmse: float | None,
    min_improvement: float = PROMOTION_MARGIN_RMSE,
) -> PromotionDecision:
    if production_rmse is None:
        return PromotionDecision(
            should_promote=True,
            target_stage=MLFLOW_PRODUCTION_STAGE,
            reason="No production model exists yet.",
        )

    improvement = production_rmse - candidate_rmse
    if improvement >= min_improvement:
        return PromotionDecision(
            should_promote=True,
            target_stage=MLFLOW_PRODUCTION_STAGE,
            reason=f"Candidate improved RMSE by {improvement:.4f}.",
        )

    return PromotionDecision(
        should_promote=False,
        target_stage=MLFLOW_STAGING_STAGE,
        reason=(
            f"Candidate RMSE improvement {improvement:.4f} did not reach the "
            f"required margin {min_improvement:.4f}."
        ),
    )


def load_production_rmse(mlflow_client: Any, model_name: str) -> float | None:
    from mlflow.exceptions import RestException
    try:
        versions = mlflow_client.get_latest_versions(model_name, stages=[MLFLOW_PRODUCTION_STAGE])
        if not versions:
            return None
        run = mlflow_client.get_run(versions[0].run_id)
        metric = run.data.metrics.get("best_rmse")
        return float(metric) if metric is not None else None
    except RestException as e:
        if "RESOURCE_DOES_NOT_EXIST" in str(e):
            return None
        raise


def promote_model(
    mlflow_client: Any,
    model_name: str,
    version: str,
    stage: str,
    archive_existing: bool = True,
) -> None:
    mlflow_client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage,
        archive_existing_versions=archive_existing,
    )
