from datetime import datetime, timedelta, timezone

from mlops.dataset_pipeline import (
    chronological_split,
    clean_sensor_records,
    prepare_training_dataset,
    time_aware_cv_slices,
)
from mlops.exploration import render_markdown


def _ts(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 1, 1, hour, minute, tzinfo=timezone.utc)


def test_clean_sensor_records_deduplicates_and_fills_temperature():
    records = [
        {"zone_id": "z1", "sensor_id": "s1", "timestamp": _ts(0), "moisture": 10.0, "temperature": 20.0},
        {"zone_id": "z1", "sensor_id": "s1", "timestamp": _ts(0), "moisture": 14.0, "temperature": None},
        {"zone_id": "z1", "sensor_id": "s1", "timestamp": _ts(1), "moisture": 11.0, "temperature": None},
    ]

    cleaned = clean_sensor_records(records)

    assert len(cleaned) == 2
    assert cleaned[0]["moisture"] == 12.0
    assert cleaned[1]["temperature"] == 20.0


def test_prepare_training_dataset_uses_only_past_features():
    sensor_rows = [
        {"zone_id": "z1", "sensor_id": "s1", "timestamp": _ts(0), "moisture": 10.0, "temperature": 20.0},
        {"zone_id": "z1", "sensor_id": "s1", "timestamp": _ts(1), "moisture": 11.0, "temperature": 21.0},
        {"zone_id": "z1", "sensor_id": "s1", "timestamp": _ts(2), "moisture": 12.0, "temperature": 22.0},
    ]
    feature_rows = [
        {
            "computed_at": _ts(0),
            "zone_id": "z1",
            "sensor_id": "s1",
            "window_size": "1h",
            "feature_name": "mean_moisture",
            "feature_value": 10.0,
            "model_version": "v1",
        },
        {
            "computed_at": _ts(2),
            "zone_id": "z1",
            "sensor_id": "s1",
            "window_size": "1h",
            "feature_name": "mean_moisture",
            "feature_value": 12.0,
            "model_version": "v1",
        },
    ]

    result = prepare_training_dataset(
        sensor_rows,
        feature_rows,
        target_horizon_minutes=60,
    )

    assert len(result.rows) == 2
    assert result.rows[0]["target_moisture"] == 11.0
    assert result.rows[0]["mean_moisture_1h"] == 10.0
    assert result.rows[0]["mean_moisture_1h_scaled"] != result.rows[1]["mean_moisture_1h_scaled"]


def test_chronological_split_preserves_order():
    rows = [
        {"timestamp": _ts(0)},
        {"timestamp": _ts(1)},
        {"timestamp": _ts(2)},
        {"timestamp": _ts(3)},
        {"timestamp": _ts(4)},
        {"timestamp": _ts(5)},
        {"timestamp": _ts(6)},
        {"timestamp": _ts(7)},
        {"timestamp": _ts(8)},
        {"timestamp": _ts(9)},
    ]

    split = chronological_split(rows)

    assert split["train"][0]["timestamp"] == _ts(0)
    assert split["train"][-1]["timestamp"] < split["validation"][0]["timestamp"]
    assert split["validation"][-1]["timestamp"] < split["test"][0]["timestamp"]


def test_time_aware_cv_slices_are_forward_only():
    rows = [{"timestamp": _ts(0) + timedelta(hours=index)} for index in range(8)]

    folds = time_aware_cv_slices(rows, folds=3)

    assert len(folds) == 3
    for fold in folds:
        assert fold["train"][-1]["timestamp"] < fold["validation"][0]["timestamp"]


def test_render_markdown_contains_expected_sections():
    markdown = render_markdown(
        {
            "totals": {
                "reading_count": 10,
                "zone_count": 2,
                "sensor_count": 3,
                "min_timestamp": _ts(0),
                "max_timestamp": _ts(2),
                "avg_moisture": 11.2,
                "avg_temperature": 21.5,
            },
            "by_soil": [
                {
                    "soil_type": "loam",
                    "reading_count": 10,
                    "avg_moisture": 11.2,
                    "avg_temperature": 21.5,
                }
            ],
            "monthly": [],
            "sensor_health": [],
        }
    )

    assert "# ML Exploration Report" in markdown
    assert "Moisture Distribution by Soil Type" in markdown
    assert "loam" in markdown
