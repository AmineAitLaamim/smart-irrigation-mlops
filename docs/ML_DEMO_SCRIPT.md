# ML Demo Script

## End-to-End Flow
1. Start the stack with the ML services and monitoring enabled.
2. Show recent `sensor_readings` and the latest `feature_references` rows.
3. Trigger or reference a training run through Airflow and show the resulting MLflow run.
4. Call `POST /v1/predict` on the model server with a recent zone feature vector.
5. Show the new row in `model_predictions`.
6. Show the Redis-driven irrigation event in `irrigation_events`.
7. Open Grafana and highlight prediction throughput, latency, and drift signals.

## Demo Talking Points
- Why soil-specific indices improve agronomic relevance.
- How the model promotion rule prevents regressions.
- How drift alerts surface changing field behavior before silent failures.

## Rehearsal Checklist
- Verify MLflow is reachable.
- Verify `model-server`, `drift-monitor`, and `irrigation-controller` are healthy.
- Verify at least one prediction exists in `model_predictions`.
- Verify the Grafana ML dashboard loads.
