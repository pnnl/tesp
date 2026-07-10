# ============================================================================
# FILE: main.py
# PURPOSE: Reference implementation showing how all classes are instantiated
#          and methods are called. This demonstrates the full simulation loop
#          with one instance of each device type and a Market Operator.
#
# This script is NOT intended to run — it is a structural reference showing
# the wiring between components.
# ============================================================================

from enums_and_constants import (
    DeviceType, MarketType, OperatingMode, PenaltyStructureType
)
from data_types import MarketTimingParams, EventDefinition
from gridlabd_interface import GridLABDInterface
from data_streams import (
    DataStreamManager, ContinuousForecast, EventForecast,
    ConstraintStream, UncertaintyModel
)
from device_agent import DeviceAgent
from penalty_model import PenaltyModel
from market_agent import MarketCommunicationInterface
from market_operator import (
    MarketOperator, SupplyCurve, DSOLoadEstimationEngine, DSOInflexibleLoadBid
)
from data_types import BidPoint


def create_weather_streams() -> dict:
    """Create weather forecast data streams.
    
    EXTERNAL DATA REQUIRED:
        - Outdoor air temperature forecast (48hr horizon, hourly)
        - Solar irradiance forecast (48hr horizon, hourly)
        - Humidity forecast (48hr horizon, hourly)
        
    These must be populated from a weather service API or
    simulation-provided weather data before the simulation loop starts.
    
    Returns:
        Dictionary of stream_id -> ContinuousForecast objects.
    """
    outdoor_temp_uncertainty = UncertaintyModel(
        model_type='saturating_exp',
        params={'sigma_inf': 10.0, 'tau_c': 24 * 3600}  # °F, seconds
    )
    outdoor_temp_forecast = ContinuousForecast(
        variable_name='outdoor_air_temp',
        unit='°F',
        uncertainty_model=outdoor_temp_uncertainty
        # EXTERNAL: series must be populated from weather service
    )

    solar_uncertainty = UncertaintyModel(
        model_type='saturating_exp',
        params={'sigma_inf': 250.0, 'tau_c': 6 * 3600}  # W/m², seconds
    )
    solar_forecast = ContinuousForecast(
        variable_name='solar_irradiance',
        unit='W/m²',
        uncertainty_model=solar_uncertainty
        # EXTERNAL: series must be populated from weather service
    )

    return {
        'outdoor_air_temp': outdoor_temp_forecast,
        'solar_irradiance': solar_forecast,
    }


def create_hvac_data_streams(device_type: DeviceType) -> DataStreamManager:
    """Create and populate data streams for an HVAC agent.
    
    EXTERNAL DATA REQUIRED:
        - Weather forecasts (outdoor temp, solar, humidity)
        - Customer setpoint schedule (thermostat program)
        - Building occupancy forecast/schedule
        - Electricity price forecast (initial prior)
    
    Args:
        device_type: HVAC_HEAT_PUMP or HVAC_AC_ONLY.
    
    Returns:
        Populated DataStreamManager.
    """
    dsm = DataStreamManager(device_type)

    # Weather streams
    weather = create_weather_streams()
    for stream_id, forecast in weather.items():
        dsm.register_continuous_stream(stream_id, forecast)

    # Customer setpoint schedule
    # EXTERNAL: From customer's thermostat program
    setpoint_uncertainty = UncertaintyModel(
        model_type='empirical',
        params={'lead_time_sigma_table': [(0, 0.0), (86400, 0.5)]}
        # Very low uncertainty — customer-declared
    )
    setpoint_schedule = ContinuousForecast(
        variable_name='hvac_setpoint',
        unit='°F',
        uncertainty_model=setpoint_uncertainty
        # EXTERNAL: series must be populated from thermostat program
        # Example: 72°F 6am-10pm, 68°F 10pm-6am
    )
    dsm.register_schedule('hvac_setpoint_schedule', setpoint_schedule)

    # Price forecast (initial prior)
    # EXTERNAL: From historical data or MO-provided forecast
    # Updated by informational market clears during simulation
    price_uncertainty = UncertaintyModel(
        model_type='saturating_exp',
        params={'sigma_inf': 0.05, 'tau_c': 4 * 3600}  # $/kWh, seconds
    )
    price_forecast = ContinuousForecast(
        variable_name='electricity_price',
        unit='$/kWh',
        uncertainty_model=price_uncertainty
        # EXTERNAL: initial series from historical average prices
    )
    dsm.register_continuous_stream('price_forecast', price_forecast)

    return dsm


