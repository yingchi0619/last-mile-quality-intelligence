"""Command-line entry point for operational root-cause analysis."""

import json

from src.analytics.rca import run_root_cause_analysis


if __name__ == "__main__":
    print(json.dumps(run_root_cause_analysis(), indent=2))
