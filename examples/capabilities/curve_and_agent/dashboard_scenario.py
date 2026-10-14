#!/usr/bin/env python3
"""
Generate an interactive Plotly dashboard from the demo_main_scenario simulation.

Shows all five device types (HVAC HP, HVAC AC, Water Heater, EV Charger,
Battery) participating in a real-time energy market.

Produces dashboard_scenario.html with:
  1. RT Supply vs Aggregate Demand — clearing intersection
  2. Per-device-type bid curves (color-coded)
  3. Flexibility envelopes by device type (dumbbell chart)
  4. HVAC Heat-Pump delivery timeline (5 ticks)
  5. Preference curves — price→quantity mapping per device
  6. Summary statistics table
  7. Clearing price timeseries
  8. Per-device cleared quantity timeseries
  9. Battery & EV SOC timeseries
 10. Temperature timeseries (HVAC air temps, outdoor, water heater)
"""

import math
import random
import os

from tesp_support.curve_and_agent.enums_and_constants import (
    DeviceType,
    MarketType,
    OperatingMode,
    PenaltyStructureType,
)
from tesp_support.curve_and_agent.data_types import (
    BidPoint,
    ClearingResult,
    EventDefinition,
    FlexibilityEnvelope,
    MarketTimingParams,
)
from tesp_support.curve_and_agent.data_streams import (
    ContinuousForecast,
    ConstraintStream,
    DataStreamManager,
    EventForecast,
    UncertaintyModel,
)
from tesp_support.curve_and_agent.gridlabd_interface import GridLABDInterface
from tesp_support.curve_and_agent.device_agent import DeviceAgent
from tesp_support.curve_and_agent.market_agent import MarketCommunicationInterface
from tesp_support.curve_and_agent.market_operator import (
    MarketOperator,
    SupplyCurve,
    DSOLoadEstimationEngine,
)
from tesp_support.curve_and_agent.penalty_model import PenaltyModel

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Device-type color palette & labels ────────────────────────────────

DEVICE_COLORS = {
    DeviceType.HVAC_HEAT_PUMP: "#3498db",
    DeviceType.HVAC_AC_ONLY: "#1abc9c",
    DeviceType.WATER_HEATER: "#e67e22",
    DeviceType.EV_CHARGER: "#2ecc71",
    DeviceType.BATTERY: "#9b59b6",
}

DEVICE_LABELS = {
    DeviceType.HVAC_HEAT_PUMP: "HVAC HP",
    DeviceType.HVAC_AC_ONLY: "HVAC AC",
    DeviceType.WATER_HEATER: "Water Heater",
    DeviceType.EV_CHARGER: "EV Charger",
    DeviceType.BATTERY: "Battery",
}

# ── Mocks ─────────────────────────────────────────────────────────────


class MockConnection:
    """Simple in-memory key/value backend for GridLABDInterface."""

    def __init__(self, initial_props=None):
        self._props = dict(initial_props or {})
        self.written = {}

    def get_value(self, key):
        return self._props.get(key, "")

    def set_value(self, key, value):
        self.written[key] = value


class MockTransport:
    def __init__(self, mo):
        self._mo = mo
        self._results = {}

    def submit(
        self,
        *,
        agent_id,
        market_type=None,
        bid=None,
        settlement=None,
        market_id=None,
        interval_id=None,
    ):
        if bid is not None:
            return self._mo.submit_agent_bid(agent_id, bid)
        return True

    def receive(self, *, agent_id, market_id):
        return self._results.get(agent_id)

    def push_results(self, results):
        self._results.update(results)


# ── Data-stream factories (same as demo_main_scenario) ───────────────


def _create_hvac_data_streams(device_type):
    dsm = DataStreamManager(device_type)
    dsm.register_continuous_stream(
        "outdoor_air_temp",
        ContinuousForecast(
            variable_name="outdoor_air_temp",
            unit="°F",
            uncertainty_model=UncertaintyModel(
                model_type="saturating_exp",
                params={"sigma_inf": 10.0, "tau_c": 24 * 3600},
            ),
        ),
    )
    dsm.register_continuous_stream(
        "solar_irradiance",
        ContinuousForecast(
            variable_name="solar_irradiance",
            unit="W/m²",
            uncertainty_model=UncertaintyModel(
                model_type="saturating_exp",
                params={"sigma_inf": 250.0, "tau_c": 6 * 3600},
            ),
        ),
    )
    dsm.register_schedule(
        "hvac_setpoint_schedule",
        ContinuousForecast(
            variable_name="hvac_setpoint",
            unit="°F",
            uncertainty_model=UncertaintyModel(
                model_type="empirical",
                params={"lead_time_sigma_table": [(0, 0.0), (86400, 0.5)]},
            ),
        ),
    )
    dsm.register_continuous_stream(
        "price_forecast",
        ContinuousForecast(
            variable_name="electricity_price",
            unit="$/kWh",
            uncertainty_model=UncertaintyModel(
                model_type="saturating_exp",
                params={"sigma_inf": 0.05, "tau_c": 4 * 3600},
            ),
        ),
    )
    return dsm


