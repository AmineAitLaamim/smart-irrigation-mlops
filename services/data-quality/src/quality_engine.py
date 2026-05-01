import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .database import db, stats
from .metrics import (
    anomalies_detected_total,
    rule_eval_duration_seconds,
    stuck_value_detected_total,
    sudden_jump_detected_total,
    flatline_detected_total,
    readings_checked_total,
    active_rules_gauge,
)

# Cache rules for a short window to avoid hammering the DB
_RULES_CACHE: List[Dict[str, Any]] = []
_RULES_CACHE_AT: Optional[datetime] = None
_RULES_TTL_SECONDS = int(os.getenv("QUALITY_RULES_CACHE_TTL", "30"))


def _parse_timestamp(ts: Any) -> datetime:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    return datetime.utcnow()


async def _load_active_rules(force: bool = False) -> List[Dict[str, Any]]:
    global _RULES_CACHE, _RULES_CACHE_AT
    now = datetime.utcnow()
    if not force and _RULES_CACHE_AT and (now - _RULES_CACHE_AT).seconds < _RULES_TTL_SECONDS:
        return _RULES_CACHE

    rows = await db.fetch(
        """
        SELECT rule_id, rule_name, rule_type, sensor_type, zone_id,
               parameters, severity, active
        FROM quality_rules
        WHERE active = TRUE
        ORDER BY rule_type, rule_name
        """
    )
    _RULES_CACHE = [dict(r) for r in rows]
    _RULES_CACHE_AT = now
    active_rules_gauge.set(len(_RULES_CACHE))
    return _RULES_CACHE


async def _get_recent_readings(
    zone_id: str,
    sensor_id: str,
    minutes: int,
) -> List[Dict[str, Any]]:
    """Fetch the last N minutes of readings for a sensor."""
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    rows = await db.fetch(
        """
        SELECT timestamp, moisture, temperature
        FROM sensor_readings
        WHERE zone_id = $1
          AND sensor_id = $2
          AND timestamp >= $3
        ORDER BY timestamp DESC
        """,
        zone_id,
        sensor_id,
        cutoff,
    )
    return [
        {
            "timestamp": r["timestamp"],
            "moisture": r["moisture"],
            "temperature": r["temperature"],
        }
        for r in rows
    ]


def _get_value(reading: Dict[str, Any], sensor_type: str) -> Optional[float]:
    if sensor_type == "moisture":
        return reading["moisture"]
    if sensor_type == "temperature":
        temp = reading["temperature"]
        return temp if temp is not None and temp != -1.0 else None
    # Fallback: try either column
    val = reading.get(sensor_type)
    if val is not None:
        return val
    return reading.get("moisture")


def _matches_rule(rule: Dict[str, Any], zone_id: str, sensor_id: str, sensor_type: str) -> bool:
    r_zone = rule.get("zone_id")
    r_sensor = rule.get("sensor_type")
    if r_zone is not None and r_zone != zone_id:
        return False
    if r_sensor is not None and r_sensor != sensor_type:
        return False
    return True


def _make_anomaly(
    zone_id: str,
    sensor_id: str,
    timestamp: Any,
    event_type: str,
    event_value: Any,
    severity: str,
    details: str,
    expected_min: Optional[float] = None,
    expected_max: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "zone_id": zone_id,
        "sensor_id": sensor_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "event_value": event_value,
        "severity": severity,
        "details": details,
        "expected_min": expected_min,
        "expected_max": expected_max,
    }


async def _check_stuck_value(
    rule: Dict[str, Any],
    zone_id: str,
    sensor_id: str,
    sensor_type: str,
    current_value: float,
    timestamp: Any,
) -> Optional[Dict[str, Any]]:
    params = rule["parameters"]
    consecutive = params.get("consecutive_count", 5)
    tolerance = params.get("tolerance", 0.001)

    # Look back far enough to cover the consecutive count
    readings = await _get_recent_readings(zone_id, sensor_id, minutes=60)
    if not readings:
        return None

    values = [_get_value(r, sensor_type) for r in readings]
    values = [v for v in values if v is not None]
    if len(values) < consecutive:
        return None

    # Check the most recent `consecutive` readings (including current)
    window = values[:consecutive]
    if all(abs(v - current_value) <= tolerance for v in window):
        stuck_value_detected_total.labels(zone_id=zone_id, sensor_id=sensor_id).inc()
        return _make_anomaly(
            zone_id, sensor_id, timestamp,
            event_type="stuck_value",
            event_value=current_value,
            severity=rule["severity"],
            details=f"Sensor stuck at ~{current_value} for {consecutive} consecutive readings (tolerance={tolerance})",
        )
    return None


