"""Train and evaluate the prototype late-delivery risk models."""

import json

from src.models.pipeline import run_late_delivery_model


if __name__ == "__main__":
    print(json.dumps(run_late_delivery_model(), indent=2))
