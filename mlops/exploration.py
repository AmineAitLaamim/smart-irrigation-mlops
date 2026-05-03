from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any

from .settings import settings

if TYPE_CHECKING:
    import asyncpg


EXPLORATION_REPORT_PATH = Path("docs/ML_EXPLORATION.md")


def _format_float(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


async def collect_summary(connection: "asyncpg.Connection") -> dict[str, Any]:
    totals = await connection.fetchrow(
        """
        SELECT
            COUNT(*) AS reading_count,
            COUNT(DISTINCT zone_id) AS zone_count,
            COUNT(DISTINCT sensor_id) AS sensor_count,
            MIN(timestamp) AS min_timestamp,
            MAX(timestamp) AS max_timestamp,
            AVG(moisture) AS avg_moisture,
            AVG(temperature) AS avg_temperature
        FROM sensor_readings
        """
    )
    by_soil = await connection.fetch(
        """
        SELECT
            z.soil_type,
            COUNT(*) AS reading_count,
            AVG(sr.moisture) AS avg_moisture,
            AVG(sr.temperature) AS avg_temperature
        FROM sensor_readings sr
        JOIN zones z ON z.zone_id = sr.zone_id
        GROUP BY z.soil_type
        ORDER BY reading_count DESC, z.soil_type
        """
    )
    monthly = await connection.fetch(
        """
        SELECT
            DATE_TRUNC('month', timestamp) AS month_start,
            AVG(moisture) AS avg_moisture,
            AVG(temperature) AS avg_temperature,
            COUNT(*) AS reading_count
        FROM sensor_readings
        GROUP BY month_start
        ORDER BY month_start
        """
    )
    sensor_health = await connection.fetch(
        """
        SELECT
            sensor_id,
            zone_id,
            COUNT(*) AS reading_count,
            STDDEV(moisture) AS moisture_stddev
        FROM sensor_readings
        GROUP BY sensor_id, zone_id
        ORDER BY reading_count DESC, sensor_id
        LIMIT 10
        """
    )
    return {
        "totals": dict(totals) if totals else {},
        "by_soil": [dict(row) for row in by_soil],
        "monthly": [dict(row) for row in monthly],
        "sensor_health": [dict(row) for row in sensor_health],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    totals = summary.get("totals", {})
    by_soil = summary.get("by_soil", [])
    monthly = summary.get("monthly", [])
    sensor_health = summary.get("sensor_health", [])

    soil_lines = "\n".join(
        f"| {row['soil_type']} | {row['reading_count']} | {_format_float(row['avg_moisture'])} | {_format_float(row['avg_temperature'])} |"
        for row in by_soil
    ) or "| n/a | 0 | n/a | n/a |"
    monthly_lines = "\n".join(
        f"| {row['month_start'].date()} | {row['reading_count']} | {_format_float(row['avg_moisture'])} | {_format_float(row['avg_temperature'])} |"
        for row in monthly
    ) or "| n/a | 0 | n/a | n/a |"
    sensor_lines = "\n".join(
        f"| {row['sensor_id']} | {row['zone_id']} | {row['reading_count']} | {_format_float(row['moisture_stddev'])} |"
        for row in sensor_health
    ) or "| n/a | n/a | 0 | n/a |"

    generated_at = datetime.now(timezone.utc).isoformat()
    return dedent(
        f"""\
        # ML Exploration Report

        Generated at: `{generated_at}`

        ## Summary

        - Total readings: `{totals.get("reading_count", 0)}`
        - Zones covered: `{totals.get("zone_count", 0)}`
        - Sensors covered: `{totals.get("sensor_count", 0)}`
        - Data range: `{totals.get("min_timestamp")}` -> `{totals.get("max_timestamp")}`
        - Average moisture: `{totals.get("avg_moisture")}`
        - Average temperature: `{totals.get("avg_temperature")}`

        ## Moisture Distribution by Soil Type

        | Soil Type | Readings | Avg Moisture | Avg Temperature |
        | --- | ---: | ---: | ---: |
        {soil_lines}

        ## Seasonal Patterns

        | Month | Readings | Avg Moisture | Avg Temperature |
        | --- | ---: | ---: | ---: |
        {monthly_lines}

        ## Sensor Reliability Snapshot

        | Sensor ID | Zone ID | Readings | Moisture Stddev |
        | --- | --- | ---: | ---: |
        {sensor_lines}
        """
    )


async def generate_report(output_path: Path = EXPLORATION_REPORT_PATH) -> Path:
    import asyncpg

    connection = await asyncpg.connect(settings.database_url)
    try:
        summary = await collect_summary(connection)
    finally:
        await connection.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(summary), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an ML exploration report.")
    parser.add_argument(
        "--output",
        default=str(EXPLORATION_REPORT_PATH),
        help="Path to the generated markdown report.",
    )
    args = parser.parse_args()
    path = asyncio.run(generate_report(Path(args.output)))
    print(path)


if __name__ == "__main__":
    main()