async def _check_sudden_jump(
    rule: Dict[str, Any],
    zone_id: str,
    sensor_id: str,
    sensor_type: str,
    current_value: float,
    timestamp: Any,
) -> Optional[Dict[str, Any]]:
    params = rule["parameters"]
    max_delta = params.get("max_delta")
    max_pct = params.get("max_pct_change")

    prev = await db.fetchrow(
        """
        SELECT moisture, temperature
        FROM sensor_readings
        WHERE zone_id = $1
          AND sensor_id = $2
          AND timestamp < $3
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        zone_id,
        sensor_id,
        _parse_timestamp(timestamp),
    )
    if not prev:
        return None

    prev_val = _get_value(dict(prev), sensor_type)
    if prev_val is None or prev_val == 0:
        return None

    delta = abs(current_value - prev_val)
    pct_change = (delta / abs(prev_val)) * 100 if prev_val != 0 else 0

    exceeded = False
    detail_parts = []
    if max_delta is not None and delta > max_delta:
        exceeded = True
        detail_parts.append(f"delta {delta:.4f} > max {max_delta}")
    if max_pct is not None and pct_change > max_pct:
        exceeded = True
        detail_parts.append(f"pct_change {pct_change:.1f}% > max {max_pct}%")

    if exceeded:
        sudden_jump_detected_total.labels(zone_id=zone_id, sensor_id=sensor_id).inc()
        return _make_anomaly(
            zone_id, sensor_id, timestamp,
            event_type="sudden_jump",
            event_value=current_value,
            severity=rule["severity"],
            details=f"Sudden jump from {prev_val:.4f} to {current_value:.4f}: {', '.join(detail_parts)}",
            expected_min=prev_val - (max_delta or 0),
            expected_max=prev_val + (max_delta or 0),
        )
    return None


async def _check_flatline(
    rule: Dict[str, Any],
    zone_id: str,
    sensor_id: str,
    sensor_type: str,
    current_value: float,
    timestamp: Any,
) -> Optional[Dict[str, Any]]:
    params = rule["parameters"]
    window_minutes = params.get("window_minutes", 30)
    max_variance = params.get("max_variance", 0.0001)

    readings = await _get_recent_readings(zone_id, sensor_id, minutes=window_minutes)
    values = [_get_value(r, sensor_type) for r in readings]
    values = [v for v in values if v is not None]

    if len(values) < 3:
        return None

    mean_v = sum(values) / len(values)
    variance = sum((x - mean_v) ** 2 for x in values) / (len(values) - 1) if len(values) > 1 else 0

    if variance <= max_variance:
        flatline_detected_total.labels(zone_id=zone_id, sensor_id=sensor_id).inc()
        return _make_anomaly(
            zone_id, sensor_id, timestamp,
            event_type="flatline",
            event_value=current_value,
            severity=rule["severity"],
            details=f"Flatline over {window_minutes}m: variance={variance:.6f} <= {max_variance} ({len(values)} readings)",
        )
    return None


async def _check_rate_of_change(
    rule: Dict[str, Any],
    zone_id: str,
    sensor_id: str,
    sensor_type: str,
    current_value: float,
    timestamp: Any,
) -> Optional[Dict[str, Any]]:
    params = rule["parameters"]
    window_minutes = params.get("window_minutes", 15)
    max_rate_per_min = params.get("max_rate_per_min", 2.0)

    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    rows = await db.fetch(
        """
        SELECT timestamp, moisture, temperature
        FROM sensor_readings
        WHERE zone_id = $1
          AND sensor_id = $2
          AND timestamp >= $3
        ORDER BY timestamp
        """,
        zone_id,
        sensor_id,
        cutoff,
    )
    if len(rows) < 2:
        return None

    first = dict(rows[0])
    last = dict(rows[-1])
    first_val = _get_value(first, sensor_type)
    last_val = _get_value(last, sensor_type)
    if first_val is None or last_val is None:
        return None

    time_diff_min = (last["timestamp"] - first["timestamp"]).total_seconds() / 60.0
    if time_diff_min <= 0:
        return None

    rate = abs(last_val - first_val) / time_diff_min
    if rate > max_rate_per_min:
        return _make_anomaly(
            zone_id, sensor_id, timestamp,
            event_type="rate_of_change",
            event_value=current_value,
            severity=rule["severity"],
            details=f"Rate of change {rate:.4f}/min exceeds {max_rate_per_min}/min over {time_diff_min:.1f}min",
            expected_max=max_rate_per_min,
        )
    return None


_RULE_TYPE_HANDLERS = {
    "stuck_value": _check_stuck_value,
    "sudden_jump": _check_sudden_jump,
    "flatline": _check_flatline,
    "rate_of_change": _check_rate_of_change,
}


async def evaluate_reading(
    zone_id: str,
    sensor_id: str,
    timestamp: Any,
    value: float,
    sensor_type: str,
    is_valid: bool = True,
) -> List[Dict[str, Any]]:
    """Run all applicable quality rules against a single reading."""
    readings_checked_total.labels(
        zone_id=zone_id, sensor_id=sensor_id, sensor_type=sensor_type
    ).inc()

    anomalies: List[Dict[str, Any]] = []
    rules = await _load_active_rules()

    for rule in rules:
        if not _matches_rule(rule, zone_id, sensor_id, sensor_type):
            continue
        handler = _RULE_TYPE_HANDLERS.get(rule["rule_type"])
        if not handler:
            continue

        start = datetime.utcnow()
        try:
            result = await handler(rule, zone_id, sensor_id, sensor_type, value, timestamp)
            if result:
                anomalies.append(result)
                anomalies_detected_total.labels(
                    rule_type=rule["rule_type"],
                    severity=rule["severity"],
                    zone_id=zone_id,
                    sensor_id=sensor_id,
                ).inc()
        except Exception as exc:
            await stats.increment(error=True)
            print(f"Rule {rule['rule_name']} failed for {zone_id}/{sensor_id}: {exc}")
        finally:
            elapsed = (datetime.utcnow() - start).total_seconds()
            rule_eval_duration_seconds.labels(rule_type=rule["rule_type"]).observe(elapsed)

        await stats.increment(rules=True)

    await stats.increment(checked=True, anomalies=len(anomalies) > 0)
    return anomalies


async def insert_quality_anomalies(anomalies: List[Dict[str, Any]]) -> None:
    """Persist detected anomalies to the data_quality_events hypertable."""
    if not anomalies:
        return

    values = [
        (
            _parse_timestamp(a["timestamp"]),
            a["zone_id"],
            a["sensor_id"],
            a["event_type"],
            a.get("event_value"),
            a.get("expected_min"),
            a.get("expected_max"),
            a["severity"],
            a.get("details"),
        )
        for a in anomalies
    ]

    await db.executemany(
        """
        INSERT INTO data_quality_events (
            timestamp, zone_id, sensor_id, event_type, event_value,
            expected_min, expected_max, severity, details
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        values,
    )


async def run_batch_scan(window_minutes: int = 60) -> int:
    """Batch malfunction detection: check all active sensors for flatlines
    over a longer window.  Returns number of anomalies written."""
    rows = await db.fetch(
        """
        SELECT zone_id, sensor_id, sensor_type
        FROM sensor_metadata
        WHERE active = TRUE
        ORDER BY zone_id, sensor_id
        """
    )
    total_anomalies = 0
    for row in rows:
        zone_id = row["zone_id"]
        sensor_id = row["sensor_id"]
        sensor_type = row["sensor_type"] or "moisture"
        try:
            # Pull latest reading in the window to use as the "current" value
            cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
            latest = await db.fetchrow(
                """
                SELECT timestamp, moisture, temperature
                FROM sensor_readings
                WHERE zone_id = $1 AND sensor_id = $2
                  AND timestamp >= $3
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                zone_id,
                sensor_id,
                cutoff,
            )
            if not latest:
                continue
            value = _get_value(dict(latest), sensor_type)
            if value is None:
                continue
            anomalies = await evaluate_reading(
                zone_id=zone_id,
                sensor_id=sensor_id,
                timestamp=latest["timestamp"],
                value=value,
                sensor_type=sensor_type,
                is_valid=True,
            )
            if anomalies:
                await insert_quality_anomalies(anomalies)
                total_anomalies += len(anomalies)
        except Exception as exc:
            await stats.increment(error=True)
            print(f"Batch scan error for {zone_id}/{sensor_id}: {exc}")
    return total_anomalies


async def update_sensor_health_gauge() -> None:
    """Update the Prometheus sensor_health gauge from the DB view."""
    from .metrics import sensor_health_status
    rows = await db.fetch("SELECT zone_id, sensor_id, sensor_type, health_status FROM v_sensor_health")
    mapping = {"healthy": 0, "degraded": 1, "unhealthy": 2}
    for r in rows:
        val = mapping.get(r["health_status"], -1)
        sensor_health_status.labels(
            zone_id=r["zone_id"],
            sensor_id=r["sensor_id"],
            sensor_type=r["sensor_type"] or "unknown",
        ).set(val)
