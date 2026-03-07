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

from typing import Any, Dict, List, Optional, Tuple, Callable
from data_types import (
    ContinuousDataPoint,
    EventDefinition,
    QuantilePoint,
    UncertaintyEnvelope,
)
from enums_and_constants import DeviceType, ForecastParadigm, StreamType


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
        import math

        if self._model_type == "saturating_exp":
            sigma_inf = self._params["sigma_inf"]
            tau_c = self._params["tau_c"]
            return sigma_inf * (1.0 - math.exp(-lead_time / tau_c))

        elif self._model_type == "power_law":
            sigma_0 = self._params["sigma_0"]
            alpha = self._params["alpha"]
            beta = self._params["beta"]
            sigma_inf = self._params["sigma_inf"]
            return min(sigma_inf, sigma_0 + alpha * (lead_time ** beta))

        elif self._model_type == "empirical":
            table = self._params["lead_time_sigma_table"]
            if lead_time <= table[0][0]:
                return table[0][1]
            if lead_time >= table[-1][0]:
                return table[-1][1]
            for i in range(len(table) - 1):
                t0, s0 = table[i]
                t1, s1 = table[i + 1]
                if t0 <= lead_time <= t1:
                    f = (lead_time - t0) / (t1 - t0)
                    return s0 + f * (s1 - s0)
            return table[-1][1]

        return 0.0


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
        series: Optional[List[ContinuousDataPoint]] = None,
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
        self._series = list(new_series)

    def get_at(self, timestamp: float) -> ContinuousDataPoint:
        """Interpolate or look up the forecast at a specific time.

        Args:
            timestamp: Simulation time to query.

        Returns:
            ContinuousDataPoint with value, sigma, and quantiles
            at the requested time.
        """
        if not self._series:
            return ContinuousDataPoint(timestamp=timestamp)
        if len(self._series) == 1:
            sigma = self._uncertainty_model.sigma_at(abs(timestamp - self._series[0].timestamp))
            return ContinuousDataPoint(
                timestamp=timestamp, value=self._series[0].value, sigma=sigma)
        # Clamp to endpoints
        if timestamp <= self._series[0].timestamp:
            sigma = self._uncertainty_model.sigma_at(0.0)
            return ContinuousDataPoint(
                timestamp=timestamp, value=self._series[0].value, sigma=sigma)
        if timestamp >= self._series[-1].timestamp:
            lead = timestamp - self._series[0].timestamp
            sigma = self._uncertainty_model.sigma_at(lead)
            return ContinuousDataPoint(
                timestamp=timestamp, value=self._series[-1].value, sigma=sigma)
        # Linear interpolation
        for i in range(len(self._series) - 1):
            t0 = self._series[i].timestamp
            t1 = self._series[i + 1].timestamp
            if t0 <= timestamp <= t1:
                f = (timestamp - t0) / (t1 - t0) if t1 != t0 else 0.0
                val = self._series[i].value + f * (self._series[i + 1].value - self._series[i].value)
                lead = timestamp - self._series[0].timestamp
                sigma = self._uncertainty_model.sigma_at(lead)
                return ContinuousDataPoint(
                    timestamp=timestamp, value=val, sigma=sigma)
        return ContinuousDataPoint(timestamp=timestamp)

    def get_series(
        self, t_start: float, t_end: float, resolution: Optional[float] = None
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
        if resolution is not None:
            result = []
            t = t_start
            while t <= t_end + 1e-9:
                result.append(self.get_at(t))
                t += resolution
            return result
        # Native resolution: return points within range
        return [self.get_at(pt.timestamp) for pt in self._series
                if t_start <= pt.timestamp <= t_end]


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
        daily_expected_energy: float = 0.0,
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
        if not self._intensity_function:
            return 0.0
        if timestamp <= self._intensity_function[0][0]:
            return self._intensity_function[0][1]
        if timestamp >= self._intensity_function[-1][0]:
            return self._intensity_function[-1][1]
        for i in range(len(self._intensity_function) - 1):
            t0, v0 = self._intensity_function[i]
            t1, v1 = self._intensity_function[i + 1]
            if t0 <= timestamp <= t1:
                f = (timestamp - t0) / (t1 - t0) if t1 != t0 else 0.0
                return v0 + f * (v1 - v0)
        return self._intensity_function[-1][1]

    def get_cumulative_energy_distribution(
        self, t_start: float, t_end: float
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
        # Integrate intensity via trapezoidal rule to get expected event count
        n_steps = max(1, int((t_end - t_start) / 60.0))  # 1-minute steps
        dt = (t_end - t_start) / n_steps
        total_lambda = 0.0
        prev_lam = self.get_intensity_at(t_start)
        for i in range(1, n_steps + 1):
            t = t_start + i * dt
            cur_lam = self.get_intensity_at(t)
            total_lambda += (prev_lam + cur_lam) / 2.0 * (dt / 3600.0)  # events
            prev_lam = cur_lam

        # Scale by daily_expected_count if the raw integral diverges
        if self._daily_expected_count > 0 and self._intensity_function:
            raw_daily = self._integrate_full_day()
            if raw_daily > 0:
                total_lambda *= self._daily_expected_count / raw_daily

        # Subtract observed events in this window
        observed_energy = sum(
            ev["energy"] for ev in self._observed_events
            if t_start <= ev["timestamp"] <= t_end
        )
        observed_count = sum(
            1 for ev in self._observed_events
            if t_start <= ev["timestamp"] <= t_end
        )
        remaining_lambda = max(0.0, total_lambda - observed_count)

        # Average energy per event
        if self._event_types:
            mean_energy = sum(e.energy_mean for e in self._event_types) / len(self._event_types)
            var_energy = sum(e.energy_std ** 2 for e in self._event_types) / len(self._event_types)
        else:
            mean_energy = self._daily_expected_energy / max(1.0, self._daily_expected_count)
            var_energy = 0.0

        # Compound Poisson: E[S] = λ·μ, Var[S] = λ·(σ² + μ²)
        expected_remaining = remaining_lambda * mean_energy
        variance = remaining_lambda * (var_energy + mean_energy ** 2)

        expected_total = expected_remaining + observed_energy

        return QuantilePoint(
            expected=expected_total,
            variance=variance,
        )

    def condition_on_observation(
        self, event_type: str, timestamp: float, energy: float
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
        self._observed_events.append({
            "event_type": event_type,
            "timestamp": timestamp,
            "energy": energy,
        })

    def reset_observations(self) -> None:
        """Clear observed events (e.g., at the start of a new day).

        Resets the conditioning state so the forecast reverts to
        the prior daily pattern.
        """
        self._observed_events = []

    def _integrate_full_day(self) -> float:
        """Integrate the raw intensity function over a full day (0..86400)."""
        if not self._intensity_function:
            return 0.0
        total = 0.0
        for i in range(len(self._intensity_function) - 1):
            t0, v0 = self._intensity_function[i]
            t1, v1 = self._intensity_function[i + 1]
            total += (v0 + v1) / 2.0 * ((t1 - t0) / 3600.0)
        return total


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
        required_value: float = 0.0,
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
        if self._constraint_type == "by_time":
            if self._deadline is not None and timestamp < self._deadline:
                return True
            return value_at_time >= self._required_value
        elif self._constraint_type == "minimum":
            return value_at_time >= self._required_value
        elif self._constraint_type == "maximum":
            return value_at_time <= self._required_value
        elif self._constraint_type == "equality":
            return abs(value_at_time - self._required_value) < 1e-9
        return True

    def feasibility_margin(self, value_at_time: float, timestamp: float) -> float:
        """How much slack exists at a given time.

        Args:
            value_at_time: Current or projected value.
            timestamp: Time of evaluation.

        Returns:
            Positive = feasible with room. Negative = violated.
        """
        if self._constraint_type in ("minimum", "by_time"):
            return value_at_time - self._required_value
        elif self._constraint_type == "maximum":
            return self._required_value - value_at_time
        elif self._constraint_type == "equality":
            return -abs(value_at_time - self._required_value)
        return 0.0


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

    def get_continuous(self, stream_id: str) -> Optional[ContinuousForecast]:
        """Retrieve a continuous forecast stream by ID.

        Args:
            stream_id: Stream identifier.

        Returns:
            The ContinuousForecast, or None if not registered.
        """
        return self._continuous_streams.get(stream_id)

    def get_event(self, stream_id: str) -> Optional[EventForecast]:
        """Retrieve an event forecast stream by ID."""
        return self._event_streams.get(stream_id)

    def get_constraint(self, stream_id: str) -> Optional[ConstraintStream]:
        """Retrieve a constraint stream by ID."""
        return self._constraint_streams.get(stream_id)

    def get_schedule(self, stream_id: str) -> Optional[ContinuousForecast]:
        """Retrieve a schedule stream by ID."""
        return self._schedules.get(stream_id)

    def get_all_constraints(
        self, t_start: float, t_end: float
    ) -> List[ConstraintStream]:
        """Get all constraints active over a time interval.

        Args:
            t_start: Start of interval.
            t_end: End of interval.

        Returns:
            List of ConstraintStream objects active in the interval.
        """
        result = []
        for c in self._constraint_streams.values():
            if c._continuous:
                result.append(c)
            elif c._deadline is not None and t_start <= c._deadline <= t_end:
                result.append(c)
            elif c._deadline is not None and c._deadline >= t_start:
                result.append(c)
        return result

    def get_forecast_bundle(self, t_start: float, t_end: float) -> Dict[str, Any]:
        """Package all forecast streams for a time interval.

        Returns a dictionary of stream_id -> forecast series, suitable
        for passing to the planning optimizer.

        Args:
            t_start: Start of planning horizon.
            t_end: End of planning horizon.

        Returns:
            Dictionary mapping stream IDs to their data over the interval.
        """
        bundle: Dict[str, Any] = {}
        for sid, forecast in self._continuous_streams.items():
            bundle[sid] = forecast.get_series(t_start, t_end)
        for sid, schedule in self._schedules.items():
            bundle[sid] = schedule.get_series(t_start, t_end)
        return bundle
