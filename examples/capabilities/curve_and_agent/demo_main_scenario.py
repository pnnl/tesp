"""Executable demo scenario for the curve_and_agent stack.

This demo mirrors the reference wiring in main.py but uses:
- a mock GridLAB-D connection (in-memory object properties), and
- a transport adapter that maps MarketCommunicationInterface calls
  onto the in-process MarketOperator API.

The result is a runnable end-to-end simulation loop that exercises:
- all device agent types,
- real-time and day-ahead markets,
- DSO inflexible load estimation,
- market clearing propagation, and
- final settlement/reconciliation hooks.
"""

from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple

from data_types import BidPoint, ClearingResult, FlexibilityEnvelope, MarketTimingParams
from device_agent import DeviceAgent
from enums_and_constants import (
    DeviceType,
    MarketType,
    OperatingMode,
    PenaltyStructureType,
)
from data_streams import (
    ContinuousForecast,
    ConstraintStream,
    DataStreamManager,
    EventForecast,
    UncertaintyModel,
)
from data_types import EventDefinition
from gridlabd_interface import GridLABDInterface
from market_agent import MarketCommunicationInterface
from market_operator import DSOLoadEstimationEngine, MarketOperator, SupplyCurve
from penalty_model import PenaltyModel


class MockGridLABDConnection:
    """Simple in-memory key/value backend for GridLABDInterface."""

    def __init__(self, initial_props: Optional[Dict[str, Any]] = None):
        self._props: Dict[str, Any] = dict(initial_props or {})

    def get_value(self, key: str) -> Any:
        return self._props.get(key, "")

    def set_value(self, key: str, val: Any) -> None:
        self._props[key] = val


class InProcessMarketTransport:
    """Adapter exposing submit/receive expected by MarketCommunicationInterface."""

    def __init__(self, operator: MarketOperator):
        self._operator = operator
        self._pending: Dict[Tuple[str, str], ClearingResult] = {}
        self._settlements: List[Tuple[str, str]] = []

    def submit(self, **kwargs: Any) -> bool:
        agent_id = kwargs.get("agent_id", "")
        bid = kwargs.get("bid")
        settlement = kwargs.get("settlement")
        if bid is not None:
            return self._operator.submit_agent_bid(agent_id=agent_id, bid=bid)
        if settlement is not None:
            market_id = kwargs.get("market_id", "")
            self._settlements.append((agent_id, market_id))
            return True
        return False

    def receive(self, agent_id: str, market_id: str) -> Optional[ClearingResult]:
        return self._pending.pop((agent_id, market_id), None)

    def publish(
        self, market_id: str, results: Optional[Dict[str, ClearingResult]]
    ) -> None:
        if not results:
            return
        for agent_id, result in results.items():
            # Stamp the market_id expected by the receiving MarketObject.
            self._pending[(agent_id, market_id)] = replace(result, market_id=market_id)

    @property
    def settlement_count(self) -> int:
        return len(self._settlements)


class DemoDeviceAgent(DeviceAgent):
    """DeviceAgent wrapper that tolerates model signature mismatch in this demo.

    Some device models in this prototype expose estimate_flexibility() with
    additional required arguments. The fallback keeps the scenario runnable.
    """

    def estimate_flexibility(
        self, state: Any, interval_duration: float
    ) -> FlexibilityEnvelope:
        try:
            return super().estimate_flexibility(state, interval_duration)
        except TypeError:
            q_baseline = max(0.0, float(getattr(state, "power_draw", 0.0)))
            q_cap = max(
                q_baseline,
                float(getattr(state, "max_charge_rate", 0.0)),
                float(getattr(state, "element_power", 0.0)),
                3.0,
            )
            return FlexibilityEnvelope(
                Q_min=0.0,
                Q_max=q_cap,
                Q_baseline=q_baseline,
                Q_min_p50=0.0,
                Q_min_p90=0.1 * q_cap,
                Q_min_p99=0.2 * q_cap,
                interval_start=0.0,
                interval_end=interval_duration,
            )