def create_water_heater_data_streams() -> DataStreamManager:
    """Create data streams for a water heater agent.
    
    EXTERNAL DATA REQUIRED:
        - Hot water draw event model (learned from historical data)
        - Inlet water temperature (seasonal model)
        - Minimum tank temperature constraint (building code / customer)
        - Electricity price forecast
    
    Returns:
        Populated DataStreamManager.
    """
    dsm = DataStreamManager(DeviceType.WATER_HEATER)

    # Hot water draw event forecast
    # EXTERNAL: Event types and intensity function must be learned
    # from historical flow sensor / meter data
    shower_def = EventDefinition(
        event_type='shower',
        duration_mean=8.0,  # minutes
        duration_std=3.0,
        magnitude_mean=2.3,  # GPM
        magnitude_std=0.4,
        energy_mean=4.0,  # kWh
        energy_std=1.0
    )
    dishwash_def = EventDefinition(
        event_type='dishwash',
        duration_mean=10.0,
        duration_std=3.0,
        magnitude_mean=1.5,
        magnitude_std=0.3,
        energy_mean=1.5,
        energy_std=0.5
    )
    hot_water_forecast = EventForecast(
        event_types=[shower_def, dishwash_def],
        # EXTERNAL: intensity_function must be learned from historical data
        # Example: λ_shower(t) peaks at 6-8am and 6-8pm
        daily_expected_count=5.0,
        daily_expected_energy=12.0  # kWh/day
    )
    dsm.register_event_stream('hot_water_draw', hot_water_forecast)

    # Minimum tank temperature constraint
    # EXTERNAL: From building code (120°F for Legionella prevention)
    tank_temp_constraint = ConstraintStream(
        constraint_id='tank_temp_min',
        variable='tank_temp',
        constraint_type='minimum',
        continuous=True,  # applies at all times
        required_value=120.0  # °F
    )
    dsm.register_constraint('tank_temp_minimum', tank_temp_constraint)

    # Inlet water temperature (slow-moving seasonal forecast)
    inlet_temp_uncertainty = UncertaintyModel(
        model_type='empirical',
        params={'lead_time_sigma_table': [(0, 0.5), (86400 * 7, 2.0)]}
    )
    inlet_temp = ContinuousForecast(
        variable_name='inlet_water_temp',
        unit='°F',
        uncertainty_model=inlet_temp_uncertainty
        # EXTERNAL: From seasonal ground temperature model
    )
    dsm.register_continuous_stream('inlet_water_temp', inlet_temp)

    # Price forecast
    price_uncertainty = UncertaintyModel(
        model_type='saturating_exp',
        params={'sigma_inf': 0.05, 'tau_c': 4 * 3600}
    )
    price_forecast = ContinuousForecast(
        variable_name='electricity_price',
        unit='$/kWh',
        uncertainty_model=price_uncertainty
    )
    dsm.register_continuous_stream('price_forecast', price_forecast)

    return dsm


