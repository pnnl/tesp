# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for data_streams.py — Forecast and constraint data management.

Ground truth for:
  - UncertaintyModel: saturating_exp, power_law, empirical functional forms
  - ContinuousForecast: interpolation, update, uncertainty propagation
  - EventForecast: intensity, cumulative energy, Bayesian conditioning
  - ConstraintStream: feasibility, margin
  - DataStreamManager: registration, retrieval, bundled access
"""

import math
import pytest

from tesp_support.curve_and_agent.enums_and_constants import DeviceType
from tesp_support.curve_and_agent.data_types import ContinuousDataPoint, EventDefinition, QuantilePoint
from tesp_support.curve_and_agent.data_streams import (
    UncertaintyModel,
    ContinuousForecast,
    EventForecast,
    ConstraintStream,
    DataStreamManager,
)


# ===================================================================
# UncertaintyModel Fixtures & Tests
# ===================================================================


@pytest.fixture
def saturating_exp_model():
    """σ(τ) = σ_∞ · (1 - e^{-τ/τ_c})
    σ_∞=5.0°F, τ_c=7200s (2 hours)."""
    return UncertaintyModel(
        model_type="saturating_exp",
        params={"sigma_inf": 5.0, "tau_c": 7200.0},
    )


@pytest.fixture
def power_law_model():
    """σ(τ) = min(σ_∞, σ_0 + α·τ^β)
    σ_0=0.5, α=0.001, β=0.7, σ_∞=6.0."""
    return UncertaintyModel(
        model_type="power_law",
        params={"sigma_0": 0.5, "alpha": 0.001, "beta": 0.7, "sigma_inf": 6.0},
    )


@pytest.fixture
def empirical_model():
    """Lookup table: linear between provided points."""
    return UncertaintyModel(
        model_type="empirical",
        params={
            "lead_time_sigma_table": [
                (0.0, 0.0),
                (3600.0, 2.0),
                (7200.0, 3.5),
                (14400.0, 5.0),
            ]
        },
    )


class TestUncertaintyModelSaturatingExp:
    def test_zero_lead_time(self, saturating_exp_model):
        """At τ=0: σ = 5.0·(1 - e^0) = 5.0·0 = 0.0."""
        assert saturating_exp_model.sigma_at(0.0) == pytest.approx(0.0, abs=1e-9)

    def test_one_time_constant(self, saturating_exp_model):
        """At τ=τ_c=7200: σ = 5.0·(1 - e^{-1}) = 5.0·0.6321 ≈ 3.161."""
        expected = 5.0 * (1 - math.exp(-1))
        assert saturating_exp_model.sigma_at(7200.0) == pytest.approx(
            expected, rel=1e-3
        )

    def test_large_lead_time_saturates(self, saturating_exp_model):
        """At τ >> τ_c, σ → σ_∞ = 5.0."""
        assert saturating_exp_model.sigma_at(100000.0) == pytest.approx(5.0, abs=0.01)


class TestUncertaintyModelPowerLaw:
    def test_zero_lead_time(self, power_law_model):
        """At τ=0: σ = min(6.0, 0.5 + 0.001·0^0.7) = 0.5."""
        assert power_law_model.sigma_at(0.0) == pytest.approx(0.5, abs=1e-9)

    def test_mid_lead_time(self, power_law_model):
        """At τ=3600: σ = min(6.0, 0.5 + 0.001·3600^0.7).
        3600^0.7 ≈ 308.61 → σ ≈ 0.5 + 0.309 = 0.809."""
        raw = 0.5 + 0.001 * (3600.0**0.7)
        expected = min(6.0, raw)
        assert power_law_model.sigma_at(3600.0) == pytest.approx(expected, rel=0.02)

    def test_cap_at_sigma_inf(self, power_law_model):
        """At very large τ, σ should not exceed σ_∞ = 6.0."""
        assert power_law_model.sigma_at(1e8) <= 6.0 + 1e-6


class TestUncertaintyModelEmpirical:
    def test_exact_table_point(self, empirical_model):
        """At τ=3600: σ = 2.0 (exact table entry)."""
        assert empirical_model.sigma_at(3600.0) == pytest.approx(2.0, abs=0.01)

    def test_interpolation_midpoint(self, empirical_model):
        """At τ=5400 (midpoint of 3600..7200): σ = (2.0+3.5)/2 = 2.75."""
        assert empirical_model.sigma_at(5400.0) == pytest.approx(2.75, abs=0.1)


# ===================================================================
# ContinuousForecast Fixtures & Tests
# ===================================================================


@pytest.fixture
def temp_forecast(saturating_exp_model):
    """Outdoor air temperature forecast: 4 hourly points."""
    series = [
        ContinuousDataPoint(timestamp=0.0, value=72.0),
        ContinuousDataPoint(timestamp=3600.0, value=75.0),
        ContinuousDataPoint(timestamp=7200.0, value=80.0),
        ContinuousDataPoint(timestamp=10800.0, value=85.0),
    ]
    return ContinuousForecast(
        variable_name="outdoor_air_temp",
        unit="°F",
        uncertainty_model=saturating_exp_model,
        series=series,
    )


class TestContinuousForecastConstructor:
    def test_attributes(self, temp_forecast):
        assert temp_forecast._variable_name == "outdoor_air_temp"
        assert temp_forecast._unit == "°F"
        assert len(temp_forecast._series) == 4


class TestContinuousForecastGetAt:
    def test_exact_timestamp(self, temp_forecast):
        """Querying at an exact data point returns that value."""
        pt = temp_forecast.get_at(3600.0)
        assert pt.value == pytest.approx(75.0, abs=0.01)

    def test_interpolated_timestamp(self, temp_forecast):
        """At t=1800 (midpoint of 0..3600): value ≈ (72+75)/2 = 73.5."""
        pt = temp_forecast.get_at(1800.0)
        assert pt.value == pytest.approx(73.5, abs=0.5)


class TestContinuousForecastUpdate:
    def test_update_replaces_series(self, temp_forecast):
        """After update(), get_at uses the new series."""
        new_series = [
            ContinuousDataPoint(timestamp=0.0, value=60.0),
            ContinuousDataPoint(timestamp=3600.0, value=62.0),
        ]
        temp_forecast.update(new_series)
        pt = temp_forecast.get_at(0.0)
        assert pt.value == pytest.approx(60.0, abs=0.01)


class TestContinuousForecastGetSeries:
    def test_full_horizon(self, temp_forecast):
        """get_series over the full horizon should return all points."""
        result = temp_forecast.get_series(0.0, 10800.0)
        assert len(result) >= 4

    def test_resampled_resolution(self, temp_forecast):
        """Requesting 1800s resolution over [0, 7200] → 5 points."""
        result = temp_forecast.get_series(0.0, 7200.0, resolution=1800.0)
        assert len(result) == 5  # 0, 1800, 3600, 5400, 7200


# ===================================================================
# EventForecast Fixtures & Tests
# ===================================================================


@pytest.fixture
def shower_event_types():
    return [
        EventDefinition(
            event_type="shower",
            energy_mean=3.0,
            energy_std=0.5,
            duration_mean=8.0,
            duration_std=2.0,
            magnitude_mean=4.5,
            magnitude_std=0.5,
        ),
    ]


@pytest.fixture
def shower_forecast(shower_event_types):
    """2 showers expected per day, total ~6 kWh, morning peak intensity."""
    intensity = [
        (0.0, 0.0),  # midnight
        (21600.0, 0.5),  # 6 AM: rising
        (28800.0, 0.0),  # 8 AM: drops off
        (64800.0, 0.3),  # 6 PM: evening bump
        (72000.0, 0.0),  # 8 PM: done
        (86400.0, 0.0),  # midnight
    ]
    return EventForecast(
        event_types=shower_event_types,
        intensity_function=intensity,
        daily_expected_count=2.0,
        daily_expected_energy=6.0,
    )


class TestEventForecastConstructor:
    def test_attributes(self, shower_forecast):
        assert len(shower_forecast._event_types) == 1
        assert shower_forecast._daily_expected_count == 2.0


class TestEventForecastIntensity:
    def test_peak_intensity(self, shower_forecast):
        """At 6 AM (21600s), intensity = 0.5 events/hr."""
        lam = shower_forecast.get_intensity_at(21600.0)
        assert lam == pytest.approx(0.5, abs=0.01)

    def test_zero_intensity(self, shower_forecast):
        """At midnight, intensity = 0."""
        lam = shower_forecast.get_intensity_at(0.0)
        assert lam == pytest.approx(0.0, abs=0.01)


class TestEventForecastCumulativeEnergy:
    def test_morning_window(self, shower_forecast):
        """6-8 AM: intensity peaks → most energy in this window.
        Expected ≈ integral of λ(t) × energy_per_event over [21600, 28800].
        Trapezoidal: avg λ ≈ 0.25 events/hr × 2 hrs = 0.50 events → 1.5 kWh."""
        dist = shower_forecast.get_cumulative_energy_distribution(21600.0, 28800.0)
        assert isinstance(dist, QuantilePoint)
        assert dist.expected > 0.0
        assert dist.expected == pytest.approx(1.5, abs=1.0)  # loose bound — Poisson

    def test_full_day_energy(self, shower_forecast):
        """The full-day distribution expected value ≈ daily_expected_energy."""
        dist = shower_forecast.get_cumulative_energy_distribution(0.0, 86400.0)
        assert dist.expected == pytest.approx(6.0, rel=0.3)


class TestEventForecastConditioning:
    def test_condition_reduces_remaining(self, shower_forecast):
        """Observing morning shower → remaining expected energy decreases."""
        before = shower_forecast.get_cumulative_energy_distribution(0.0, 86400.0)
        shower_forecast.condition_on_observation("shower", 25200.0, 3.0)
        after = shower_forecast.get_cumulative_energy_distribution(25200.0, 86400.0)
        # After observing 3 kWh in the morning, remaining < total
        assert after.expected < before.expected

    def test_reset_restores_prior(self, shower_forecast):
        """After reset, forecast returns to unconditional prior."""
        shower_forecast.condition_on_observation("shower", 25200.0, 3.0)
        shower_forecast.reset_observations()
        dist = shower_forecast.get_cumulative_energy_distribution(0.0, 86400.0)
        assert dist.expected == pytest.approx(6.0, rel=0.3)


# ===================================================================
# ConstraintStream Tests
# ===================================================================


@pytest.fixture
def min_soc_constraint():
    """EV must have SOC ≥ 0.80 by departure at t=50400 (2 PM)."""
    return ConstraintStream(
        constraint_id="ev_departure_soc",
        variable="soc",
        constraint_type="by_time",
        continuous=False,
        deadline=50400.0,
        required_value=0.80,
    )


@pytest.fixture
def continuous_min_temp():
    """Tank temp must stay ≥ 110°F at all times."""
    return ConstraintStream(
        constraint_id="min_tank_temp",
        variable="tank_temp",
        constraint_type="minimum",
        continuous=True,
        required_value=110.0,
    )


class TestConstraintStreamConstructor:
    def test_attrs(self, min_soc_constraint):
        assert min_soc_constraint._constraint_id == "ev_departure_soc"
        assert min_soc_constraint._constraint_type == "by_time"
        assert min_soc_constraint._deadline == 50400.0


class TestConstraintStreamFeasibility:
    def test_continuous_min_satisfied(self, continuous_min_temp):
        """Tank at 120°F ≥ 110°F → feasible."""
        assert continuous_min_temp.is_feasible(120.0, 0.0) is True

    def test_continuous_min_violated(self, continuous_min_temp):
        """Tank at 105°F < 110°F → infeasible."""
        assert continuous_min_temp.is_feasible(105.0, 0.0) is False

    def test_by_time_before_deadline(self, min_soc_constraint):
        """Before deadline, any SOC is feasible (deadline not reached)."""
        assert min_soc_constraint.is_feasible(0.30, 0.0) is True

    def test_by_time_at_deadline_satisfied(self, min_soc_constraint):
        """At deadline, SOC=0.85 ≥ 0.80 → feasible."""
        assert min_soc_constraint.is_feasible(0.85, 50400.0) is True

    def test_by_time_at_deadline_violated(self, min_soc_constraint):
        """At deadline, SOC=0.60 < 0.80 → infeasible."""
        assert min_soc_constraint.is_feasible(0.60, 50400.0) is False


class TestConstraintStreamMargin:
    def test_positive_margin(self, continuous_min_temp):
        """120 - 110 = 10°F margin (positive=feasible with room)."""
        margin = continuous_min_temp.feasibility_margin(120.0, 0.0)
        assert margin == pytest.approx(10.0, abs=0.1)

    def test_negative_margin(self, continuous_min_temp):
        """105 - 110 = -5°F margin (negative=violated)."""
        margin = continuous_min_temp.feasibility_margin(105.0, 0.0)
        assert margin == pytest.approx(-5.0, abs=0.1)


# ===================================================================
# DataStreamManager Tests
# ===================================================================


@pytest.fixture
def stream_manager():
    return DataStreamManager(device_type=DeviceType.HVAC_AC_ONLY)


class TestDataStreamManagerConstructor:
    def test_construct(self, stream_manager):
        assert stream_manager._device_type == DeviceType.HVAC_AC_ONLY
        assert len(stream_manager._continuous_streams) == 0
        assert len(stream_manager._event_streams) == 0
        assert len(stream_manager._constraint_streams) == 0


class TestDataStreamManagerRegistration:
    def test_register_continuous(self, stream_manager, temp_forecast):
        stream_manager.register_continuous_stream("outdoor_air_temp", temp_forecast)
        result = stream_manager.get_continuous("outdoor_air_temp")
        assert result is not None
        assert result._variable_name == "outdoor_air_temp"

    def test_register_event(self, stream_manager, shower_forecast):
        stream_manager.register_event_stream("hot_water_draw", shower_forecast)
        result = stream_manager.get_event("hot_water_draw")
        assert result is not None

    def test_register_constraint(self, stream_manager, min_soc_constraint):
        stream_manager.register_constraint("ev_departure_soc", min_soc_constraint)
        result = stream_manager.get_constraint("ev_departure_soc")
        assert result is not None

    def test_get_nonexistent_returns_none(self, stream_manager):
        assert stream_manager.get_continuous("nonexistent") is None


class TestDataStreamManagerBundle:
    def test_forecast_bundle(self, stream_manager, temp_forecast):
        stream_manager.register_continuous_stream("outdoor_air_temp", temp_forecast)
        bundle = stream_manager.get_forecast_bundle(0.0, 10800.0)
        assert "outdoor_air_temp" in bundle


class TestDataStreamManagerConstraints:
    def test_get_all_constraints_overlapping(
        self, stream_manager, min_soc_constraint, continuous_min_temp
    ):
        stream_manager.register_constraint("ev_soc", min_soc_constraint)
        stream_manager.register_constraint("min_temp", continuous_min_temp)
        # Query around the EV deadline
        constraints = stream_manager.get_all_constraints(48000.0, 52000.0)
        # Both should be returned (continuous always active, by_time near deadline)
        assert len(constraints) >= 1


class TestDataStreamManagerSchedule:
    def test_register_and_get_schedule(self, stream_manager, saturating_exp_model):
        """Register a setpoint schedule and retrieve it."""
        schedule = ContinuousForecast(
            variable_name="hvac_setpoint",
            unit="°F",
            uncertainty_model=saturating_exp_model,
            series=[
                ContinuousDataPoint(timestamp=0.0, value=72.0),
                ContinuousDataPoint(timestamp=3600.0, value=70.0),
            ],
        )
        stream_manager.register_schedule("setpoint_sched", schedule)
        result = stream_manager.get_schedule("setpoint_sched")
        assert result is not None
        assert result._variable_name == "hvac_setpoint"

    def test_get_schedule_nonexistent(self, stream_manager):
        """Getting a non-registered schedule returns None."""
        assert stream_manager.get_schedule("no_such_schedule") is None


class TestDataStreamManagerUpdateStream:
    def test_update_continuous_stream(self, stream_manager, temp_forecast):
        """After update_stream, the forecast reflects new data."""
        stream_manager.register_continuous_stream("outdoor_air_temp", temp_forecast)
        new_series = [
            ContinuousDataPoint(timestamp=0.0, value=60.0),
            ContinuousDataPoint(timestamp=3600.0, value=62.0),
        ]
        stream_manager.update_stream("outdoor_air_temp", new_series)
        forecast = stream_manager.get_continuous("outdoor_air_temp")
        pt = forecast.get_at(0.0)
        assert pt.value == pytest.approx(60.0, abs=0.5)

    def test_update_nonexistent_raises_or_noop(self, stream_manager):
        """Updating a non-registered stream should raise or be harmless."""
        # Implementor may raise KeyError or silently ignore
        try:
            stream_manager.update_stream("nonexistent", [])
        except (KeyError, ValueError):
            pass  # either is acceptable