# ---------------------------------------------------------------------------
#  Local data-stream factory functions (replaces import from main.py)
# ---------------------------------------------------------------------------

def _create_hvac_data_streams(device_type: DeviceType) -> DataStreamManager:
    dsm = DataStreamManager(device_type)
    temp_um = UncertaintyModel(model_type='saturating_exp',
                               params={'sigma_inf': 10.0, 'tau_c': 24 * 3600})
    dsm.register_continuous_stream('outdoor_air_temp',
        ContinuousForecast(variable_name='outdoor_air_temp', unit='\u00b0F',
                           uncertainty_model=temp_um))
    solar_um = UncertaintyModel(model_type='saturating_exp',
                                params={'sigma_inf': 250.0, 'tau_c': 6 * 3600})
    dsm.register_continuous_stream('solar_irradiance',
        ContinuousForecast(variable_name='solar_irradiance', unit='W/m\u00b2',
                           uncertainty_model=solar_um))
    sp_um = UncertaintyModel(model_type='empirical',
                             params={'lead_time_sigma_table': [(0, 0.0), (86400, 0.5)]})
    dsm.register_schedule('hvac_setpoint_schedule',
        ContinuousForecast(variable_name='hvac_setpoint', unit='\u00b0F',
                           uncertainty_model=sp_um))
    price_um = UncertaintyModel(model_type='saturating_exp',
                                params={'sigma_inf': 0.05, 'tau_c': 4 * 3600})
    dsm.register_continuous_stream('price_forecast',
        ContinuousForecast(variable_name='electricity_price', unit='$/kWh',
                           uncertainty_model=price_um))
    return dsm


def _create_water_heater_data_streams() -> DataStreamManager:
    dsm = DataStreamManager(DeviceType.WATER_HEATER)
    dsm.register_event_stream('hot_water_draw', EventForecast(
        event_types=[
            EventDefinition(event_type='shower', duration_mean=8.0, duration_std=3.0,
                            magnitude_mean=2.3, magnitude_std=0.4,
                            energy_mean=4.0, energy_std=1.0),
            EventDefinition(event_type='dishwash', duration_mean=10.0, duration_std=3.0,
                            magnitude_mean=1.5, magnitude_std=0.3,
                            energy_mean=1.5, energy_std=0.5),
        ],
        daily_expected_count=5.0, daily_expected_energy=12.0))
    dsm.register_constraint('tank_temp_minimum', ConstraintStream(
        constraint_id='tank_temp_min', variable='tank_temp',
        constraint_type='minimum', continuous=True, required_value=120.0))
    inlet_um = UncertaintyModel(model_type='empirical',
                                params={'lead_time_sigma_table': [(0, 0.5), (86400 * 7, 2.0)]})
    dsm.register_continuous_stream('inlet_water_temp',
        ContinuousForecast(variable_name='inlet_water_temp', unit='\u00b0F',
                           uncertainty_model=inlet_um))
    price_um = UncertaintyModel(model_type='saturating_exp',
                                params={'sigma_inf': 0.05, 'tau_c': 4 * 3600})
    dsm.register_continuous_stream('price_forecast',
        ContinuousForecast(variable_name='electricity_price', unit='$/kWh',
                           uncertainty_model=price_um))
    return dsm


def _create_ev_charger_data_streams() -> DataStreamManager:
    dsm = DataStreamManager(DeviceType.EV_CHARGER)
    dsm.register_constraint('ev_departure_soc', ConstraintStream(
        constraint_id='ev_departure', variable='soc',
        constraint_type='by_time', continuous=False,
        deadline=7.0 * 3600, required_value=0.50))
    soc_um = UncertaintyModel(model_type='empirical',
                              params={'lead_time_sigma_table': [(0, 0.0), (86400, 0.0)]})
    dsm.register_schedule('ev_preferred_soc',
        ContinuousForecast(variable_name='preferred_soc', unit='fraction',
                           uncertainty_model=soc_um))
    dsm.register_event_stream('ev_arrival', EventForecast(
        event_types=[EventDefinition(event_type='ev_arrival', duration_mean=0,
                                     magnitude_mean=0.65, magnitude_std=0.08)],
        daily_expected_count=1.0, daily_expected_energy=0.0))
    price_um = UncertaintyModel(model_type='saturating_exp',
                                params={'sigma_inf': 0.05, 'tau_c': 4 * 3600})
    dsm.register_continuous_stream('price_forecast',
        ContinuousForecast(variable_name='electricity_price', unit='$/kWh',
                           uncertainty_model=price_um))
    return dsm


