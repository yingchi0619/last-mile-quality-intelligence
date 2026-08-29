"""Generate the sample DSP capacity-allocation scenario."""

import json

from src.analytics.capacity_simulation import run_sample_capacity_simulation


if __name__ == "__main__":
    print(json.dumps(run_sample_capacity_simulation(), indent=2))
