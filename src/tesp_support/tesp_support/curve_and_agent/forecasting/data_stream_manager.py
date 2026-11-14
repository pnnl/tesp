# ============================================================================
# FILE: forecasting/data_stream_manager.py
# PURPOSE: Concrete implementation of the central registry and access
#          point for all exogenous data streams consumed by the agent.
#
# The DataStreamManager is the agent's single gateway to all forward-
# looking information about the world outside the device: weather,
# customer behavior, constraints, schedules, and market conditions.
# Every agent function that needs to know about the future — F2
# (flexibility estimation), F3 (preference curve calibration), F4
# (bid formulation risk assessment), and the planning optimizer —
# obtains that information through this manager.
#
# The manager itself does NOT generate forecasts, learn patterns, or
# run prediction models.  It is a registry and query layer that:
#     1. Stores references to forecast, schedule, and constraint objects.
#     2. Provides type-safe retrieval by stream ID.
#     3. Accepts updates from external sources and routes them to the
#        correct stream object.
#     4. Bundles multiple streams into a single dictionary for
#        convenient passing to device models and the planning optimizer.
#
# FOUR STREAM CATEGORIES:
#
#     CONTINUOUS FORECASTS (ContinuousForecast objects):
#         Smoothly varying quantities with horizon-dependent uncertainty.
#         Registered via register_continuous_stream().
#         Retrieved via get_continuous(stream_id).
#
#         Typical streams:
#             'outdoor_air_temp'    — °F, from weather service
#             'solar_irradiance'    — W/m², from weather service
#             'humidity'            — °F dewpoint, from weather service
#             'wind_speed'          — m/s, from weather service
#             'electricity_price'   — $/kWh, from historical/external forecast
#             'inlet_water_temp'    — °F, from seasonal ground temp model
#             'btm_solar_generation'— kW, from irradiance + PV specs
#             'household_net_load'  — kW, from learned load model
#
#     EVENT FORECASTS (EventForecast objects):
#         Discrete random occurrences with intensity functions and
#         cumulative energy distributions.
#         Registered via register_event_stream().
#         Retrieved via get_event(stream_id).
#
#         Typical streams:
#             'hot_water_draw'      — showers, dishes, laundry, handwash
#             'ev_arrival'          — when the vehicle arrives, at what SOC
#             'occupancy_transitions'— home/away/sleeping transitions
#
#     CONSTRAINT STREAMS (ConstraintStream objects):
#         Hard boundaries that must not be violated.
#         Registered via register_constraint().
#         Retrieved via get_constraint(stream_id) or
#                       get_all_constraints(t_start, t_end).
#
#         Typical streams:
#             'tank_temp_minimum'   — T_tank ≥ 120°F always
#             'ev_departure_soc'    — SOC ≥ 50% by 7:00 AM
#             'soc_reserve'         — battery SOC ≥ 60% always
#             'bms_limits'          — BMS floor/ceiling
#             'network_limits'      — DSO feeder power limits
#
#     SCHEDULE STREAMS (ContinuousForecast objects with low uncertainty):
#         Customer-declared intent — what the customer WANTS when not
#         being compensated for deviation.
#         Registered via register_schedule().
#         Retrieved via get_schedule(stream_id).
#
#         Typical streams:
#             'hvac_setpoint_schedule'  — thermostat program (°F)
#             'ev_preferred_soc'        — desired charge level (fraction)
#             'battery_preferred_soc'   — desired backup level (fraction)
#
#         Schedules are stored as ContinuousForecast objects because they
#         share the same time-series interpolation and query semantics.
#         The only difference is that their uncertainty is very low
#         (customer-declared values rarely change unexpectedly).
#
# STREAM UPDATES:
#
#     External systems push new data to streams via update_stream():
#
#         Weather service publishes new forecast:
#             dsm.update_stream('outdoor_air_temp', new_series)
#
#         Informational market clear updates price:
#             dsm.update_stream('electricity_price', new_price_series)
#
#         Customer changes thermostat schedule:
#             dsm.update_stream('hvac_setpoint_schedule', new_schedule)
#
#         EV plugs in — departure constraint created:
#             dsm.register_constraint('ev_departure_soc', new_constraint)
#
#         Flow sensor detects shower — event forecast conditioned:
#             dsm.get_event('hot_water_draw').condition_on_observation(
#                 'shower', timestamp, energy_kwh)
#
#         DSO issues network constraint:
#             dsm.update_stream('network_limits', new_limit)
#
#     The update_stream() method routes the new data to the correct
#     stream object's update method.  The stream type (continuous,
#     event, constraint, schedule) determines the routing.
#
# FORECAST BUNDLING:
#
#     The get_forecast_bundle() method packages all forecast streams
#     for a given time interval into a single dictionary.  This is
#     the primary interface used by device models and the planning
#     optimizer — instead of querying each stream individually, they
#     receive a pre-assembled bundle:
#
#         bundle = dsm.get_forecast_bundle(t_start, t_end)
#         # bundle = {
#         #     'outdoor_air_temp': [ContinuousDataPoint, ...],
#         #     'solar_irradiance': [ContinuousDataPoint, ...],
#         #     'hot_water_draw': QuantilePoint,
#         #     'electricity_price': [ContinuousDataPoint, ...],
#         #     ...
#         # }
#
#     The bundle format varies by stream type:
#         Continuous → List[ContinuousDataPoint] (series over interval)
#         Event → QuantilePoint (cumulative energy distribution)
#         Schedule → List[ContinuousDataPoint] (series over interval)
#         Constraints are NOT included in the bundle — they are
#         retrieved separately via get_all_constraints() because they
#         serve a different purpose (hard bounds vs. forecast inputs).
#
# DEVICE-TYPE AWARENESS:
#
#     The DataStreamManager is constructed with a device_type parameter
#     that allows it to validate that the expected streams are
#     registered for that device type.  For example:
#
#         HVAC requires: outdoor_air_temp, hvac_setpoint_schedule
#         Water Heater requires: hot_water_draw, tank_temp_minimum
#         EV requires: ev_departure_soc
#         Battery requires: soc_reserve, electricity_price
#
#     This is advisory — the manager does not prevent registration of
#     unexpected streams or enforce mandatory streams at construction
#     time.  It may issue warnings during get_forecast_bundle() if
#     expected streams are missing.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from:
#         abstractions.data_streams.AbstractDataStreamManager
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - forecasting/continuous_forecast.py:
#         ContinuousForecast objects are stored in the continuous_streams
#         and schedules dictionaries.
#
#     - forecasting/event_forecast.py:
#         EventForecast objects are stored in the event_streams dictionary.
#
#     - forecasting/constraint_stream.py:
#         ConstraintStream objects are stored in the constraint_streams
#         dictionary.
#
#     - forecasting/price_forecast_service.py:
#         The PriceForecastService is a SEPARATE object from the
#         DataStreamManager.  The DSM may hold a continuous
#         electricity_price stream (external forecast), while the
#         PriceForecastService holds the iteration-refined price
#         estimates.  They coexist — the DSM provides the prior,
#         the PFS overrides it with advisory data.
#
#     - devices/*_model.py:
#         Device models receive forecast data through the forecasts
#         dictionary parameter of estimate_flexibility().  This
#         dictionary is populated by the agent calling
#         get_forecast_bundle() and passing the result through.
#
#     - economics/planning_optimizer.py:
#         The planning optimizer receives the full forecast bundle
#         via its forecasts parameter.  It extracts the streams it
#         needs (weather for HVAC, draws for WH, etc.) from the
#         dictionary.
#
#     - agent.py (DeviceAgent):
#         The agent owns the DataStreamManager instance.  During
#         _handle_active(), it calls get_forecast_bundle() and
#         get_all_constraints() to assemble the inputs for F2
#         (flexibility estimation).  It also passes the DSM reference
#         to the planning optimizer.
#
#     - main.py:
#         The simulation harness constructs the DataStreamManager,
#         populates it with all required streams (constructed from
#         external data sources), and passes it to the DeviceAgent
#         constructor.  During the simulation loop, the harness pushes
#         updates via update_stream() when external data refreshes.
#
# DATA TYPES USED:
#     From abstractions/:
#         AbstractDataStreamManager     — the contract being implemented
#         AbstractContinuousForecast    — type of stored continuous streams
#         AbstractEventForecast         — type of stored event streams
#         AbstractConstraintStream      — type of stored constraints
#     From enums_and_constants.py:
#         DeviceType                    — advisory stream validation
#
# EXTERNAL INPUTS:
#     ALL data content in ALL streams is EXTERNAL.  The manager stores
#     and provides access but does not generate, learn, or predict.
#
#     Stream objects are constructed by the simulation harness (main.py)
#     with data from:
#         Weather service API           → outdoor_air_temp, solar, humidity, wind
#         Historical meter/sensor data  → hot_water_draw, ev_arrival, occupancy,
#                                         household_net_load
#         Customer input                → setpoint_schedule, ev_preferred_soc,
#                                         battery_preferred_soc, ev_departure_soc,
#                                         soc_reserve
#         Building codes                → tank_temp_minimum
#         Device specifications         → bms_limits, charge_rate_limits
#         DSO signals                   → network_limits
#         Seasonal models               → inlet_water_temp
#         PV system specs + irradiance  → btm_solar_generation
#         Historical prices             → electricity_price (initial prior)
#         MO forecast                   → electricity_price (if provided)
# ============================================================================

