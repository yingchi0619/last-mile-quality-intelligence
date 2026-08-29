# Capacity Planning and DSP Allocation Simulation

Run the sample scenario with:

```bash
python run_capacity_simulation.py
```

The simulation automatically identifies a synthetic station/day where one DSP exceeds the selected maximum utilization and another DSP has spare capacity. It transfers only the volume that the receiver can absorb without exceeding that limit.

## Inputs

- package volume
- planned DSP capacity
- active drivers
- historical OTD and delivery success
- packages per driver
- route density
- driver historical reliability
- DSP and station
- maximum acceptable utilization

## Expected-performance method

The simulator fits simple regularized response models to synthetic daily station/DSP history. Numeric operating factors and categorical DSP, station, and day-of-week effects are included. Before metrics are anchored to the observed synthetic scenario; after metrics apply only the model-estimated change associated with the simulated volume, utilization, and packages-per-driver movement.

This approach is useful for directional scenario comparison. It does not account for route feasibility, travel-time changes, labor schedules, contractual rules, or real-time execution constraints.

## Outputs

- `data/processed/sample_capacity_simulation.csv`: BEFORE/AFTER comparison
- `data/processed/sample_capacity_simulation.json`: inputs, transfer, recommendation, and disclaimer
- `data/processed/sample_capacity_simulation.md`: manager-readable summary

> This is a scenario simulation based on synthetic historical relationships, not a production optimization model.
