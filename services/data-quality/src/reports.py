from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .database import db


async def get_quality_summary(
    hours: int = 24,
    zone_id: Optional[str] = None,
    sensor_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return aggregate anomaly counts by type and severity."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    where_parts = ["timestamp >= $1"]
    params: List[Any] = [cutoff]
    if zone_id:
        where_parts.append(f"zone_id = ${len(params) + 1}")
        params.append(zone_id)
    if sensor_id:
        where_parts.append(f"sensor_id = ${len(params) + 1}")
        params.append(sensor_id)

    where_clause = " AND ".join(where_parts)

    rows = await db.fetch(
        f"""
        SELECT event_type, severity, COUNT(*) AS cnt
        FROM data_quality_events
        WHERE {where_clause}
        GROUP BY event_type, severity
        ORDER BY cnt DESC
        """,
        *params,
    )

    summary: Dict[str, Dict[str, int]] = {}
    total = 0
    for r in rows:
        et = r["event_type"]
        sev = r["severity"]
        cnt = r["cnt"]
        summary.setdefault(et, {})[sev] = cnt
        total += cnt

    return {
        "period_hours": hours,
        "zone_id": zone_id,
        "sensor_id": sensor_id,
        "total_anomalies": total,
        "breakdown": summary,
        "generated_at": datetime.utcnow().isoformat(),
    }


async def get_sensor_health(
    zone_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return per-sensor health status from the v_sensor_health view."""
    if zone_id:
        rows = await db.fetch(
            "SELECT * FROM v_sensor_health WHERE zone_id = $1 ORDER BY total_anomalies DESC",
            zone_id,
        )
    else:
        rows = await db.fetch("SELECT * FROM v_sensor_health ORDER BY total_anomalies DESC")

    return [
        {
            "zone_id": r["zone_id"],
            "sensor_id": r["sensor_id"],
            "sensor_type": r["sensor_type"],
            "active": r["active"],
            "critical_count": r["critical_count"],
            "warning_count": r["warning_count"],
            "total_anomalies": r["total_anomalies"],
            "health_status": r["health_status"],
        }
        for r in rows
    ]


async def get_hourly_metrics(
    hours: int = 24,
) -> List[Dict[str, Any]]:
    """Return hourly quality metrics from v_quality_metrics."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    rows = await db.fetch(
        """
        SELECT bucket, zone_id, event_type, severity, event_count, affected_sensors
        FROM v_quality_metrics
        WHERE bucket >= $1
        ORDER BY bucket DESC, event_count DESC
        """,
        cutoff,
    )
    return [
        {
            "bucket": r["bucket"].isoformat() if r["bucket"] else None,
            "zone_id": r["zone_id"],
            "event_type": r["event_type"],
            "severity": r["severity"],
            "event_count": r["event_count"],
            "affected_sensors": r["affected_sensors"],
        }
        for r in rows
    ]


async def get_active_rules() -> List[Dict[str, Any]]:
    """Return currently active quality rules."""
    rows = await db.fetch(
        """
        SELECT rule_id, rule_name, rule_type, sensor_type, zone_id,
               parameters, severity, active, created_at, updated_at
        FROM quality_rules
        WHERE active = TRUE
        ORDER BY rule_type, rule_name
        """
    )
    return [dict(r) for r in rows]


async def update_rule(
    rule_id: str,
    updates: Dict[str, Any],
) -> bool:
    """Update a quality rule (parameters, severity, active) without code changes."""
    allowed = {"parameters", "severity", "active", "rule_name"}
    set_parts = []
    params: List[Any] = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        set_parts.append(f"{key} = ${len(params) + 2}")
        params.append(value)
    if not set_parts:
        return False

    params.append(rule_id)
    query = f"""
        UPDATE quality_rules
        SET {', '.join(set_parts)}, updated_at = NOW()
        WHERE rule_id = ${len(params)}
        RETURNING rule_id
    """
    row = await db.fetchrow(query, *params)
    return row is not None
