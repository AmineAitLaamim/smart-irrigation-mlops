# Smart Irrigation System - Complete Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Irrigation Controller Service](#irrigation-controller-service)
3. [Airflow DAG - Prediction Generation](#airflow-dag---prediction-generation)
4. [Database Schema](#database-schema)
5. [Redis Channels](#redis-channels)
6. [Complete Flow Diagram](#complete-flow-diagram)
7. [Event Lifecycle](#event-lifecycle)
8. [Configuration](#configuration)
9. [Edge Cases](#edge-cases)

---

## 1. System Overview

The smart irrigation system is a fully automated MLOps pipeline that:

1. **Generates predictions** via scheduled Airflow DAG
2. **Publishes predictions** to Redis
3. **Evaluates predictions** against zone thresholds
4. **Triggers irrigation** autonomously when moisture is below threshold
5. **Notifies** stakeholders of irrigation events

### Architecture Summary

| Component | Role | Key Technology |
|-----------|------|----------------|
| Airflow DAG | Generate predictions | Python, asyncpg, httpx, Redis |
| irrigation-controller | Evaluate & trigger | FastAPI, asyncpg, Redis pubsub |
| sensor-simulator | Simulate sensor data | Redis publisher |
| notification-service | Alert users | Redis subscriber |
| database | Store events/data | TimescaleDB (PostgreSQL) |
| model-server | Serve ML predictions | MLflow |
| Redis | Message broker | Pub/Sub |

---

## 2. Irrigation Controller Service

**Location:** `services/irrigation-controller/src/main.py`

The Irrigation Controller is a FastAPI service that subscribes to Redis and automatically triggers irrigation when predicted moisture falls below zone thresholds.

### 2.1 Redis Subscription

The service connects to Redis using async pubsub:

```python
# Connection setup
async def connect(self) -> None:
    self.db_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)
    self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    self.pubsub = self.redis_client.pubsub()
    await self.pubsub.subscribe(REDIS_CHANNEL_PREDICTIONS_NEW)
```

### 2.2 Message Listener

The controller uses async iterator pattern to listen for messages:

```python
async def run(self) -> None:
    self._running = True
    try:
        async for message in self.pubsub.listen():
            if not self._running:
                break
            if message.get("type") == "message":
                try:
                    payload = json.loads(message["data"])
                    await self.evaluate_prediction(payload)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
    except asyncio.CancelledError:
        pass
```

### 2.3 Prediction Evaluation Logic

This is the core logic that decides whether to trigger irrigation:

```python
async def evaluate_prediction(self, payload: dict[str, Any]) -> dict[str, Any] | None:
    zone_id = payload["zone_id"]
    prediction = float(payload["prediction"])
    
    # 1. Fetch zone thresholds from database
    thresholds = await self._zone_thresholds(zone_id)
    if not thresholds:
        logger.debug(f"No thresholds found for zone {zone_id}")
        return None

    # 2. Log for debugging
    logger.debug(f"Zone {zone_id}: prediction={prediction}, threshold_min={thresholds['moisture_min']}")

    # 3. Check if prediction meets minimum threshold
    # If prediction >= moisture_min, moisture is adequate - no irrigation needed
    if prediction >= thresholds["moisture_min"]:
        return None

    # 4. Deduplication: check for recent events in last 10 minutes
    # Prevents multiple triggers from multiple sensors in same zone
    if await self._recent_event_exists(zone_id, minutes=10):
        logger.debug(f"Skipping irrigation for zone {zone_id}: recent event exists")
        return None

    # 5. Calculate deficit and recommended volume
    # deficit = moisture_min - prediction (how much moisture is needed)
    deficit = max(0.0, thresholds["moisture_min"] - prediction)
    # volume = deficit * 100 (convert to liters, assuming 100 units per deficit)
    recommended_volume = round(deficit * 100, 3)

    # 6. Create event with pending status
    event = {
        "zone_id": zone_id,
        "trigger_reason": "predicted_moisture_below_threshold",
        "recommended_volume": recommended_volume,
        "predicted_moisture": prediction,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await self.store_event(event)
    logger.info(f"Irrigation TRIGGERED for zone {zone_id}: volume={recommended_volume}")

    # 7. Schedule autonomous execution (runs in background)
    asyncio.create_task(self._execute_irrigation(event["zone_id"], event["recommended_volume"]))

    return event
```

### 2.4 Threshold Checking

Thresholds are fetched from the zones table:

```python
async def _zone_thresholds(self, zone_id: str) -> dict[str, Any] | None:
    async with self.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT zone_id, moisture_min, moisture_max, soil_type
            FROM zones
            WHERE zone_id = $1
            """,
            zone_id,
        )
    return dict(row) if row else None
```

### 2.5 Deduplication Mechanism

Prevents rapid repeated triggers when multiple sensors in the same zone generate predictions:

```python
async def _recent_event_exists(self, zone_id: str, minutes: int = 10) -> bool:
    async with self.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM irrigation_events
            WHERE zone_id = $1
              AND triggered_at > NOW() - INTERVAL '10 minutes'
            LIMIT 1
            """,
            zone_id,
        )
    return row is not None
```

**Why this matters:**
- Zone 2 has 2 sensors (2-s1 and 2-s2)
- When Airflow runs, it publishes predictions for both sensors
- Without deduplication, 2 events would be created
- With deduplication, only 1 event is created within 10 minutes

### 2.6 Event Storage

Events are initially stored with status `pending`:

```python
async def store_event(self, event: dict[str, Any]) -> None:
    async with self.db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO irrigation_events (
                triggered_at,
                zone_id,
                trigger_reason,
                recommended_volume,
                status
            )
            VALUES ($1, $2, $3, $4, 'pending')
            """,
            datetime.now(timezone.utc),
            event["zone_id"],
            event["trigger_reason"],
            event["recommended_volume"],
        )
```

### 2.7 Autonomous Execution (pending → completed)

After creating the event, the controller schedules an automatic execution task:

```python
async def _execute_irrigation(self, zone_id: str, volume: float) -> None:
    # Wait 5 seconds (simulated execution time)
    await asyncio.sleep(5)

    async with self.db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE irrigation_events
            SET status = 'completed',
                actual_volume = $1,
                duration_seconds = 300,
                completed_at = NOW()
            WHERE id = (
                SELECT id FROM irrigation_events
                WHERE zone_id = $2 AND status = 'pending'
                ORDER BY triggered_at DESC
                LIMIT 1
            )
            """,
            volume,
            zone_id,
        )

    logger.info(f"Irrigation COMPLETED for zone {zone_id}: volume={volume}")

    # Publish completion event to Redis for notification service
    if self.redis_client:
        await self.redis_client.publish(
            "irrigation:triggered",
            json.dumps({
                "zone_id": zone_id,
                "status": "completed",
                "volume": volume,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
        )
```

**What happens:**
- Status changes from `pending` → `completed`
- `actual_volume` is set to the recommended volume
- `duration_seconds` is set to 300 (5 minutes)
- `completed_at` timestamp is recorded
- A message is published to `irrigation:triggered` for notifications

---

## 3. Airflow DAG - Prediction Generation

**Location:** `airflow/dags/smart_irrigation_dags.py`

The `scheduled_zone_predictions` function generates predictions for all active zones and publishes them to Redis.

### 3.1 Function Overview

```python
def scheduled_zone_predictions(**context):
    import asyncio
    import asyncpg
    import httpx
    import redis.asyncio as redis

    async def _run():
        # Connect to database and Redis
        conn = await asyncpg.connect(DATABASE_URL)
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)

        try:
            # Get all active zones and sensors
            zones = await conn.fetch(
                "SELECT DISTINCT zone_id, sensor_id FROM sensor_metadata WHERE active = TRUE"
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                for row in zones:
                    # 1. Get latest sensor reading
                    latest_reading = await conn.fetchrow(
                        """SELECT moisture FROM sensor_readings
                           WHERE zone_id = $1 AND sensor_id = $2
                           ORDER BY timestamp DESC LIMIT 1""",
                        row["zone_id"], row["sensor_id"]
                    )
                    if not latest_reading:
                        continue

                    # 2. Assemble feature vector
                    features = [
                        float(latest_reading["moisture"]),
                        0.0  # Default temperature
                    ]

                    # 3. Call model-server for prediction
                    response = await client.post(
                        f"{MODEL_SERVER_REST_URL}/v1/predict",
                        json={
                            "zone_id": row["zone_id"],
                            "sensor_id": row["sensor_id"],
                            "features": features,
                        },
                    )
                    payload = response.json()

                    # 4. Store prediction in database
                    await conn.execute(
                        """INSERT INTO model_predictions
                           (predicted_at, zone_id, model_version, prediction, confidence)
                           VALUES ($1, $2, $3, $4, $5)""",
                        datetime.utcnow(),
                        row["zone_id"],
                        payload["model_version"],
                        payload["predicted_moisture"],
                        payload["confidence_interval"][1] - payload["confidence_interval"][0],
                    )

                    # 5. PUBLISH to Redis for irrigation-controller
                    publish_payload = json.dumps({
                        "zone_id": row["zone_id"],
                        "sensor_id": row["sensor_id"],
                        "prediction": payload["predicted_moisture"],
                        "model_version": payload["model_version"],
                        "predicted_at": datetime.utcnow().isoformat(),
                    })
                    await redis_client.publish(REDIS_CHANNEL_PREDICTIONS_NEW, publish_payload)

        finally:
            await conn.close()
            await redis_client.close()

    asyncio.run(_run())
```

### 3.2 DAG Task Flow

The full DAG has 5 tasks:

```
prepare_dataset → train_candidate_models → evaluate_and_register → export_training_summary → scheduled_zone_predictions
```

The last task (`scheduled_zone_predictions`) publishes predictions to Redis.

---

## 4. Database Schema

### 4.1 zones Table

Defines irrigation zones and their thresholds:

```sql
CREATE TABLE IF NOT EXISTS zones (
    zone_id       VARCHAR(50)  PRIMARY KEY,
    zone_name     VARCHAR(200) NOT NULL,
    soil_type     VARCHAR(50)  NOT NULL,
    crop_type     VARCHAR(50)  NOT NULL,
    moisture_min  FLOAT        NOT NULL,  -- Threshold for triggering irrigation
    moisture_max  FLOAT        NOT NULL,  -- Upper bound for alerts
    min_plausible JSONB        NOT NULL DEFAULT '{}',
    max_plausible JSONB        NOT NULL DEFAULT '{}',
    active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

**Example data:**
```
 zone_id | zone_name | soil_type | crop_type | moisture_min | moisture_max
---------+-----------+-----------+-----------+---------------+--------------
 1       | Zone A    | loam      | corn      |            30 |           60
 2       | Zone B    | clay      | wheat     |            55 |           60
 3       | Zone C    | sandy     | barley    |            50 |           60
```

### 4.2 irrigation_events Table

Tracks irrigation trigger events:

```sql
CREATE TABLE IF NOT EXISTS irrigation_events (
    id                 BIGSERIAL,
    triggered_at       TIMESTAMPTZ  NOT NULL,
    zone_id            VARCHAR(50)  NOT NULL REFERENCES zones(zone_id),
    trigger_reason     VARCHAR(100) NOT NULL,
    recommended_volume FLOAT,
    actual_volume      FLOAT,
    duration_seconds   INTEGER,
    status             VARCHAR(20)  NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'completed', 'failed')),
    completed_at       TIMESTAMPTZ,
    PRIMARY KEY (id, triggered_at)
);
```

**Status values:**
- `pending`: Event created, irrigation not yet executed
- `completed`: Irrigation executed successfully
- `failed`: Irrigation failed

**Example data:**
```
 zone_id | status   | recommended_volume | actual_volume | duration_seconds | triggered_at          | completed_at
---------+----------+--------------------+---------------+------------------+-----------------------+--------------------
 2       | completed|            1833.68 |       1833.68 |              300 | 2026-05-03 13:17:08+00 | 2026-05-03 13:17:13+00
 3       | completed|            773.265 |       773.265 |              300 | 2026-05-03 13:17:11+00 | 2026-05-03 13:17:16+00
```

### 4.3 model_predictions Table

Stores prediction results:

```sql
CREATE TABLE IF NOT EXISTS model_predictions (
    id            BIGSERIAL,
    predicted_at  TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    model_version VARCHAR(100),
    prediction    FLOAT,
    confidence    FLOAT,
    PRIMARY KEY (id, predicted_at)
);
```

---

## 5. Redis Channels

### 5.1 predictions:new

| Property | Value |
|----------|-------|
| Channel name | `predictions:new` |
| Publisher | Airflow DAG (`scheduled_zone_predictions`) |
| Subscriber | irrigation-controller |
| Payload format | JSON |

**Payload example:**
```json
{
  "zone_id": "2",
  "sensor_id": "2-s1",
  "prediction": 36.66,
  "model_version": "1",
  "predicted_at": "2026-05-03T13:17:13.103229"
}
```

### 5.2 irrigation:triggered

| Property | Value |
|----------|-------|
| Channel name | `irrigation:triggered` |
| Publisher | irrigation-controller |
| Subscribers | notification-service, sensor-simulator |
| Payload format | JSON |

**Payload example:**
```json
{
  "zone_id": "2",
  "status": "completed",
  "volume": 1833.68,
  "completed_at": "2026-05-03T13:17:18.000000"
}
```

---

## 6. Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        AIRFLOW DAG (scheduled daily)                                │
│                                                                                     │
│  1. Fetch active zones from sensor_metadata                                        │
│  2. Get latest sensor readings for each zone                                       │
│  3. Call model-server for predictions                                              │
│  4. Store predictions in model_predictions table                                   │
│  5. PUBLISH to Redis channel: predictions:new                                    │
└────────────────────────────────┬────────────────────────────────────────────────────┘
                                 │
                                 │ Redis message
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    IRRIGATION-CONTROLLER Service                                   │
│                                                                                     │
│  1. SUBSCRIBE to Redis channel: predictions:new                                  │
│  2. Parse prediction payload                                                       │
│  3. Fetch zone thresholds (moisture_min, moisture_max)                            │
│  4. IF prediction >= moisture_min: SKIP (no irrigation needed)                  │
│  5. Check for recent events in last 10 minutes (deduplication)                   │
│     IF exists: SKIP                                                                │
│  6. Calculate deficit: max(0, moisture_min - prediction)                         │
│  7. Calculate volume: deficit * 100                                               │
│  8. INSERT into irrigation_events (status='pending')                              │
│  9. ASYNC TASK: _execute_irrigation()                                              │
└────────────────────────────────┬────────────────────────────────────────────────────┘
                                 │
                                 │ asyncio.create_task
                                 ▼ (after 5 seconds)
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                   Autonomous Execution                                             │
│                                                                                     │
│  1. Wait 5 seconds (simulated execution)                                          │
│  2. UPDATE irrigation_events: status='completed'                                  │
│     - actual_volume = recommended_volume                                          │
│     - duration_seconds = 300                                                      │
│     - completed_at = NOW()                                                        │
│  3. PUBLISH to Redis channel: irrigation:triggered                               │
└────────────────────────────────┬────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
    ┌──────────────────────┐    ┌──────────────────────┐
    │  SENSOR-SIMULATOR    │    │ NOTIFICATION-SERVICE │
    │                      │    │                      │
    │ Listens for          │    │ Listens for           │
    │ irrigation:triggered │    │ irrigation:triggered │
    │ Increases simulated  │    │ Sends alert/notify   │
    │ moisture readings    │    │ users                │
    └──────────────────────┘    └──────────────────────┘
```

---

## 7. Event Lifecycle

### State Diagram

```
[Prediction Received from Redis]
          │
          ▼
    ┌───────────┐
    │ Evaluate │ ──No──> [Skip: Above threshold]
    │ Threshold│
    └─────┬─────┘
          │Yes
          ▼
    ┌───────────┐
    │ Check     │ ──Yes──> [Skip: Recent event exists]
    │ Recent    │         (Deduplication)
    │ Events   │
    └─────┬─────┘
          │No
          ▼
    ┌─────────────────┐
    │ INSERT Event    │ ──> Status: 'pending'
    │ (store_event)   │
    └─────┬───────────┘
          │
          │ asyncio.create_task
          ▼ (5 second delay)
    ┌───────────────────┐
    │ UPDATE to         │ ──> Status: 'completed'
    │ 'completed'       │       actual_volume set
    └─────┬─────────────┘
          │
          ▼
    ┌─────────────────────┐
    │ PUBLISH to Redis:   │
    │ irrigation:triggered│
    └─────────────────────┘
```

### Event Timeline

| Time | Action | Status |
|------|--------|--------|
| T+0 | Prediction received from Redis | - |
| T+0 | Threshold evaluation passes | - |
| T+0 | Event inserted | `pending` |
| T+0 | Async task started | `pending` |
| T+5 | Execution simulated complete | - |
| T+5 | Event updated | `completed` |
| T+5 | Published to `irrigation:triggered` | `completed` |

---

## 8. Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db` | Database connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `REDIS_CHANNEL_PREDICTIONS_NEW` | `predictions:new` | Channel for predictions |
| `IRRIGATION_CONTROLLER_PORT` | `8503` | Service port |

### API Endpoints

The irrigation controller exposes these endpoints:

```
GET  /health                    - Health check
GET  /metrics                   - Prometheus metrics
GET  /v1/irrigation/events      - List irrigation events
GET  /v1/irrigation/recent      - List recent events
```

---

## 9. Edge Cases

### 9.1 No Zone Thresholds Found

If zone doesn't exist in the database, the controller logs and skips:

```python
if not thresholds:
    logger.debug(f"No thresholds found for zone {zone_id}")
    return None
```

### 9.2 Prediction Above Threshold

If predicted moisture is above minimum threshold, no irrigation needed:

```python
if prediction >= thresholds["moisture_min"]:
    return None
```

### 9.3 Recent Event Exists (Deduplication)

If irrigation already triggered in last 10 minutes, skip:

```python
if await self._recent_event_exists(zone_id, minutes=10):
    logger.debug(f"Skipping irrigation for zone {zone_id}: recent event exists")
    return None
```

### 9.4 Redis Connection Failure

The controller uses try-except in the message loop to handle errors gracefully:

```python
except Exception as e:
    logger.error(f"Error processing message: {e}")
```

### 9.5 Multiple Sensors per Zone

When zone has multiple sensors (e.g., Zone 2 has 2-s1 and 2-s2):
- Airflow publishes predictions for each sensor
- First prediction triggers irrigation event
- Second prediction is skipped due to deduplication
- Result: 1 event per zone per 10 minutes