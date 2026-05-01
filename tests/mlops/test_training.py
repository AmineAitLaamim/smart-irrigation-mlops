from mlops.dataset_pipeline import DatasetBuildResult
from mlops.training import (
    choose_best_run,
    render_model_card,
    select_feature_columns,
    ModelMetrics,
    ModelRunResult,
)


def _dataset() -> DatasetBuildResult:
    return DatasetBuildResult(
        rows=[
            {
                "zone_id": "z1",
                "sensor_id": "s1",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "target_timestamp": "2026-01-01T01:00:00+00:00",
                "target_moisture": 10.0,
                "model_version": "v1",
                "mean_moisture_1h_scaled": 0.1,
                "soil_dryness_index_1h_scaled": 0.2,
            }
        ],
        feature_columns=["mean_moisture_1h", "soil_dryness_index_1h"],
        metadata={
            "row_count": 1,
            "feature_count": 2,
            "target_horizon_minutes": 60,
            "model_version": "v1",
        },
    )


def test_select_feature_columns_prefers_scaled_features():
    columns = select_feature_columns(_dataset().rows)
    assert columns == ["mean_moisture_1h_scaled", "soil_dryness_index_1h_scaled"]


def test_choose_best_run_uses_lowest_rmse():
    best = choose_best_run(
        [
            ModelRunResult("linear", ModelMetrics(2.0, 1.0, 0.5), {}),
            ModelRunResult("xgboost", ModelMetrics(1.5, 0.8, 0.7), {}),
        ]
    )
    assert best.model_name == "xgboost"


def test_render_model_card_mentions_selected_model():
    run = ModelRunResult("xgboost", ModelMetrics(1.5, 0.8, 0.7), {"max_depth": 6})
    model_card = render_model_card(run, _dataset())
    assert "Selected model: `xgboost`" in model_card
    assert "soil retention index" in model_card.lower()