def create_ev_charger_data_streams() -> DataStreamManager:
    """Create data streams for an EV charger agent.
    
    EXTERNAL DATA REQUIRED:
        - EV departure constraint (customer input: time + min SOC)
        - EV preferred SOC schedule (customer preference)
        - EV arrival forecast (learned from historical patterns)
        - Electricity price forecast
    
    Returns:
        Populated DataStreamManager.
    """
    dsm = DataStreamManager(DeviceType.EV_CHARGER)

    # Departure constraint
    # EXTERNAL: From customer's EV app input per charging session
    departure_constraint = ConstraintStream(
        constraint_id='ev_departure',
        variable='soc',
        constraint_type='by_time',
        continuous=False,
        deadline=7.0 * 3600,  # 7:00 AM in seconds-since-midnight
        required_value=0.50   # 50% SOC minimum at departure
    )
    dsm.register_constraint('ev_departure_soc', departure_constraint)

    # Preferred SOC schedule
    # EXTERNAL: Customer setting (e.g., "I'd like 90% by morning")
    preferred_soc_uncertainty = UncertaintyModel(
        model_type='empirical',
        params={'lead_time_sigma_table': [(0, 0.0), (86400, 0.0)]}
        # Zero uncertainty — customer-declared preference
    )
    preferred_soc = ContinuousForecast(
        variable_name='preferred_soc',
        unit='fraction',
        uncertainty_model=preferred_soc_uncertainty
        # EXTERNAL: From customer's EV app
    )
    dsm.register_schedule('ev_preferred_soc', preferred_soc)

    # Arrival forecast
    # EXTERNAL: Learned from historical charging session data
    ev_arrival = EventForecast(
        event_types=[EventDefinition(
            event_type='ev_arrival',
            duration_mean=0,  # single event, no duration
            magnitude_mean=0.65,  # expected arrival SOC
            magnitude_std=0.08
        )],
        # EXTERNAL: Arrival time distribution learned from history
        # Example: Normal(μ=6:15pm, σ=35min)
        daily_expected_count=1.0,
        daily_expected_energy=0.0  # not energy-consuming
    )
    dsm.register_event_stream('ev_arrival', ev_arrival)

    # Price forecast
    price_uncertainty = UncertaintyModel(
        model_type='saturating_exp',
        params={'sigma_inf': 0.05, 'tau_c': 4 * 3600}
    )
    price_forecast = ContinuousForecast(
        variable_name='electricity_price',
        unit='$/kWh',
        uncertainty_model=price_uncertainty
    )
    dsm.register_continuous_stream('price_forecast', price_forecast)

    return dsm


def create_battery_data_streams() -> DataStreamManager:
    """Create data streams for a battery agent.
    
    EXTERNAL DATA REQUIRED:
        - Backup reserve SOC constraint (customer setting)
        - Preferred SOC schedule (customer preference)
        - Grid outage probability forecast (optional, from DSO)
        - Electricity price forecast
        - BTM solar generation forecast (if customer has solar)
        - Household net load forecast
    
    Returns:
        Populated DataStreamManager.
    """
    dsm = DataStreamManager(DeviceType.BATTERY)

    # Backup reserve constraint
    # EXTERNAL: From customer setting
    reserve_constraint = ConstraintStream(
        constraint_id='battery_reserve',
        variable='soc',
        constraint_type='minimum',
        continuous=True,  # applies at all times
        required_value=0.60  # 60% SOC backup reserve
    )
    dsm.register_constraint('soc_reserve', reserve_constraint)

    # Preferred SOC schedule
    # EXTERNAL: Customer setting
    preferred_soc_uncertainty = UncertaintyModel(
        model_type='empirical',
        params={'lead_time_sigma_table': [(0, 0.0), (86400, 0.0)]}
    )
    preferred_soc = ContinuousForecast(
        variable_name='preferred_soc',
        unit='fraction',
        uncertainty_model=preferred_soc_uncertainty
        # EXTERNAL: Customer preference, e.g., 80% SOC
    )
    dsm.register_schedule('battery_preferred_soc', preferred_soc)

    # Price forecast
    price_uncertainty = UncertaintyModel(
        model_type='saturating_exp',
        params={'sigma_inf': 0.05, 'tau_c': 4 * 3600}
    )
    price_forecast = ContinuousForecast(
        variable_name='electricity_price',
        unit='$/kWh',
        uncertainty_model=price_uncertainty
    )
    dsm.register_continuous_stream('price_forecast', price_forecast)

    # BTM solar forecast (if applicable)
    # EXTERNAL: From solar irradiance forecast + PV system specs
    solar_uncertainty = UncertaintyModel(
        model_type='saturating_exp',
        params={'sigma_inf': 2.0, 'tau_c': 6 * 3600}  # kW
    )
    btm_solar = ContinuousForecast(
        variable_name='btm_solar_generation',
        unit='kW',
        uncertainty_model=solar_uncertainty
    )
    dsm.register_continuous_stream('btm_solar', btm_solar)

    # Household net load forecast
    # EXTERNAL: From historical meter data + occupancy model
    net_load_uncertainty = UncertaintyModel(
        model_type='saturating_exp',
        params={'sigma_inf': 3.0, 'tau_c': 4 * 3600}  # kW
    )
    net_load = ContinuousForecast(
        variable_name='household_net_load',
        unit='kW',
        uncertainty_model=net_load_uncertainty
    )
    dsm.register_continuous_stream('household_net_load', net_load)

    return dsm


