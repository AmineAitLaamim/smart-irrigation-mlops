import json
from dataclasses import dataclass
from typing import Optional, Dict, Any
from .database import db


@dataclass
class ValidationResult:
    is_valid: bool
    anomalies: list
    sensor_type: str


async def get_zone_bounds(zone_id: str) -> Optional[Dict[str, float]]:
    row = await db.fetchrow(
        "SELECT min_plausible, max_plausible FROM zones WHERE zone_id = $1",
        zone_id
    )
    if not row:
        return None
    return {
        "min": dict(row["min_plausible"]) if row["min_plausible"] else {},
        "max": dict(row["max_plausible"]) if row["max_plausible"] else {}
    }


async def validate_reading(sensor_data: Dict[str, Any]) -> ValidationResult:
    zone_id = sensor_data.get("zone_id")
    sensor_id = sensor_data.get("sensor_id")
    timestamp = sensor_data.get("timestamp")
    reading_value = sensor_data.get("value")
    sensor_type = sensor_data.get("type", "moisture")

    bounds = await get_zone_bounds(zone_id)

    anomalies = []

    if bounds is None:
        anomalies.append({
            "zone_id": zone_id,
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "event_type": "unknown_zone",
            "event_value": reading_value,
            "severity": "critical",
            "details": f"Zone {zone_id} not found in database"
        })
        return ValidationResult(is_valid=False, anomalies=anomalies, sensor_type=sensor_type)

    min_bounds = bounds.get("min", {})
    max_bounds = bounds.get("max", {})

    min_plausible = min_bounds.get(sensor_type)
    max_plausible = max_bounds.get(sensor_type)

    if min_plausible is not None and reading_value < min_plausible:
        anomalies.append({
            "zone_id": zone_id,
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "event_type": "below_min_plausible",
            "event_value": reading_value,
            "expected_min": min_plausible,
            "expected_max": max_plausible,
            "severity": "warning",
            "details": f"{sensor_type} reading {reading_value} below min plausible {min_plausible}"
        })

    if max_plausible is not None and reading_value > max_plausible:
        anomalies.append({
            "zone_id": zone_id,
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "event_type": "above_max_plausible",
            "event_value": reading_value,
            "expected_min": min_plausible,
            "expected_max": max_plausible,
            "severity": "critical" if reading_value > max_plausible * 1.5 else "warning",
            "details": f"{sensor_type} reading {reading_value} above max plausible {max_plausible}"
        })

    is_valid = len(anomalies) == 0

    return ValidationResult(
        is_valid=is_valid,
        anomalies=anomalies,
        sensor_type=sensor_type
    )