def _create_water_heater_data_streams():
    dsm = DataStreamManager(DeviceType.WATER_HEATER)
    dsm.register_event_stream(
        "hot_water_draw",
        EventForecast(
            event_types=[
                EventDefinition(
                    event_type="shower",
                    duration_mean=8.0,
                    duration_std=3.0,
                    magnitude_mean=2.3,
                    magnitude_std=0.4,
                    energy_mean=4.0,
                    energy_std=1.0,
                ),
                EventDefinition(
                    event_type="dishwash",
                    duration_mean=10.0,
                    duration_std=3.0,
                    magnitude_mean=1.5,
                    magnitude_std=0.3,
                    energy_mean=1.5,
                    energy_std=0.5,
                ),
            ],
            intensity_function=[
                (0.0, 4.0),  # Morning rush: 4 events/hr
                (3600.0, 2.0),  # Tapering
                (7200.0, 0.5),  # Post-rush
                (43200.0, 1.0),  # Midday
                (64800.0, 3.0),  # Evening peak
                (86400.0, 0.5),  # Night
            ],
            daily_expected_count=5.0,
            daily_expected_energy=12.0,
        ),
    )
    dsm.register_constraint(
        "tank_temp_minimum",
        ConstraintStream(
            constraint_id="tank_temp_min",
            variable="tank_temp",
            constraint_type="minimum",
            continuous=True,
            required_value=110.0,
        ),
    )
    dsm.register_continuous_stream(
        "inlet_water_temp",
        ContinuousForecast(
            variable_name="inlet_water_temp",
            unit="°F",
            uncertainty_model=UncertaintyModel(
                model_type="empirical",
                params={"lead_time_sigma_table": [(0, 0.5), (86400 * 7, 2.0)]},
            ),
        ),
    )
    dsm.register_continuous_stream(
        "price_forecast",
        ContinuousForecast(
            variable_name="electricity_price",
            unit="$/kWh",
            uncertainty_model=UncertaintyModel(
                model_type="saturating_exp",
                params={"sigma_inf": 0.05, "tau_c": 4 * 3600},
            ),
        ),
    )
    return dsm


def _create_ev_charger_data_streams():
    dsm = DataStreamManager(DeviceType.EV_CHARGER)
    dsm.register_constraint(
        "ev_departure_soc",
        ConstraintStream(
            constraint_id="ev_departure",
            variable="soc",
            constraint_type="by_time",
            continuous=False,
            deadline=7.0 * 3600,
            required_value=0.50,
        ),
    )
    dsm.register_schedule(
        "ev_preferred_soc",
        ContinuousForecast(
            variable_name="preferred_soc",
            unit="fraction",
            uncertainty_model=UncertaintyModel(
                model_type="empirical",
                params={"lead_time_sigma_table": [(0, 0.0), (86400, 0.0)]},
            ),
        ),
    )
    dsm.register_event_stream(
        "ev_arrival",
        EventForecast(
            event_types=[
                EventDefinition(
                    event_type="ev_arrival",
                    duration_mean=0,
                    magnitude_mean=0.65,
                    magnitude_std=0.08,
                )
            ],
            daily_expected_count=1.0,
            daily_expected_energy=0.0,
        ),
    )
    dsm.register_continuous_stream(
        "price_forecast",
        ContinuousForecast(
            variable_name="electricity_price",
            unit="$/kWh",
            uncertainty_model=UncertaintyModel(
                model_type="saturating_exp",
                params={"sigma_inf": 0.05, "tau_c": 4 * 3600},
            ),
        ),
    )
    return dsm


def _create_battery_data_streams():
    dsm = DataStreamManager(DeviceType.BATTERY)
    dsm.register_constraint(
        "soc_reserve",
        ConstraintStream(
            constraint_id="battery_reserve",
            variable="soc",
            constraint_type="minimum",
            continuous=True,
            required_value=0.20,
        ),
    )
    dsm.register_schedule(
        "battery_preferred_soc",
        ContinuousForecast(
            variable_name="preferred_soc",
            unit="fraction",
            uncertainty_model=UncertaintyModel(
                model_type="empirical",
                params={"lead_time_sigma_table": [(0, 0.0), (86400, 0.0)]},
            ),
        ),
    )
    dsm.register_continuous_stream(
        "price_forecast",
        ContinuousForecast(
            variable_name="electricity_price",
            unit="$/kWh",
            uncertainty_model=UncertaintyModel(
                model_type="saturating_exp",
                params={"sigma_inf": 0.05, "tau_c": 4 * 3600},
            ),
        ),
    )
    dsm.register_continuous_stream(
        "btm_solar",
        ContinuousForecast(
            variable_name="btm_solar_generation",
            unit="kW",
            uncertainty_model=UncertaintyModel(
                model_type="saturating_exp",
                params={"sigma_inf": 2.0, "tau_c": 6 * 3600},
            ),
        ),
    )
    dsm.register_continuous_stream(
        "household_net_load",
        ContinuousForecast(
            variable_name="household_net_load",
            unit="kW",
            uncertainty_model=UncertaintyModel(
                model_type="saturating_exp",
                params={"sigma_inf": 3.0, "tau_c": 4 * 3600},
            ),
        ),
    )
    return dsm


# ── Device mock properties (same as demo_main_scenario) ──────────────

