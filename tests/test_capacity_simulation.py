"""Tests for the synthetic DSP allocation scenario simulation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.analytics.capacity_simulation import (
    CapacityAllocationSimulator,
    run_sample_capacity_simulation,
)
from src.analytics.rca.data_access import load_route_factors


@pytest.fixture(scope="module")
def simulation_result() -> tuple[pd.DataFrame, dict[str, object]]:
    simulator = CapacityAllocationSimulator(load_route_factors())
    scenario = simulator.select_sample_scenario(0.95)
    return simulator.simulate(scenario)


def test_transfer_conserves_volume_and_respects_receiver_limit(
    simulation_result: tuple[pd.DataFrame, dict[str, object]],
) -> None:
    comparison, metadata = simulation_result
    before = comparison[comparison["phase"] == "BEFORE"]
    after = comparison[comparison["phase"] == "AFTER"]
    assert after["package_volume"].sum() == pytest.approx(before["package_volume"].sum())
    receiver_after = after[after["role"] == "RECEIVING_DSP"].iloc[0]
    assert receiver_after["utilization"] <= receiver_after["maximum_acceptable_utilization"] + 1e-12
    assert metadata["transfer_packages"] > 0


def test_simulated_direction_is_operationally_coherent(
    simulation_result: tuple[pd.DataFrame, dict[str, object]],
) -> None:
    comparison, _ = simulation_result
    overloaded = comparison[comparison["role"] == "OVERLOADED_DSP"].set_index("phase")
    receiver = comparison[comparison["role"] == "RECEIVING_DSP"].set_index("phase")
    assert overloaded.loc["AFTER", "utilization"] < overloaded.loc["BEFORE", "utilization"]
    assert overloaded.loc["AFTER", "expected_otd"] > overloaded.loc["BEFORE", "expected_otd"]
    assert overloaded.loc["AFTER", "exception_risk"] < overloaded.loc["BEFORE", "exception_risk"]
    assert receiver.loc["AFTER", "utilization"] > receiver.loc["BEFORE", "utilization"]


def test_sample_outputs_include_cautious_recommendation(tmp_path: Path) -> None:
    result = run_sample_capacity_simulation(output_dir=tmp_path)
    assert {path.name for path in tmp_path.iterdir()} == {
        "sample_capacity_simulation.csv",
        "sample_capacity_simulation.json",
        "sample_capacity_simulation.md",
    }
    assert "suggests considering" in str(result["recommendation"])
    assert "not a production optimization model" in str(result["disclaimer"])
