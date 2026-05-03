# Drift Monitoring & Automatic Retraining

The `drift-monitor` service is a critical MLOps component responsible for continuously evaluating the performance of the deployed XGBoost model in real-time. It acts as the "self-healing" trigger for the system.

## 1. When Does Drift Evaluation Happen?
The `drift-monitor` evaluates the model on a continuous schedule defined by the `DRIFT_SCAN_INTERVAL_SECONDS` environment variable (default: **every 60 seconds**).

During each scan, the service connects to the TimescaleDB database and fetches the **latest 200 model predictions**. 
- It splits these predictions chronologically into a **reference window** (the older 100 predictions) and a **current window** (the newest 100 predictions).

## 2. How is Drift Calculated?
The service evaluates these prediction windows against three statistical signals. Drift is officially declared if **any** of the following thresholds are breached:

1. **Page-Hinkley Score (Threshold: `0.5`)**:
   - A sequential analysis technique that detects sustained shifts in the prediction stream over time, ignoring minor momentary fluctuations.
2. **KL Divergence (Threshold: `0.1`)**:
   - Measures how the probability distribution of the *current* window differs from the *reference* window. A high score means the model is suddenly predicting values in a completely different range than it was recently.
3. **Mean Error (Threshold: `0.15`)**:
   - A rolling absolute error proxy calculated when actual sensor readings are available to compare against past predictions.

## 3. What Happens When Drift is Detected?
The exact moment `drift_detected` evaluates to `True`, the system takes two immediate, parallel actions:

### Action A: Alert Generation
The service creates a `model_drift` JSON payload containing the exact statistical scores and publishes it to the Redis `alerts:anomaly` channel. 
- The `notification-service` listens to this channel and dispatches warnings (e.g., emails or webhooks) to administrators.
- Prometheus simultaneously scrapes the `/metrics` endpoint to display the drift spike on the Grafana dashboards.

### Action B: Autonomous Model Retraining
To implement a "self-healing" system, the `drift-monitor` makes a direct REST API call to Apache Airflow to train a new model.
- **The Trigger**: It sends an authenticated `POST` request to `http://airflow:8080/api/v1/dags/smart_irrigation_model_training/dagRuns`.
- **The Process**: Airflow receives the request and instantly spins up the `smart_irrigation_model_training` DAG. This pipeline will fetch all the latest sensor data, build a new dataset, train XGBoost, evaluate it, and promote it to Production in MLflow if the accuracy improves.
- **The Cooldown**: To prevent the `drift-monitor` from spamming Airflow with retraining requests while the first training job is still running (because the model will continue to perform poorly during the 5-10 minutes it takes to train), a **1-hour cooldown** is enforced. The monitor will simply log the drift and ignore further Airflow triggers until 60 minutes have passed since the last successful request.
