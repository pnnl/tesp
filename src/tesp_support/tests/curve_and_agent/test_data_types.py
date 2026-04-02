# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for data_types.py — Level 0 foundation.

All dataclasses are already implemented (plain containers, no logic).
Tests verify correct default values, mutable-default isolation, field
types, and equality semantics. Every test should pass immediately.
"""

import copy
from dataclasses import replace

import pytest

from data_types import (
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
from enums_and_constants import (
    IterationType,
    CommitmentStatus,
    MarketType,
    ProductType,
    DeviceType,
)


# ===================================================================
# Device State Defaults
# ===================================================================


class TestHVACStateDefaults:
    """Verify physically reasonable defaults for HVACState."""

    def test_instantiates_with_defaults(self):
        s = HVACState()
        assert isinstance(s, HVACState)

    def test_indoor_temp_default(self):
        assert HVACState().indoor_air_temp == 72.0

    def test_outdoor_temp_default(self):
        assert HVACState().outdoor_air_temp == 85.0

    def test_mode_default(self):
        assert HVACState().hvac_mode == "cooling"

    def test_hvac_off_by_default(self):
        assert HVACState().hvac_on is False

    def test_thermal_params_positive(self):
        s = HVACState()
        assert s.air_mass > 0
        assert s.thermal_mass > 0
        assert s.UA_envelope > 0
        assert s.UA_mass > 0

    def test_cop_reasonable(self):
        s = HVACState()
        # COP should be between 1 and 8 for typical residential
        assert 1.0 <= s.cooling_COP <= 8.0
        assert 1.0 <= s.heating_COP <= 8.0


class TestWaterHeaterStateDefaults:
    def test_instantiates_with_defaults(self):
        s = WaterHeaterState()
        assert isinstance(s, WaterHeaterState)

    def test_upper_temp_ge_lower(self):
        s = WaterHeaterState()
        assert s.tank_temp_upper >= s.tank_temp_lower

    def test_tank_volume_positive(self):
        assert WaterHeaterState().tank_volume > 0

    def test_element_power_positive(self):
        assert WaterHeaterState().element_power > 0

    def test_inlet_temp_below_setpoint(self):
        s = WaterHeaterState()
        assert s.inlet_water_temp < s.thermostat_setpoint


class TestEVChargerStateDefaults:
    def test_instantiates_with_defaults(self):
        s = EVChargerState()
        assert isinstance(s, EVChargerState)

    def test_soc_in_range(self):
        s = EVChargerState()
        assert 0.0 <= s.soc <= 1.0

    def test_not_plugged_by_default(self):
        assert EVChargerState().vehicle_plugged_in is False

    def test_efficiency_in_range(self):
        s = EVChargerState()
        assert 0.0 < s.charger_efficiency <= 1.0

    def test_max_ge_min_charge_rate(self):
        s = EVChargerState()
        assert s.max_charge_rate >= s.min_charge_rate


class TestBatteryStateDefaults:
    def test_instantiates_with_defaults(self):
        s = BatteryState()
        assert isinstance(s, BatteryState)

    def test_soc_in_range(self):
        s = BatteryState()
        assert 0.0 <= s.soc <= 1.0

    def test_bms_limits_ordered(self):
        s = BatteryState()
        assert s.soc_min_bms < s.soc_max_bms

    def test_efficiency_in_range(self):
        s = BatteryState()
        assert 0.0 < s.round_trip_efficiency <= 1.0

    def test_health_in_range(self):
        s = BatteryState()
        assert 0.0 < s.state_of_health <= 1.0


# ===================================================================
# Market / Bidding Structures
# ===================================================================


class TestBidPoint:
    def test_construct(self):
        bp = BidPoint(price=0.10, quantity=5.0)
        assert bp.price == 0.10
        assert bp.quantity == 5.0

    def test_equality(self):
        a = BidPoint(0.10, 5.0)
        b = BidPoint(0.10, 5.0)
        assert a == b

    def test_inequality(self):
        a = BidPoint(0.10, 5.0)
        b = BidPoint(0.10, 4.0)
        assert a != b


class TestBidCurve:
    def test_default_points_empty(self):
        bc = BidCurve()
        assert bc.points == []

    def test_mutable_default_isolation(self):
        """Two BidCurves with default points should NOT share the list."""
        bc1 = BidCurve()
        bc2 = BidCurve()
        bc1.points.append(BidPoint(0.10, 5.0))
        assert len(bc2.points) == 0, "mutable default leaked between instances"

    def test_construct_with_points(self, simple_downward_bid):
        assert len(simple_downward_bid.points) == 4
        assert simple_downward_bid.market_id == "RT_1000"


class TestClearingResult:
    def test_default_iteration_type(self):
        cr = ClearingResult()
        assert cr.iteration_type == IterationType.BINDING

    def test_construct(self, simple_clearing_result):
        assert simple_clearing_result.cleared_price == 0.10
        assert simple_clearing_result.cleared_quantity == 5.0


class TestMarketTimingParams:
    def test_defaults_are_rt_market(self, rt_timing_params):
        tp = rt_timing_params
        assert tp.t_activate < tp.t_negotiate < tp.t_market_lead <= tp.t_clear
        assert tp.t_delivery_start <= tp.t_delivery_end < tp.t_reconcile_end

    def test_delivery_interval_positive(self, rt_timing_params):
        duration = rt_timing_params.t_delivery_end - rt_timing_params.t_delivery_start
        assert duration > 0

    def test_da_timing_longer(self, da_timing_params):
        """DA delivery interval (1 hr) > RT delivery interval (5 min)."""
        da_dur = da_timing_params.t_delivery_end - da_timing_params.t_delivery_start
        assert da_dur == 3600.0


# ===================================================================
# Flexibility / Commitment
# ===================================================================


class TestFlexibilityEnvelope:
    def test_defaults(self):
        fe = FlexibilityEnvelope()
        assert fe.Q_min <= fe.Q_baseline <= fe.Q_max

    def test_load_only_positive(self, load_only_flexibility):
        assert load_only_flexibility.Q_min >= 0

    def test_battery_bidirectional(self, battery_flexibility):
        assert battery_flexibility.Q_min < 0
        assert battery_flexibility.Q_max > 0

    def test_confidence_ordering(self):
        """p50 <= p90 <= p99 (more conservative = higher Q_min)."""
        fe = FlexibilityEnvelope()
        assert fe.Q_min_p50 <= fe.Q_min_p90 <= fe.Q_min_p99


class TestEconomicCommitment:
    def test_defaults(self):
        ec = EconomicCommitment()
        assert ec.status == CommitmentStatus.TENTATIVE
        assert ec.quantity == 0.0
        assert ec.displacement_plan == []

    def test_mutable_default_isolation(self):
        ec1 = EconomicCommitment()
        ec2 = EconomicCommitment()
        ec1.displacement_plan.append({"market": "test"})
        assert len(ec2.displacement_plan) == 0


# ===================================================================
# Forecast Structures
# ===================================================================


class TestContinuousDataPoint:
    def test_defaults(self):
        cdp = ContinuousDataPoint()
        assert cdp.value == 0.0
        assert cdp.sigma == 0.0
        assert cdp.quantiles == {}

    def test_mutable_default_isolation(self):
        a = ContinuousDataPoint()
        b = ContinuousDataPoint()
        a.quantiles[0.5] = 42.0
        assert 0.5 not in b.quantiles


class TestQuantilePoint:
    def test_defaults(self):
        qp = QuantilePoint()
        assert qp.expected == 0.0
        assert qp.quantiles == {}


class TestUncertaintyEnvelope:
    def test_defaults(self):
        ue = UncertaintyEnvelope()
        assert ue.distribution_type == "gaussian"


class TestEventDefinition:
    def test_construct(self):
        ed = EventDefinition(
            event_type="shower",
            duration_mean=8.0,
            magnitude_mean=2.5,
        )
        assert ed.event_type == "shower"


# ===================================================================
# Delivery / Settlement Structures
# ===================================================================


class TestFulfillmentRecord:
    def test_defaults(self):
        fr = FulfillmentRecord()
        assert fr.shortfall == 0.0
        assert fr.displaced_by is None


class TestSettlementRecord:
    def test_defaults(self):
        sr = SettlementRecord()
        assert sr.net_settlement == 0.0
        assert sr.displacement_count == 0


class TestAdvisoryRecord:
    def test_price_delta_default_inf(self):
        ar = AdvisoryRecord()
        assert ar.price_delta == float("inf")
        assert ar.quantity_delta == float("inf")


# ===================================================================
# Optimizer Output / Command Structures
# ===================================================================


class TestDispatchSolution:
    def test_defaults(self):
        ds = DispatchSolution()
        assert ds.Q == 0.0
        assert ds.allocation == {}

    def test_mutable_default_isolation(self):
        a = DispatchSolution()
        b = DispatchSolution()
        a.allocation["market_1"] = 5.0
        assert "market_1" not in b.allocation


class TestDeviceCommand:
    def test_defaults(self):
        dc = DeviceCommand()
        assert dc.device_type == DeviceType.HVAC_AC_ONLY
        assert dc.setpoint == 72.0


class TestPlanningResult:
    def test_defaults(self):
        pr = PlanningResult()
        assert pr.intervals == []
        assert pr.V_stored == []
        assert pr.total_cost == 0.0


# ===================================================================
# Dataclass Utilities (copy, replace)
# ===================================================================


class TestDataclassUtilities:
    def test_replace_hvac_state(self):
        s = HVACState()
        s2 = replace(s, indoor_air_temp=75.0)
        assert s2.indoor_air_temp == 75.0
        assert s.indoor_air_temp == 72.0  # original unchanged

    def test_deepcopy_bid_curve(self):
        bc = BidCurve(points=[BidPoint(0.10, 5.0)])
        bc2 = copy.deepcopy(bc)
        bc2.points[0] = BidPoint(0.20, 3.0)
        assert bc.points[0].price == 0.10  # original unchanged

    def test_replace_battery_state(self):
        s = BatteryState()
        s2 = replace(s, soc=0.80)
        assert s2.soc == 0.80
        assert s.soc == 0.50
