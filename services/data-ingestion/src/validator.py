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

    def parse_json(val):
        if val is None:
            return {}
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return {}
        return {}

    return {
        "min": parse_json(row["min_plausible"]),
        "max": parse_json(row["max_plausible"])
    }


async def validate_reading(sensor_data: Dict[str, Any]) -> ValidationResult:
    zone_id = sensor_data.get("zone_id")
    sensor_id = sensor_data.get("sensor_id")
    timestamp = sensor_data.get("timestamp")
    
    # Handle both new combined format and old single-value format
    moisture = sensor_data.get("moisture")
    temperature = sensor_data.get("temperature")
    
    # Fallback for single value format
    if moisture is None and sensor_data.get("type") == "moisture":
        moisture = sensor_data.get("value")
    if temperature is None and sensor_data.get("type") == "temperature":
        temperature = sensor_data.get("value")

    bounds = await get_zone_bounds(zone_id)
    anomalies = []

    if bounds is None:
        anomalies.append({
            "zone_id": zone_id,
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "event_type": "unknown_zone",
            "event_value": moisture or temperature,
            "severity": "critical",
            "details": f"Zone {zone_id} not found in database"
        })
        return ValidationResult(is_valid=False, anomalies=anomalies, sensor_type="combined")

    def check_bounds(val, s_type):
        if val is None:
            return
        min_p = bounds.get("min", {}).get(s_type)
        max_p = bounds.get("max", {}).get(s_type)
        
        if min_p is not None and val < min_p:
            anomalies.append({
                "zone_id": zone_id,
                "sensor_id": sensor_id,
                "timestamp": timestamp,
                "event_type": f"below_min_plausible_{s_type}",
                "event_value": val,
                "expected_min": min_p,
                "severity": "warning",
                "details": f"{s_type} reading {val} below min plausible {min_p}"
            })
        if max_p is not None and val > max_p:
            anomalies.append({
                "zone_id": zone_id,
                "sensor_id": sensor_id,
                "timestamp": timestamp,
                "event_type": f"above_max_plausible_{s_type}",
                "event_value": val,
                "expected_max": max_p,
                "severity": "critical" if val > max_p * 1.5 else "warning",
                "details": f"{s_type} reading {val} above max plausible {max_p}"
            })

    check_bounds(moisture, "moisture")
    check_bounds(temperature, "temperature")

    return ValidationResult(
        is_valid=len(anomalies) == 0,
        anomalies=anomalies,
        sensor_type="combined"
    )