# Sensor Simulator Documentation

## Overview

The Sensor Simulator generates realistic synthetic sensor data for the Smart Irrigation System. It simulates:
- **Soil moisture** readings with realistic depletion patterns
- **Temperature** readings with daily variation
- **Soil-specific behavior** based on soil type
- **Irrigation events** (responds to irrigation triggers from the controller)

**Location:** `services/sensor-simulator/src/`

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SENSOR SIMULATOR                                      │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                      Main Loop (every 10 seconds)                        │   │
│  │                                                                          │   │
│  │   1. Check Redis for irrigation events                                  │   │
│  │   2. Sync zones from User Service API (every 60 sec)                     │   │
│  │   3. Generate readings for all active sensors                            │   │
│  │   4. Publish to Redis channel "sensor:data"                              │   │
│  │   5. Sleep 10 seconds                                                    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    Zone & Sensor Management                            │   │
│  │                                                                          │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │   │
│  │   │   Zone 1   │  │   Zone 2    │  │   Zone 3    │                   │   │
│  │   │             │  │             │  │             │                   │   │
│  │   │ - s1        │  │ - s1        │  │ - s1        │                   │   │
│  │   │ - s2        │  │ - s2        │  │ - s2        │                   │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘                   │   │
│  │                                                                          │   │
│  │   Each zone: 2 sensors (for redundancy simulation)                     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  User Service   │    │     Redis      │    │   Irrigation   │
│                 │    │                 │    │   Controller   │
│  /v1/zones      │    │  sensor:data   │    │                 │
│  (get active    │    │   (output)     │    │irrigation:     │
│   zones)        │    │                 │    │ triggered      │
│                 │    │                 │    │   (input)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Components

### 1. SensorGenerator Class

Generates realistic sensor readings based on soil type.

**Key Properties:**
- `current_moisture` - Current moisture level (0-100%)
- `current_temperature` - Current temperature (°C)
- `depletion_base` - Base rate of moisture loss per tick
- `retention_variance` - Random variation in depletion
- `irrigating_ticks` - Counter for active irrigation

**Methods:**
```python
def generate_reading(self) -> SensorReading:
    # 1. Update temperature (slight warming trend)
    temp_delta = random.uniform(-0.2, 1.5)
    self.current_temperature = max(10.0, min(40.0, self.current_temperature + temp_delta))

    # 2. Calculate moisture depletion
    temp_factor = max(0.5, self.current_temperature / 20.0)
    demo_multiplier = 10.0  # Aggressive for demo
    depletion = (self.depletion_base + random_variance) * temp_factor * demo_multiplier

    # 3. Apply irrigation or depletion
    if self.irrigating_ticks > 0:
        self.current_moisture += random.uniform(5.0, 10.0)  # Increase
        self.irrigating_ticks -= 1
    else:
        self.current_moisture -= depletion  # Decrease

    # 4. Add sensor noise and return
    noise = random.uniform(-0.5, 0.5)
    return SensorReading(...)
```

### 2. Main Loop

Runs continuously, performing these tasks:

```python
while True:
    # 1. Check for irrigation events from Redis
    message = pubsub.get_message(IRRIGATION_CHANNEL)
    if message:
        zone_id = message["zone_id"]
        generators[zone_id].trigger_irrigation()

    # 2. Sync zones from API (every 60 seconds)
    if time elapsed > 60:
        active_zones = get_zones_from_api()
        add_new_generators()
        remove_inactive_generators()

    # 3. Generate and publish readings
    for each generator:
        reading = generate_reading()
        r.publish("sensor:data", reading.json())

    sleep(10 seconds)
```

---

## Soil Type Behavior

Each soil type has different moisture characteristics:

| Soil Type | Depletion Base | Initial Moisture | Behavior |
|------------|----------------|-------------------|----------|
| **Sand** | 0.6 | 35-45% | Fast drainage, low retention |
| **Sandy Loam** | 0.45 | 40-50% | Moderate drainage |
| **Loam** | 0.25 | 45-55% | Balanced |
| **Silty Loam** | 0.2 | 48-58% | Good retention |
| **Silt** | 0.18 | 50-60% | Slow drainage |
| **Clay Loam** | 0.15 | 52-62% | High retention |
| **Clay** | 0.1 | 55-65% | Very slow drainage |
| **Peat** | 0.05 | 60-70% | Extremely high retention |

**Moisture Depletion Formula:**
```
depletion = (depletion_base ± variance) × temperature_factor × demo_multiplier
```

---

## Data Model

### SensorReading

```python
class SensorReading(BaseModel):
    zone_id: str        # Zone identifier (e.g., "2")
    sensor_id: str       # Sensor identifier (e.g., "2-s1")
    moisture: float      # Moisture percentage (0-100)
    temperature: float  # Temperature in Celsius
    timestamp: str      # ISO 8601 timestamp
```

**Example JSON:**
```json
{
  "zone_id": "2",
  "sensor_id": "2-s1",
  "moisture": 48.32,
  "temperature": 22.45,
  "timestamp": "2026-05-03T12:00:00.123456Z"
}
```

---

## Output

### Redis Channel

