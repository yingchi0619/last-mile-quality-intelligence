"""Scenario-based DSP capacity allocation simulation for synthetic operations."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .database import DEFAULT_DATABASE, project_root
from .rca.data_access import load_route_factors

PathLike = Union[str, Path]


@dataclass(frozen=True)
class DSPScenarioState:
    """Daily station/DSP inputs used by the allocation simulation."""

    service_date: str
    station: str
    provider_id: str
    package_volume: float
    dsp_capacity: float
    active_drivers: int
    historical_otd: float
    historical_delivery_success: float
    historical_exception_rate: float
    packages_per_driver: float
    route_density: float
    driver_reliability: float

    @property
    def utilization(self) -> float:
        return self.package_volume / self.dsp_capacity


@dataclass(frozen=True)
class AllocationScenario:
    overloaded: DSPScenarioState
    receiver: DSPScenarioState
    maximum_acceptable_utilization: float = 0.95


class CapacityAllocationSimulator:
    """Estimate directional KPI changes using synthetic historical relationships."""

    numeric_features = [
        "capacity_utilization",
        "package_volume",
        "active_drivers",
        "packages_per_driver",
        "route_density",
        "driver_reliability",
    ]
    categorical_features = ["station", "provider_id", "day_of_week"]

    def __init__(self, routes: pd.DataFrame):
        self.routes = routes.copy()
        self.daily_states = self._build_daily_states(self.routes)
        self._models = {
            outcome: self._fit_model(outcome)
            for outcome in [
                "on_time_delivery_rate",
                "delivery_success_rate",
                "exception_rate",
            ]
        }

    @staticmethod
    def _build_daily_states(routes: pd.DataFrame) -> pd.DataFrame:
        grouped = routes.groupby(
            ["service_date", "station_id", "provider_id", "day_of_week"]
        ).agg(
            package_volume=("package_volume", "sum"),
            dsp_capacity=("planned_capacity", "sum"),
            active_drivers=("driver_id", "nunique"),
            package_records=("package_records", "sum"),
            on_time_packages=("on_time_packages", "sum"),
            delivered_packages=("delivered_packages", "sum"),
            exception_packages=("exception_packages", "sum"),
            route_density=("route_density", "mean"),
            driver_reliability=("driver_reliability", "mean"),
        ).reset_index().rename(columns={"station_id": "station"})
        grouped["capacity_utilization"] = grouped["package_volume"] / grouped["dsp_capacity"]
        grouped["packages_per_driver"] = grouped["package_volume"] / grouped["active_drivers"]
        grouped["on_time_delivery_rate"] = grouped["on_time_packages"] / grouped["package_records"]
        grouped["delivery_success_rate"] = grouped["delivered_packages"] / grouped["package_records"]
        grouped["exception_rate"] = grouped["exception_packages"] / grouped["package_records"]
        return grouped

    def _fit_model(self, outcome: str) -> Pipeline:
        transformer = ColumnTransformer(
            [
                ("numeric", StandardScaler(), self.numeric_features),
                ("categorical", OneHotEncoder(handle_unknown="ignore"), self.categorical_features),
            ]
        )
        model = Pipeline([("features", transformer), ("regression", Ridge(alpha=8.0))])
        sample_weight = np.sqrt(self.daily_states["package_records"].to_numpy())
        model.fit(
            self.daily_states[self.numeric_features + self.categorical_features],
            self.daily_states[outcome],
            regression__sample_weight=sample_weight,
        )
        return model

    @staticmethod
    def _state_from_row(row: pd.Series) -> DSPScenarioState:
        return DSPScenarioState(
            service_date=str(pd.Timestamp(row["service_date"]).date()),
            station=str(row["station"]),
            provider_id=str(row["provider_id"]),
            package_volume=float(row["package_volume"]),
            dsp_capacity=float(row["dsp_capacity"]),
            active_drivers=int(row["active_drivers"]),
            historical_otd=float(row["on_time_delivery_rate"]),
            historical_delivery_success=float(row["delivery_success_rate"]),
            historical_exception_rate=float(row["exception_rate"]),
            packages_per_driver=float(row["packages_per_driver"]),
            route_density=float(row["route_density"]),
            driver_reliability=float(row["driver_reliability"]),
        )

    def select_sample_scenario(self, maximum_acceptable_utilization: float = 0.95) -> AllocationScenario:
        """Select the largest overload with an eligible same-station receiver."""
        if not 0 < maximum_acceptable_utilization <= 1.5:
            raise ValueError("Maximum acceptable utilization must be between 0 and 1.5.")
        states = self.daily_states.copy()
        states["overload_packages"] = states["package_volume"] - maximum_acceptable_utilization * states["dsp_capacity"]
        overloaded_candidates = states[states["overload_packages"] > 0].sort_values("overload_packages", ascending=False)
        for _, overloaded in overloaded_candidates.iterrows():
            receivers = states[
                (states["service_date"] == overloaded["service_date"])
                & (states["station"] == overloaded["station"])
                & (states["provider_id"] != overloaded["provider_id"])
            ].copy()
            receivers["spare_packages"] = maximum_acceptable_utilization * receivers["dsp_capacity"] - receivers["package_volume"]
            receivers = receivers[receivers["spare_packages"] >= 1].sort_values("spare_packages", ascending=False)
            if not receivers.empty:
                return AllocationScenario(
                    overloaded=self._state_from_row(overloaded),
                    receiver=self._state_from_row(receivers.iloc[0]),
                    maximum_acceptable_utilization=maximum_acceptable_utilization,
                )
        raise ValueError("No feasible overloaded/underutilized DSP pair was found.")

    def create_scenario(
        self,
        service_date: str,
        station: str,
        source_provider: str,
        receiving_provider: str,
        maximum_acceptable_utilization: float = 0.95,
    ) -> AllocationScenario:
        """Create an interactive scenario from an observed synthetic station/day."""
        if source_provider == receiving_provider:
            raise ValueError("Source and receiving DSP must be different.")
        date = pd.Timestamp(service_date)
        matches = self.daily_states[
            (self.daily_states["service_date"] == date)
            & (self.daily_states["station"] == station)
        ]
        source = matches[matches["provider_id"] == source_provider]
        receiver = matches[matches["provider_id"] == receiving_provider]
        if source.empty or receiver.empty:
            raise ValueError("Both DSPs must have activity at the selected station and date.")
        return AllocationScenario(
            overloaded=self._state_from_row(source.iloc[0]),
            receiver=self._state_from_row(receiver.iloc[0]),
            maximum_acceptable_utilization=maximum_acceptable_utilization,
        )

    @staticmethod
    def _feature_row(state: DSPScenarioState, volume: float) -> pd.DataFrame:
        service_date = pd.Timestamp(state.service_date)
        return pd.DataFrame(
            [
                {
                    "capacity_utilization": volume / state.dsp_capacity,
                    "package_volume": volume,
                    "active_drivers": state.active_drivers,
                    "packages_per_driver": volume / state.active_drivers,
                    "route_density": state.route_density,
                    "driver_reliability": state.driver_reliability,
                    "station": state.station,
                    "provider_id": state.provider_id,
                    "day_of_week": service_date.day_name(),
                }
            ]
        )

    def _expected_metrics(self, state: DSPScenarioState, volume: float) -> dict[str, float]:
        before_features = self._feature_row(state, state.package_volume)
        after_features = self._feature_row(state, volume)
        anchors = {
            "on_time_delivery_rate": state.historical_otd,
            "delivery_success_rate": state.historical_delivery_success,
            "exception_rate": state.historical_exception_rate,
        }
        metrics: dict[str, float] = {}
        for outcome, model in self._models.items():
            predicted_before = float(model.predict(before_features)[0])
            predicted_after = float(model.predict(after_features)[0])
            metrics[outcome] = float(np.clip(anchors[outcome] + predicted_after - predicted_before, 0, 1))
        return metrics

    def simulate(
        self,
        scenario: AllocationScenario,
        transfer_packages: Optional[float] = None,
    ) -> tuple[pd.DataFrame, dict[str, object]]:
        """Transfer the feasible overload and compare both DSPs before and after."""
        overloaded, receiver = scenario.overloaded, scenario.receiver
        limit = scenario.maximum_acceptable_utilization
        required_relief = max(0.0, overloaded.package_volume - limit * overloaded.dsp_capacity)
        receiver_spare = max(0.0, limit * receiver.dsp_capacity - receiver.package_volume)
        maximum_feasible_transfer = float(max(0, math.floor(min(overloaded.package_volume, receiver_spare))))
        if transfer_packages is None:
            transfer_packages = float(max(0, math.floor(min(required_relief, receiver_spare))))
        else:
            transfer_packages = float(transfer_packages)
            if transfer_packages > maximum_feasible_transfer:
                raise ValueError("Transfer exceeds receiving capacity under the configured limit.")
        if transfer_packages < 1:
            raise ValueError("Scenario has no transferable capacity under the configured limit.")

        rows: list[dict[str, object]] = []
        for state, role, after_volume in [
            (overloaded, "OVERLOADED_DSP", overloaded.package_volume - transfer_packages),
            (receiver, "RECEIVING_DSP", receiver.package_volume + transfer_packages),
        ]:
            for phase, volume in [("BEFORE", state.package_volume), ("AFTER", after_volume)]:
                metrics = self._expected_metrics(state, volume)
                rows.append(
                    {
                        "scenario_date": state.service_date,
                        "station": state.station,
                        "provider_id": state.provider_id,
                        "role": role,
                        "phase": phase,
                        "package_volume": volume,
                        "dsp_capacity": state.dsp_capacity,
                        "active_drivers": state.active_drivers,
                        "utilization": volume / state.dsp_capacity,
                        "expected_otd": metrics["on_time_delivery_rate"],
                        "expected_delivery_success": metrics["delivery_success_rate"],
                        "packages_per_driver": volume / state.active_drivers,
                        "exception_risk": metrics["exception_rate"],
                        "route_density": state.route_density,
                        "maximum_acceptable_utilization": limit,
                    }
                )
        comparison = pd.DataFrame(rows)
        transfer_share = transfer_packages / overloaded.package_volume
        residual_overload = max(
            0.0,
            overloaded.package_volume
            - transfer_packages
            - limit * overloaded.dsp_capacity,
        )
        qualifier = (
            "This transfer would still leave residual overload because the receiving DSP does not have enough spare capacity."
            if residual_overload > 0
            else "This transfer brings both simulated DSP utilization levels within the selected limit."
        )
        recommendation = (
            f"This scenario suggests considering a transfer of up to {transfer_packages:.0f} synthetic packages "
            f"({transfer_share:.1%} of {overloaded.provider_id} volume) from {overloaded.provider_id} to "
            f"{receiver.provider_id} at {overloaded.station}. {qualifier} Validate route feasibility, staffing, "
            "and service constraints before any operating decision."
        )
        metadata = {
            "transfer_packages": transfer_packages,
            "transfer_share": transfer_share,
            "residual_overload_packages": residual_overload,
            "recommendation": recommendation,
            "disclaimer": "This is a scenario simulation based on synthetic historical relationships, not a production optimization model.",
        }
        return comparison, metadata


def run_sample_capacity_simulation(
    database_path: Optional[PathLike] = None,
    output_dir: Optional[PathLike] = None,
    maximum_acceptable_utilization: float = 0.95,
) -> dict[str, object]:
    """Generate and save one fully data-derived sample allocation scenario."""
    root = project_root()
    database = Path(database_path) if database_path else root / DEFAULT_DATABASE
    if not database.is_absolute():
        database = root / database
    routes = load_route_factors(database)
    simulator = CapacityAllocationSimulator(routes)
    scenario = simulator.select_sample_scenario(maximum_acceptable_utilization)
    comparison, metadata = simulator.simulate(scenario)
    target = Path(output_dir) if output_dir else root / "data" / "processed"
    if not target.is_absolute():
        target = root / target
    target.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(target / "sample_capacity_simulation.csv", index=False)
    payload = {"scenario": {"overloaded": asdict(scenario.overloaded), "receiver": asdict(scenario.receiver),
                             "maximum_acceptable_utilization": scenario.maximum_acceptable_utilization},
               **metadata}
    (target / "sample_capacity_simulation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    summary = _build_simulation_summary(comparison, metadata)
    (target / "sample_capacity_simulation.md").write_text(summary, encoding="utf-8")
    return payload


def _build_simulation_summary(comparison: pd.DataFrame, metadata: dict[str, object]) -> str:
    before_after = comparison.pivot(index=["provider_id", "role"], columns="phase", values=["package_volume", "utilization", "expected_otd", "packages_per_driver", "exception_risk"])
    lines = ["# Capacity Planning and DSP Allocation Scenario", ""]
    role_labels = {"OVERLOADED_DSP": "Overloaded DSP", "RECEIVING_DSP": "Receiving DSP"}
    for (provider_id, role), row in before_after.iterrows():
        lines.extend([
            f"## {provider_id} — {role_labels[role]}", "",
            f"- Volume: {row[('package_volume', 'BEFORE')]:.0f} → {row[('package_volume', 'AFTER')]:.0f}",
            f"- Utilization: {row[('utilization', 'BEFORE')]:.1%} → {row[('utilization', 'AFTER')]:.1%}",
            f"- Expected OTD: {row[('expected_otd', 'BEFORE')]:.1%} → {row[('expected_otd', 'AFTER')]:.1%}",
            f"- Packages per driver: {row[('packages_per_driver', 'BEFORE')]:.1f} → {row[('packages_per_driver', 'AFTER')]:.1f}",
            f"- Exception risk: {row[('exception_risk', 'BEFORE')]:.1%} → {row[('exception_risk', 'AFTER')]:.1%}", "",
        ])
    lines.extend(["## Recommendation", "", str(metadata["recommendation"]), "", f"> {metadata['disclaimer']}"])
    return "\n".join(lines)