PROPS = {
    # HVAC heat pump
    "house_1#power_state": "COOL",
    "house_1#air_temperature": 74.0,
    "house_1#outdoor_temperature": 90.0,
    "house_1#cooling_setpoint": 72.0,
    "house_1#heating_setpoint": 68.0,
    "house_1#hvac_load": 3000.0,
    "house_1#mass_temperature": 73.0,
    "house_1#Ca": 1500.0,
    "house_1#Cm": 5000.0,
    "house_1#Ua": 450.0,
    "house_1#Hm": 1400.0,
    "house_1#cooling_COP": 3.5,
    "house_1#heating_COP": 3.1,
    "house_1#design_cooling_capacity": 36000.0,
    "house_1#design_heating_capacity": 32000.0,
    # HVAC AC-only
    "house_2#power_state": "COOL",
    "house_2#air_temperature": 75.0,
    "house_2#outdoor_temperature": 90.0,
    "house_2#cooling_setpoint": 73.0,
    "house_2#heating_setpoint": 67.0,
    "house_2#hvac_load": 2600.0,
    "house_2#mass_temperature": 74.0,
    "house_2#Ca": 1400.0,
    "house_2#Cm": 4700.0,
    "house_2#Ua": 500.0,
    "house_2#Hm": 1350.0,
    "house_2#cooling_COP": 3.4,
    "house_2#heating_COP": 2.8,
    "house_2#design_cooling_capacity": 30000.0,
    "house_2#design_heating_capacity": 20000.0,
    # Water heater
    "waterheater_1#UTTemp": 128.0,
    "waterheater_1#LTTemp": 124.0,
    "waterheater_1#upper_tank_setpoint": 130.0,
    "waterheater_1#lower_tank_setpoint": 130.0,
    "waterheater_1#UTState": "OFF",
    "waterheater_1#LTState": "ON",
    "waterheater_1#WHLoad": 2.5,
    "waterheater_1#tank_volume": 50.0,
    "waterheater_1#tank_UA": 2.0,
    "waterheater_1#heating_element_capacity": 4.5,
    "waterheater_1#inlet_water_temperature": 62.0,
    "waterheater_1#WDRate": 0.0,
    "waterheater_1#tank_height": 4.0,
    # EV charger
    "evcharger_1#SOC": 0.42,
    "evcharger_1#charge_rate": 0.0,
    "evcharger_1#battery_capacity": 72.0,
    "evcharger_1#max_charge_rate": 7.2,
    "evcharger_1#charger_efficiency": 0.92,
    "evcharger_1#vehicle_connected": "TRUE",
    "evcharger_1#min_charge_rate": 1.0,
    "evcharger_1#soc_at_max_taper": 0.82,
    # Home battery
    "battery_1#SOC": 0.58,
    "battery_1#p_out": 0.0,
    "battery_1#battery_capacity": 13.5,
    "battery_1#rated_power": 5.0,
    "battery_1#round_trip_efficiency": 0.9,
    "battery_1#cell_temperature": 25.0,
    "battery_1#soc_min_bms": 0.1,
    "battery_1#soc_max_bms": 0.95,
    "battery_1#inverter_rated_power": 5.0,
    "battery_1#state_of_health": 0.98,
}

AGENT_CONFIGS = [
    {
        "label": "HVAC HP",
        "dtype": DeviceType.HVAC_HEAT_PUMP,
        "obj": "house_1",
        "k": 0.3,
    },
    {
        "label": "HVAC AC",
        "dtype": DeviceType.HVAC_AC_ONLY,
        "obj": "house_2",
        "k": 0.5,
    },
    {
        "label": "Water Heater",
        "dtype": DeviceType.WATER_HEATER,
        "obj": "waterheater_1",
        "k": 0.4,
    },
    {
        "label": "EV Charger",
        "dtype": DeviceType.EV_CHARGER,
        "obj": "evcharger_1",
        "k": 0.6,
    },
    {
        "label": "Battery",
        "dtype": DeviceType.BATTERY,
        "obj": "battery_1",
        "k": 0.8,
    },
]

N_STEPS = 24  # 24 clearing cycles
INTERVAL = 300.0  # 5-minute RT interval (seconds)


# ── Run the simulation and collect data ───────────────────────────────


def _make_dsm(dtype):
    if dtype in (DeviceType.HVAC_AC_ONLY, DeviceType.HVAC_HEAT_PUMP):
        return _create_hvac_data_streams(dtype)
    if dtype == DeviceType.WATER_HEATER:
        return _create_water_heater_data_streams()
    if dtype == DeviceType.EV_CHARGER:
        return _create_ev_charger_data_streams()
    return _create_battery_data_streams()


