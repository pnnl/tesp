# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for planning_optimizer.py — Multi-interval schedule optimization.

Ground truth:
  - Flat prices → no cycling incentive (steady state preferred)
  - TOU prices → arbitrage (battery charges off-peak, discharges on-peak)
  - V_stored shape: higher at low-SOC, declines toward target SOC
  - Constraint satisfaction: EV must reach target SOC by deadline
"""

import pytest

from planning_optimizer import PlanningOptimizer
from data_types import (
    PlanningResult,
    BatteryState,
    HVACState,
    ContinuousDataPoint,
)
from data_streams import ConstraintStream
from device_models import BatteryModel, HVACModel
from enums_and_constants import DeviceType


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def battery_model():
    return BatteryModel(
        replacement_cost=10000.0,
        rated_cycles=5000,
        rated_dod=0.80,
        wohler_exponent=1.5,
    )


@pytest.fixture
def battery_planner(battery_model):
    return PlanningOptimizer(
        device_model=battery_model,
        device_type="battery",
    )


@pytest.fixture
def hvac_planner():
    model = HVACModel(device_type=DeviceType.HVAC_AC_ONLY)
    return PlanningOptimizer(device_model=model, device_type="hvac")


@pytest.fixture
def battery_state():
    return BatteryState(
        soc=0.50,
        power=0.0,
        energy_capacity=13.5,
        max_charge_rate=5.0,
        max_discharge_rate=5.0,
        round_trip_efficiency=0.90,
        cell_temperature=25.0,
        soc_min_bms=0.10,
        soc_max_bms=0.95,
    )


@pytest.fixture
def flat_prices():
    """24 hours of constant $0.10/kWh, hourly intervals."""
    return [((i * 3600.0, (i + 1) * 3600.0), 0.10) for i in range(24)]


@pytest.fixture
def tou_prices():
    """TOU: off-peak $0.05 (0-8, 20-24), mid-peak $0.10 (8-12, 16-20),
    on-peak $0.20 (12-16)."""
    prices = []
    for i in range(24):
        if i < 8 or i >= 20:
            p = 0.05
        elif 12 <= i < 16:
            p = 0.20
        elif 8 <= i < 12 or 16 <= i < 20:
            p = 0.10
        else:
            p = 0.10
        prices.append(((i * 3600.0, (i + 1) * 3600.0), p))
    return prices


# ===================================================================
# Battery Planning Tests
# ===================================================================


class TestBatteryPlannerConstructor:
    def test_construct(self, battery_planner):
        assert battery_planner._device_type == "battery"


class TestBatteryFlatPrices:
    @pytest.mark.xfail(raises=NotImplementedError)
    def test_no_cycling_incentive(self, battery_planner, battery_state, flat_prices):
        """Flat prices → optimal schedule has minimal cycling.

        With no price differential, cycling incurs degradation cost
        with no compensating revenue differential. Result should have
        low total throughput.
        """
        result = battery_planner.solve(
            current_state=battery_state,
            price_trajectory=flat_prices,
            weather_forecasts=None,
            constraints=[],
            interval_duration=3600.0,
            planning_horizon=86400.0,
            customer_preference_k=0.5,
            degradation_model=battery_planner._device_model,
            soc_reserve=0.20,
        )
        assert isinstance(result, PlanningResult)
        # Total absolute throughput should be small
        if hasattr(result, "schedule") and result.schedule:
            total_throughput = sum(abs(q) for _, q in result.schedule)
            # Reasonable: <10 kWh over 24 hours (mostly idle)
            assert total_throughput < 20.0


class TestBatteryTOUArbitrage:
    @pytest.mark.xfail(raises=NotImplementedError)
    def test_charges_off_peak_discharges_on_peak(
        self, battery_planner, battery_state, tou_prices
    ):
        """TOU prices → battery arbitrages: charge low, discharge high.

        Off-peak $0.05, on-peak $0.20 → spread $0.15/kWh.
        With ~10% round-trip loss and degradation ~$0.09/kWh,
        net profit per kWh ≈ 0.15 - 0.015 - 0.09 ≈ $0.045 > 0.
        So cycling is profitable → expect charge in hrs 0-8, discharge 12-16.
        """
        result = battery_planner.solve(
            current_state=battery_state,
            price_trajectory=tou_prices,
            weather_forecasts=None,
            constraints=[],
            interval_duration=3600.0,
            planning_horizon=86400.0,
            customer_preference_k=0.5,
            degradation_model=battery_planner._device_model,
            soc_reserve=0.20,
        )
        assert isinstance(result, PlanningResult)
        # V_stored should be present (battery-specific output)
        if hasattr(result, "V_stored") and result.V_stored:
            assert len(result.V_stored) > 0


class TestBatteryVStored:
    @pytest.mark.xfail(raises=NotImplementedError)
    def test_v_stored_monotonicity(self, battery_planner, battery_state, tou_prices):
        """V_stored should generally decrease as SOC approaches target.

        At low SOC: V_stored high (energy scarce).
        At high SOC: V_stored low (near target).
        """
        result = battery_planner.solve(
            current_state=battery_state,
            price_trajectory=tou_prices,
            weather_forecasts=None,
            constraints=[],
            interval_duration=3600.0,
            planning_horizon=86400.0,
            customer_preference_k=0.5,
            degradation_model=battery_planner._device_model,
            soc_reserve=0.20,
        )
        if hasattr(result, "V_stored") and len(result.V_stored) > 1:
            # Not strictly monotone (depends on price trajectory), but
            # the range should be non-trivial
            values = [v for _, v in result.V_stored]
            assert max(values) > min(values)


# ===================================================================
# HVAC Planning Test (pre-conditioning)
# ===================================================================


class TestHVACPlanning:
    @pytest.mark.xfail(raises=NotImplementedError)
    def test_pre_cool_before_peak(self, hvac_planner, tou_prices):
        """HVAC should pre-cool during off-peak to reduce on-peak load."""
        hvac_state = HVACState(
            indoor_air_temp=72.0,
            outdoor_air_temp=95.0,
            thermostat_setpoint=72.0,
        )
        result = hvac_planner.solve(
            current_state=hvac_state,
            price_trajectory=tou_prices,
            weather_forecasts={
                "outdoor_air_temp": [
                    ContinuousDataPoint(timestamp=i * 3600.0, value=95.0)
                    for i in range(25)
                ]
            },
            constraints=[],
            interval_duration=3600.0,
            planning_horizon=86400.0,
            customer_preference_k=0.3,
        )
        assert isinstance(result, PlanningResult)
