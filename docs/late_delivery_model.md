# Late Delivery Risk Model

> This is a portfolio prototype, not a production-ready AI or operational decision system.

Run training and holdout scoring with:

```bash
python run_late_delivery_model.py
```

## Target

`late_route_flag = 1` when final route-level OTD is below the configurable target threshold. The default prototype threshold is 85%.

The target is used only after route completion for supervised training and evaluation. It is never included as a model feature.

## Feature timing and leakage controls

Eligible features are restricted to information available before dispatch or at route start:

- planned packages
- expected utilization based on planned packages / planned capacity
- planned route distance and density
- pickup delay observed at route start
- driver historical reliability
- DSP historical OTD through the prior service date
- station historical OTD through the prior service date
- DSP, station, and day of week

Actual package volume, delivery outcomes, completion timestamps, exception outcomes, and same-day DSP/station results are excluded. Development and test periods are separated chronologically using complete service dates. An internal chronological validation window inside the development period selects the scoring model; the final future holdout is reserved for comparative reporting.

## Models and evaluation

- Logistic Regression baseline
- Random Forest comparison
- ROC-AUC, precision, recall, F1, and confusion matrix on the later holdout period

The model with higher holdout ROC-AUC supplies `late_delivery_risk_score`. Low, Medium, and High Risk tiers use the selected model's training-score 50th and 80th percentiles; test outcomes are not used to set the tier boundaries.

## Outputs

Artifacts are generated under `data/processed/late_delivery_model/`:

- fitted model files
- comparative metrics and confusion matrices
- encoded feature importance/coefficients
- route-level CSV and Parquet risk scores
- model metadata and prototype summary

Performance on synthetic historical data does not establish production performance, causality, fairness, stability, or operational readiness.