def run_simulation():
    random.seed(42)  # reproducible event sampling
    connection = MockConnection(dict(PROPS))  # copy so mutations stay local

    rt_timing = MarketTimingParams()
    mo = MarketOperator(
        market_type=MarketType.RT_ENERGY,
        timing_params=rt_timing,
        iteration_protocol="fixed_count",
        n_informational=0,
    )
    supply = SupplyCurve(
        points=[
            BidPoint(price=0.02, quantity=0.0),
            BidPoint(price=0.05, quantity=500.0),
            BidPoint(price=0.08, quantity=1000.0),
            BidPoint(price=0.15, quantity=1500.0),
            BidPoint(price=0.50, quantity=2000.0),
            BidPoint(price=1.00, quantity=2000.0),
        ]
    )
    mo.set_supply_curve(supply)

    dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
    transport = MockTransport(mo)

    rt_penalty = PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
    )

    # ── Create agents ─────────────────────────────────────────────────
    agents, comms = [], []
    for cfg in AGENT_CONFIGS:
        aid = cfg["label"].lower().replace(" ", "_")
        gld = GridLABDInterface(
            connection=connection,
            object_name=cfg["obj"],
            device_type=cfg["dtype"],
        )
        dsm = _make_dsm(cfg["dtype"])
        ag = DeviceAgent(
            agent_id=aid,
            device_type=cfg["dtype"],
            gridlabd=gld,
            customer_preference_k=cfg["k"],
            data_stream_manager=dsm,
        )
        if cfg["dtype"] == DeviceType.BATTERY:
            ag.initialize(
                {
                    "replacement_cost": 10000.0,
                    "rated_cycles": 5000,
                    "rated_dod": 0.80,
                    "wohler_exponent": 1.5,
                }
            )
        else:
            ag.initialize({})

        comm = MarketCommunicationInterface(
            transport=transport,
            agent_id=aid,
            market_type=MarketType.RT_ENERGY,
        )
        ag.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=rt_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=rt_penalty,
            communication=comm,
        )
        agents.append(ag)
        comms.append(comm)

    # ── Timeseries collectors ─────────────────────────────────────────
    ts = {
        "time": [],
        "clearing_price": [],
        "clearing_quantity": [],
        "device_qty": {cfg["label"]: [] for cfg in AGENT_CONFIGS},
        "battery_soc": [],
        "ev_soc": [],
        "hvac_hp_temp": [],
        "hvac_ac_temp": [],
        "outdoor_temp": [],
        "wh_temp": [],
    }
    first_step = {}
    first_hp_pref = None
    first_hp_state = None
    first_hp_mid = None

    # ── Multi-step simulation loop ────────────────────────────────────
    for step in range(N_STEPS):
        t = step * INTERVAL

        # Evolve outdoor temperature sinusoidally
        outdoor = 85.0 + 10.0 * math.sin(2 * math.pi * step / N_STEPS)
        connection._props["house_1#outdoor_temperature"] = outdoor
        connection._props["house_2#outdoor_temperature"] = outdoor

        # Evolve inflexible load
        inflexible_load = 300.0 + 150.0 * math.sin(2 * math.pi * step / N_STEPS + 0.5)
        btm_solar = 50.0 + 40.0 * max(0, math.sin(2 * math.pi * step / N_STEPS - 0.3))

        dso_bid = dso.estimate_inflexible_load(
            interval=(t, t + INTERVAL),
            total_load_forecast=inflexible_load,
            flexible_committed=0.0,
            btm_solar_forecast=btm_solar,
            loss_factor=0.04,
        )
        mo.submit_dso_inflexible_bid("feeder_1", dso_bid)

        # F1–F5 for all agents
        step_bids = {}
        step_states = {}
        step_flexes = {}
        step_prefs = {}

        for i, (ag, cfg) in enumerate(zip(agents, AGENT_CONFIGS)):
            label = cfg["label"]
            aid = label.lower().replace(" ", "_")

            st = ag.observe_device_state()
            fl = ag.estimate_flexibility(st, INTERVAL)
            pr = ag.generate_preference_curve(fl)
            m = ag.spawn_market_cycle(MarketType.RT_ENERGY, clearing_time=t + INTERVAL)
            mobj = ag._market_objects[m]
            mobj.available_flexibility = fl
            mobj.preference_curve = pr
            bid = ag.formulate_bid(mobj, fl, pr)
            comms[i].submit_bid(bid, market_id=m, interval_id=f"int_{m}")

            step_bids[label] = [(pt.price, pt.quantity) for pt in bid.points]
            step_states[label] = st
            step_flexes[label] = fl

            if step == 0:
                pref_pts = []
                for p_cents in range(1, 101):
                    p = p_cents / 100.0
                    q = pr.evaluate(p)
                    pref_pts.append((p, q))
                step_prefs[label] = pref_pts

        # Clear market
        clearing = mo.clear_market()
        per_agent = mo.propagate_results()

        # Record timeseries
        ts["time"].append(t / 60.0)
        ts["clearing_price"].append(clearing.cleared_price)
        ts["clearing_quantity"].append(clearing.cleared_quantity)
        ts["battery_soc"].append(connection._props["battery_1#SOC"])
        ts["ev_soc"].append(connection._props["evcharger_1#SOC"])
        ts["hvac_hp_temp"].append(connection._props["house_1#air_temperature"])
        ts["hvac_ac_temp"].append(connection._props["house_2#air_temperature"])
        ts["outdoor_temp"].append(outdoor)
        ts["wh_temp"].append(connection._props["waterheater_1#UTTemp"])

        for cfg in AGENT_CONFIGS:
            aid = cfg["label"].lower().replace(" ", "_")
            r = per_agent.get(aid)
            ts["device_qty"][cfg["label"]].append(r.cleared_quantity if r else 0.0)

        # Save first-step snapshot for static panels
        if step == 0:
            first_step = {
                "dso_bid": dso_bid,
                "clearing": clearing,
                "per_agent": per_agent,
                "agg_demand": mo.aggregate_demand(),
                "all_bids": dict(step_bids),
                "all_prefs": dict(step_prefs),
                "all_states": dict(step_states),
                "all_flexes": dict(step_flexes),
            }
            for cfg in AGENT_CONFIGS:
                aid = cfg["label"].lower().replace(" ", "_")
                r = per_agent.get(aid)
                cfg["cleared_qty"] = r.cleared_quantity if r else 0.0
            first_hp_pref = agents[0]._current_preference_curve
            first_hp_state = step_states["HVAC HP"]
            first_hp_mid = list(agents[0]._market_objects.keys())[0]

        # Update device states for next step
        bat_r = per_agent.get("battery")
        if bat_r:
            eta = math.sqrt(0.9)
            p_kw = bat_r.cleared_quantity
            energy = (p_kw * eta if p_kw >= 0 else p_kw / eta) * (INTERVAL / 3600.0)
            new_soc = connection._props["battery_1#SOC"] + energy / 13.5
            connection._props["battery_1#SOC"] = max(0.1, min(0.95, new_soc))

        ev_r = per_agent.get("ev_charger")
        if ev_r and ev_r.cleared_quantity > 0:
            delta = ev_r.cleared_quantity * (INTERVAL / 3600.0) * 0.92 / 72.0
            connection._props["evcharger_1#SOC"] = min(
                0.95, connection._props["evcharger_1#SOC"] + delta
            )

        hp_r = per_agent.get("hvac_hp")
        if hp_r and hp_r.cleared_quantity > 0.5:
            connection._props["house_1#air_temperature"] -= 0.3
        else:
            drift = (
                0.15
                * (outdoor - connection._props["house_1#air_temperature"])
                * (INTERVAL / 3600.0)
            )
            connection._props["house_1#air_temperature"] += drift

        ac_r = per_agent.get("hvac_ac")
        if ac_r and ac_r.cleared_quantity > 0.5:
            connection._props["house_2#air_temperature"] -= 0.25
        else:
            drift = (
                0.15
                * (outdoor - connection._props["house_2#air_temperature"])
                * (INTERVAL / 3600.0)
            )
            connection._props["house_2#air_temperature"] += drift

        wh_r = per_agent.get("water_heater")
        # Sample draw events from EventForecast using Poisson intensity
        wh_agent = agents[2]  # Water Heater agent
        draw_forecast = wh_agent._data_streams.get_event("hot_water_draw")
        lam = draw_forecast.get_intensity_at(t)  # events/hour
        p_event = 1.0 - math.exp(-lam * (INTERVAL / 3600.0))
        if random.random() < p_event:
            # Pick an EventDefinition weighted uniformly
            edef = random.choice(draw_forecast._event_types)
            flow_gpm = max(
                0.1,
                random.gauss(
                    edef.magnitude_mean, getattr(edef, "magnitude_std", 0) or 0
                ),
            )
            energy = max(
                0.1, random.gauss(edef.energy_mean, getattr(edef, "energy_std", 0) or 0)
            )
            connection._props["waterheater_1#WDRate"] = flow_gpm
            temp_drop = flow_gpm * 1.8  # heuristic: higher flow → bigger drop
            connection._props["waterheater_1#UTTemp"] = max(
                115.0, connection._props["waterheater_1#UTTemp"] - temp_drop
            )
            connection._props["waterheater_1#LTTemp"] = max(
                110.0, connection._props["waterheater_1#LTTemp"] - temp_drop * 1.2
            )
            # Condition the forecast on the observed event (Bayesian update)
            draw_forecast.condition_on_observation(edef.event_type, t, energy)
        else:
            connection._props["waterheater_1#WDRate"] = 0.0

        if wh_r and wh_r.cleared_quantity > 0.5:
            connection._props["waterheater_1#UTTemp"] = min(
                140.0, connection._props["waterheater_1#UTTemp"] + 0.6
            )
            # Lower zone warms via mixing with heated upper zone
            connection._props["waterheater_1#LTTemp"] = min(
                connection._props["waterheater_1#UTTemp"],
                connection._props["waterheater_1#LTTemp"] + 0.3,
            )
        else:
            connection._props["waterheater_1#UTTemp"] = max(
                115.0, connection._props["waterheater_1#UTTemp"] - 0.15
            )

        connection._props["house_1#mass_temperature"] = (
            connection._props["house_1#air_temperature"] - 1.0
        )
        connection._props["house_2#mass_temperature"] = (
            connection._props["house_2#air_temperature"] - 1.0
        )

    # ── HVAC HP delivery trace (first-step data) ─────────────────────
    hp_agent = agents[0]
    hp_mobj = hp_agent._market_objects[first_hp_mid]
    first_clearing = first_step["clearing"]
    hp_mobj.cleared_price = first_clearing.cleared_price
    hp_result = first_step["per_agent"].get(
        AGENT_CONFIGS[0]["label"].lower().replace(" ", "_")
    )
    hp_mobj.cleared_quantity = hp_result.cleared_quantity if hp_result else 0.0

    hp_agent._command_arbiter.register_delivery(
        market_id=first_hp_mid,
        market_type=str(MarketType.RT_ENERGY),
        product_type="ENERGY_BASE",
        committed_qty=hp_result.cleared_quantity if hp_result else 0.0,
        cleared_price=first_clearing.cleared_price,
        penalty_model=rt_penalty,
        interval=(0.0, INTERVAL),
    )

    delivery_trace = []
    for tick in range(5):
        tick_t = tick * 60.0
        frs = hp_agent._command_arbiter.resolve_and_actuate(
            device_state=first_hp_state,
            preference_curve=first_hp_pref,
            amenity_weight=hp_agent._k,
            current_time=tick_t,
        )
        for m_id, fr in frs.items():
            delivery_trace.append(
                {
                    "t": tick_t,
                    "committed": fr.committed,
                    "actual": fr.actual,
                    "shortfall": fr.shortfall,
                    "revenue": fr.revenue,
                    "penalty": fr.penalty,
                    "net_value": fr.net_value,
                }
            )

    settlement = hp_agent.reconcile(hp_mobj)

    return {
        "supply": supply,
        "dso_bid": first_step["dso_bid"],
        "agg_demand": first_step["agg_demand"],
        "clearing": first_step["clearing"],
        "per_agent": first_step["per_agent"],
        "agent_configs": AGENT_CONFIGS,
        "all_bids": first_step["all_bids"],
        "all_prefs": first_step["all_prefs"],
        "all_states": first_step["all_states"],
        "all_flexes": first_step["all_flexes"],
        "delivery_trace": delivery_trace,
        "settlement": settlement,
        "timeseries": ts,
    }