def _create_battery_data_streams() -> DataStreamManager:
    dsm = DataStreamManager(DeviceType.BATTERY)
    dsm.register_constraint('soc_reserve', ConstraintStream(
        constraint_id='battery_reserve', variable='soc',
        constraint_type='minimum', continuous=True, required_value=0.60))
    soc_um = UncertaintyModel(model_type='empirical',
                              params={'lead_time_sigma_table': [(0, 0.0), (86400, 0.0)]})
    dsm.register_schedule('battery_preferred_soc',
        ContinuousForecast(variable_name='preferred_soc', unit='fraction',
                           uncertainty_model=soc_um))
    price_um = UncertaintyModel(model_type='saturating_exp',
                                params={'sigma_inf': 0.05, 'tau_c': 4 * 3600})
    dsm.register_continuous_stream('price_forecast',
        ContinuousForecast(variable_name='electricity_price', unit='$/kWh',
                           uncertainty_model=price_um))
    solar_um = UncertaintyModel(model_type='saturating_exp',
                                params={'sigma_inf': 2.0, 'tau_c': 6 * 3600})
    dsm.register_continuous_stream('btm_solar',
        ContinuousForecast(variable_name='btm_solar_generation', unit='kW',
                           uncertainty_model=solar_um))
    net_um = UncertaintyModel(model_type='saturating_exp',
                              params={'sigma_inf': 3.0, 'tau_c': 4 * 3600})
    dsm.register_continuous_stream('household_net_load',
        ContinuousForecast(variable_name='household_net_load', unit='kW',
                           uncertainty_model=net_um))
    return dsm


