# End-to-End Pipeline Workflow

## Overview

The Smart Irrigation System operates as a continuous data pipeline, transforming raw sensor data into automated irrigation actions. This document presents the complete workflow as a unified pipeline.

---

## The Big Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      SMART IRRIGATION PIPELINE                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   STAGE 1    │    │   STAGE 2    │    │   STAGE 3    │    │   STAGE 4    │    │   STAGE 5    │
│   SENSOR     │    │   INGEST     │    │   PROCESS    │    │   PREDICT    │    │   ACTUATE    │
│   INPUT     │───▶│   & VALIDATE │───▶│   & ENRICH   │───▶│   & DECIDE   │───▶│   & NOTIFY    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                  │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼                  ▼
   ┌────────┐         ┌────────┐         ┌────────┐         ┌────────┐         ┌────────┐
   │Sensor  │         │Data    │         │Feature │         │Model   │         │Irrig.  │
   │Simulator│        │Ingestion│        │Engineer│         │Server  │         │Controller│
   │:8000   │         │:8001   │         │:8004   │         │:8501   │         │:8503   │
   └────────┘         └────────┘         └────────┘         └────────┘         └────────┘
                          │                                     │                  │
                          ▼                                     ▼                  ▼
                   ┌────────────┐                      ┌────────────┐      ┌────────────┐
                   │Redis Pub/Sub│                     │Drift       │      │Notification│
                   │Channels    │                      │Monitor     │      │Service     │
                   └────────────┘                      │:8502       │      │:8505       │
                                                        └────────────┘      └────────────┘
                                                                  │
                                                                  ▼
                                                        ┌────────────┐
                                                        │Prometheus  │
                                                        │Grafana     │
                                                        │Alertmanager│
                                                        └────────────┘