def main():
    """Reference implementation: simulation setup and main loop.
    
    This demonstrates the complete wiring of all components.
    It is structured as:
    1. Create simulation infrastructure (GridLAB-D connections)
    2. Create data streams for each device
    3. Instantiate device agents
    4. Register markets for each agent
    5. Set up the Market Operator and DSO
    6. Run the simulation loop
    """

    # ==================================================================
    # STEP 1: Simulation Infrastructure
    # ==================================================================

    # EXTERNAL: GridLAB-D co-simulation connection.
    # In practice, this would be a FNCS or HELICS connection object.
    gridlabd_connection = None  # placeholder

    # Create GridLAB-D interfaces for each device.
    # Each interface is connected to a specific GridLAB-D object.
    # EXTERNAL: object names must match the GridLAB-D model (.glm file).
    gld_hvac_hp = GridLABDInterface(
        connection=gridlabd_connection,
        object_name="house_1",  # EXTERNAL: GridLAB-D object name
        device_type=DeviceType.HVAC_HEAT_PUMP
    )
    gld_hvac_ac = GridLABDInterface(
        connection=gridlabd_connection,
        object_name="house_2",
        device_type=DeviceType.HVAC_AC_ONLY
    )
    gld_water_heater = GridLABDInterface(
        connection=gridlabd_connection,
        object_name="waterheater_1",
        device_type=DeviceType.WATER_HEATER
    )
    gld_ev = GridLABDInterface(
        connection=gridlabd_connection,
        object_name="evcharger_1",
        device_type=DeviceType.EV_CHARGER
    )
    gld_battery = GridLABDInterface(
        connection=gridlabd_connection,
        object_name="battery_1",
        device_type=DeviceType.BATTERY
    )

    # ==================================================================
    # STEP 2: Data Streams
    # ==================================================================

    # Create data stream managers for each device type.
    # EXTERNAL: All forecast/schedule/constraint data must be populated
    # from external sources before or during the simulation.
    dsm_hvac_hp = create_hvac_data_streams(DeviceType.HVAC_HEAT_PUMP)
    dsm_hvac_ac = create_hvac_data_streams(DeviceType.HVAC_AC_ONLY)
    dsm_water_heater = create_water_heater_data_streams()
    dsm_ev = create_ev_charger_data_streams()
    dsm_battery = create_battery_data_streams()

    # ==================================================================
    # STEP 3: Device Agents
    # ==================================================================

    # Customer preference factors.
    # EXTERNAL: Provided by the customer.
    # 0 = full amenity preference, 1 = full financial preference.
    k_hvac_hp = 0.3       # comfort-focused customer
    k_hvac_ac = 0.5       # balanced
    k_water_heater = 0.4  # slightly comfort-focused
    k_ev = 0.6            # slightly financially-focused
    k_battery = 0.8       # financially-focused (battery is for revenue)

    agent_hvac_hp = DeviceAgent(
        agent_id="agent_hvac_hp_1",
        device_type=DeviceType.HVAC_HEAT_PUMP,
        gridlabd=gld_hvac_hp,
        customer_preference_k=k_hvac_hp,
        data_stream_manager=dsm_hvac_hp
    )

    agent_hvac_ac = DeviceAgent(
        agent_id="agent_hvac_ac_1",
        device_type=DeviceType.HVAC_AC_ONLY,
        gridlabd=gld_hvac_ac,
        customer_preference_k=k_hvac_ac,
        data_stream_manager=dsm_hvac_ac
    )

    agent_wh = DeviceAgent(
        agent_id="agent_wh_1",
        device_type=DeviceType.WATER_HEATER,
        gridlabd=gld_water_heater,
        customer_preference_k=k_water_heater,
        data_stream_manager=dsm_water_heater
    )

    agent_ev = DeviceAgent(
        agent_id="agent_ev_1",
        device_type=DeviceType.EV_CHARGER,
        gridlabd=gld_ev,
        customer_preference_k=k_ev,
        data_stream_manager=dsm_ev
    )

    agent_battery = DeviceAgent(
        agent_id="agent_battery_1",
        device_type=DeviceType.BATTERY,
        gridlabd=gld_battery,
        customer_preference_k=k_battery,
        data_stream_manager=dsm_battery
    )

    # Initialize agents with device-specific parameters.
    agent_hvac_hp.initialize({})  # HVAC params come from GridLAB-D state
    agent_hvac_ac.initialize({})
    agent_wh.initialize({})
    agent_ev.initialize({})
    agent_battery.initialize({
        'replacement_cost': 10000.0,  # EXTERNAL: battery specs
        'rated_cycles': 5000,
        'rated_dod': 0.80,
        'wohler_exponent': 1.5
    })

    all_agents = [agent_hvac_hp, agent_hvac_ac, agent_wh, 
                  agent_ev, agent_battery]

    # ==================================================================
    # STEP 4: Market Operator and DSO Setup
    # ==================================================================

    # Real-time energy market (5-minute intervals)
    rt_timing = MarketTimingParams(
        t_activate=-600.0,     # 10 min before clearing
        t_negotiate=-420.0,    # 7 min before clearing
        t_market_lead=-60.0,   # 1 min before clearing
        t_clear=0.0,
        t_delivery_start=0.0,  # delivery starts at clearing
        t_delivery_end=300.0,  # 5-minute delivery
        t_reconcile_end=600.0
    )

    rt_market_operator = MarketOperator(
        market_type=MarketType.RT_ENERGY,
        timing_params=rt_timing,
        iteration_protocol='fixed_count',
        n_informational=0  # RT market: no informational iterations
    )

    # Day-ahead energy market (hourly intervals, 24 hours)
    da_timing = MarketTimingParams(
        t_activate=-14 * 3600,     # 14 hours before clearing
        t_negotiate=-12 * 3600,    # 12 hours before clearing
        t_market_lead=-1 * 3600,   # 1 hour before clearing
        t_clear=0.0,
        t_delivery_start=3600.0,   # delivery starts 1 hour after clearing
        t_delivery_end=25 * 3600,  # 24 hours of delivery
        t_reconcile_end=49 * 3600
    )

    da_market_operator = MarketOperator(
        market_type=MarketType.DA_ENERGY,
        timing_params=da_timing,
        iteration_protocol='fixed_count',
        n_informational=3  # 3 informational iterations before binding
    )

    # DSO Load Estimation Engine
    dso_load_engine = DSOLoadEstimationEngine(feeder_id="feeder_1")

    # Supply curve
    # EXTERNAL: Constructed from wholesale market data by the DSO.
    # This is a simplified example.
    rt_supply = SupplyCurve(points=[
        BidPoint(price=0.02, quantity=0.0),      # minimum price
        BidPoint(price=0.05, quantity=500.0),     # baseload generation
        BidPoint(price=0.08, quantity=1000.0),    # mid-merit
        BidPoint(price=0.15, quantity=1500.0),    # peaking
        BidPoint(price=0.50, quantity=2000.0),    # scarcity
        BidPoint(price=1.00, quantity=2000.0),    # price cap
    ])
    rt_market_operator.set_supply_curve(rt_supply)

    # Penalty models
    # EXTERNAL: Defined by market rules from the MO.
    rt_penalty = PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={
            'rate_reference': 'cleared_price_multiple',
            'multiplier': 2.0  # penalty = 2× cleared price per kWh shortfall
        }
    )

    da_penalty = PenaltyModel(
        market_type=MarketType.DA_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={
            'rate_reference': 'cleared_price_multiple',
            'multiplier': 1.5
        }
    )

    # ==================================================================
    # STEP 5: Register Markets for Each Agent
    # ==================================================================

    for agent in all_agents:
        # RT Energy market — all agents participate in bidding mode
        rt_comm = MarketCommunicationInterface(
            transport=rt_market_operator,  # direct reference (in-process)
            agent_id=agent._agent_id,
            market_type=MarketType.RT_ENERGY
        )
        agent.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=rt_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=rt_penalty,
            communication=rt_comm,
            iteration_protocol='fixed_count',
            n_informational=0
        )

        # DA Energy market — all agents participate
        da_comm = MarketCommunicationInterface(
            transport=da_market_operator,
            agent_id=agent._agent_id,
            market_type=MarketType.DA_ENERGY
        )
        agent.register_market(
            market_type=MarketType.DA_ENERGY,
            timing_params=da_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=da_penalty,
            communication=da_comm,
            iteration_protocol='fixed_count',
            n_informational=3
        )

    # ==================================================================
    # STEP 6: Simulation Loop
    # ==================================================================

    # Simulation parameters
    # EXTERNAL: Defined by the simulation configuration.
    sim_start = 0.0          # seconds (simulation epoch)
    sim_end = 86400.0        # 24 hours
    sim_timestep = 60.0      # 1-minute timestep
    market_interval = 300.0  # 5-minute RT market interval

    current_time = sim_start
    next_rt_clearing = sim_start + market_interval
    next_da_clearing = sim_start + 12 * 3600  # DA clears at noon

    while current_time < sim_end:

        # ----------------------------------------------------------
        # 6a: Update exogenous data streams
        # ----------------------------------------------------------
        # EXTERNAL: In a real simulation, this is where new weather
        # forecasts, customer schedule changes, EV plug-in events,
        # and other external data would be pushed to the data stream
        # managers.
        #
        # Example:
        # if new_weather_available(current_time):
        #     new_forecast = fetch_weather_forecast()
        #     for dsm in [dsm_hvac_hp, dsm_hvac_ac, dsm_battery]:
        #         dsm.update_stream('outdoor_air_temp', new_forecast)
        #
        # if ev_just_plugged_in(current_time):
        #     dsm_ev.update_stream('ev_departure_soc', new_constraint)

        # ----------------------------------------------------------
        # 6b: Spawn new market cycles as needed
        # ----------------------------------------------------------
        if current_time >= next_rt_clearing - rt_timing.t_activate:
            for agent in all_agents:
                agent.spawn_market_cycle(
                    MarketType.RT_ENERGY,
                    clearing_time=next_rt_clearing
                )

        # DA market spawning (once per day)
        # Similar logic for DA cycles

        # ----------------------------------------------------------
        # 6c: Step all device agents
        # ----------------------------------------------------------
        # Each agent checks its MarketObjects for transitions,
        # executes phase handlers, and runs delivery tick if needed.
        for agent in all_agents:
            agent.step(current_time)

        # ----------------------------------------------------------
        # 6d: DSO prepares inflexible load bid
        # ----------------------------------------------------------
        # The DSO estimates the inflexible load and submits it to
        # the MO. This happens before market clearing.
        if abs(current_time - (next_rt_clearing + rt_timing.t_negotiate)) < sim_timestep:
            # Get total flexible committed from previous cycle
            flexible_committed = rt_market_operator.get_total_flexible_committed()

            # EXTERNAL: total_load_forecast from substation forecast model
            # EXTERNAL: btm_solar_forecast from solar generation model
            # EXTERNAL: loss_factor from network loss model
            dso_bid = dso_load_engine.estimate_inflexible_load(
                interval=(next_rt_clearing, 
                         next_rt_clearing + market_interval),
                total_load_forecast=1200.0,  # EXTERNAL: kW forecast
                flexible_committed=flexible_committed,
                btm_solar_forecast=150.0,    # EXTERNAL: kW forecast
                loss_factor=0.05             # EXTERNAL: from network model
            )
            rt_market_operator.submit_dso_inflexible_bid(
                feeder_id="feeder_1",
                bid=dso_bid
            )

        # ----------------------------------------------------------
        # 6e: Market Operator clears the market
        # ----------------------------------------------------------
        rt_results = rt_market_operator.step(current_time)
        if rt_results is not None:
            # Results are available — agents will pick them up
            # in their next step() call via receive_clear()
            next_rt_clearing += market_interval

        da_results = da_market_operator.step(current_time)
        # DA results handled similarly

        # ----------------------------------------------------------
        # 6f: Update DSO metering (for real-time correction)
        # ----------------------------------------------------------
        # EXTERNAL: substation_load_actual from SCADA measurement
        # This would come from the GridLAB-D simulation's substation
        # meter object.
        # dso_load_engine.update_with_metering(
        #     substation_load_actual=...,  # from GridLAB-D substation meter
        #     flexible_actual=...,          # sum of device agent actual power
        #     timestamp=current_time
        # )

        # ----------------------------------------------------------
        # 6g: Advance time
        # ----------------------------------------------------------
        current_time += sim_timestep

    # ==================================================================
    # STEP 7: Final Reconciliation
    # ==================================================================
    # After simulation ends, all remaining market objects in DELIVERY
    # or RECONCILE should be finalized.
    for agent in all_agents:
        # Agent's step() method handles reconciliation as markets
        # transition to RECONCILE and EXPIRED phases.
        # A final step at sim_end triggers remaining transitions.
        agent.step(sim_end)


if __name__ == "__main__":
    main()