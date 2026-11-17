# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for agent_redesign/hvac_agent_stub.py.

Covers the device definition (parity with DSO+T), the forecasts and market
horizon, the ETP model, both built-in amenity metrics, flexibility across
cooling, heating, and non-flexible cases, and the GridLAB-D, physics stub,
and statistical stub observers.
"""

import datetime as dt
import itertools
import math

import numpy as np
import pytest
from tesp_support.agent_redesign.hvac_agent_stub import (
    AmenityMetric,
    ComfortBand,
    DegreeMinutesOutsideBand,
    EndOfIntervalDeviation,
    ETPModel,
    GridLABDHVACObserver,
    HeatingFuel,
    HouseForecast,
    HVACAgentStub,
    HVACDefinition,
    HVACFlexibilityModel,
    HVACMode,
    HVACObservation,
    MarketHorizon,
    ObservationMode,
    PhysicsStubHVACObserver,
    StatisticalStubHVACObserver,
    ThermostatSchedule,
    WeatherForecast,
    calc_structure_etp,
    comfort_bands,
    resolve_amenity_metric,
)

START = dt.datetime(2016, 8, 12, 6)  # a Friday
HOUR = dt.timedelta(hours=1)
N_HOURS = 72


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def house_config():
    """House from the DSO+T hvac_agent.py test(), with a heat pump."""
    return {
        "sqft": 1040.0, "stories": 2, "doors": 4,
        "cooling": "ELECTRIC", "heating": "HEAT_PUMP",
        "Rroof": 20.07, "Rwall": 11.47, "Rfloor": 10.05, "Rdoors": 3.27,
        "airchange_per_hour": 0.68, "ceiling_height": 9,
        "thermal_mass_per_floor_area": 2.97, "aspect_ratio": 1.0,
        "exterior_wall_fraction": 1.0, "exterior_floor_fraction": 1.0,
        "exterior_ceiling_fraction": 1.0,
        "window_exterior_transmission_coefficient": 0.57,
        "glazing_layers": 2, "glass_type": 1, "window_frame": 1, "glazing_treatment": 1,
        "cooling_COP": 4.0, "over_sizing_factor": 0.2488,
    }


@pytest.fixture
def hvac_config():
    return {
        "wakeup_start": 7.0, "daylight_start": 9.0, "evening_start": 18.0, "night_start": 22.0,
        "weekend_day_start": 9.0, "weekend_night_start": 22.0,
        "wakeup_set_cool": 75.0, "daylight_set_cool": 78.0, "evening_set_cool": 75.0,
        "night_set_cool": 74.0, "weekend_day_set_cool": 76.0, "weekend_night_set_cool": 74.0,
        "wakeup_set_heat": 68.0, "daylight_set_heat": 65.0, "evening_set_heat": 68.0,
        "night_set_heat": 66.0, "weekend_day_set_heat": 67.0, "weekend_night_set_heat": 66.0,
        "deadband": 2.427, "range_high_limit": 5.0, "range_low_limit": 3.0,
        "slider_setting": 0.3105, "cooling_participating": True, "heating_participating": True,
    }


@pytest.fixture
def definition(house_config, hvac_config):
    return HVACDefinition.from_dsot_config(house_config, hvac_config)


def make_weather(mean_temp=85.0, amplitude=12.0, peak_solar=60.0, n=N_HOURS, step=HOUR):
    steps_per_hour = HOUR / step
    hours = [i / steps_per_hour for i in range(n)]
    hour_of_day = [(START.hour + h) % 24 for h in hours]
    return WeatherForecast(
        start=START, step=step,
        outdoor_air_temp=[mean_temp + amplitude * math.sin(2 * math.pi * (h - 9) / 24) for h in hour_of_day],
        humidity=[0.5] * n,
        solar_flux=[max(0.0, peak_solar * math.sin(math.pi * (h - 6) / 12)) for h in hour_of_day])


def make_house(cool=75.0, heat=68.0, internal_gain=2000.0, n=N_HOURS):
    return HouseForecast(start=START, step=HOUR, internal_gain=[internal_gain] * n,
                         cooling_setpoint=[cool] * n, heating_setpoint=[heat] * n)


def make_observation(air_temp=75.5, mass_temp=None, mode=HVACMode.COOLING):
    return HVACObservation(timestamp=START, indoor_air_temp=air_temp, hvac_mode=mode, hvac_on=False,
                           cooling_setpoint=75.0, heating_setpoint=68.0, hvac_kw=0.0, mass_temp=mass_temp)


def point_at(interval, q):
    return next(p for p in interval.amenity_map if p.q_kw == q)


# ---------------------------------------------------------------------------
# Device definition
# ---------------------------------------------------------------------------

class TestHVACDefinition:
    # Reference values computed with HVACDSOT.calc_etp_model() in
    # dsot/hvac_agent.py for this house.
    DSOT_UA = 528.2289281442298
    DSOT_CA = 495.743976
    DSOT_HM = 7037.716312261805
    DSOT_CM = 2758.304016
    DSOT_SOLAR_HEATGAIN_FACTOR = 94.05352688659791

    @pytest.mark.parametrize("heating, design_heating", [
        ("HEAT_PUMP", 54000.0), ("GAS", 50000.0), ("ELECTRIC", 50000.0)])
    def test_matches_dsot(self, house_config, hvac_config, heating, design_heating):
        house_config["heating"] = heating
        d = HVACDefinition.from_dsot_config(house_config, hvac_config)
        assert d.UA == pytest.approx(self.DSOT_UA)
        assert d.CA == pytest.approx(self.DSOT_CA)
        assert d.HM == pytest.approx(self.DSOT_HM)
        assert d.CM == pytest.approx(self.DSOT_CM)
        assert d.solar_heatgain_factor == pytest.approx(self.DSOT_SOLAR_HEATGAIN_FACTOR)
        assert d.design_cooling_capacity == 54000.0
        assert d.design_heating_capacity == design_heating

    def test_infiltration_is_part_of_UA(self, house_config):
        tight = dict(house_config, airchange_per_hour=0.0)
        air_heat_capacity = 1040.0 * 9 * 0.0735 * 0.2402
        assert (calc_structure_etp(house_config)["UA"] - calc_structure_etp(tight)["UA"]
                == pytest.approx(0.68 * air_heat_capacity))

    def test_heating_fuel_names(self):
        assert HeatingFuel.from_string("ELECTRIC") == HeatingFuel.RESISTANCE
        assert HeatingFuel.from_string("resistance") == HeatingFuel.RESISTANCE
        assert HeatingFuel.from_string("HEAT_PUMP") == HeatingFuel.HEAT_PUMP
        assert HeatingFuel.from_string("GAS") == HeatingFuel.GAS

    def test_overrides(self, house_config, hvac_config):
        d = HVACDefinition.from_dsot_config(house_config, hvac_config, slider=0.8,
                                            cooling_design_temperature=100.0)
        assert d.slider == 0.8
        assert d.design_cooling_capacity > 54000.0

    def test_single_pane_low_e_rejected(self, house_config):
        with pytest.raises(ValueError, match="U-value"):
            calc_structure_etp(dict(house_config, glass_type=2, glazing_layers=1))


class TestThermostatSchedule:
    def test_weekday_and_weekend_periods(self, hvac_config):
        s = ThermostatSchedule.from_dsot_config(hvac_config)
        friday = dt.datetime(2016, 8, 12)
        assert s.setpoints(friday.replace(hour=8)) == (75.0, 68.0)
        assert s.setpoints(friday.replace(hour=12)) == (78.0, 65.0)
        assert s.setpoints(friday.replace(hour=19)) == (75.0, 68.0)
        assert s.setpoints(friday.replace(hour=23)) == (74.0, 66.0)
        assert s.setpoints(friday.replace(hour=3)) == (74.0, 66.0)
        saturday = dt.datetime(2016, 8, 13)
        assert s.setpoints(saturday.replace(hour=12)) == (76.0, 67.0)
        assert s.setpoints(saturday.replace(hour=23)) == (74.0, 66.0)

    def test_house_forecast_from_schedule(self, hvac_config):
        s = ThermostatSchedule.from_dsot_config(hvac_config)
        house = HouseForecast.from_schedule(s, [1000.0] * 24, START, HOUR)
        assert house.cooling_setpoint[0] == 74.0  # 06:00, night
        assert house.cooling_setpoint[1] == 75.0  # 07:00, wakeup
        assert house.cooling_setpoint[6] == 78.0  # 12:00, daylight


# ---------------------------------------------------------------------------
# Forecasts and horizon
# ---------------------------------------------------------------------------

class TestForecasts:
    def test_mean_over_averages_finer_steps(self):
        quarter = dt.timedelta(minutes=15)
        w = WeatherForecast(START, quarter, [80.0, 82.0, 84.0, 86.0], [0.5] * 4, [0.0] * 4)
        assert w.mean_over(START, START + HOUR).outdoor_air_temp == pytest.approx(83.0)
        assert w.mean_over(START + quarter / 2, START + 3 * quarter / 2).outdoor_air_temp == pytest.approx(81.0)

    def test_mean_over_within_one_step(self):
        w = make_weather()
        five = dt.timedelta(minutes=5)
        assert w.mean_over(START, START + five).outdoor_air_temp == w.outdoor_air_temp[0]

    def test_at_selects_containing_step(self):
        house = HouseForecast(START, HOUR, [1.0, 2.0], [75.0, 76.0], [68.0, 67.0])
        assert house.at(START + dt.timedelta(minutes=59)).internal_gain == 1.0
        assert house.at(START + HOUR).cooling_setpoint == 76.0

    def test_coverage_enforced(self):
        house = make_house(n=24)
        with pytest.raises(ValueError, match="coverage"):
            house.mean_over(START + 23 * HOUR, START + 25 * HOUR)
        with pytest.raises(ValueError, match="coverage"):
            house.at(START - HOUR)

    def test_mismatched_lengths_rejected(self):
        with pytest.raises(ValueError, match="equal length"):
            WeatherForecast(START, HOUR, [80.0, 81.0], [0.5], [0.0, 0.0])

    def test_horizons(self):
        da = MarketHorizon.day_ahead(START)
        assert da.n_intervals == 48 and da.interval == HOUR
        assert da.intervals()[-1] == (START + 47 * HOUR, START + 48 * HOUR)
        rt = MarketHorizon.real_time(START)
        assert rt.intervals() == [(START, START + dt.timedelta(minutes=5))]


# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------

class TestETPModel:
    def test_discretization_is_exact(self, definition):
        etp = ETPModel(definition)
        x0 = np.array([75.0, 73.0])
        b = etp.forcing(95.0, 2000.0, 40.0)
        one_step = etp.simulate(x0, b, 1.0, 1)[-1]
        many_steps = etp.simulate(x0, b, 1.0 / 60, 60)[-1]
        assert one_step == pytest.approx(many_steps)

    def test_free_floating_reaches_outdoor_temperature(self, definition):
        etp = ETPModel(definition)
        end = etp.simulate(np.array([70.0, 70.0]), etp.forcing(90.0, 0.0, 0.0), 100.0, 1)[-1]
        assert end == pytest.approx([90.0, 90.0])

    def test_rejects_nonphysical_parameters(self, definition):
        from dataclasses import replace
        with pytest.raises(ValueError, match="positive"):
            ETPModel(replace(definition, CM=0.0))


class TestComfortBands:
    def test_slider_scales_band(self, definition):
        bands = comfort_bands(75.0, 68.0, definition)
        cool = bands[HVACMode.COOLING]
        assert cool.setpoint == 75.0
        assert cool.upper == pytest.approx(75.0 + 5.0 * 0.3105)
        assert cool.lower == pytest.approx(75.0 - 3.0 * 0.3105)

    def test_overlapping_setpoints_are_separated(self, definition):
        bands = comfort_bands(70.0, 69.0, definition)
        gap = bands[HVACMode.COOLING].setpoint - bands[HVACMode.HEATING].setpoint
        assert gap == pytest.approx(definition.deadband + 1.0)
        assert bands[HVACMode.COOLING].lower > bands[HVACMode.HEATING].upper


# ---------------------------------------------------------------------------
# Amenity metrics
# ---------------------------------------------------------------------------

class TestAmenityMetrics:
    band = ComfortBand(setpoint=75.0, lower=74.0, upper=77.0)

    def test_end_of_interval_deviation(self):
        temps = np.array([[75.0, 76.0, 78.0], [75.0, 74.0, 73.5]])
        metric = EndOfIntervalDeviation()
        assert metric.evaluate(temps, self.band, 1.0) == pytest.approx([3.0, -1.5])
        assert metric.violation(temps, self.band, 1.0) == pytest.approx([1.0, 0.5])

    def test_degree_minutes_outside_band(self):
        temps = np.array([[77.0, 78.0, 79.0], [75.0, 76.0, 76.5]])
        # excursion [0, 1, 2] at 10 minute substeps: trapezoid = 10 * (0.5 + 1.5)
        assert DegreeMinutesOutsideBand().evaluate(temps, self.band, 10.0) == pytest.approx([20.0, 0.0])

    def test_resolve_by_name(self):
        assert isinstance(resolve_amenity_metric("degree_minutes_outside_band"), DegreeMinutesOutsideBand)
        with pytest.raises(ValueError, match="Unknown amenity metric"):
            resolve_amenity_metric("comfort_vibes")


# ---------------------------------------------------------------------------
# Flexibility
# ---------------------------------------------------------------------------

def define(definition, weather=None, house=None, observation=None, horizon=None, metric="end_of_interval_deviation"):
    return HVACFlexibilityModel(metric).define_flexibility(
        observation or make_observation(), definition, weather or make_weather(),
        house or make_house(), horizon or MarketHorizon.day_ahead(START))


class TestFlexibilityCooling:
    def test_day_ahead_invariants(self, definition):
        flex = define(definition)
        assert len(flex.intervals) == 48
        assert flex.amenity_metric == "end_of_interval_deviation"
        for interval in flex.intervals:
            assert interval.mode == HVACMode.COOLING
            assert 0.0 <= interval.q_min_kw <= interval.q_baseline_kw <= interval.q_max_kw <= interval.q_capacity_kw
            qs = [p.q_kw for p in interval.amenity_map]
            assert qs == sorted(qs) and qs[0] == 0.0 and qs[-1] == pytest.approx(interval.q_capacity_kw)
            amenity = [p.amenity for p in interval.amenity_map]
            assert all(a >= b for a, b in itertools.pairwise(amenity))  # more cooling -> cooler

    def test_range_edges_land_on_band_edges(self, definition):
        flex = define(definition)
        interior = [i for i in flex.intervals if 0.0 < i.q_min_kw and i.q_max_kw < i.q_capacity_kw]
        assert interior
        for interval in interior:
            band = interval.comfort_band
            assert point_at(interval, interval.q_min_kw).amenity == pytest.approx(band.upper - band.setpoint, abs=1e-6)
            assert point_at(interval, interval.q_max_kw).amenity == pytest.approx(band.lower - band.setpoint, abs=1e-6)

    def test_baseline_tracks_setpoint(self, definition):
        flex = define(definition)
        for interval in flex.intervals:
            if 0.0 < interval.q_baseline_kw < interval.q_capacity_kw:
                assert interval.baseline_end_temp == pytest.approx(75.0)
                assert interval.baseline_amenity == pytest.approx(0.0, abs=1e-9)

    def test_hotter_afternoon_needs_more_power(self, definition):
        flex = define(definition)
        by_hour = {i.start.hour: i for i in flex.intervals[:24]}
        assert by_hour[16].q_baseline_kw > by_hour[6].q_baseline_kw

    def test_degree_minutes_metric(self, definition):
        end_of_interval = define(definition)
        degree_minutes = define(definition, metric="degree_minutes_outside_band")
        assert degree_minutes.amenity_unit == "degF*min"
        for dm, eoi in zip(degree_minutes.intervals, end_of_interval.intervals):
            # staying inside the band all interval implies ending inside it
            assert eoi.q_min_kw - 1e-6 <= dm.q_min_kw and dm.q_max_kw <= eoi.q_max_kw + 1e-6
            for p in dm.amenity_map:
                if dm.q_min_kw <= p.q_kw <= dm.q_max_kw:
                    assert p.amenity == pytest.approx(0.0, abs=1e-6)
                else:
                    assert p.amenity >= 0.0
            assert point_at(dm, 0.0).amenity > 0.0 or dm.q_min_kw == 0.0

    def test_custom_metric(self, definition):
        class PeakDeviation(AmenityMetric):
            name = "peak_deviation"
            unit = "degF"

            def evaluate(self, temps, band, substep_minutes):
                return np.abs(temps - band.setpoint).max(axis=1)

            def violation(self, temps, band, substep_minutes):
                return band.excursion(temps).max(axis=1)

        flex = define(definition, metric=PeakDeviation())
        assert flex.amenity_metric == "peak_deviation"
        assert all(p.amenity >= 0.0 for i in flex.intervals for p in i.amenity_map)

    def test_slider_zero_removes_flexibility(self, house_config, hvac_config):
        d = HVACDefinition.from_dsot_config(house_config, dict(hvac_config, slider_setting=0.0))
        for interval in define(d).intervals:
            assert interval.q_min_kw == pytest.approx(interval.q_max_kw, abs=1e-6)
            assert interval.q_baseline_kw == pytest.approx(interval.q_min_kw, abs=1e-6)

    def test_not_participating(self, house_config, hvac_config):
        d = HVACDefinition.from_dsot_config(house_config, dict(hvac_config, cooling_participating=False))
        for interval in define(d).intervals:
            assert interval.q_min_kw == interval.q_max_kw == interval.q_baseline_kw

    def test_unreachable_band_collapses_to_full_power(self, definition):
        hot = make_observation(air_temp=95.0, mass_temp=95.0)
        flex = define(definition, observation=hot, horizon=MarketHorizon.real_time(START))
        interval = flex.intervals[0]
        assert not interval.comfort_feasible
        assert interval.q_min_kw == pytest.approx(interval.q_capacity_kw)
        assert interval.q_max_kw == pytest.approx(interval.q_capacity_kw)

    def test_no_cooling_equipment(self, definition):
        from dataclasses import replace
        flex = define(replace(definition, has_cooling=False))
        for interval in flex.intervals:
            assert interval.mode == HVACMode.OFF
            assert interval.q_max_kw == 0.0
            assert len(interval.amenity_map) == 1

    def test_unknown_mass_temperature_uses_air(self, definition):
        with_mass = define(definition, observation=make_observation(mass_temp=75.5))
        without_mass = define(definition, observation=make_observation(mass_temp=None))
        assert with_mass.q_baseline_kw == pytest.approx(without_mass.q_baseline_kw)

    def test_real_time_interval(self, definition):
        flex = define(definition, horizon=MarketHorizon.real_time(START))
        assert len(flex.intervals) == 1
        assert flex.intervals[0].end - flex.intervals[0].start == dt.timedelta(minutes=5)

    def test_horizon_beyond_forecast_rejected(self, definition):
        with pytest.raises(ValueError, match="coverage"):
            define(definition, weather=make_weather(n=24))


class TestFlexibilityHeating:
    @pytest.fixture
    def cold(self):
        return make_weather(mean_temp=25.0, amplitude=8.0, peak_solar=30.0)

    def test_heat_pump(self, definition, cold):
        flex = define(definition, weather=cold, observation=make_observation(air_temp=68.0, mode=HVACMode.HEATING))
        for interval in flex.intervals:
            assert interval.mode == HVACMode.HEATING
            assert interval.q_capacity_kw > 0.0
            assert interval.q_min_kw <= interval.q_baseline_kw <= interval.q_max_kw
            amenity = [p.amenity for p in interval.amenity_map]
            assert all(a <= b for a, b in itertools.pairwise(amenity))  # more heat -> warmer

    def test_resistance_uses_unit_cop(self, house_config, hvac_config, cold):
        resistance = HVACDefinition.from_dsot_config(dict(house_config, heating="ELECTRIC"), hvac_config)
        heat_pump = HVACDefinition.from_dsot_config(house_config, hvac_config)
        obs = make_observation(air_temp=68.0, mode=HVACMode.HEATING)
        r = define(resistance, weather=cold, observation=obs).intervals[0]
        hp = define(heat_pump, weather=cold, observation=obs).intervals[0]
        assert r.q_baseline_kw > hp.q_baseline_kw

    def test_gas_heat_has_no_electric_flexibility(self, house_config, hvac_config, cold):
        gas = HVACDefinition.from_dsot_config(dict(house_config, heating="GAS"), hvac_config)
        flex = define(gas, weather=cold, observation=make_observation(air_temp=68.0, mode=HVACMode.HEATING))
        for interval in flex.intervals:
            assert interval.mode == HVACMode.HEATING
            assert interval.q_min_kw == interval.q_max_kw == interval.q_baseline_kw == 0.0
            assert interval.baseline_end_temp == pytest.approx(68.0)


# ---------------------------------------------------------------------------
# Observers
# ---------------------------------------------------------------------------

class FakeConnection:
    def __init__(self, values):
        self.values = values

    def get_value(self, key):
        return self.values.get(key)


class TestGridLABDObserver:
    def make(self, **overrides):
        values = {"air_temperature": "+76.2 degF", "mass_temperature": "+75.1 degF",
                  "cooling_setpoint": "75", "heating_setpoint": "68",
                  "hvac_load": "3.4 kW", "system_mode": "COOL", "power_state": "ON",
                  "thermostat_mode": "AUTO"}
        values.update(overrides)
        return GridLABDHVACObserver(FakeConnection({f"house_1#{k}": v for k, v in values.items() if v is not None}),
                                    "house_1")

    def test_running_cooling(self):
        obs = self.make().observe(START)
        assert obs.source == ObservationMode.GRIDLABD
        assert obs.hvac_mode == HVACMode.COOLING and obs.hvac_on
        assert obs.indoor_air_temp == 76.2 and obs.mass_temp == 75.1
        assert obs.hvac_kw == 3.4  # GridLAB-D hvac_load is already kW

    def test_aux_heat_is_heating(self):
        obs = self.make(system_mode="AUX").observe(START)
        assert obs.hvac_mode == HVACMode.HEATING and obs.hvac_on

    def test_idle_auto_infers_mode_from_temperature(self):
        warm = self.make(system_mode="OFF", air_temperature="73").observe(START)
        assert warm.hvac_mode == HVACMode.COOLING and not warm.hvac_on
        cool = self.make(system_mode="OFF", air_temperature="70").observe(START)
        assert cool.hvac_mode == HVACMode.HEATING

    def test_idle_thermostat_mode_restricts(self):
        obs = self.make(system_mode="OFF", air_temperature="70", thermostat_mode="COOL").observe(START)
        assert obs.hvac_mode == HVACMode.COOLING

    def test_power_state_fallback(self):
        obs = self.make(system_mode=None, power_state="ON", air_temperature="70").observe(START)
        assert obs.hvac_on and obs.hvac_mode == HVACMode.HEATING

    def test_numeric_values_and_missing_mass(self):
        obs = self.make(air_temperature=76.0, mass_temperature=None).observe(START)
        assert obs.indoor_air_temp == 76.0 and obs.mass_temp is None

    def test_missing_required_property(self):
        with pytest.raises(ValueError, match="air_temperature"):
            self.make(air_temperature=None).observe(START)


class TestPhysicsStubObserver:
    def test_thermostat_holds_deadband(self, definition):
        house = make_house(cool=75.0)
        stub = PhysicsStubHVACObserver(definition, make_weather(), house, START, initial_air_temp=75.0)
        temps, states = [], []
        for minute in range(60, 24 * 60, 5):
            obs = stub.observe(START + dt.timedelta(minutes=minute))
            temps.append(obs.indoor_air_temp)
            states.append(obs.hvac_on)
            assert obs.source == ObservationMode.PHYSICS_STUB
            assert obs.hvac_kw > 0.0 if obs.hvac_on else obs.hvac_kw == 0.0
        half_band = definition.deadband / 2.0
        assert 75.0 - half_band - 1.0 < min(temps) and max(temps) < 75.0 + half_band + 1.0
        assert any(states) and not all(states)  # cycles

    def test_cannot_move_backward(self, definition):
        stub = PhysicsStubHVACObserver(definition, make_weather(), make_house(), START, initial_air_temp=75.0)
        stub.observe(START + HOUR)
        with pytest.raises(ValueError, match="backward"):
            stub.observe(START)

    def test_parameter_scaling(self, definition):
        stub = PhysicsStubHVACObserver(definition, make_weather(), make_house(), START, 75.0,
                                       parameter_scaling={"UA": 1.2})
        assert stub.definition.UA == pytest.approx(1.2 * definition.UA)
        assert definition.UA == pytest.approx(TestHVACDefinition.DSOT_UA)
        with pytest.raises(TypeError, match="non-numeric"):
            PhysicsStubHVACObserver(definition, make_weather(), make_house(), START, 75.0,
                                    parameter_scaling={"has_cooling": 2.0})
        with pytest.raises(AttributeError):
            PhysicsStubHVACObserver(definition, make_weather(), make_house(), START, 75.0,
                                    parameter_scaling={"not_a_field": 2.0})


def test_statistical_stub_is_placeholder():
    with pytest.raises(NotImplementedError):
        StatisticalStubHVACObserver().observe(START)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class TestHVACAgentStub:
    def test_hourly_day_ahead_updates(self, definition):
        weather, house = make_weather(), make_house()
        observer = PhysicsStubHVACObserver(definition, weather, house, START, initial_air_temp=75.0,
                                           parameter_scaling={"UA": 1.1, "CM": 0.9})
        agent = HVACAgentStub("hvac_1", definition, observer)
        first = agent.update(START, weather, house)
        second = agent.update(START + HOUR, weather, house)
        assert len(first.intervals) == len(second.intervals) == 48
        assert second.intervals[0].start == START + HOUR
        assert second.observation.timestamp == START + HOUR
        assert agent.flexibility is second

    def test_degree_minutes_agent_real_time(self, definition):
        weather, house = make_weather(), make_house()
        observer = PhysicsStubHVACObserver(definition, weather, house, START, initial_air_temp=75.0)
        agent = HVACAgentStub("hvac_1", definition, observer,
                              HVACFlexibilityModel("degree_minutes_outside_band"))
        flex = agent.update(START + HOUR, weather, house, MarketHorizon.real_time(START + HOUR))
        assert len(flex.intervals) == 1 and flex.amenity_unit == "degF*min"

    def test_flexibility_requires_observation(self, definition):
        agent = HVACAgentStub("hvac_1", definition, StatisticalStubHVACObserver())
        with pytest.raises(RuntimeError, match="observe"):
            agent.define_flexibility(make_weather(), make_house(), MarketHorizon.day_ahead(START))
