from src.feature_computation import (
    compute_window_features,
    get_soil_profile,
    parse_window_to_interval,
    serialize_feature_payload,
)


def test_parse_window_to_interval_supports_project_windows():
    assert parse_window_to_interval("30m").total_seconds() == 1800
    assert parse_window_to_interval("1h").total_seconds() == 3600
    assert parse_window_to_interval("24h").total_seconds() == 86400


def test_compute_window_features_includes_soil_specific_indices():
    features = compute_window_features(
        "1h",
        moisture_values=[25.0, 30.0, 20.0],
        temperature_values=[18.0, 20.0, 22.0],
        soil_type="clay",
    )
    payload = serialize_feature_payload(features)

    assert "mean_moisture_1h" in payload
    assert "variance_moisture_1h" in payload
    assert "soil_water_retention_index_1h" in payload
    assert "soil_dryness_index_1h" in payload
    assert "evapotranspiration_proxy_1h" in payload
    assert payload["soil_water_retention_index_1h"] > payload["mean_moisture_1h"]


def test_get_soil_profile_uses_default_for_unknown_type():
    assert get_soil_profile("volcanic")["water_retention_factor"] == 1.0
