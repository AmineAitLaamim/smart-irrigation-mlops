# Feature Engineering Guide

## Core Feature Families
- Rolling moisture aggregates: mean, std, min, max, variance, range
- Rolling temperature aggregates: mean, std, min, max, variance
- Trend features: rate of change for moisture and temperature
- Soil-aware indices: `soil_water_retention_index`, `soil_dryness_index`
- Environmental proxy: `evapotranspiration_proxy`

## Agricultural Intent
- Retention index increases for soils that hold water longer.
- Dryness index increases when average moisture is low and drainage is high.
- Evapotranspiration proxy combines heat and dryness pressure for irrigation relevance.

## Versioning
- Every computed feature row is stored in `feature_references` with `model_version`.
- `FEATURE_MODEL_VERSION` controls the active feature logic tag.
