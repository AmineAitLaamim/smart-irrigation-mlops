from datetime import datetime
from typing import Any, Dict

from .database import db


def _parse_timestamp(ts: Any) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    return datetime.utcnow()


async def insert_sensor_reading(
    zone_id: str,
    sensor_id: str,
    timestamp: Any,
    sensor_type: str,
    value: float,
) -> None:
    dt = _parse_timestamp(timestamp)

    if sensor_type == "moisture":
        moisture = value
        temperature = None
    elif sensor_type == "temperature":
        # Schema requires moisture NOT NULL; use sentinel because this row
        # represents a temperature-only reading. A migration could make
        # moisture nullable or add a generic metric_type column.
        moisture = -1.0
        temperature = value
    else:
        moisture = value
        temperature = None

    await db.execute(
        """
        INSERT INTO sensor_readings (timestamp, zone_id, sensor_id, moisture, temperature)
        VALUES ($1, $2, $3, $4, $5)
        """,
        dt,
        zone_id,
        sensor_id,
        moisture,
        temperature,
    )


async def insert_data_quality_event(anomaly: Dict[str, Any]) -> None:
    dt = _parse_timestamp(anomaly.get("timestamp"))

    await db.execute(
        """
        INSERT INTO data_quality_events (
            timestamp, zone_id, sensor_id, event_type, event_value,
            expected_min, expected_max, severity, details
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        dt,
        anomaly["zone_id"],
        anomaly["sensor_id"],
        anomaly["event_type"],
        anomaly.get("event_value"),
        anomaly.get("expected_min"),
        anomaly.get("expected_max"),
        anomaly.get("severity", "warning"),
        anomaly.get("details"),
    )