def _build_mock_interfaces() -> Dict[DeviceType, GridLABDInterface]:
    """Create one GridLABDInterface per device type with plausible defaults."""

    props = {
        # HVAC heat pump house
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
        # HVAC AC-only house
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

    connection = MockGridLABDConnection(props)
    return {
        DeviceType.HVAC_HEAT_PUMP: GridLABDInterface(
            connection, "house_1", DeviceType.HVAC_HEAT_PUMP
        ),
        DeviceType.HVAC_AC_ONLY: GridLABDInterface(
            connection, "house_2", DeviceType.HVAC_AC_ONLY
        ),
        DeviceType.WATER_HEATER: GridLABDInterface(
            connection, "waterheater_1", DeviceType.WATER_HEATER
        ),
        DeviceType.EV_CHARGER: GridLABDInterface(
            connection, "evcharger_1", DeviceType.EV_CHARGER
        ),
        DeviceType.BATTERY: GridLABDInterface(
            connection, "battery_1", DeviceType.BATTERY
        ),
    }


def run_demo() -> None:
    """Run a compact but complete scenario with RT + DA market participation."""

    # Build interfaces and data streams for all supported device agent types.
    gld_ifaces = _build_mock_interfaces()
    agents = [
        DemoDeviceAgent(
            agent_id="agent_hvac_hp_1",
            device_type=DeviceType.HVAC_HEAT_PUMP,
            gridlabd=gld_ifaces[DeviceType.HVAC_HEAT_PUMP],
            customer_preference_k=0.3,
            data_stream_manager=_create_hvac_data_streams(DeviceType.HVAC_HEAT_PUMP),
        ),
        DemoDeviceAgent(
            agent_id="agent_hvac_ac_1",
            device_type=DeviceType.HVAC_AC_ONLY,
            gridlabd=gld_ifaces[DeviceType.HVAC_AC_ONLY],
            customer_preference_k=0.5,
            data_stream_manager=_create_hvac_data_streams(DeviceType.HVAC_AC_ONLY),
        ),
        DemoDeviceAgent(
            agent_id="agent_wh_1",
            device_type=DeviceType.WATER_HEATER,
            gridlabd=gld_ifaces[DeviceType.WATER_HEATER],
            customer_preference_k=0.4,
            data_stream_manager=_create_water_heater_data_streams(),
        ),
        DemoDeviceAgent(
            agent_id="agent_ev_1",
            device_type=DeviceType.EV_CHARGER,
            gridlabd=gld_ifaces[DeviceType.EV_CHARGER],
            customer_preference_k=0.6,
            data_stream_manager=_create_ev_charger_data_streams(),
        ),
        DemoDeviceAgent(
            agent_id="agent_battery_1",
            device_type=DeviceType.BATTERY,
            gridlabd=gld_ifaces[DeviceType.BATTERY],
            customer_preference_k=0.8,
            data_stream_manager=_create_battery_data_streams(),
        ),
    ]

    for agent in agents:
        if agent._device_type == DeviceType.BATTERY:
            agent.initialize(
                {
                    "replacement_cost": 10000.0,
                    "rated_cycles": 5000,
                    "rated_dod": 0.80,
                    "wohler_exponent": 1.5,
                }
            )
        else:
            agent.initialize({})

    # Real-time market every 5 minutes.
    rt_timing = MarketTimingParams(
        t_activate=-600.0,
        t_negotiate=-420.0,
        t_market_lead=-60.0,
        t_clear=0.0,
        t_delivery_start=0.0,
        t_delivery_end=300.0,
        t_reconcile_end=600.0,
    )
    rt_operator = MarketOperator(
        market_type=MarketType.RT_ENERGY,
        timing_params=rt_timing,
        iteration_protocol="fixed_count",
        n_informational=0,
    )
    rt_operator.set_supply_curve(
        SupplyCurve(
            points=[
                BidPoint(price=0.02, quantity=0.0),
                BidPoint(price=0.05, quantity=500.0),
                BidPoint(price=0.08, quantity=1000.0),
                BidPoint(price=0.15, quantity=1500.0),
                BidPoint(price=0.50, quantity=2000.0),
                BidPoint(price=1.00, quantity=2000.0),
            ]
        )
    )

    # Day-ahead market hourly in this demo (shortened horizon vs reference 24h block).
    da_timing = MarketTimingParams(
        t_activate=-3600.0,
        t_negotiate=-1800.0,
        t_market_lead=-300.0,
        t_clear=0.0,
        t_delivery_start=300.0,
        t_delivery_end=3600.0,
        t_reconcile_end=5400.0,
    )
    da_operator = MarketOperator(
        market_type=MarketType.DA_ENERGY,
        timing_params=da_timing,
        iteration_protocol="fixed_count",
        n_informational=1,
    )
    da_operator.set_supply_curve(
        SupplyCurve(
            points=[
                BidPoint(price=0.03, quantity=0.0),
                BidPoint(price=0.06, quantity=700.0),
                BidPoint(price=0.10, quantity=1200.0),
                BidPoint(price=0.20, quantity=1800.0),
                BidPoint(price=0.90, quantity=2200.0),
            ]
        )
    )

    rt_transport = InProcessMarketTransport(rt_operator)
    da_transport = InProcessMarketTransport(da_operator)

    rt_penalty = PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
    )
    da_penalty = PenaltyModel(
        market_type=MarketType.DA_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate_reference": "cleared_price_multiple", "multiplier": 1.5},
    )

    for agent in agents:
        agent.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=rt_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=rt_penalty,
            communication=MarketCommunicationInterface(
                transport=rt_transport,
                agent_id=agent._agent_id,
                market_type=MarketType.RT_ENERGY,
            ),
            iteration_protocol="fixed_count",
            n_informational=0,
        )
        agent.register_market(
            market_type=MarketType.DA_ENERGY,
            timing_params=da_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=da_penalty,
            communication=MarketCommunicationInterface(
                transport=da_transport,
                agent_id=agent._agent_id,
                market_type=MarketType.DA_ENERGY,
            ),
            iteration_protocol="fixed_count",
            n_informational=1,
        )

    dso_engine = DSOLoadEstimationEngine(feeder_id="feeder_1")

    sim_start = 0.0
    sim_end = 3 * 3600.0
    sim_timestep = 60.0
    rt_interval = 300.0
    da_interval = 3600.0

    current_time = sim_start
    next_rt_clearing = sim_start + rt_interval
    next_da_clearing = sim_start + da_interval

    spawned_rt: set[float] = set()
    spawned_da: set[float] = set()
    rt_clears = 0
    da_clears = 0

    while current_time < sim_end:
        # Spawn RT and DA cycles ahead of clearing according to timing params.
        if (
            next_rt_clearing not in spawned_rt
            and current_time >= next_rt_clearing + rt_timing.t_activate
        ):
            for agent in agents:
                agent.spawn_market_cycle(MarketType.RT_ENERGY, next_rt_clearing)
            spawned_rt.add(next_rt_clearing)

        if (
            next_da_clearing not in spawned_da
            and current_time >= next_da_clearing + da_timing.t_activate
        ):
            for agent in agents:
                agent.spawn_market_cycle(MarketType.DA_ENERGY, next_da_clearing)
            spawned_da.add(next_da_clearing)

        for agent in agents:
            agent.step(current_time)

        # Feed DSO inflexible estimate near RT negotiation point.
        if (
            abs(current_time - (next_rt_clearing + rt_timing.t_negotiate))
            < sim_timestep
        ):
            dso_bid = dso_engine.estimate_inflexible_load(
                interval=(next_rt_clearing, next_rt_clearing + rt_interval),
                total_load_forecast=1150.0,
                flexible_committed=rt_operator.get_total_flexible_committed(),
                btm_solar_forecast=120.0,
                loss_factor=0.05,
            )
            rt_operator.submit_dso_inflexible_bid("feeder_1", dso_bid)

        # Clear RT only at its scheduled clearing times.
        if abs(current_time - next_rt_clearing) < sim_timestep:
            rt_results = rt_operator.step(current_time)
            rt_transport.publish(
                market_id=f"{MarketType.RT_ENERGY.name}_{int(next_rt_clearing)}",
                results=rt_results,
            )
            rt_clears += 1
            next_rt_clearing += rt_interval

        # Clear DA only at its scheduled clearing times.
        if abs(current_time - next_da_clearing) < sim_timestep:
            da_results = da_operator.step(current_time)
            da_transport.publish(
                market_id=f"{MarketType.DA_ENERGY.name}_{int(next_da_clearing)}",
                results=da_results,
            )
            da_clears += 1
            next_da_clearing += da_interval

        current_time += sim_timestep

    for agent in agents:
        agent.step(sim_end)

    rt_last_price = (
        rt_operator._clearing_history[-1].cleared_price
        if rt_operator._clearing_history
        else 0.0
    )
    da_last_price = (
        da_operator._clearing_history[-1].cleared_price
        if da_operator._clearing_history
        else 0.0
    )

    print("Demo complete")
    print(f"  Agents: {len(agents)} (HVAC HP, HVAC AC, WH, EV, Battery)")
    print(f"  RT clears: {rt_clears}, last RT price: ${rt_last_price:.4f}/kWh")
    print(f"  DA clears: {da_clears}, last DA price: ${da_last_price:.4f}/kWh")
    print(f"  RT reconciliations submitted: {rt_transport.settlement_count}")
    print(f"  DA reconciliations submitted: {da_transport.settlement_count}")


if __name__ == "__main__":
    run_demo()