"""Concrete data stream manager — the agent's gateway to the outside world.

The DataStreamManager is the central registry for all exogenous
information the agent needs: weather forecasts, event predictions,
customer schedules, hard constraints, and price estimates.  It does
not generate forecasts — it stores, routes updates, interpolates,
and bundles data from external sources for consumption by device
models, the planning optimizer, and bid formulation.

Four stream categories:
    Continuous forecasts — smoothly varying quantities with uncertainty.
    Event forecasts      — discrete random occurrences with intensities.
    Constraints          — hard boundaries that must not be violated.
    Schedules            — customer-declared intent with low uncertainty.

Key methods:
    register_continuous_stream()  — Add a weather/price/device forecast.
    register_event_stream()       — Add a draw/arrival/occupancy forecast.
    register_constraint()         — Add a hard constraint.
    register_schedule()           — Add a customer schedule.
    update_stream()               — Push new data from external source.
    get_continuous() / get_event() / get_constraint() / get_schedule()
                                  — Retrieve individual streams by ID.
    get_all_constraints()         — All constraints active in an interval.
    get_forecast_bundle()         — All forecasts packaged for a time
                                    interval, ready for device models
                                    and the planning optimizer.
"""

from typing import Any, Dict, List, Optional

from abstractions.data_streams import (
    AbstractContinuousForecast,
    AbstractConstraintStream,
    AbstractDataStreamManager,
    AbstractEventForecast,
)
from enums_and_constants import DeviceType
from tesp_support.tesp_support.curve_and_agent.forecasting.continuous_forecast import ContinuousForecast
from tesp_support.tesp_support.curve_and_agent.forecasting.event_forecast import EventForecast
from tesp_support.tesp_support.curve_and_agent.forecasting.constraint_stream import ConstraintStream


