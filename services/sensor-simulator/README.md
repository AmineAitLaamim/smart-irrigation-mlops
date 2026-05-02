# Sensor Simulator

This service is responsible for generating realistic mock sensor telemetry (soil moisture and temperature) and streaming it into the smart-irrigation system for analysis and decision-making.

## Features
- **Dynamic Zone Discovery**: Periodically polls the `user-service` API to fetch all active zones and their configured soil types.
- **Realistic Soil Modeling**: Supports different moisture retention characteristics based on soil type (`sandy` depletes faster, `clay` retains longer).
- **Environmental Simulation**: Generates pseudo-random temperature curves and simulates unexpected rain/irrigation events.
- **Redundancy Simulation**: Automatically creates two sensors (`-s1` and `-s2`) for each discovered zone to simulate physical sensor redundancy.
- **Redis Pub/Sub Integration**: Pushes JSON-formatted sensor readings directly to the `sensor:data` Redis channel.

## Environment Variables
- `REDIS_URL`: Connection string for Redis (default: `redis://redis:6379/0`)
- `REDIS_CHANNEL_SENSOR_DATA`: Redis channel to publish to (default: `sensor:data`)
- `USER_SERVICE_URL`: URL to the user-service to fetch active zones (default: `http://user-service:5005`)
- `SENSOR_PUBLISH_INTERVAL`: Delay in seconds between generating each batch of readings (default: `10.0`)

## Usage
The service is automatically started as part of the `docker-compose.data.yml` stack.
```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.data.yml up -d --build sensor-simulator
```
