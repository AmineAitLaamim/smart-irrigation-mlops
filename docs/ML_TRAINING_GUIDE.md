# Model Training Guide: Smart Irrigation

This guide explains when and how model training occurs, the lifecycle of a model candidate, and the specific algorithms used in the Smart Irrigation System.

## 1. Training Schedule (The "When")
Model retraining is fully automated and orchestrated by **Apache Airflow**.

- **Primary Schedule**: The `smart_irrigation_model_training` DAG runs daily at **02:00 AM UTC**.
- **Manual Overrides**: Training can be triggered manually via the Airflow UI or CLI for rapid iteration or emergency retraining after identifying data drift.
- **Automatic Retraining Trigger**: The system is fully autonomous. When the `drift-monitor` service detects significant concept drift or a drop in prediction accuracy, it automatically triggers the Airflow retraining DAG via the REST API. A 1-hour cooldown prevents redundant training cycles.

## 2. Training Workflow (The "How")
The training process follows a "Champion-Challenger" pattern to ensure only superior models reach production.

### Step 1: Dataset Construction
The system fetches raw sensor data and corresponding windowed features from the **TimescaleDB Feature Store**. 
- It creates a **1-hour future target** (predicting moisture 60 minutes ahead).
- It performs **Deduplication**, **Outlier Smoothing**, and **Forward-Filling** for temperature missing values.

### Step 2: Candidate Generation
The pipeline trains and evaluates three distinct types of models:
1. **Linear Regression**: A simple baseline to confirm basic signal presence.
2. **Random Forest**: A robust ensemble model for non-linear relationships.
3. **XGBoost**: A high-performance gradient boosting model.

### Step 3: Hyperparameter Optimization
For the XGBoost candidate, the system uses **Optuna** to perform a Bayesian search for the best hyperparameters:
- `learning_rate`, `max_depth`, `n_estimators`, `subsample`, and `colsample_bytree`.

### Step 4: Time-Aware Evaluation
Models are evaluated using **Time-Aware Cross-Validation** (3 folds). This ensures that we never train on future data to predict the past, maintaining the chronological integrity of the time-series.

### Step 5: Registry & Promotion
The best model (lowest RMSE) is bundled into a **scikit-learn Pipeline** containing a `StandardScaler`.
- **MLflow Registration**: The pipeline is logged to the MLflow Registry.
- **Auto-Promotion**: If the new candidate's RMSE is better than the current Production model by a configurable margin, it is automatically promoted to the `Production` stage.

## 3. Models Used (The "Which")
We prioritize models that offer high accuracy while remaining efficient enough for edge or containerized deployment.

| Model | Role | Strength |
| :--- | :--- | :--- |
| **XGBoost** | Primary Predictor | Excellent at handling complex interactions and missing data. Our current production choice. |
| **Random Forest** | Robust Challenger | Stable, hard to overfit, and provides good baseline metrics. |
| **Linear Regression** | Sanity Check | Lightweight and interpretable; used to detect if the training set has become fundamentally noisy. |

## 4. Serving Logic
Models are served via the `model-server` (FastAPI).
- **Dynamic Reloading**: Every 60 seconds, the server checks MLflow for a new `Production` version and reloads it without downtime.
- **Bundled Scaling**: Because we use Pipelines, the server accepts **raw data** (e.g., moisture = 45.5%) and handles the normalization automatically, preventing "Training-Serving Skew".
