# Sensor Simulator

The **Sensor Simulator** is a critical data-generation component of the Smart Irrigation System. Since the system does not yet have physical IoT devices deployed in the field, this service acts as the digital twin of agricultural sensors, pumping realistic, pseudo-random telemetry into the data pipeline.

## System Architecture Role
- **Domain**: DataOps
- **Location**: `services/sensor-simulator`
- **Output**: Redis Pub/Sub (`sensor:data` channel)
- **Dependencies**: None (aside from querying the User Service for configuration).

## Features

### 1. Dynamic Zone Discovery
Unlike static configurations, the simulator fetches active zones dynamically from the `user-service` API (`http://user-service:5005/v1/zones`). This means if you create a new zone via the Web Dashboard, the simulator will automatically detect it within 60 seconds and start generating data for it.

### 2. Realistic Soil Modeling
The simulator adjusts moisture retention based on the `soil_type` associated with the zone:
- **Sandy**: Drains moisture very quickly (highest depletion rate).
- **Loam**: Balanced moisture retention (medium depletion rate).
- **Clay**: Retains water for a long time (lowest depletion rate).

### 3. Environmental Engine
- **Temperature Drift**: Simulates ambient temperature changes using a bounded random walk (between 10°C and 40°C). Higher temperatures linearly increase the soil moisture depletion rate.
- **Weather Events**: Incorporates a random 5% probability per tick to simulate sudden "rain" or manual irrigation, instantly boosting the moisture levels to keep the system dynamic and test the prediction models.

### 4. Sensor Redundancy
For each configured zone, the simulator spins up **two** virtual sensors (e.g., `zone-id-s1` and `zone-id-s2`). This mimics real-world redundancy, allowing the downstream Data Quality service to detect if one sensor malfunctions or drifts away from the cluster average.

## Payload Schema
The service publishes JSON strings to the Redis channel with the following format (validated downstream by Pydantic):

```json
{
  "zone_id": "north-garden-1",
  "sensor_id": "north-garden-1-s1",
  "moisture": 45.23,
  "temperature": 22.4,
  "timestamp": "2026-05-02T12:00:00Z"
}
```

## Running the Simulator
The simulator is packaged as part of the data stack and is managed via Docker Compose:
```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.data.yml up -d sensor-simulator
```