══════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                                    DETAILED STAGES
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 1: SENSOR INPUT

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: SENSOR INPUT                                                        │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                     SENSOR SIMULATOR (:8000)                         │    │
│   │                                                                      │    │
│   │   Input Sources:                                                     │    │
│   │   • Real sensors (hardware)                                          │    │
│   │   • Simulator (for testing/development)                              │    │
│   │                                                                      │    │
│   │   Logic:                                                              │    │
│   │   1. Fetch zone config (soil_type, crop_type)                       │    │
│   │   2. Apply diurnal cycles (evaporation peaks afternoon)             │    │
│   │   3. Add noise (±2% random variation)                               │    │
│   │   4. Post-irrigation: moisture spike + gradual decline              │    │
│   │                                                                      │    │
│   │   Output Rate: Every 30 seconds (configurable)                       │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │  MESSAGE FORMAT                                                      │    │
│   │  ────────────────                                                     │    │
│   │  {                                                                  │    │
│   │    "zone_id": "zone-001",                                          │    │
│   │    "sensor_id": "sensor-001",                                      │    │
│   │    "timestamp": "2026-05-03T14:30:00Z",                            │    │
│   │    "moisture": 42.5,  // percent                                    │    │
│   │    "temperature": 24.3  // celsius                                  │    │
│   │  }                                                                  │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   [sensor:data channel]                                                       │
│          │                                                                    │
│          ▼                                                                    │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 2: INGEST & VALIDATE

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: INGEST & VALIDATE                                                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                   DATA INGESTION (:8001)                              │    │
│   │                                                                      │    │
│   │   Process:                                                            │    │
│   │   1. Subscribe to [sensor:data]                                      │    │
│   │   2. Parse JSON message                                              │    │
│   │   3. Fetch zone bounds (min_plausible/max_plausible)                 │    │
│   │   4. Validate:                                                        │    │
│   │      ✓ Check zone exists in DB                                       │    │
│   │      ✓ Check moisture within plausible range                        │    │
│   │      ✓ Check temperature within plausible range                     │    │
│   │   5. Decision:                                                       │    │
│   │      ✓ Valid → INSERT into sensor_readings                           │    │
│   │      ✗ Invalid → INSERT anomaly into data_quality_events            │    │
│   │   6. Publish [ingestion:processed]                                  │    │
│   │                                                                      │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   ┌─────────────────────────────┬──────────────────────────────────────────┐ │
│   │      VALID PATH              │          INVALID PATH                    │ │
│   ├─────────────────────────────┼──────────────────────────────────────────┤ │
│   │ sensor_readings (hypertable) │   data_quality_events                    │ │
│   │ • timestamp                 │   • event_type (below_min, above_max)    │ │
│   │ • zone_id                   │   • severity (warning/critical)          │ │
│   │ • sensor_id                 │   • details                              │ │
│   │ • moisture                  │                                         │ │
│   │ • temperature              │   → Triggers alert if critical           │ │
│   └─────────────────────────────┴──────────────────────────────────────────┘ │
│                                                                                │
│   [ingestion:processed channel]                                              │
│          │                                                                    │
│          ▼                                                                    │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
               ▼                    ▼                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 3: PROCESS & ENRICH

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: PROCESS & ENRICH                                                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│   │  FEATURE ENGINEERING│  │    DATA QUALITY     │  │   STORE RAW DATA    │  │
│   │      (:8004)        │  │      (:8005)        │  │                     │  │
│   ├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤  │
│   │                     │  │                     │  │                     │  │
│   │ Subscribe to        │  │ Subscribe to         │  │ TimescaleDB         │  │
│   │ [ingestion:processed│  │ [ingestion:processed│  │ • sensor_readings  │  │
│   │                     │  │                     │  │ • sensor_metadata  │  │
│   │ Compute features:  │  │ Quality rules:       │  │ • zones             │  │
│   │ • 1h rolling mean  │  │ • stuck_value       │  │ • users             │  │
│   │ • 6h rolling mean  │  │ • sudden_jump       │  │                     │  │
│   │ • 24h rolling mean │  │ • flatline          │  │                     │  │
│   │ • trend (slope)   │  │ • rate_of_change    │  │                     │  │
│   │ • volatility       │  │                     │  │                     │  │
│   │                     │  │ Update health:      │  │                     │  │
│   │ Store to:          │  │ • healthy (0)       │  │                     │  │
│   │ feature_store      │  │ • degraded (1)      │  │                     │  │
│   │ table              │  │ • unhealthy (2)     │  │                     │  │
│   │                     │  │                     │  │                     │  │
│   │ Publish to:        │  │ Prometheus gauge:    │  │                     │  │
│   │ [features:computed]│  │ data_quality_sensor │  │                     │  │
│   │                    │  │ _health_status      │  │                     │  │
│   └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│                                                                                │
│   [features:computed channel]                                                │
│          │                                                                    │
│          ▼                                                                    │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 4: PREDICT & DECIDE

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: PREDICT & DECIDE                                                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                         MODEL SERVER (:8501)                        │    │
│   │                                                                      │    │
│   │   Subscribe to: [features:computed]                                 │    │
│   │                                                                      │    │
│   │   Process:                                                            │    │
│   │   1. Load features from feature_store (last 24h window)             │    │
│   │   2. Prepare input tensor for TensorFlow model                      │    │
│   │   3. Run inference: model.predict(features)                         │    │
│   │   4. Output: Predicted moisture for next 6 hours (hourly)           │    │
│   │   5. Store predictions in predictions table                         │    │
│   │   6. Publish to [predictions:new]                                    │    │
│   │                                                                      │    │
│   │   Model: Production model from MLflow (Staging/Production)          │    │
│   │   Latency: < 100ms per prediction                                    │    │
│   │                                                                      │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   [predictions:new channel]                                                  │
│          │                                                                    │
│          ├──────────────────────┐                                          │
│          │                      │                                          │
│          ▼                      ▼                                          │
│   ┌──────────────────┐   ┌──────────────────┐                               │
│   │  DRIFT MONITOR   │   │IRRIGATION CTRL  │                               │
│   │     (:8502)      │   │     (:8503)      │                               │
│   ├──────────────────┤   ├──────────────────┤                               │
│   │                  │   │                  │                               │
│   │ Compare:        │   │ Trigger Logic:   │                               │
│   │ prediction vs   │   │ IF predicted <   │                               │
│   │ actual (when     │   │   moisture_min    │                               │
│   │   actual arrives)│   │   THEN           │                               │
│   │                  │   │   create event   │                               │
│   │ Drift Tests:     │   │                  │                               │
│   │ • Page-Hinkley   │   │ Deduplication:   │                               │
│   │ • KL Divergence  │   │ 10min per zone   │                               │
│   │                  │   │                  │                               │
│   │ If drift >       │   │ Auto-complete:   │                               │
│   │ threshold →      │   │ after 5 seconds │                               │
│   │ [alerts:anomaly] │   │                  │                               │
│   └──────────────────┘   └──────────────────┘                               │
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │  IRRIGATION EVENT TABLE                                               │    │
│   │  ─────────────────────                                               │    │
│   │  • zone_id            • trigger_reason (prediction_based)          │    │
│   │  • triggered_at       • recommended_volume                           │    │
│   │  • status (pending/completed) • actual_volume                       │    │
│   │  • duration_seconds   • completed_at                                 │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   [irrigation:triggered channel]                                              │
│          │                                                                    │
│          ▼                                                                    │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 5: ACTUATE & NOTIFY

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: ACTUATE & NOTIFY                                                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                   NOTIFICATION SERVICE (:8505)                     │    │
│   │                                                                      │    │
│   │   Subscribes to:                                                     │    │
│   │   • [alerts:anomaly]  (from drift-monitor, data-quality)           │    │
│   │   • [irrigation:triggered] (from irrigation-controller)             │    │
│   │   • /alerts/webhook (from Alertmanager)                              │    │
│   │                                                                      │    │
│   │   Process:                                                            │    │
│   │   1. Receive alert payload                                          │    │
│   │   2. Check severity threshold (info/warning/critical)              │    │
│   │   3. If meets threshold:                                            │    │
│   │      • Send email via SMTP                                           │    │
│   │      • Send webhook HTTP POST                                        │    │
│   │   4. Track metrics: notification_service_deliveries_total           │    │
│   │                                                                      │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                     ACTUATION (Physical)                            │    │
│   │                                                                      │    │
│   │   In a real system, irrigation:triggered signals would control:     │    │
│   │   • Solenoid valves (open/close)                                    │    │
│   │   • Water pumps (on/off)                                            │    │
│   │   • Flow meters (measure actual volume)                             │    │
│   │                                                                      │    │
│   │   For this implementation:                                          │    │
│   │   • Event logged in irrigation_events table                         │    │
│   │   • Status changed from 'pending' to 'completed' after 5 seconds    │    │
│   │   • actual_volume and duration_seconds recorded                     │    │
│   │                                                                      │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                    │
                                    ▼
                    ┌───────────────────────────────────────┐
                    │          COMPLETE CYCLE                │
                    │                                       │
                    │   Sensor → Ingest → Process →        │
                    │   Predict → Actuate → Notify          │
                    │                                       │
                    │   Then: Repeat from Stage 1           │
                    │   (Continuous pipeline)               │
                    └───────────────────────────────────────┘
```

---

## Pipeline Summary

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE AT A GLANCE                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STAGE          │ SERVICE         │ INPUT                │ OUTPUT              │
│  ──────────────────────────────────────────────────────────────────────────────│
│  1. INPUT       │ Sensor Sim      │ (generated)         │ sensor:data          │
│  2. INGEST      │ Data Ingestion  │ sensor:data          │ sensor_readings      │
│  3. PROCESS     │ Feature Eng     │ ingestion:processed  │ features:computed   │
│  4. PREDICT     │ Model Server    │ features:computed    │ predictions:new      │
│  5. ACTUATE     │ Irrig Ctrl      │ predictions:new      │ irrigation_events    │
│       +         │ Notify Svc      │ irrigation:triggered│ email/webhook       │
│                                                                                 │
│  ══════════════════════════════════════════════════════════════════════════════│
│                                                                                 │
│  TIMING:                                                                      │
│  • Stage 1 → 2: ~1 second                                                     │
│  • Stage 2 → 3: ~1 second                                                     │
│  • Stage 3 → 4: ~2 seconds                                                    │
│  • Stage 4 → 5: ~1 second                                                     │
│  • Auto-complete: 5 seconds                                                   │
│                                                                                 │
│  Total cycle: ~10-15 seconds                                                 │
│                                                                                 │
│  ══════════════════════════════════════════════════════════════════════════════│
│                                                                                 │
│  METRICS AT EACH STAGE:                                                        │
│  Stage 1: sensor_simulator_readings_total                                     │
│  Stage 2: data_ingestion_total_processed, data_ingestion_valid_readings       │
│  Stage 3: feature_engineering_features_computed, data_quality_sensor_health    │
│  Stage 4: model_server_predictions_total, drift_monitor_kl_divergence         │
│  Stage 5: irrigation_triggers_total, notification_service_deliveries_total     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Redis Channel Flow

```
                    ┌─────────────────┐
                    │  sensor:data     │
                    │  (Stage 1 out)  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ ingestion:      │
                    │ processed       │
                    │ (Stage 2 out)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
      ┌────────────┐  ┌───────────┐  ┌─────────────┐
      │features:   │  │(directly) │  │(not used)   │
      │computed    │  │           │  │             │
      └─────┬──────┘  └─────┬─────┘  └──────┬──────┘
            │              │              │
            ▼              │              │
      ┌────────────┐       │              │
      │predictions:│◄──────┘              │
      │new         │                     │
      └─────┬──────┘                     │
            │                             │
     ┌──────┴──────┐                      │
     ▼             ▼                      │
┌─────────┐  ┌─────────────┐              │
│drift:   │  │irrigation:  │              │
│alerts   │  │triggered    │              │
└────┬────┘  └──────┬──────┘              │
     │             │                      │
     └──────┬──────┘                      │
            ▼                             │
      ┌─────────────────────────────┐    │
      │    Notification Service      │◄───┘
      │    (Stage 5 - Notify)        │
      └─────────────────────────────┘
```

This pipeline runs continuously, processing new sensor data every 30 seconds and triggering irrigation automatically based on ML predictions.