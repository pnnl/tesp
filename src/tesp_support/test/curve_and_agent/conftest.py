# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Shared test fixtures for the curve_and_agent module.

Provides factory functions and reusable fixtures for all device states,
market configurations, bid curves, and other data structures used across
test files.
"""

import pytest

from tesp_support.curve_and_agent.enums_and_constants import (
    MarketType,
    MarketPhase,
    OperatingMode,
    IterationType,
    CommitmentStatus,
    DeviceType,
    ProductType,
    ForecastParadigm,
    StreamType,
    PenaltyStructureType,
)
from tesp_support.curve_and_agent.data_types import (
    HVACState,
    WaterHeaterState,
    EVChargerState,
    BatteryState,
    BidPoint,
    BidCurve,
    ClearingResult,
    MarketTimingParams,
    FlexibilityEnvelope,
    EconomicCommitment,
    ContinuousDataPoint,
    EventDefinition,
    QuantilePoint,
    UncertaintyEnvelope,
    FulfillmentRecord,
    PerformanceEntry,
    SettlementRecord,
    AdvisoryRecord,
    DeliveryEconomics,
    DispatchSolution,
    DeviceCommand,
    PlanningResult,
)


# ===================================================================
# Device State Fixtures
# ===================================================================


@pytest.fixture
def default_hvac_state():
    """HVACState with all defaults (cooling mode, 72°F indoor, 85°F outdoor)."""
    return HVACState()


@pytest.fixture
def hot_day_hvac_state():
    """HVACState on a hot day: 95°F outdoor, cooling hard."""
    return HVACState(
        indoor_air_temp=74.0,
        outdoor_air_temp=95.0,
        thermostat_setpoint=72.0,
        hvac_mode="cooling",
        power_draw=3.5,
        hvac_on=True,
        thermal_mass_temp=73.0,
        solar_gain=2000.0,
        internal_gain=1500.0,
    )


@pytest.fixture
def default_wh_state():
    """WaterHeaterState with all defaults (130°F upper, 125°F lower)."""
    return WaterHeaterState()


@pytest.fixture
def default_ev_state():
    """EVChargerState with all defaults (50% SOC, vehicle not plugged in)."""
    return EVChargerState()


@pytest.fixture
def plugged_in_ev_state():
    """EVChargerState with vehicle plugged in at 30% SOC."""
    return EVChargerState(
        soc=0.30,
        charge_rate=0.0,
        battery_capacity=60.0,
        max_charge_rate=7.2,
        charger_efficiency=0.90,
        vehicle_plugged_in=True,
    )


@pytest.fixture
def default_battery_state():
    """BatteryState with all defaults (50% SOC, 13.5 kWh)."""
    return BatteryState()


@pytest.fixture
def mid_soc_battery_state():
    """BatteryState at 50% SOC, fully idle."""
    return BatteryState(
        soc=0.50,
        power=0.0,
        energy_capacity=13.5,
        max_charge_rate=5.0,
        max_discharge_rate=5.0,
        round_trip_efficiency=0.90,
    )


# ===================================================================
# Market Timing Fixtures
# ===================================================================


@pytest.fixture
def rt_timing_params():
    """MarketTimingParams for a 5-minute real-time market.

    Timeline (seconds relative to clearing):
        -600  ACTIVE      (observe + flexibility)
        -420  NEGOTIATION (bid formulation)
         -60  MARKET_LEAD (MO processing)
           0  CLEARING    (t_clear)
           0  DELIVERY_START
         300  DELIVERY_END
         600  RECONCILE_END
    """
    return MarketTimingParams(
        t_activate=-600.0,
        t_negotiate=-420.0,
        t_market_lead=-60.0,
        t_clear=0.0,
        t_delivery_start=0.0,
        t_delivery_end=300.0,
        t_reconcile_end=600.0,
    )


@pytest.fixture
def da_timing_params():
    """MarketTimingParams for a 1-hour day-ahead market interval."""
    return MarketTimingParams(
        t_activate=-7200.0,
        t_negotiate=-5400.0,
        t_market_lead=-600.0,
        t_clear=0.0,
        t_delivery_start=0.0,
        t_delivery_end=3600.0,
        t_reconcile_end=7200.0,
    )


# ===================================================================
# Bid / Clearing Fixtures
# ===================================================================


@pytest.fixture
def simple_downward_bid():
    """A 4-point downward-sloping demand bid curve.

    price ($/kWh)  |  quantity (kW)
    ──────────────────────────────
        0.20       |     1.0
        0.15       |     3.0
        0.10       |     5.0
        0.05       |     8.0
    """
    return BidCurve(
        points=[
            BidPoint(price=0.20, quantity=1.0),
            BidPoint(price=0.15, quantity=3.0),
            BidPoint(price=0.10, quantity=5.0),
            BidPoint(price=0.05, quantity=8.0),
        ],
        market_id="RT_1000",
        interval_id="int_1000_1300",
        timestamp=1000.0,
    )


@pytest.fixture
def simple_clearing_result():
    """ClearingResult at $0.10/kWh, 5 kW, binding."""
    return ClearingResult(
        market_id="RT_1000",
        interval_id="int_1000_1300",
        cleared_price=0.10,
        cleared_quantity=5.0,
        iteration=1,
        iteration_type=IterationType.BINDING,
        timestamp=1000.0,
    )


# ===================================================================
# Flexibility Fixtures
# ===================================================================


@pytest.fixture
def load_only_flexibility():
    """FlexibilityEnvelope for a typical load-only device (HVAC/WH)."""
    return FlexibilityEnvelope(
        Q_min=0.0,
        Q_max=5.0,
        Q_baseline=3.0,
        Q_min_p50=0.0,
        Q_min_p90=0.5,
        Q_min_p99=1.0,
        interval_start=0.0,
        interval_end=300.0,
    )


@pytest.fixture
def battery_flexibility():
    """FlexibilityEnvelope for a battery (bidirectional, Q_min < 0)."""
    return FlexibilityEnvelope(
        Q_min=-5.0,
        Q_max=5.0,
        Q_baseline=0.0,
        Q_min_p50=-5.0,
        Q_min_p90=-4.5,
        Q_min_p99=-4.0,
        interval_start=0.0,
        interval_end=300.0,
    )


# ===================================================================
# Price / Forecast Fixture Helpers
# ===================================================================


@pytest.fixture
def flat_price_trajectory():
    """24 hourly intervals at $0.10/kWh (flat price)."""
    return [((i * 3600.0, (i + 1) * 3600.0), 0.10) for i in range(24)]


@pytest.fixture
def tou_price_trajectory():
    """24 hourly intervals with time-of-use pricing.

    Off-peak (0–6, 22–24): $0.06/kWh
    Mid-peak (6–14, 18–22): $0.10/kWh
    On-peak (14–18):        $0.25/kWh
    """
    prices = []
    for i in range(24):
        if i < 6 or i >= 22:
            p = 0.06
        elif 14 <= i < 18:
            p = 0.25
        else:
            p = 0.10
        prices.append(((i * 3600.0, (i + 1) * 3600.0), p))
    return prices