class DataStreamManager:
    """Central registry and access point for all exogenous data streams.

    Owns all forecast, schedule, and constraint streams. Provides
    queries to agent functions that need forward-looking information.

    All data content in the streams must be provided by external sources.
    This manager handles storage, interpolation, and bundled access,
    but does not generate forecasts.

    Args:
        device_type: The device type this manager serves. Determines
            which streams are expected to be registered.
    """

    def __init__(self, device_type: DeviceType):
        self._device_type = device_type
        self._continuous_streams: dict[str, ContinuousForecast] = {}
        self._event_streams: dict[str, EventForecast] = {}
        self._constraint_streams: dict[str, ConstraintStream] = {}
        self._schedules: dict[str, ContinuousForecast] = {}

    def register_continuous_stream(
        self, stream_id: str, forecast: ContinuousForecast
    ) -> None:
        """Register a continuous-process forecast stream.

        Args:
            stream_id: Unique identifier (e.g., 'outdoor_air_temp').
            forecast: The ContinuousForecast object.
                EXTERNAL: The forecast content must be populated
                from an external source (weather API, price model).
        """
        self._continuous_streams[stream_id] = forecast

    def register_event_stream(self, stream_id: str, forecast: EventForecast) -> None:
        """Register an event-process forecast stream.

        Args:
            stream_id: Unique identifier (e.g., 'hot_water_draw').
            forecast: The EventForecast object.
                EXTERNAL: Intensity functions and event distributions
                must be learned from historical data.
        """
        self._event_streams[stream_id] = forecast

    def register_constraint(self, stream_id: str, constraint: ConstraintStream) -> None:
        """Register a constraint stream.

        Args:
            stream_id: Unique identifier (e.g., 'ev_departure_soc').
            constraint: The ConstraintStream object.
                EXTERNAL: Constraint values come from customer input.
        """
        self._constraint_streams[stream_id] = constraint

    def register_schedule(self, stream_id: str, schedule: ContinuousForecast) -> None:
        """Register a customer schedule stream.

        Args:
            stream_id: Unique identifier (e.g., 'hvac_setpoint_schedule').
            schedule: Represented as a ContinuousForecast with very low
                uncertainty (customer-declared values).
                EXTERNAL: From customer's thermostat program, EV app, etc.
        """
        self._schedules[stream_id] = schedule

    def update_stream(self, stream_id: str, new_data: Any) -> None:
        """Push new data to an existing stream.

        Called when external data is refreshed (e.g., new weather
        forecast, informational market clear updates price forecast,
        customer changes thermostat schedule).

        Args:
            stream_id: Which stream to update.
            new_data: The new data. Format depends on stream type.
                EXTERNAL: The caller is responsible for providing
                data in the correct format.
        """
        if stream_id in self._continuous_streams:
            self._continuous_streams[stream_id].update(new_data)
        elif stream_id in self._schedules:
            self._schedules[stream_id].update(new_data)
        else:
            raise KeyError(f"Stream '{stream_id}' not registered")

    def get_continuous(self, stream_id: str) -> ContinuousForecast | None:
        """Retrieve a continuous forecast stream by ID.

        Args:
            stream_id: Stream identifier.

        Returns:
            The ContinuousForecast, or None if not registered.
        """
        return self._continuous_streams.get(stream_id)

    def get_event(self, stream_id: str) -> EventForecast | None:
        """Retrieve an event forecast stream by ID."""
        return self._event_streams.get(stream_id)

    def get_constraint(self, stream_id: str) -> ConstraintStream | None:
        """Retrieve a constraint stream by ID."""
        return self._constraint_streams.get(stream_id)

    def get_schedule(self, stream_id: str) -> ContinuousForecast | None:
        """Retrieve a schedule stream by ID."""
        return self._schedules.get(stream_id)

    def get_all_constraints(
        self, t_start: float, t_end: float
    ) -> list[ConstraintStream]:
        """Get all constraints active over a time interval.

        Args:
            t_start: Start of interval.
            t_end: End of interval.

        Returns:
            List of ConstraintStream objects active in the interval.
        """
        result = []
        for c in self._constraint_streams.values():
            if c._continuous or (c._deadline is not None and t_start <= c._deadline <= t_end) or (c._deadline is not None and c._deadline >= t_start):
                result.append(c)
        return result

    def get_forecast_bundle(self, t_start: float, t_end: float) -> dict[str, Any]:
        """Package all forecast streams for a time interval.

        Returns a dictionary of stream_id -> forecast series, suitable
        for passing to the planning optimizer.

        Args:
            t_start: Start of planning horizon.
            t_end: End of planning horizon.

        Returns:
            Dictionary mapping stream IDs to their data over the interval.
        """
        bundle: dict[str, Any] = {}
        for sid, forecast in self._continuous_streams.items():
            bundle[sid] = forecast.get_series(t_start, t_end)
        for sid, schedule in self._schedules.items():
            bundle[sid] = schedule.get_series(t_start, t_end)
        return bundle
