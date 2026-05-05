from datetime import datetime, timezone, timedelta
from mlops.dataset_pipeline import prepare_training_dataset

def _ts(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 1, 1, hour, minute, tzinfo=timezone.utc)

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
        "computed_at": _ts(1),
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
    model_version="v1"
)

print(f"Rows: {len(result.rows)}")
for i, row in enumerate(result.rows):
    print(f"Row {i}: mean_moisture_1h={row.get('mean_moisture_1h')}, scaled={row.get('mean_moisture_1h_scaled')}")
