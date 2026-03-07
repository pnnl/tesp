# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for device_models.py — Level 1 physics models.

Hand-calculated ground truth for the agent's internal device models:
  - HVACModel:  2-node ETP thermal dynamics
  - WaterHeaterModel: stratified tank with heat loss and draws
  - EVChargerModel: CCCV charging model
  - BatteryModel: degradation-aware storage

All method tests are xfail(raises=NotImplementedError) until
model methods are implemented.

Physics reference for HVAC 2-node ETP
--------------------------------------
Ca · dTa/dt = UA_env·(To - Ta) + UA_mass·(Tm - Ta) + Qhvac + Qsolar + Qint
Cm · dTm/dt = UA_mass·(Ta - Tm)

Where Ca = air_mass (Btu/°F), Cm = thermal_mass (Btu/°F),
UA_env = UA_envelope (Btu/hr·°F), UA_mass = UA_mass (Btu/hr·°F)
"""

import math

import pytest

from enums_and_constants import DeviceType
from data_types import (
    HVACState,
    WaterHeaterState,
    EVChargerState,
    BatteryState,
    FlexibilityEnvelope,
    ContinuousDataPoint,
)
from device_models import HVACModel, WaterHeaterModel, EVChargerModel, BatteryModel


# ===================================================================
# HVAC Model Fixtures
# ===================================================================


@pytest.fixture
def hvac_model():
    return HVACModel(device_type=DeviceType.HVAC_AC_ONLY)


@pytest.fixture
def hp_model():
    return HVACModel(device_type=DeviceType.HVAC_HEAT_PUMP)


@pytest.fixture
def hvac_cooling_state():
    """Hot day: outdoor 95°F, indoor 72°F, thermal mass 72°F."""
    return HVACState(
        indoor_air_temp=72.0,
        outdoor_air_temp=95.0,
        thermostat_setpoint=72.0,
        hvac_mode="cooling",
        power_draw=0.0,
        hvac_on=False,
        thermal_mass_temp=72.0,
        air_mass=1500.0,
        thermal_mass=5000.0,
        UA_envelope=500.0,
        UA_mass=1500.0,
        cooling_COP=3.5,
        rated_cooling_capacity=36000.0,
        solar_gain=0.0,
        internal_gain=0.0,
    )


@pytest.fixture
def simple_outdoor_forecast():
    """Constant 95°F outdoor temp for 1 hour."""
    return [ContinuousDataPoint(timestamp=i * 60, value=95.0) for i in range(61)]


# ===================================================================
# HVAC Model Tests
# ===================================================================


class TestHVACModelConstructor:
    def test_construct(self, hvac_model):
        assert hvac_model._device_type == DeviceType.HVAC_AC_ONLY


class TestHVACPredictTemperature:
    def test_free_floating_temp_rise(
        self, hvac_model, hvac_cooling_state, simple_outdoor_forecast
    ):
        """With HVAC off (0 kW), indoor temp drifts toward outdoor temp.

        Ground truth (Euler step, dt=60s → dt_hr=1/60 hr):
            dTa/dt = (UA_env*(To-Ta) + UA_mass*(Tm-Ta) + Qsolar + Qint) / Ca
                   = (500*(95-72) + 1500*(72-72) + 0 + 0) / 1500
                   = 11500 / 1500
                   = 7.667 °F/hr

        After 5 minutes (1/12 hr):
            ΔTa ≈ 7.667 * (5/60) = 0.639 °F
            Ta(5min) ≈ 72.639 °F  (first-order approx, ignoring mass coupling)
        """
        trajectory = hvac_model.predict_temperature(
            state=hvac_cooling_state,
            hvac_power_kw=0.0,
            outdoor_temp_forecast=simple_outdoor_forecast,
            solar_gain_forecast=None,
            internal_gain_forecast=None,
            duration_seconds=300.0,
            timestep_seconds=60.0,
        )
        # Should return list of (time_offset, temp) tuples
        assert len(trajectory) > 0
        final_temp = trajectory[-1][1]
        # Temp should have risen from 72° toward 95°
        assert final_temp > 72.0
        # First-order: ≈ 72.64, but coupling will modify slightly
        assert final_temp == pytest.approx(72.64, abs=0.5)

    def test_cooling_holds_temp(
        self, hvac_model, hvac_cooling_state, simple_outdoor_forecast
    ):
        """With sufficient cooling power, temp should stay near setpoint.

        Steady-state cooling load ≈ UA_env*(To-Ta) / COP
            = 500*(95-72) / 3.5 = 11500/3.5 ≈ 3286 W ≈ 3.286 kW

        Providing 3.5 kW should slightly over-cool.
        """
        trajectory = hvac_model.predict_temperature(
            state=hvac_cooling_state,
            hvac_power_kw=3.5,
            outdoor_temp_forecast=simple_outdoor_forecast,
            solar_gain_forecast=None,
            internal_gain_forecast=None,
            duration_seconds=300.0,
            timestep_seconds=60.0,
        )
        final_temp = trajectory[-1][1]
        # Should stay near 72°F or slightly below
        assert abs(final_temp - 72.0) < 2.0


class TestHVACFlexibility:
    def test_flexibility_range(
        self, hvac_model, hvac_cooling_state, simple_outdoor_forecast
    ):
        """Q_min=0 (HVAC off), Q_max > 0 (rated capacity), baseline in between."""
        flex = hvac_model.estimate_flexibility(
            state=hvac_cooling_state,
            outdoor_temp_forecast=simple_outdoor_forecast,
            solar_gain_forecast=None,
            internal_gain_forecast=None,
            setpoint_schedule=[ContinuousDataPoint(value=72.0)],
            interval_duration=300.0,
        )
        assert isinstance(flex, FlexibilityEnvelope)
        assert flex.Q_min >= 0.0
        assert flex.Q_max > flex.Q_min
        assert flex.Q_min <= flex.Q_baseline <= flex.Q_max


class TestHVACPowerSetpointRoundtrip:
    def test_roundtrip(self, hvac_model, hvac_cooling_state):
        """power_to_setpoint → setpoint_to_power should approximate identity."""
        target_kw = 3.0
        setpoint = hvac_model.power_to_setpoint(
            target_power_kw=target_kw,
            state=hvac_cooling_state,
            outdoor_temp=95.0,
            interval_duration=300.0,
        )
        recovered_kw = hvac_model.setpoint_to_power(
            setpoint=setpoint,
            state=hvac_cooling_state,
            outdoor_temp=95.0,
            interval_duration=300.0,
        )
        assert recovered_kw == pytest.approx(target_kw, rel=0.05)


# ===================================================================
# Water Heater Model
# ===================================================================


@pytest.fixture
def wh_model():
    return WaterHeaterModel()


@pytest.fixture
def wh_state_hot():
    """Water heater at setpoint, no draw."""
    return WaterHeaterState(
        tank_temp_upper=130.0,
        tank_temp_lower=125.0,
        thermostat_setpoint=130.0,
        element_on=False,
        power_draw=0.0,
        tank_volume=50.0,
        tank_UA=2.0,
        element_power=4.5,
        inlet_water_temp=60.0,
        current_draw_rate=0.0,
    )


class TestWaterHeaterModel:
    def test_standby_temperature_drop(self, wh_model, wh_state_hot):
        """Element off, no draw → tank cools via standby losses.

        Standby loss = tank_UA × (T_tank - T_ambient)
        Assuming ambient ≈ 72°F:
            Q_loss = 2.0 × (130 - 72) = 116 Btu/hr

        Tank thermal mass ≈ tank_volume × 8.34 lb/gal × 1 Btu/(lb·°F)
            = 50 × 8.34 = 417 Btu/°F

        dT/dt = -116 / 417 ≈ -0.278 °F/hr
        After 1 hour: T ≈ 130 - 0.278 = 129.72 °F
        """
        from data_types import QuantilePoint

        trajectory = wh_model.predict_tank_temperature(
            state=wh_state_hot,
            element_power_kw=0.0,
            draw_forecast=QuantilePoint(expected=0.0),
            inlet_temp_forecast=None,
            ambient_temp=72.0,
            duration_seconds=3600.0,
        )
        assert len(trajectory) > 0
        # Upper zone temp should decrease slightly
        final_upper = trajectory[-1][1]
        assert final_upper < 130.0
        assert final_upper > 128.0  # shouldn't drop drastically in 1 hr

    def test_flexibility_range(self, wh_model, wh_state_hot):
        """Q_min=0 (element off), Q_max=element_power (4.5 kW)."""
        from data_types import QuantilePoint, ContinuousDataPoint

        flex = wh_model.estimate_flexibility(
            state=wh_state_hot,
            draw_forecast=QuantilePoint(expected=0.0),
            inlet_temp_forecast=ContinuousDataPoint(value=60.0),
            ambient_temp=72.0,
            min_tank_temp=110.0,
            interval_duration=300.0,
        )
        assert isinstance(flex, FlexibilityEnvelope)
        assert flex.Q_min >= 0.0
        assert flex.Q_max <= 4.5  # element_power


# ===================================================================
# EV Charger Model
# ===================================================================


@pytest.fixture
def ev_model():
    return EVChargerModel()


@pytest.fixture
def ev_charging_state():
    """EV plugged in at 30% SOC."""
    return EVChargerState(
        soc=0.30,
        charge_rate=0.0,
        battery_capacity=60.0,
        max_charge_rate=7.2,
        charger_efficiency=0.90,
        vehicle_plugged_in=True,
        min_charge_rate=1.0,
        soc_at_max_taper=0.80,
    )


class TestEVChargerModel:
    def test_predict_soc_charging(self, ev_model, ev_charging_state):
        """Charge at 7.2 kW for 1 hour: linear SOC increase.

        AC power = 7.2 kW, efficiency = 0.90
        DC power = 7.2 × 0.90 = 6.48 kW
        Energy added = 6.48 kWh in 1 hour
        ΔSOC = 6.48 / 60.0 = 0.108
        Final SOC = 0.30 + 0.108 = 0.408

        (No taper because SOC < 0.80 throughout)
        """
        trajectory = ev_model.predict_soc(
            state=ev_charging_state,
            charge_power_kw=7.2,
            duration_seconds=3600.0,
        )
        assert len(trajectory) > 0
        final_soc = trajectory[-1][1]
        expected_soc = 0.30 + (7.2 * 0.90 * 1.0) / 60.0
        assert final_soc == pytest.approx(expected_soc, rel=0.02)

    def test_flexibility_must_depart(self, ev_model, ev_charging_state):
        """Tight departure constraint forces high Q_min.

        Must reach SOC=0.80 in 4 hours from SOC=0.30.
        Need ΔSOC = 0.50, energy = 0.50 × 60 = 30 kWh
        DC power needed = 30 / 4 = 7.5 kW
        AC power = 7.5 / 0.90 = 8.33 kW → exceeds max_charge_rate

        So Q_min should be near max_charge_rate (7.2 kW) or indicate
        the constraint may not be satisfiable exactly.
        """
        flex = ev_model.estimate_flexibility(
            state=ev_charging_state,
            departure_constraint=(14400.0, 0.80),  # (4 hrs, 80% SOC)
            preferred_soc=0.80,
            interval_duration=300.0,
            time_until_departure=14400.0,
        )
        assert isinstance(flex, FlexibilityEnvelope)
        # Q_min should be elevated (must charge aggressively)
        assert flex.Q_min > 0.0

    def test_no_flexibility_unplugged(self, ev_model):
        """No vehicle → zero flexibility."""
        unplugged = EVChargerState(vehicle_plugged_in=False)
        flex = ev_model.estimate_flexibility(
            state=unplugged,
            departure_constraint=None,
            preferred_soc=0.80,
            interval_duration=300.0,
        )
        assert flex.Q_min == 0.0
        assert flex.Q_max == 0.0


# ===================================================================
# Battery Model
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
def battery_mid_soc():
    """Battery at 50% SOC, idle."""
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


class TestBatteryModelConstructor:
    def test_construct(self, battery_model):
        assert battery_model._replacement_cost == 10000.0
        assert battery_model._rated_cycles == 5000
        assert battery_model._cumulative_throughput_kwh == 0.0


class TestBatteryPredictSOC:
    def test_charging_soc_increases(self, battery_model, battery_mid_soc):
        """Charge at 5 kW for 1 hour.

        One-way efficiency (charge) = √(round_trip) = √0.90 ≈ 0.9487
        Energy stored = 5.0 × 0.9487 × 1.0 = 4.744 kWh
        ΔSOC = 4.744 / 13.5 = 0.3514
        Final SOC = 0.50 + 0.3514 = 0.8514
        (Clamped to soc_max_bms = 0.95 if exceeded)
        """
        trajectory = battery_model.predict_soc(
            state=battery_mid_soc,
            power_kw=5.0,
            duration_seconds=3600.0,
        )
        assert len(trajectory) > 0
        final_soc = trajectory[-1][1]
        charge_eff = math.sqrt(0.90)
        expected = 0.50 + (5.0 * charge_eff * 1.0) / 13.5
        assert final_soc == pytest.approx(min(expected, 0.95), rel=0.02)

    def test_discharging_soc_decreases(self, battery_model, battery_mid_soc):
        """Discharge at -5 kW for 1 hour.

        One-way efficiency (discharge) = √0.90 ≈ 0.9487
        Energy removed from SOC = 5.0 / 0.9487 × 1.0 = 5.270 kWh
        (More energy leaves SOC than reaches the grid)
        ΔSOC = -5.270 / 13.5 = -0.3904
        Final SOC = 0.50 - 0.3904 = 0.1096
        """
        trajectory = battery_model.predict_soc(
            state=battery_mid_soc,
            power_kw=-5.0,
            duration_seconds=3600.0,
        )
        final_soc = trajectory[-1][1]
        assert final_soc < 0.50
        assert final_soc >= battery_mid_soc.soc_min_bms


class TestBatteryFlexibility:
    def test_bidirectional_envelope(self, battery_model, battery_mid_soc):
        """Battery has negative Q_min (discharge) and positive Q_max (charge)."""
        flex = battery_model.estimate_flexibility(
            state=battery_mid_soc,
            soc_reserve=0.20,
            soc_preferred=0.50,
            interval_duration=300.0,
        )
        assert isinstance(flex, FlexibilityEnvelope)
        assert flex.Q_min < 0.0  # can discharge
        assert flex.Q_max > 0.0  # can charge
        assert flex.Q_baseline == pytest.approx(0.0, abs=0.5)  # at preferred SOC, idle


class TestBatteryDegradation:
    def test_degradation_cost_positive(self, battery_model, battery_mid_soc):
        """Marginal degradation cost should be positive for any cycling."""
        cost = battery_model.marginal_degradation_cost(
            state=battery_mid_soc,
            power_kw=3.0,
        )
        assert cost > 0.0

    def test_degradation_increases_with_power(self, battery_model, battery_mid_soc):
        """Higher C-rate → higher stress → higher degradation cost."""
        cost_low = battery_model.marginal_degradation_cost(
            state=battery_mid_soc,
            power_kw=1.0,
        )
        cost_high = battery_model.marginal_degradation_cost(
            state=battery_mid_soc,
            power_kw=5.0,
        )
        assert cost_high > cost_low

    def test_base_degradation_cost_order_of_magnitude(
        self, battery_model, battery_mid_soc
    ):
        """Base cost ≈ replacement / (rated_cycles × rated_dod × capacity × 2).

        base = 10000 / (5000 × 0.80 × 13.5 × 2) = 10000 / 108000 ≈ $0.0926/kWh
        The actual cost includes stress factors, but the base gives order of magnitude.
        """
        cost = battery_model.marginal_degradation_cost(
            state=battery_mid_soc,
            power_kw=2.0,
        )
        # Should be in the range $0.05–$0.30/kWh for moderate conditions
        assert 0.01 < cost < 1.0


class TestBatteryThresholds:
    def test_charge_below_discharge(self, battery_model, battery_mid_soc):
        """Charge threshold < discharge threshold (dead band for degradation).

        charge_threshold = V_stored - degradation_cost
        discharge_threshold = V_stored + degradation_cost
        """
        V_stored = 0.10  # $/kWh marginal value of stored energy
        deg_cost = 0.05  # $/kWh
        charge_th, discharge_th = battery_model.compute_charge_discharge_thresholds(
            state=battery_mid_soc,
            V_stored=V_stored,
            degradation_cost=deg_cost,
        )
        assert charge_th < discharge_th
        # Dead band width ≈ 2 × degradation_cost
        assert discharge_th - charge_th == pytest.approx(2 * deg_cost, rel=0.2)


class TestBatteryDegradationTracking:
    def test_update_increases_cumulative(self, battery_model, battery_mid_soc):
        """After tracking 1 kWh throughput, cumulative should increase.

        throughput=1 kWh, avg_soc=0.50, power=3 kW, temp=25°C, 1200s.
        Base cost ≈ replacement / (rated_cycles × rated_dod × capacity × 2)
             = 10000 / (5000 × 0.80 × 13.5 × 2) ≈ $0.0926/kWh
        Degradation cost ≈ $0.09 (moderate stress).
        """
        before = battery_model._cumulative_throughput_kwh
        cost = battery_model.update_degradation_tracking(
            throughput_kwh=1.0,
            avg_soc=0.50,
            avg_power_kw=3.0,
            avg_temperature=25.0,
            duration_seconds=1200.0,
        )
        assert cost > 0.0
        assert battery_model._cumulative_throughput_kwh == before + 1.0

    def test_cost_scales_with_throughput(self, battery_model, battery_mid_soc):
        """Twice the throughput ≈ twice the degradation cost."""
        cost_1 = battery_model.update_degradation_tracking(
            throughput_kwh=1.0,
            avg_soc=0.50,
            avg_power_kw=3.0,
            avg_temperature=25.0,
            duration_seconds=1200.0,
        )
        # Reset for a fair comparison — use a fresh model
        model2 = BatteryModel(
            replacement_cost=10000.0,
            rated_cycles=5000,
            rated_dod=0.80,
            wohler_exponent=1.5,
        )
        cost_2 = model2.update_degradation_tracking(
            throughput_kwh=2.0,
            avg_soc=0.50,
            avg_power_kw=3.0,
            avg_temperature=25.0,
            duration_seconds=2400.0,
        )
        assert cost_2 == pytest.approx(2 * cost_1, rel=0.1)


class TestBatteryBudgetUtilization:
    def test_initial_rate(self, battery_model):
        """Before any cycling, budget utilization should be defined.

        With zero throughput, rate could be 0.0 or a sentinel.
        """
        rate = battery_model.budget_utilization_rate
        assert isinstance(rate, float)

    def test_rate_increases_after_heavy_cycling(self, battery_model, battery_mid_soc):
        """Heavy cycling should push utilization rate above baseline."""
        battery_model.update_degradation_tracking(
            throughput_kwh=50.0,
            avg_soc=0.50,
            avg_power_kw=5.0,
            avg_temperature=35.0,  # elevated temp = more stress
            duration_seconds=36000.0,
        )
        rate = battery_model.budget_utilization_rate
        assert rate > 0.0


# ===================================================================
# Water Heater — additional scenario tests
# ===================================================================


class TestWaterHeaterActiveHeating:
    def test_element_raises_temperature(self, wh_model, wh_state_hot):
        """Element on at full power (4.5 kW) heats the tank.

        Element thermal output = 4.5 kW × 3412 Btu/kW = 15354 Btu/hr.
        Tank thermal mass = 50 gal × 8.34 lb/gal = 417 Btu/°F.
        dT/dt ≈ (15354 - 116) / 417 ≈ 36.5 °F/hr (net of standby loss).
        After 5 min: ΔT ≈ 36.5 × (5/60) ≈ 3.04 °F.
        """
        from data_types import QuantilePoint

        # Start from a cool tank to see clear heating
        import dataclasses

        cool_state = dataclasses.replace(
            wh_state_hot, tank_temp_upper=120.0, tank_temp_lower=115.0
        )
        trajectory = wh_model.predict_tank_temperature(
            state=cool_state,
            element_power_kw=4.5,
            draw_forecast=QuantilePoint(expected=0.0),
            inlet_temp_forecast=None,
            ambient_temp=72.0,
            duration_seconds=300.0,
        )
        final_upper = trajectory[-1][1]
        assert final_upper > 120.0

    def test_draw_cools_tank(self, wh_model, wh_state_hot):
        """Hot water draw brings cold inlet water into the tank, cooling it.

        A 2 gal/min draw over 5 min = 10 gal of 60°F water into a
        50-gal tank at 130°F.
        Rough mixing: (40×130 + 10×60) / 50 = (5200 + 600)/50 = 116°F lower zone.
        """
        from data_types import QuantilePoint

        trajectory = wh_model.predict_tank_temperature(
            state=wh_state_hot,
            element_power_kw=0.0,
            draw_forecast=QuantilePoint(expected=10.0),  # 10 gal draw
            inlet_temp_forecast=None,
            ambient_temp=72.0,
            duration_seconds=300.0,
        )
        # Lower zone should drop significantly
        final_lower = trajectory[-1][2]
        assert final_lower < 125.0  # started at 125


class TestWaterHeaterPowerToSetpoint:
    def test_full_power_high_setpoint(self, wh_model, wh_state_hot):
        """At full element power, setpoint should be at or above current temp."""
        sp = wh_model.power_to_setpoint(
            target_power_kw=4.5,
            state=wh_state_hot,
            interval_duration=300.0,
        )
        assert sp >= wh_state_hot.tank_temp_upper

    def test_zero_power_low_setpoint(self, wh_model, wh_state_hot):
        """At zero power, setpoint is well below current temp (element stays off)."""
        sp = wh_model.power_to_setpoint(
            target_power_kw=0.0,
            state=wh_state_hot,
            interval_duration=300.0,
        )
        assert sp < wh_state_hot.tank_temp_upper


# ===================================================================
# EV Charger — additional scenario tests
# ===================================================================


class TestEVChargerTaper:
    def test_taper_reduces_effective_power(self, ev_model):
        """Above soc_at_max_taper, actual charge rate tapers down.

        SOC=0.90 is well above taper point (0.80).
        Even requesting 7.2 kW, the BMS should limit actual power.
        """
        high_soc_state = EVChargerState(
            soc=0.90,
            battery_capacity=60.0,
            max_charge_rate=7.2,
            charger_efficiency=0.90,
            vehicle_plugged_in=True,
            soc_at_max_taper=0.80,
        )
        trajectory = ev_model.predict_soc(
            state=high_soc_state,
            charge_power_kw=7.2,
            duration_seconds=3600.0,
        )
        # SOC should increase, but by less than the untapered 0.108
        delta_soc = trajectory[-1][1] - 0.90
        untapered_delta = (7.2 * 0.90 * 1.0) / 60.0  # 0.108
        assert 0.0 < delta_soc < untapered_delta


class TestEVPowerToCommand:
    def test_within_limits(self, ev_model, ev_charging_state):
        """Requesting 5 kW (within range) should return ~5 kW."""
        cmd = ev_model.power_to_command(
            target_power_kw=5.0,
            state=ev_charging_state,
        )
        assert cmd == pytest.approx(5.0, abs=0.5)

    def test_clamped_to_max(self, ev_model, ev_charging_state):
        """Requesting 20 kW (above max 7.2) should clamp to max_charge_rate."""
        cmd = ev_model.power_to_command(
            target_power_kw=20.0,
            state=ev_charging_state,
        )
        assert cmd == pytest.approx(7.2, abs=0.1)

    def test_below_minimum_goes_to_zero(self, ev_model, ev_charging_state):
        """Requesting 0.5 kW (below min 1.0) should snap to 0 (off)."""
        cmd = ev_model.power_to_command(
            target_power_kw=0.5,
            state=ev_charging_state,
        )
        assert cmd == pytest.approx(0.0, abs=0.1)

    def test_unplugged_returns_zero(self, ev_model):
        """No vehicle plugged in → command is 0 regardless of request."""
        unplugged = EVChargerState(vehicle_plugged_in=False)
        cmd = ev_model.power_to_command(
            target_power_kw=5.0,
            state=unplugged,
        )
        assert cmd == pytest.approx(0.0)
