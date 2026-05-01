from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# ── Prometheus metrics for Grafana ──────────────────────────────

readings_checked_total = Counter(
    "data_quality_readings_checked_total",
    "Total sensor readings evaluated by the quality engine",
    ["zone_id", "sensor_id", "sensor_type"],
)

anomalies_detected_total = Counter(
    "data_quality_anomalies_detected_total",
    "Total anomalies detected, labeled by rule type and severity",
    ["rule_type", "severity", "zone_id", "sensor_id"],
)

active_rules_gauge = Gauge(
    "data_quality_active_rules",
    "Number of currently active quality rules",
)

rule_eval_duration_seconds = Histogram(
    "data_quality_rule_eval_duration_seconds",
    "Time spent evaluating a single quality rule",
    ["rule_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

sensor_health_status = Gauge(
    "data_quality_sensor_health_status",
    "Sensor health status: 0=healthy, 1=degraded, 2=unhealthy",
    ["zone_id", "sensor_id", "sensor_type"],
)

stuck_value_detected_total = Counter(
    "data_quality_stuck_value_detected_total",
    "Total stuck-value anomalies detected",
    ["zone_id", "sensor_id"],
)

sudden_jump_detected_total = Counter(
    "data_quality_sudden_jump_detected_total",
    "Total sudden-jump anomalies detected",
    ["zone_id", "sensor_id"],
)

flatline_detected_total = Counter(
    "data_quality_flatline_detected_total",
    "Total flatline anomalies detected",
    ["zone_id", "sensor_id"],
)
