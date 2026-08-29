"""Command-line entry point for synthetic data generation."""

import json
from src.data_generation import run_generation


if __name__ == "__main__":
    print(json.dumps(run_generation(), indent=2))
