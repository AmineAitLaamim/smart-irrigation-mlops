import math
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
try:
    from .database import db, stats
    from .feature_computation import (
        ROLLUP_WINDOWS,
        compute_window_features,
        normalize_sensor_rows,
        parse_window_to_interval,
        serialize_feature_payload,
    )
except (ImportError, ValueError):
    from database import db, stats  # type: ignore
    from feature_computation import (  # type: ignore
        ROLLUP_WINDOWS,
        compute_window_features,
        normalize_sensor_rows,
        parse_window_to_interval,
        serialize_feature_payload,
    )

OUTLIER_ZSCORE_THRESHOLD = float(os.getenv("OUTLIER_ZSCORE_THRESHOLD", "3.0"))


def _parse_timestamp(ts: Any) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    return datetime.utcnow()


def _deduplicate(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Average duplicate readings at the same timestamp."""
    grouped = defaultdict(list)
    for r in records:
        key = (r["zone_id"], r["sensor_id"], r["timestamp"])
        grouped[key].append(r)

    result = []
    for (zone_id, sensor_id, ts), group in grouped.items():
        moistures = [r["moisture"] for r in group]
        avg_moisture = sum(moistures) / len(moistures)

        temps = [
            r["temperature"]
            for r in group
            if r["temperature"] is not None and r["temperature"] != -1.0
        ]
        avg_temp = sum(temps) / len(temps) if temps else None

        result.append({
            "zone_id": zone_id,
            "sensor_id": sensor_id,
            "timestamp": ts,
            "moisture": avg_moisture,
            "temperature": avg_temp,
        })

    result.sort(key=lambda r: r["timestamp"])
    return result


def _handle_nulls(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Forward-fill missing temperature values."""
    last_temp = None
    for r in records:
        if r["temperature"] is not None:
            last_temp = r["temperature"]
        else:
            r["temperature"] = last_temp
    return records


def _smooth_outliers(records: List[Dict[str, Any]], threshold: float = OUTLIER_ZSCORE_THRESHOLD) -> List[Dict[str, Any]]:
    """Cap extreme values using z-score smoothing."""
    if len(records) < 2:
        return records

    moistures = [r["moisture"] for r in records]
    mean_m = sum(moistures) / len(moistures)
    variance_m = sum((x - mean_m) ** 2 for x in moistures) / (len(moistures) - 1)
    std_m = math.sqrt(variance_m) if variance_m > 0 else 0

    temps = [r["temperature"] for r in records if r["temperature"] is not None]
    mean_t = sum(temps) / len(temps) if temps else 0
    variance_t = sum((x - mean_t) ** 2 for x in temps) / (len(temps) - 1) if len(temps) > 1 else 0
    std_t = math.sqrt(variance_t) if variance_t > 0 else 0

    smoothed_count = 0
    for r in records:
        if std_m > 0 and abs(r["moisture"] - mean_m) / std_m > threshold:
            r["moisture"] = mean_m
            smoothed_count += 1
        if r["temperature"] is not None and std_t > 0 and abs(r["temperature"] - mean_t) / std_t > threshold:
            r["temperature"] = mean_t
            smoothed_count += 1

    if smoothed_count:
        stats.anomalies_smoothed += smoothed_count
    return records


async def clean_raw_data(
    zone_id: str,
    sensor_id: str,
    start_time: datetime,
    end_time: datetime,
) -> List[Dict[str, Any]]:
    """Extract and clean raw sensor readings for a zone/sensor."""
    rows = await db.fetch(
        """
        SELECT timestamp, zone_id, sensor_id, moisture, temperature
        FROM sensor_readings
        WHERE zone_id = $1
          AND sensor_id = $2
          AND timestamp >= $3
          AND timestamp < $4
        ORDER BY timestamp
        """,
        zone_id,
        sensor_id,
        start_time,
        end_time,
    )

    records = [
        {
            "timestamp": row["timestamp"],
            "zone_id": row["zone_id"],
            "sensor_id": row["sensor_id"],
            "moisture": row["moisture"],
            "temperature": row["temperature"],
        }
        for row in rows
    ]

    records = _deduplicate(records)
    records = _handle_nulls(records)
    records = _smooth_outliers(records)

    await stats.increment(processed=len(records))
    return records


async def compute_hourly_rollup(zone_id: str, sensor_id: str, hour: Optional[datetime] = None) -> None:
    """Aggregate raw data into hourly rollups."""
    if hour is None:
        hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    await db.execute(
        """
        INSERT INTO hourly_rollup (
            hour_start, zone_id, sensor_id,
            avg_moisture, min_moisture, max_moisture, std_moisture, count_moisture,
            avg_temperature, min_temperature, max_temperature, std_temperature, count_temperature
        )
        SELECT
            time_bucket('1 hour', timestamp) AS bucket,
            zone_id,
            sensor_id,
            AVG(moisture) AS avg_moisture,
            MIN(moisture) AS min_moisture,
            MAX(moisture) AS max_moisture,
            STDDEV(moisture) AS std_moisture,
            COUNT(*) AS count_moisture,
            AVG(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS avg_temperature,
            MIN(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS min_temperature,
            MAX(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS max_temperature,
            STDDEV(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS std_temperature,
            COUNT(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS count_temperature
        FROM sensor_readings
        WHERE zone_id = $1
          AND sensor_id = $2
          AND timestamp >= $3
          AND timestamp < $3 + INTERVAL '1 hour'
        GROUP BY bucket, zone_id, sensor_id
        ON CONFLICT (hour_start, zone_id, sensor_id) DO UPDATE
            SET avg_moisture      = EXCLUDED.avg_moisture,
                min_moisture      = EXCLUDED.min_moisture,
                max_moisture      = EXCLUDED.max_moisture,
                std_moisture      = EXCLUDED.std_moisture,
                count_moisture    = EXCLUDED.count_moisture,
                avg_temperature   = EXCLUDED.avg_temperature,
                min_temperature   = EXCLUDED.min_temperature,
                max_temperature   = EXCLUDED.max_temperature,
                std_temperature   = EXCLUDED.std_temperature,
                count_temperature = EXCLUDED.count_temperature
        """,
        zone_id,
        sensor_id,
        hour,
    )
    await stats.increment(rollups=True)


async def compute_daily_rollup(zone_id: str, sensor_id: str, day: Optional[datetime] = None) -> None:
    """Aggregate raw data into daily rollups."""
    if day is None:
        day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    await db.execute(
        """
        INSERT INTO daily_rollup (
            day_start, zone_id, sensor_id,
            avg_moisture, min_moisture, max_moisture, std_moisture, count_moisture,
            avg_temperature, min_temperature, max_temperature, std_temperature, count_temperature
        )
        SELECT
            time_bucket('1 day', timestamp) AS bucket,
            zone_id,
            sensor_id,
            AVG(moisture) AS avg_moisture,
            MIN(moisture) AS min_moisture,
            MAX(moisture) AS max_moisture,
            STDDEV(moisture) AS std_moisture,
            COUNT(*) AS count_moisture,
            AVG(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS avg_temperature,
            MIN(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS min_temperature,
            MAX(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS max_temperature,
            STDDEV(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS std_temperature,
            COUNT(temperature) FILTER (WHERE temperature IS NOT NULL AND temperature != -1.0) AS count_temperature
        FROM sensor_readings
        WHERE zone_id = $1
          AND sensor_id = $2
          AND timestamp >= $3
          AND timestamp < $3 + INTERVAL '1 day'
        GROUP BY bucket, zone_id, sensor_id
        ON CONFLICT (day_start, zone_id, sensor_id) DO UPDATE
            SET avg_moisture      = EXCLUDED.avg_moisture,
                min_moisture      = EXCLUDED.min_moisture,
                max_moisture      = EXCLUDED.max_moisture,
                std_moisture      = EXCLUDED.std_moisture,
                count_moisture    = EXCLUDED.count_moisture,
                avg_temperature   = EXCLUDED.avg_temperature,
                min_temperature   = EXCLUDED.min_temperature,
                max_temperature   = EXCLUDED.max_temperature,
                std_temperature   = EXCLUDED.std_temperature,
                count_temperature = EXCLUDED.count_temperature
        """,
        zone_id,
        sensor_id,
        day,
    )
    await stats.increment(rollups=True)


async def compute_rolling_features(
    zone_id: str,
    sensor_id: str,
    windows: Optional[List[str]] = None,
) -> Dict[str, float]:
    """Compute rolling-window features and store them."""
    if windows is None:
        windows = ROLLUP_WINDOWS

    now = datetime.utcnow()
    all_features: Dict[str, float] = {}
    computed_at = now
    insert_values = []
    zone_row = await db.fetchrow(
        """
        SELECT soil_type
        FROM zones
        WHERE zone_id = $1
        """,
        zone_id,
    )
    soil_type = zone_row["soil_type"] if zone_row else None

    for window in windows:
        interval = parse_window_to_interval(window)
        start = now - interval

        rows = await db.fetch(
            """
            SELECT moisture, temperature
            FROM sensor_readings
            WHERE zone_id = $1
              AND sensor_id = $2
              AND timestamp >= $3
              AND timestamp <= $4
            ORDER BY timestamp
            """,
            zone_id,
            sensor_id,
            start,
            now,
        )
        moisture_values, temperature_values = normalize_sensor_rows([dict(row) for row in rows])
        features = compute_window_features(
            window,
            moisture_values=moisture_values,
            temperature_values=temperature_values,
            soil_type=soil_type,
        )
        insert_values.extend(
            [
                (
                    computed_at,
                    zone_id,
                    sensor_id,
                    feature.window_size,
                    feature.feature_name,
                    feature.feature_value,
                    feature.model_version,
                )
                for feature in features
            ]
        )
        all_features.update(serialize_feature_payload(features))

    if insert_values:
        await db.executemany(
            """
            INSERT INTO feature_references (
                computed_at, zone_id, sensor_id, window_size, 
                feature_name, feature_value, model_version
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT DO NOTHING
            """,
            insert_values,
        )
        for _ in insert_values:
            await stats.increment(features=True)

    return all_features


def _parse_window_to_interval(window: str) -> timedelta:
    """Convert a window string like '30m', '1h', '3h', '24h' to a timedelta."""
    return parse_window_to_interval(window)


async def get_active_sensors() -> List[Tuple[str, str]]:
    """Return list of (zone_id, sensor_id) pairs that are active."""
    rows = await db.fetch(
        """
        SELECT zone_id, sensor_id
        FROM sensor_metadata
        WHERE active = TRUE
        ORDER BY zone_id, sensor_id
        """
    )
    return [(r["zone_id"], r["sensor_id"]) for r in rows]


async def run_batch() -> None:
    """Batch ETL: compute rollups and rolling features for all active sensors."""
    sensors = await get_active_sensors()
    now = datetime.utcnow()

    for zone_id, sensor_id in sensors:
        try:
            # Hourly rollup for the current hour
            hour = now.replace(minute=0, second=0, microsecond=0)
            await compute_hourly_rollup(zone_id, sensor_id, hour)

            # Daily rollup for the current day
            day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            await compute_daily_rollup(zone_id, sensor_id, day)

            # Rolling features for all configured windows
            await compute_rolling_features(zone_id, sensor_id)
        except Exception as exc:
            await stats.increment(error=True)
            print(f"Batch ETL error for {zone_id}/{sensor_id}: {exc}")


async def run_streaming(zone_id: str, sensor_id: str) -> Dict[str, float]:
    """Streaming ETL: triggered by a single ingestion event."""
    try:
        features = await compute_rolling_features(zone_id, sensor_id)
        return features
    except Exception as exc:
        await stats.increment(error=True)
        print(f"Streaming ETL error for {zone_id}/{sensor_id}: {exc}")
        return {}
