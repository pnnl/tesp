# ============================================================================
# FILE: data_streams.py
# PURPOSE: Forecast, schedule, and constraint data stream management.
#          Provides the exogenous information that device agents need
#          for flexibility estimation, bid formulation, and planning.
#
# EXTERNAL DEPENDENCIES:
#     All data stream content must be provided by external sources:
#     - Weather forecasts: weather service API or MO-provided
#     - Customer schedules: thermostat program, EV app, etc.
#     - Customer constraints: EV departure requirements, etc.
#     - Price forecasts: MO informational clears, historical data
#     - Occupancy: customer schedule, learned patterns, sensors
#     - Event models: learned from historical meter/sensor data
# ============================================================================

from typing import Dict, List, Optional, Tuple, Callable
from data_types import (
    ContinuousDataPoint, EventDefinition, QuantilePoint,
    UncertaintyEnvelope
)
from enums_and_constants import ForecastParadigm, StreamType


class UncertaintyModel:
    """Models how forecast uncertainty grows with lead time.
    
    Supports three functional forms:
    - SATURATING_EXP: σ(τ) = σ_∞ · (1 - e^{-τ/τ_c})
    - POWER_LAW: σ(τ) = min(σ_∞, σ_0 + α·τ^β)
    - EMPIRICAL: σ(τ) interpolated from a lookup table
    
    Args:
        model_type: One of 'saturating_exp', 'power_law', 'empirical'.
        params: Dictionary of model parameters.
            EXTERNAL: Must be calibrated from historical forecast
            verification data or set to reasonable defaults.
            
            For saturating_exp:
                sigma_inf: Climatological std dev (maximum uncertainty).
                tau_c: Correlation time constant (seconds).
            For power_law:
                sigma_0: Measurement uncertainty at τ=0.
                alpha: Growth rate coefficient.
                beta: Growth exponent (0.5-1.0 typical).
                sigma_inf: Climatological cap.
            For empirical:
                lead_time_sigma_table: List of (lead_time_seconds, sigma).
    """

    def __init__(self, model_type: str, params: Dict):
        self._model_type = model_type
        self._params = params

    def sigma_at(self, lead_time: float) -> float:
        """Compute forecast standard deviation at a given lead time.
        
        Args:
            lead_time: Time from forecast issue to forecast valid time
                (seconds).
        
        Returns:
            Standard deviation of the forecast error at this lead time.
        """
        raise NotImplementedError


class ContinuousForecast:
    """Forecast of a continuously-varying quantity (temperature, price, etc.).
    
    Provides point forecasts with horizon-dependent uncertainty envelopes
    at each timestep across the forecast horizon.
    
    Args:
        variable_name: What is being forecasted (e.g., 'outdoor_air_temp').
        unit: Physical unit (e.g., '°F', '$/kWh').
        uncertainty_model: The UncertaintyModel governing how σ grows.
            EXTERNAL: Must be provided with calibrated parameters.
        series: Initial forecast time series.
            EXTERNAL: Must be provided by a weather service, price
            forecasting model, or other external source.
    """

    def __init__(
        self,
        variable_name: str,
        unit: str,
        uncertainty_model: UncertaintyModel,
        series: Optional[List[ContinuousDataPoint]] = None
    ):
        self._variable_name = variable_name
        self._unit = unit
        self._uncertainty_model = uncertainty_model
        self._series = series or []

    def update(self, new_series: List[ContinuousDataPoint]) -> None:
        """Replace the forecast series with updated data.
        
        Args:
            new_series: New forecast data points.
                EXTERNAL: From weather service update, new price 
                forecast, or informational market clear.
        """
        raise NotImplementedError

    def get_at(self, timestamp: float) -> ContinuousDataPoint:
        """Interpolate or look up the forecast at a specific time.
        
        Args:
            timestamp: Simulation time to query.
        
        Returns:
            ContinuousDataPoint with value, sigma, and quantiles
            at the requested time.
        """
        raise NotImplementedError

    def get_series(
        self,
        t_start: float,
        t_end: float,
        resolution: Optional[float] = None
    ) -> List[ContinuousDataPoint]:
        """Return forecast series over an interval.
        
        Args:
            t_start: Start of the interval.
            t_end: End of the interval.
            resolution: Optional resampling interval (seconds).
                If None, returns data at native resolution.
        
        Returns:
            List of ContinuousDataPoint covering the interval.
        """
        raise NotImplementedError


