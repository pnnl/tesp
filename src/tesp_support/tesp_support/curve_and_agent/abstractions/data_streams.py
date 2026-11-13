# ============================================================================
# FILE: abstractions/data_streams.py
# PURPOSE: Abstract base classes for all exogenous data streams:
#          forecasts, uncertainty models, constraints, and the data
#          stream manager.
#
# Contains six ABCs that form a cohesive type family:
#
#     AbstractUncertaintyModel
#         Models how forecast uncertainty grows with lead time.
#
#     AbstractForecast
#         Common interface for all forward-looking data.
#         ├── AbstractContinuousForecast (temperature, price, solar, …)
#         └── AbstractEventForecast (showers, EV arrival, occupancy, …)
#
#     AbstractConstraintStream
#         Hard constraints (tank temp minimum, EV departure SOC, …).
#
#     AbstractDataStreamManager
#         Central registry and access point for all streams.
#
# These classes are co-located because they have mutual type references
# (the manager holds collections of all stream types; forecasts reference
# the uncertainty model) and are always consumed together by the agent's
# flexibility estimation and planning functions.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - AbstractDataStreamManager used by:
#           AbstractDeviceAgent._handle_active() (forecasts + constraints)
#           AbstractDeviceModel.estimate_flexibility() (via forecast bundle)
#           AbstractPlanningOptimizer.solve() (full forecast bundle)
#     - AbstractConstraintStream used by:
#           AbstractPlanningOptimizer.solve() (hard limits over horizon)
#           AbstractDeviceModel.estimate_flexibility() (interval limits)
#     - AbstractContinuousForecast used by:
#           AbstractDeviceModel.estimate_flexibility() (weather inputs)
#           Concrete preference curve generation (schedule for P₀, Q₀)
#     - AbstractEventForecast used by:
#           Concrete device models (water heater draw, EV arrival)
#
# IMPORTS FROM:
#     - typing: Any, Dict, List, Optional, Tuple
#     - data_types: ContinuousDataPoint, QuantilePoint, UncertaintyEnvelope
#     - enums_and_constants: ForecastParadigm
# ============================================================================

