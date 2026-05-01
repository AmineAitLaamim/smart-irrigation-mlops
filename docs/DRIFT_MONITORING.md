# Drift Monitoring

## Signals
- `Page-Hinkley`: detects sustained shifts in the prediction stream.
- `KL divergence`: compares recent predictions against the reference window.
- `Mean error`: rolling absolute error proxy when actuals are available.

## Alerting
- When drift is detected, the service publishes a `model_drift` event to `alerts:anomaly`.
- Prometheus scrapes `/metrics` from `drift-monitor` and Grafana visualizes the latest scores.

## Threshold Defaults
- Page-Hinkley threshold: `0.5`
- KL divergence alert threshold: `0.1`
- Mean error alert threshold: `0.15`