class EventForecast:
    """Forecast of discrete random events (showers, EV arrivals, etc.).
    
    Uses an intensity function λ(t) and per-event energy distributions
    to produce cumulative energy draw distributions over the forecast
    horizon. Supports Bayesian conditioning on observed events.
    
    Args:
        event_types: List of event type definitions.
            EXTERNAL: Learned from historical data (meter, flow sensors).
        intensity_function: Time series of event intensity λ(t) in
            events/hour. 
            EXTERNAL: Learned from historical patterns.
        daily_expected_count: Expected number of events per day.
        daily_expected_energy: Expected total energy from events per day.
    """

    def __init__(
        self,
        event_types: List[EventDefinition],
        intensity_function: Optional[List[Tuple[float, float]]] = None,
        daily_expected_count: float = 0.0,
        daily_expected_energy: float = 0.0
    ):
        self._event_types = event_types
        self._intensity_function = intensity_function or []
        self._daily_expected_count = daily_expected_count
        self._daily_expected_energy = daily_expected_energy
        self._observed_events: List[Dict] = []

    def get_intensity_at(self, timestamp: float) -> float:
        """Get event intensity (events/hour) at a specific time.
        
        Args:
            timestamp: Simulation time to query.
        
        Returns:
            λ(t) in events per hour.
        """
        raise NotImplementedError

    def get_cumulative_energy_distribution(
        self,
        t_start: float,
        t_end: float
    ) -> QuantilePoint:
        """Compute the distribution of cumulative energy drawn by events
        over a time interval.
        
        This is the core output of the event forecast: not "when will
        events happen?" but "how much total energy will events consume
        between t_start and t_end?"
        
        The distribution is computed analytically (compound Poisson)
        or by Monte Carlo sampling from the intensity function and
        per-event energy distributions.
        
        Args:
            t_start: Start of interval.
            t_end: End of interval.
        
        Returns:
            QuantilePoint with expected value, variance, and quantiles
            of total energy drawn.
        """
        raise NotImplementedError

    def condition_on_observation(
        self,
        event_type: str,
        timestamp: float,
        energy: float
    ) -> None:
        """Update the forecast by conditioning on an observed event.
        
        When an event is observed (e.g., a shower is detected by a
        flow sensor), this method updates the remaining intensity
        function and cumulative distributions using Bayesian updating.
        
        For example, observing a first morning shower shifts the
        distribution of the second shower's timing and reduces
        overall uncertainty in the daily energy budget.
        
        Args:
            event_type: Type of observed event (e.g., 'shower').
            timestamp: When the event occurred.
            energy: Energy consumed by the event (kWh).
                SOURCE: From real-time metering/sensing.
        """
        raise NotImplementedError

    def reset_observations(self) -> None:
        """Clear observed events (e.g., at the start of a new day).
        
        Resets the conditioning state so the forecast reverts to
        the prior daily pattern.
        """
        raise NotImplementedError