# ── Build Dashboard ──────────────────────────────────────────────────


def build_dashboard(data):
    supply = data["supply"]
    dso_bid = data["dso_bid"]
    agg_demand = data["agg_demand"]
    clearing = data["clearing"]
    agent_configs = data["agent_configs"]
    all_bids = data["all_bids"]
    all_prefs = data["all_prefs"]
    all_flexes = data["all_flexes"]
    delivery_trace = data["delivery_trace"]
    settlement = data["settlement"]
    ts = data["timeseries"]

    SUPPLY_COLOR = "#2ecc71"
    DEMAND_COLOR = "#3498db"
    CLEARING_COLOR = "#e74c3c"
    INFLEXIBLE_COLOR = "#95a5a6"
    BG_COLOR = "#fafbfc"
    GRID_COLOR = "#e0e0e0"

    fig = make_subplots(
        rows=5,
        cols=2,
        subplot_titles=(
            "RT Supply vs Aggregate Demand",
            "Per-Device Bid Curves",
            "Flexibility Envelopes by Device",
            "HVAC Heat-Pump — Delivery Timeline",
            "Preference Curves (Price → Quantity)",
            "Summary Statistics",
            "Clearing Price (timeseries)",
            "Per-Device Cleared Quantities (timeseries)",
            "Battery & EV SOC (timeseries)",
            "Temperatures (timeseries)",
        ),
        specs=[
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "table"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "xy"}],
        ],
        vertical_spacing=0.06,
        horizontal_spacing=0.08,
    )

    # ── 1. Supply vs Aggregate Demand ─────────────────────────────────
    s_qty = [pt.quantity for pt in supply.points]
    s_price = [pt.price for pt in supply.points]
    fig.add_trace(
        go.Scatter(
            x=s_qty,
            y=s_price,
            mode="lines+markers",
            name="Supply",
            line=dict(color=SUPPLY_COLOR, width=3),
            marker=dict(size=6),
        ),
        row=1,
        col=1,
    )

    d_qty = [pt.quantity for pt in agg_demand]
    d_price = [pt.price for pt in agg_demand]
    fig.add_trace(
        go.Scatter(
            x=d_qty,
            y=d_price,
            mode="lines+markers",
            name="Agg. Demand",
            line=dict(color=DEMAND_COLOR, width=3),
            marker=dict(size=6),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=[dso_bid.quantity, dso_bid.quantity],
            y=[0, 1.0],
            mode="lines",
            name=f"Inflexible ({dso_bid.quantity:.0f} kW)",
            line=dict(color=INFLEXIBLE_COLOR, width=2, dash="dash"),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=[clearing.cleared_quantity],
            y=[clearing.cleared_price],
            mode="markers",
            name="Clearing Point",
            marker=dict(
                color=CLEARING_COLOR,
                size=14,
                symbol="star",
                line=dict(width=2, color="white"),
            ),
            text=[
                f"${clearing.cleared_price:.4f}/kWh"
                f"<br>{clearing.cleared_quantity:.1f} kW"
            ],
            hoverinfo="text",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=[0, max(s_qty[-1], d_qty[0] if d_qty else 0) * 1.05],
            y=[clearing.cleared_price, clearing.cleared_price],
            mode="lines",
            line=dict(color=CLEARING_COLOR, width=1.5, dash="dot"),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    fig.update_xaxes(title_text="Quantity (kW)", row=1, col=1)
    fig.update_yaxes(title_text="Price ($/kWh)", row=1, col=1)

    # ── 2. Per-Device Bid Curves ──────────────────────────────────────
    for cfg in agent_configs:
        label = cfg["label"]
        color = DEVICE_COLORS[cfg["dtype"]]
        pts = all_bids[label]
        prices = [p for p, q in pts]
        qtys = [q for p, q in pts]
        fig.add_trace(
            go.Scatter(
                x=qtys,
                y=prices,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=3),
                marker=dict(size=5, color=color),
                hovertemplate=(
                    f"<b>{label}</b> (k={cfg['k']:.2f})<br>"
                    "Price: $%{y:.4f}/kWh<br>Qty: %{x:.3f} kW<extra></extra>"
                ),
            ),
            row=1,
            col=2,
        )

    # Clearing price line
    fig.add_trace(
        go.Scatter(
            x=[
                min(q for pts in all_bids.values() for _, q in pts) - 0.5,
                max(q for pts in all_bids.values() for _, q in pts) + 0.5,
            ],
            y=[clearing.cleared_price, clearing.cleared_price],
            mode="lines",
            line=dict(color=CLEARING_COLOR, width=1.5, dash="dot"),
            name="Clearing Price",
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    fig.update_xaxes(title_text="Quantity (kW)", row=1, col=2)
    fig.update_yaxes(title_text="Price ($/kWh)", row=1, col=2)

    # ── 3. Flexibility Envelopes (dumbbell chart) ─────────────────────
    labels = [cfg["label"] for cfg in agent_configs]
    for i, cfg in enumerate(agent_configs):
        label = cfg["label"]
        color = DEVICE_COLORS[cfg["dtype"]]
        flex = all_flexes[label]

        # Range line Q_min → Q_max
        fig.add_trace(
            go.Scatter(
                x=[flex.Q_min, flex.Q_max],
                y=[label, label],
                mode="lines",
                line=dict(color=color, width=10),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=2,
            col=1,
        )

        # Q_min endpoint
        fig.add_trace(
            go.Scatter(
                x=[flex.Q_min],
                y=[label],
                mode="markers",
                marker=dict(
                    symbol="line-ns-open",
                    size=14,
                    color=color,
                    line=dict(width=3, color=color),
                ),
                showlegend=False,
                hovertemplate=(
                    f"<b>{label}</b><br>Q_min: {flex.Q_min:.2f} kW<extra></extra>"
                ),
            ),
            row=2,
            col=1,
        )

        # Q_baseline diamond
        fig.add_trace(
            go.Scatter(
                x=[flex.Q_baseline],
                y=[label],
                mode="markers",
                marker=dict(
                    symbol="diamond",
                    size=14,
                    color="white",
                    line=dict(width=2.5, color=color),
                ),
                showlegend=False,
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    f"Baseline: {flex.Q_baseline:.2f} kW<extra></extra>"
                ),
            ),
            row=2,
            col=1,
        )

        # Q_max endpoint
        fig.add_trace(
            go.Scatter(
                x=[flex.Q_max],
                y=[label],
                mode="markers",
                marker=dict(
                    symbol="line-ns-open",
                    size=14,
                    color=color,
                    line=dict(width=3, color=color),
                ),
                showlegend=False,
                hovertemplate=(
                    f"<b>{label}</b><br>Q_max: {flex.Q_max:.2f} kW<extra></extra>"
                ),
            ),
            row=2,
            col=1,
        )

    # Zero-power reference line
    fig.add_vline(
        x=0,
        line_dash="dot",
        line_color=INFLEXIBLE_COLOR,
        line_width=1,
        row=2,
        col=1,
    )

    fig.update_xaxes(title_text="Power (kW)", row=2, col=1)
    fig.update_yaxes(title_text="", row=2, col=1)

    # ── 4. HVAC HP Delivery Timeline ──────────────────────────────────
    times = [d["t"] for d in delivery_trace]
    committed = [d["committed"] for d in delivery_trace]
    actual = [d["actual"] for d in delivery_trace]

    fig.add_trace(
        go.Bar(
            x=times,
            y=committed,
            name="Committed",
            marker_color=DEMAND_COLOR,
            opacity=0.5,
            width=40,
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Bar(
            x=times,
            y=actual,
            name="Actual",
            marker_color=SUPPLY_COLOR,
            opacity=0.8,
            width=30,
        ),
        row=2,
        col=2,
    )

    for d in delivery_trace:
        fig.add_annotation(
            x=d["t"],
            y=d["actual"] * 1.08 if d["actual"] != 0 else 0.08,
            text=f"${d['revenue']:.3f}",
            showarrow=False,
            font=dict(size=9, color="#555"),
            row=2,
            col=2,
        )

    fig.update_xaxes(title_text="Time (s)", row=2, col=2)
    fig.update_yaxes(title_text="Power (kW)", row=2, col=2)

    # ── 5. Preference Curves ──────────────────────────────────────────
    for cfg in agent_configs:
        label = cfg["label"]
        color = DEVICE_COLORS[cfg["dtype"]]
        pts = all_prefs[label]
        prices = [p for p, q in pts]
        qtys = [q for p, q in pts]
        fig.add_trace(
            go.Scatter(
                x=prices,
                y=qtys,
                mode="lines",
                name=label,
                line=dict(color=color, width=2.5),
                showlegend=False,
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "Price: $%{x:.2f}/kWh<br>Q: %{y:.2f} kW<extra></extra>"
                ),
            ),
            row=3,
            col=1,
        )

    # Clearing price vertical line
    fig.add_vline(
        x=clearing.cleared_price,
        line_dash="dash",
        line_color=CLEARING_COLOR,
        annotation_text=f"${clearing.cleared_price:.4f}",
        annotation_font_color=CLEARING_COLOR,
        row=3,
        col=1,
    )

    fig.update_xaxes(title_text="Price ($/kWh)", row=3, col=1)
    fig.update_yaxes(title_text="Quantity (kW)", row=3, col=1)

    # ── 6. Summary Statistics Table ───────────────────────────────────
    metric_labels = [
        "Device types in market",
        "Clearing price (t=0)",
        "Aggregate cleared load (t=0)",
        "Inflexible load (DSO, t=0)",
        f"Simulation steps",
        "",
    ]
    metric_values = [
        "5 (HVAC HP, HVAC AC, WH, EV, Battery)",
        f"${clearing.cleared_price:.4f}/kWh",
        f"{clearing.cleared_quantity:.1f} kW",
        f"{dso_bid.quantity:.1f} kW",
        f"{N_STEPS} × {INTERVAL:.0f}s = {N_STEPS * INTERVAL / 60:.0f} min",
        "",
    ]

    for cfg in agent_configs:
        label = cfg["label"]
        flex = all_flexes[label]
        q = cfg.get("cleared_qty", 0.0)
        metric_labels.append(f"<b>{label}</b> (k={cfg['k']:.2f})")
        metric_values.append("")
        metric_labels.append("  Cleared quantity (t=0)")
        metric_values.append(f"{q:.3f} kW")
        metric_labels.append("  Flex range (t=0)")
        metric_values.append(f"[{flex.Q_min:.2f}, {flex.Q_max:.2f}] kW")
        metric_labels.append("  Baseline")
        metric_values.append(f"{flex.Q_baseline:.2f} kW")

    metric_labels += [
        "",
        "<b>HVAC HP Settlement (5 min)</b>",
        "  Revenue",
        "  Penalty",
        "  Net settlement",
    ]
    metric_values += [
        "",
        "",
        f"${settlement.total_revenue:.4f}",
        f"${settlement.total_penalty:.4f}",
        f"<b>${settlement.net_settlement:.4f}</b>",
    ]

    fig.add_trace(
        go.Table(
            header=dict(
                values=["<b>Metric</b>", "<b>Value</b>"],
                fill_color="#34495e",
                font=dict(color="white", size=12),
                align="left",
                height=28,
            ),
            cells=dict(
                values=[metric_labels, metric_values],
                fill_color=[["#f7f9fa", "white"] * (len(metric_labels) // 2 + 1)],
                align="left",
                height=24,
                font=dict(size=11),
            ),
        ),
        row=3,
        col=2,
    )

    # ── 7. Clearing Price Timeseries ──────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=ts["time"],
            y=ts["clearing_price"],
            mode="lines+markers",
            name="Clearing Price",
            line=dict(color=CLEARING_COLOR, width=2.5),
            marker=dict(size=5),
            showlegend=False,
            hovertemplate="t=%{x:.0f} min<br>$%{y:.4f}/kWh<extra></extra>",
        ),
        row=4,
        col=1,
    )

    fig.update_xaxes(title_text="Time (min)", row=4, col=1)
    fig.update_yaxes(title_text="Price ($/kWh)", row=4, col=1)

    # ── 8. Per-Device Cleared Quantities Timeseries ───────────────────
    for cfg in agent_configs:
        label = cfg["label"]
        color = DEVICE_COLORS[cfg["dtype"]]
        fig.add_trace(
            go.Scatter(
                x=ts["time"],
                y=ts["device_qty"][label],
                mode="lines+markers",
                name=f"{label} (ts)",
                line=dict(color=color, width=2),
                marker=dict(size=4, color=color),
                showlegend=False,
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "t=%{x:.0f} min<br>%{y:.3f} kW<extra></extra>"
                ),
            ),
            row=4,
            col=2,
        )

    fig.update_xaxes(title_text="Time (min)", row=4, col=2)
    fig.update_yaxes(title_text="Cleared Quantity (kW)", row=4, col=2)

    # ── 9. Battery & EV SOC Timeseries ────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=ts["time"],
            y=[s * 100 for s in ts["battery_soc"]],
            mode="lines+markers",
            name="Battery SOC",
            line=dict(color=DEVICE_COLORS[DeviceType.BATTERY], width=2.5),
            marker=dict(size=5),
            showlegend=False,
            hovertemplate=(
                "<b>Battery</b><br>t=%{x:.0f} min<br>SOC: %{y:.1f}%<extra></extra>"
            ),
        ),
        row=5,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=ts["time"],
            y=[s * 100 for s in ts["ev_soc"]],
            mode="lines+markers",
            name="EV SOC",
            line=dict(color=DEVICE_COLORS[DeviceType.EV_CHARGER], width=2.5),
            marker=dict(size=5),
            showlegend=False,
            hovertemplate=(
                "<b>EV</b><br>t=%{x:.0f} min<br>SOC: %{y:.1f}%<extra></extra>"
            ),
        ),
        row=5,
        col=1,
    )

    # SOC reserve line for battery (drawn as Scatter to avoid
    # Plotly bug with add_hline after a Table trace)
    fig.add_trace(
        go.Scatter(
            x=[ts["time"][0], ts["time"][-1]],
            y=[20, 20],
            mode="lines",
            line=dict(
                dash="dot",
                color=DEVICE_COLORS[DeviceType.BATTERY],
                width=1,
            ),
            showlegend=False,
            hoverinfo="skip",
        ),
        row=5,
        col=1,
    )

    fig.update_xaxes(title_text="Time (min)", row=5, col=1)
    fig.update_yaxes(title_text="SOC (%)", range=[0, 100], row=5, col=1)

    # ── 10. Temperature Timeseries ────────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=ts["time"],
            y=ts["outdoor_temp"],
            mode="lines",
            name="Outdoor",
            line=dict(color="#e74c3c", width=2, dash="dash"),
            showlegend=False,
            hovertemplate=(
                "<b>Outdoor</b><br>t=%{x:.0f} min<br>%{y:.1f} °F<extra></extra>"
            ),
        ),
        row=5,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=ts["time"],
            y=ts["hvac_hp_temp"],
            mode="lines+markers",
            name="HVAC HP Indoor",
            line=dict(color=DEVICE_COLORS[DeviceType.HVAC_HEAT_PUMP], width=2),
            marker=dict(size=4),
            showlegend=False,
            hovertemplate=(
                "<b>HVAC HP</b><br>t=%{x:.0f} min<br>%{y:.1f} °F<extra></extra>"
            ),
        ),
        row=5,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=ts["time"],
            y=ts["hvac_ac_temp"],
            mode="lines+markers",
            name="HVAC AC Indoor",
            line=dict(color=DEVICE_COLORS[DeviceType.HVAC_AC_ONLY], width=2),
            marker=dict(size=4),
            showlegend=False,
            hovertemplate=(
                "<b>HVAC AC</b><br>t=%{x:.0f} min<br>%{y:.1f} °F<extra></extra>"
            ),
        ),
        row=5,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=ts["time"],
            y=ts["wh_temp"],
            mode="lines+markers",
            name="Water Heater",
            line=dict(color=DEVICE_COLORS[DeviceType.WATER_HEATER], width=2),
            marker=dict(size=4),
            showlegend=False,
            hovertemplate=(
                "<b>Water Heater</b><br>t=%{x:.0f} min<br>%{y:.1f} °F<extra></extra>"
            ),
        ),
        row=5,
        col=2,
    )

    fig.update_xaxes(title_text="Time (min)", row=5, col=2)
    fig.update_yaxes(title_text="Temperature (°F)", row=5, col=2)

    # ── Layout ────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text=(
                "<b>TESP Multi-Device Scenario Dashboard</b>"
                f"<br><sup>5 device types · RT energy market · "
                f"Clearing: ${clearing.cleared_price:.4f}/kWh "
                f"@ {clearing.cleared_quantity:.1f} kW</sup>"
            ),
            x=0.5,
            y=0.98,
            yanchor="top",
            font=dict(size=20),
        ),
        height=1350,
        width=1400,
        margin=dict(t=140),
        template="plotly_white",
        paper_bgcolor=BG_COLOR,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.065,
            xanchor="center",
            x=0.5,
        ),
        barmode="overlay",
    )

    for i in range(1, 4):
        for j in range(1, 3):
            try:
                fig.update_xaxes(gridcolor=GRID_COLOR, row=i, col=j)
                fig.update_yaxes(gridcolor=GRID_COLOR, row=i, col=j)
            except Exception:
                pass

    return fig


# ── Main ──────────────────────────────────────────────────────────────


def main():
    print(f"Running multi-device scenario ({N_STEPS} steps)...")
    data = run_simulation()

    print("Building dashboard...")
    fig = build_dashboard(data)

    out_path = os.path.join(os.path.dirname(__file__), "dashboard_scenario.html")
    fig.write_html(out_path, include_plotlyjs=True, full_html=True)
    print(f"Dashboard written to {out_path}")
    print(f"Open in browser:  file://{os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