The simulator publishes to `sensor:data` channel:

```python
r.publish("sensor:data", reading.model_dump_json())
```

### Consumer

The `data-ingestion` service consumes this channel and processes the data.

---

## Irrigation Response

When the irrigation controller triggers an irrigation event:

```
Irrigation Controller → Redis (irrigation:triggered)
        │
        ▼
Sensor Simulator subscribes to irrigation:triggered
        │
        ▼
For each sensor in zone:
    trigger_irrigation()  # Sets irrigating_ticks = 10
        │
        ▼
Next 10 readings:
    moisture += random(5.0, 10.0)  # Increase rapidly
    temperature -= random(0.5, 1.5)  # Slight cooling
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `USER_SERVICE_URL` | `http://user-service:5005` | User service API |
| `SENSOR_PUBLISH_INTERVAL` | `10.0` | Seconds between readings |
| `REDIS_CHANNEL_SENSOR_DATA` | `sensor:data` | Output channel |
| `REDIS_CHANNEL_IRRIGATION_TRIGGERED` | `irrigation:triggered` | Input channel |

### Docker Configuration

```yaml
sensor-simulator:
  image: sensor-simulator:latest
  environment:
    - REDIS_URL=redis://redis:6379/0
    - USER_SERVICE_URL=http://user-service:5005
    - SENSOR_PUBLISH_INTERVAL=10.0
  depends_on:
    - redis
    - user-service
```

---

## Simulation Logic

### Temperature Simulation

```python
# Slight warming trend with random variation
temp_delta = random.uniform(-0.2, 1.5)
self.current_temperature = max(10.0, min(40.0, self.current_temperature + temp_delta))
```

- Range: 10°C to 40°C
- Trend: Slight warming
- Variation: -0.2 to +1.5 per tick

### Moisture Simulation

```python
# Depletion based on soil type and temperature
temp_factor = max(0.5, self.current_temperature / 20.0)
depletion = depletion_base * temp_factor * demo_multiplier

# 10x multiplier for demo (makes irrigation trigger faster)
# In production, use multiplier=1.0
```

### Irrigation Effect

```python
if self.irrigating_ticks > 0:
    # Rapid moisture increase
    self.current_moisture += random.uniform(5.0, 10.0)
    # Slight cooling
    self.current_temperature -= random.uniform(0.5, 1.5)
    self.irrigating_ticks -= 1
```

### Natural Variation

```python
# 0.1% chance of natural moisture increase (rain)
if random.random() < 0.001:
    self.current_moisture += random.uniform(2.0, 5.0)
```

### Sensor Noise

```python
# Add realistic sensor noise
noise = random.uniform(-0.5, 0.5)
reported_moisture = current_moisture + noise
```

---

## Features

### 1. Dynamic Zone Discovery

The simulator fetches active zones from the User Service API every 60 seconds:
- New zones are automatically added
- Removed zones are automatically cleaned up

### 2. Multi-Sensor Per Zone

Each zone gets 2 sensors (s1 and s2) for redundancy:
- Independent moisture readings
- Simulates real-world sensor network

### 3. Soil-Specific Behavior

Different soil types have:
- Different depletion rates
- Different initial moisture levels
- Realistic moisture retention characteristics

### 4. Irrigation Response

When irrigation triggers:
- Moisture rapidly increases
- Temperature slightly decreases
- Continues for 10 ticks (100 seconds with 10s interval)

### 5. Realistic Variation

- Random noise on readings
- Natural moisture variation (rare rain events)
- Temperature trends

---

## Monitoring

### Log Messages

```
INFO - Starting sensor simulator... Connecting to Redis at redis://redis:6379/0
INFO - Successfully connected to Redis.
INFO - Subscribed to irrigation channel: irrigation:triggered
INFO - Syncing zones from API...
INFO - Initialized sensors for new zone: 2 (Soil: loam)
INFO - Irrigation triggered for zone 2. Increasing moisture!
DEBUG - Published 6 readings.
```

### Check Active Sensors

```python
# In the simulator code
generators = {
    "1": [sensor_s1, sensor_s2],
    "2": [sensor_s1, sensor_s2],
    "3": [sensor_s1, sensor_s2],
}
```

---

## Testing

### Manual Simulation

```bash
# Check Redis for sensor data
docker exec redis redis-cli
> SUBSCRIBE sensor:data

# Check irrigation channel
> SUBSCRIBE irrigation:triggered
```

### Batch Generation

For testing, use the batch generator:

```bash
# Generate 100 readings with 30-second interval
make generate-data count=100 interval=30

# Simulate 12 hours (1440 data points)
make fast-forward
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Input | User Service API (active zones) |
| Output | Redis `sensor:data` channel |
| Irrigation Input | Redis `irrigation:triggered` channel |
| Per Zone | 2 sensors (redundancy) |
| Tick Interval | 10 seconds (configurable) |
| Soil Types | 8 types (sand to peat) |
| Response | Moisture increases for 10 ticks after irrigation |

The Sensor Simulator provides realistic, dynamic sensor data that drives the entire Smart Irrigation system's ML pipeline and automated irrigation logic.