class ConstraintStream:
    """A hard constraint that the agent must not violate.
    
    Constraints may be continuous (apply at all times) or deadline-based
    (must be satisfied by a specific time).
    
    Args:
        constraint_id: Unique identifier for this constraint.
        variable: What variable is constrained (e.g., 'soc', 'tank_temp').
        constraint_type: 'minimum', 'maximum', 'equality', 'by_time'.
        continuous: Whether the constraint applies at all times.
        deadline: For by_time constraints, the time by which the
            constraint must be satisfied.
            EXTERNAL: From customer input (e.g., EV departure time).
        required_value: The threshold or target value.
            EXTERNAL: From customer input (e.g., minimum SOC at departure).
    """

    def __init__(
        self,
        constraint_id: str,
        variable: str,
        constraint_type: str,
        continuous: bool = False,
        deadline: Optional[float] = None,
        required_value: float = 0.0
    ):
        self._constraint_id = constraint_id
        self._variable = variable
        self._constraint_type = constraint_type
        self._continuous = continuous
        self._deadline = deadline
        self._required_value = required_value

    def is_feasible(self, value_at_time: float, timestamp: float) -> bool:
        """Check if a given value satisfies this constraint at a given time.
        
        Args:
            value_at_time: The current or projected value of the
                constrained variable.
            timestamp: The time at which to check.
        
        Returns:
            True if the constraint is satisfied.
        """
        raise NotImplementedError

    def feasibility_margin(
        self,
        value_at_time: float,
        timestamp: float
    ) -> float:
        """How much slack exists at a given time.
        
        Args:
            value_at_time: Current or projected value.
            timestamp: Time of evaluation.
        
        Returns:
            Positive = feasible with room. Negative = violated.
        """
        raise NotImplementedError


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
        self._continuous_streams: Dict[str, ContinuousForecast] = {}
        self._event_streams: Dict[str, EventForecast] = {}
        self._constraint_streams: Dict[str, ConstraintStream] = {}
        self._schedules: Dict[str, ContinuousForecast] = {}

    def register_continuous_stream(
        self,
        stream_id: str,
        forecast: ContinuousForecast
    ) -> None:
        """Register a continuous-process forecast stream.
        
        Args:
            stream_id: Unique identifier (e.g., 'outdoor_air_temp').
            forecast: The ContinuousForecast object.
                EXTERNAL: The forecast content must be populated
                from an external source (weather API, price model).
        """
        raise NotImplementedError

    def register_event_stream(
        self,
        stream_id: str,
        forecast: EventForecast
    ) -> None:
        """Register an event-process forecast stream.
        
        Args:
            stream_id: Unique identifier (e.g., 'hot_water_draw').
            forecast: The EventForecast object.
                EXTERNAL: Intensity functions and event distributions
                must be learned from historical data.
        """
        raise NotImplementedError

    def register_constraint(
        self,
        stream_id: str,
        constraint: ConstraintStream
    ) -> None:
        """Register a constraint stream.
        
        Args:
            stream_id: Unique identifier (e.g., 'ev_departure_soc').
            constraint: The ConstraintStream object.
                EXTERNAL: Constraint values come from customer input.
        """
        raise NotImplementedError

    def register_schedule(
        self,
        stream_id: str,
        schedule: ContinuousForecast
    ) -> None:
        """Register a customer schedule stream.
        
        Args:
            stream_id: Unique identifier (e.g., 'hvac_setpoint_schedule').
            schedule: Represented as a ContinuousForecast with very low
                uncertainty (customer-declared values).
                EXTERNAL: From customer's thermostat program, EV app, etc.
        """
        raise NotImplementedError

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
        raise NotImplementedError

    def get_continuous(self, stream_id: str) -> Optional[ContinuousForecast]:
        """Retrieve a continuous forecast stream by ID.
        
        Args:
            stream_id: Stream identifier.
        
        Returns:
            The ContinuousForecast, or None if not registered.
        """
        raise NotImplementedError

    def get_event(self, stream_id: str) -> Optional[EventForecast]:
        """Retrieve an event forecast stream by ID."""
        raise NotImplementedError

    def get_constraint(self, stream_id: str) -> Optional[ConstraintStream]:
        """Retrieve a constraint stream by ID."""
        raise NotImplementedError

    def get_schedule(self, stream_id: str) -> Optional[ContinuousForecast]:
        """Retrieve a schedule stream by ID."""
        raise NotImplementedError

    def get_all_constraints(
        self,
        t_start: float,
        t_end: float
    ) -> List[ConstraintStream]:
        """Get all constraints active over a time interval.
        
        Args:
            t_start: Start of interval.
            t_end: End of interval.
        
        Returns:
            List of ConstraintStream objects active in the interval.
        """
        raise NotImplementedError

    def get_forecast_bundle(
        self,
        t_start: float,
        t_end: float
    ) -> Dict[str, Any]:
        """Package all forecast streams for a time interval.
        
        Returns a dictionary of stream_id -> forecast series, suitable
        for passing to the planning optimizer.
        
        Args:
            t_start: Start of planning horizon.
            t_end: End of planning horizon.
        
        Returns:
            Dictionary mapping stream IDs to their data over the interval.
        """
        raise NotImplementedError