"""Abstract data streams — forecasts, uncertainty, constraints, and their manager.

This module defines the contract for all exogenous information that the
agent consumes.  Data stream content must be provided by external sources
(weather services, customer input, learned models, market operator).  The
abstractions handle storage, interpolation, uncertainty modeling, Bayesian
conditioning (for event forecasts), and bundled access.

Two forecast paradigms are supported:
    CONTINUOUS — smoothly varying quantities (temperature, price)
                 with horizon-dependent Gaussian-like uncertainty.
    EVENT      — discrete random occurrences (showers, EV arrivals)
                 with intensity functions and cumulative energy
                 distributions.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from data_types import ContinuousDataPoint, QuantilePoint, UncertaintyEnvelope
from enums_and_constants import ForecastParadigm

class AbstractForecast(ABC):
    """Abstract base for all forward-looking data streams, whether
    continuous-process or event-process.

    Every forecast can report its paradigm, return an expected value at
    a future time, and provide a full uncertainty envelope.
    """

    @property
    @abstractmethod
    def paradigm(self) -> ForecastParadigm:
        """Whether this is a CONTINUOUS, EVENT, or HYBRID forecast.

        Returns:
            ``ForecastParadigm`` enum member.
        """
        ...

    @abstractmethod
    def get_expected_at(self, timestamp: float) -> float:
        """Point estimate (mean) at a future time.

        Args:
            timestamp: Simulation time to query.

        Returns:
            Expected value of the forecasted variable.
        """
        ...

    @abstractmethod
    def get_uncertainty_at(self, timestamp: float) -> UncertaintyEnvelope:
        """Full distributional information at a future time.

        Args:
            timestamp: Simulation time to query.

        Returns:
            ``UncertaintyEnvelope`` with expected value, sigma, and
            quantiles.
        """
        ...


class AbstractContinuousForecast(AbstractForecast):
    """Abstract base for forecasts of continuously varying quantities
    (temperature, price, irradiance, …).

    Provides a time series of point forecasts with horizon-dependent
    uncertainty envelopes governed by an ``AbstractUncertaintyModel``.
    """

    @property
    def paradigm(self) -> ForecastParadigm:
        return ForecastParadigm.CONTINUOUS

    @abstractmethod
    def update(self, new_series: List[ContinuousDataPoint]) -> None:
        """Replace the forecast series with updated data.

        Args:
            new_series: New forecast data points.
                EXTERNAL: From weather service, price model, or
                informational market clear.
        """
        ...

    @abstractmethod
    def get_at(self, timestamp: float) -> ContinuousDataPoint:
        """Interpolate the forecast at a specific time.

        Args:
            timestamp: Simulation time to query.

        Returns:
            ``ContinuousDataPoint`` with value, sigma, and quantiles.
        """
        ...

    @abstractmethod
    def get_series(
        self,
        t_start: float,
        t_end: float,
        resolution: Optional[float] = None,
    ) -> List[ContinuousDataPoint]:
        """Return the forecast series over an interval.

        Args:
            t_start: Start of interval.
            t_end: End of interval.
            resolution: Optional resampling interval (seconds).

        Returns:
            List of ``ContinuousDataPoint`` covering the interval.
        """
        ...


class AbstractEventForecast(AbstractForecast):
    """Abstract base for forecasts of discrete random events
    (showers, EV arrivals, occupancy transitions, …).

    Uses an intensity function λ(t) and per-event energy distributions
    to produce cumulative energy draw distributions.  Supports Bayesian
    conditioning on observed events.
    """

    @property
    def paradigm(self) -> ForecastParadigm:
        return ForecastParadigm.EVENT

    @abstractmethod
    def get_intensity_at(self, timestamp: float) -> float:
        """Event intensity (events/hour) at a specific time.

        Args:
            timestamp: Simulation time to query.

        Returns:
            λ(t) in events per hour.
        """
        ...

    @abstractmethod
    def get_cumulative_energy_distribution(
        self,
        t_start: float,
        t_end: float,
    ) -> QuantilePoint:
        """Distribution of cumulative energy consumed by events over
        a time interval.

        Args:
            t_start: Start of interval.
            t_end: End of interval.

        Returns:
            ``QuantilePoint`` with expected value, variance, and
            quantiles of total energy drawn.
        """
        ...

    @abstractmethod
    def condition_on_observation(
        self,
        event_type: str,
        timestamp: float,
        energy: float,
    ) -> None:
        """Update the forecast by conditioning on an observed event.

        Args:
            event_type: Type of observed event (e.g., ``'shower'``).
            timestamp: When the event occurred.
            energy: Energy consumed by the event (kWh).
                SOURCE: From real-time metering / sensing.
        """
        ...

    @abstractmethod
    def reset_observations(self) -> None:
        """Clear observed events (e.g., at the start of a new day)."""
        ...


class AbstractUncertaintyModel(ABC):
    """Abstract base for models of how forecast uncertainty grows
    with lead time.

    Args:
        model_type: Identifier for the functional form
            (e.g., ``'saturating_exp'``, ``'power_law'``, ``'empirical'``).
        params: Model-specific parameters.
            EXTERNAL: Calibrated from historical forecast verification
            data or set to reasonable defaults.
    """

    def __init__(self, model_type: str, params: Dict[str, Any]):
        self._model_type = model_type
        self._params = params

    @abstractmethod
    def sigma_at(self, lead_time: float) -> float:
        """Forecast standard deviation at a given lead time.

        Args:
            lead_time: Seconds from forecast issue to valid time.

        Returns:
            σ(τ) — standard deviation of the forecast error.
        """
        ...


class AbstractConstraintStream(ABC):
    """Abstract base for hard constraints the agent must not violate.

    Constraints may be continuous (all times) or deadline-based
    (by a specific time).

    Args:
        constraint_id: Unique identifier.
        variable: What variable is constrained (e.g., ``'soc'``).
        constraint_type: ``'minimum'``, ``'maximum'``, ``'equality'``,
            or ``'by_time'``.
    """

    def __init__(
        self,
        constraint_id: str,
        variable: str,
        constraint_type: str,
    ):
        self._constraint_id = constraint_id
        self._variable = variable
        self._constraint_type = constraint_type

    @abstractmethod
    def is_feasible(self, value_at_time: float, timestamp: float) -> bool:
        """Check whether a value satisfies this constraint at a given time.

        Args:
            value_at_time: Current or projected variable value.
            timestamp: Simulation time.

        Returns:
            ``True`` if the constraint is satisfied.
        """
        ...

    @abstractmethod
    def feasibility_margin(
        self,
        value_at_time: float,
        timestamp: float,
    ) -> float:
        """How much slack exists.

        Args:
            value_at_time: Current or projected value.
            timestamp: Simulation time.

        Returns:
            Positive = feasible with room.  Negative = violated.
        """
        ...


class AbstractDataStreamManager(ABC):
    """Abstract base for the central registry and access point for all
    exogenous data streams (forecasts, schedules, constraints).

    All data *content* must be provided by external sources.  The
    manager handles storage, interpolation, and bundled access.
    """

    @abstractmethod
    def register_continuous_stream(
        self,
        stream_id: str,
        forecast: AbstractContinuousForecast,
    ) -> None:
        """Register a continuous-process forecast stream.

        Args:
            stream_id: Unique identifier (e.g., ``'outdoor_air_temp'``).
            forecast: The forecast object.
                EXTERNAL: Content must be populated from an external source.
        """
        ...

    @abstractmethod
    def register_event_stream(
        self,
        stream_id: str,
        forecast: AbstractEventForecast,
    ) -> None:
        """Register an event-process forecast stream.

        Args:
            stream_id: Unique identifier (e.g., ``'hot_water_draw'``).
            forecast: The forecast object.
                EXTERNAL: Intensity functions learned from historical data.
        """
        ...

    @abstractmethod
    def register_constraint(
        self,
        stream_id: str,
        constraint: AbstractConstraintStream,
    ) -> None:
        """Register a constraint stream.

        Args:
            stream_id: Unique identifier.
            constraint: The constraint object.
                EXTERNAL: Values from customer input.
        """
        ...

    @abstractmethod
    def register_schedule(
        self,
        stream_id: str,
        schedule: AbstractContinuousForecast,
    ) -> None:
        """Register a customer schedule stream.

        Args:
            stream_id: Unique identifier.
            schedule: Schedule represented as a low-uncertainty forecast.
                EXTERNAL: From customer thermostat program, EV app, etc.
        """
        ...

    @abstractmethod
    def update_stream(self, stream_id: str, new_data: Any) -> None:
        """Push new data to an existing stream.

        Args:
            stream_id: Which stream to update.
            new_data: The new data (format depends on stream type).
                EXTERNAL: Caller provides correctly formatted data.
        """
        ...

    @abstractmethod
    def get_all_constraints(
        self,
        t_start: float,
        t_end: float,
    ) -> List[AbstractConstraintStream]:
        """Get all constraints active over a time interval.

        Args:
            t_start: Start of interval.
            t_end: End of interval.

        Returns:
            List of active constraint streams.
        """
        ...

    @abstractmethod
    def get_forecast_bundle(
        self,
        t_start: float,
        t_end: float,
    ) -> Dict[str, Any]:
        """Package all forecast streams for a time interval.

        Returns:
            Dictionary mapping stream IDs to their data.
        """
        ...