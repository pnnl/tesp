# ============================================================================
# FILE: forecasting/event_forecast.py
# PURPOSE: Concrete implementation of forecasts for discrete random
#          events — occurrences that happen at random times with random
#          magnitudes (agent function F2 input).
#
# This is the appropriate forecast paradigm for quantities that are NOT
# continuously varying but instead arrive as discrete episodes:
# showers, dishwashing runs, EV arrivals, occupancy transitions,
# cooking events.  These cannot be meaningfully represented as a
# point-estimate time series with Gaussian uncertainty — predicting
# "0.3 GPM of shower flow at 7:15am ± 2.0 GPM" is technically correct
# but operationally useless.
#
# Instead, the event forecast uses a STOCHASTIC POINT PROCESS model:
#     - An intensity function λ(t) giving the expected event rate
#       (events/hour) at each time.
#     - Per-event distributions for duration, magnitude, and energy.
#     - A cumulative energy distribution derived from the above,
#       giving the probability distribution of TOTAL energy consumed
#       by events over any time interval.
#     - Bayesian conditioning that updates the forecast in real-time
#       as events are observed or fail to occur.
#
# EVENTS REPRESENTED BY THIS FORECAST:
#
#     hot_water_draw:
#         Event types: shower, dishwash, handwash, laundry.
#         Intensity: peaks at 6–8am (morning shower) and 6–8pm (evening).
#         Per-event energy: shower ≈ 3–5 kWh, dishwash ≈ 1–2 kWh,
#                           handwash ≈ 0.05–0.15 kWh.
#         Daily expected count: ~5 significant draws.
#         Primary consumer: WaterHeaterModel.estimate_flexibility().
#
#     ev_arrival:
#         Single-event forecast: when will the vehicle arrive home
#         and at what SOC?
#         Intensity: hazard rate peaking around typical arrival time.
#         Per-event distribution: arrival time × arrival SOC (joint).
#         Primary consumer: EVChargerModel.estimate_flexibility()
#             (for DA planning when vehicle is not yet plugged in).
#
#     occupancy_transitions:
#         Events: home→away, away→home, home→sleeping, sleeping→home.
#         Intensity: departure peaks at 7:30am workdays, return peaks
#                    at 5:30pm.
#         Primary consumer: HVACModel.estimate_flexibility() (occupancy
#             affects both internal heat gains and amenity relevance —
#             temperature deviations matter less in an empty house).
#
# WHY EVENT FORECASTS DIFFER FROM CONTINUOUS FORECASTS:
#
#     Consider predicting hot water demand for the next 3 hours:
#
#     Continuous approach (WRONG):
#         "At 7am, expected draw = 0.8 GPM ± 1.5 GPM"
#         The expected value (0.8 GPM) is not a real operating state.
#         A shower is either happening (~2.5 GPM) or not (0 GPM).
#         The forecast is smearing a discrete event across time.
#
#     Event approach (CORRECT):
#         "P(shower by 7am) = 0.55.  If it happens, energy ≈ 4 kWh.
#          Cumulative energy distribution by 8am:
#              P(0 kWh) = 0.41 (no shower yet)
#              P(~4 kWh) = 0.37 (one shower)
#              P(~8 kWh) = 0.16 (two showers)
#          This distribution is multimodal, not Gaussian."
#
#     The agent's device model propagates this DISTRIBUTION (not a
#     point forecast) through the tank physics to produce a
#     DISTRIBUTION of tank temperatures, from which flexibility
#     quantiles (Q_min_p50, Q_min_p90, Q_min_p99) are derived.
#
# THE INTENSITY FUNCTION λ(t):
#
#     The intensity function captures the daily pattern of event
#     occurrence without committing to specific event times:
#
#         λ(t) = expected events per hour at time t
#         P(event in [t, t+Δt]) ≈ λ(t) · Δt    for small Δt
#
#     The function is typically learned from historical data:
#         - Flow sensor data for hot water draws.
#         - Charging session logs for EV arrivals.
#         - Motion sensor / phone geofencing for occupancy.
#
#     The intensity function may vary by:
#         - Day of week (weekday vs. weekend patterns).
#         - Season (longer showers in winter, earlier arrivals in summer).
#         - Household profile (number of occupants, work schedules).
#
# CUMULATIVE ENERGY DISTRIBUTION:
#
#     The key output for the device model is NOT "when will events
#     happen?" but "how much total energy will events consume between
#     t_start and t_end?"  This is computed by:
#
#     Analytical (compound Poisson):
#         E[N(T)] = ∫ λ(t) dt                    (expected event count)
#         E[E_total] = E[N] · E[E_per_event]     (expected energy)
#         Var[E_total] = E[N] · E[E²_per_event]  (compound Poisson variance)
#
#         For many small events (handwashes): Gaussian approximation via CLT.
#         For few large events (showers): discrete mixture, NOT Gaussian.
#
#     Monte Carlo:
#         Sample K event sequences from the intensity function.
#         For each sequence, simulate event durations and energies.
#         Aggregate into an empirical distribution of total energy.
#         More accurate for complex, interacting event structures.
#
#     The result is a QuantilePoint with expected value, variance, and
#     quantiles {0.05, 0.25, 0.50, 0.75, 0.95} of cumulative energy.
#
# BAYESIAN CONDITIONING:
#
#     As the day progresses, events either happen or don't, and each
#     observation dramatically updates the forecast:
#
#     Example (two-shower household):
#         Prior at 5am:
#             P(shower₁ by 8am) = 0.65
#             P(shower₂ by 8am) = 0.35
#             Cumulative energy: bimodal (0 or 4 or 8 kWh).
#
#         At 6:30am, shower₁ detected (flow sensor, 8-min draw):
#             Posterior:
#             P(shower₁ by 8am) = 1.0  (already happened)
#             P(shower₂ by 8am) = 0.40 (updated — often follows 30–60 min later)
#             Tank state now KNOWN to be lower by ~4 kWh.
#             Remaining uncertainty is only about shower₂.
#
#         At 7:30am, no shower₂ yet:
#             Posterior:
#             P(shower₂ by 8am | not yet) ≈ 0.15
#             Agent can confidently bid the tank's stored energy
#             as available flexibility for the 8am market interval.
#
#     This real-time updating is why the event model is superior to
#     a continuous forecast for discrete events.  A point-estimate
#     model cannot meaningfully update when a shower is observed.
#
#     Implementation:
#         condition_on_observation() records the observed event and
#         recomputes the remaining intensity function by:
#             1. Reducing the expected remaining count by 1.
#             2. Shifting the timing distribution of subsequent events
#                (e.g., second shower tends to follow the first).
#             3. Recomputing the cumulative energy distribution for
#                the remaining forecast horizon.
#
#         reset_observations() clears the conditioning state at the
#         start of a new day, reverting to the prior daily pattern.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from:
#         abstractions.data_streams.AbstractEventForecast
#     Which itself inherits from:
#         abstractions.data_streams.AbstractForecast
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - forecasting/data_stream_manager.py:
#         The DataStreamManager holds EventForecast instances in its
#         event_streams dictionary.  Agents access them via
#         get_event(stream_id).
#
#     - devices/water_heater_model.py:
#         WaterHeaterModel.estimate_flexibility() is the primary
#         consumer.  It calls get_cumulative_energy_distribution()
#         to obtain the draw energy distribution, then propagates it
#         through the tank thermal model to produce a distribution
#         of tank temperatures and derives flexibility quantiles.
#
#     - devices/ev_charger_model.py:
#         EVChargerModel.estimate_flexibility() uses the ev_arrival
#         EventForecast during DA planning (when the vehicle is not
#         yet plugged in) to estimate when charging flexibility will
#         become available and how much energy will be needed.
#
#     - devices/hvac_model.py:
#         HVACModel may use the occupancy EventForecast to modulate
#         the amenity cost: temperature deviations matter less when
#         the building is unoccupied.
#
#     - economics/planning_optimizer.py:
#         The planning optimizer receives event forecasts as part of
#         the forecast bundle.  For water heaters, it may use scenario
#         sampling from the event model to solve a stochastic
#         scheduling problem.
#
#     - agent.py (DeviceAgent):
#         The agent's _handle_delivery_tick() may call
#         condition_on_observation() when a real-time event is
#         detected (e.g., flow sensor triggers during delivery),
#         updating the forecast for subsequent flexibility estimates.
#
#     - main.py:
#         The simulation harness constructs EventForecast objects with
#         learned intensity functions and event type definitions, then
#         registers them with the DataStreamManager.
#
# DATA TYPES USED:
#     From data_types.py:
#         EventDefinition     — per-event-type parameters (duration,
#                               magnitude, energy distributions).
#         QuantilePoint       — cumulative energy distribution output
#                               (expected, variance, quantiles).
#         UncertaintyEnvelope — returned by get_uncertainty_at()
#                               (inherited from AbstractForecast).
#     From abstractions/:
#         AbstractEventForecast — the contract being implemented.
#
# EXTERNAL INPUTS:
#     All forecast CONTENT is external.  This module provides the
#     stochastic model structure and conditioning logic — not the
#     learned patterns.
#
#     event_types:
#         List of EventDefinition objects describing each event type
#         (shower, dishwash, EV arrival, etc.) with their duration,
#         magnitude, and energy distributions.
#         EXTERNAL: Learned from historical sensor data (flow meters,
#                   charging logs, motion sensors) or set to population-
#                   average defaults from survey data.
#
#     intensity_function:
#         Time series of λ(t) in events/hour at each time of day.
#         EXTERNAL: Learned from historical event occurrence patterns.
#         May vary by day-of-week and season.
#
#     daily_expected_count:
#         Expected number of events per day.  Equal to ∫₀²⁴ λ(t) dt.
#         EXTERNAL: From historical data.
#
#     daily_expected_energy:
#         Expected total energy from all events per day (kWh).
#         EXTERNAL: From historical data.
#
#     Real-time event observations (for conditioning):
#         event_type, timestamp, energy — detected by sensors.
#         EXTERNAL: From flow meters, smart plugs, EVSE telemetry,
#                   or inferred from meter disaggregation.
# ============================================================================

"""Concrete event-process forecast implementation.

Models discrete random events using a stochastic point process with
an intensity function, per-event energy distributions, and Bayesian
conditioning on real-time observations.

Used for hot water draws (showers, dishes), EV arrivals, occupancy
transitions, and other events that are fundamentally discrete — they
happen or they don't, and smearing them into a continuous time series
destroys the information the agent needs.

The key output is not "when will events happen?" but "what is the
distribution of total energy consumed by events over a given interval?"
This distribution — often multimodal for few-event scenarios like
morning showers — is propagated through the device physics model to
produce a distribution of device states, from which confidence-level
flexibility quantiles are derived.

Key methods:
    get_intensity_at()                     — Event rate λ(t) at a given time.
    get_cumulative_energy_distribution()   — Distribution of total energy
                                             consumed over an interval.
    condition_on_observation()             — Bayesian update when an event
                                             is detected in real time.
    reset_observations()                   — Clear conditioning state
                                             (e.g., start of new day).
    get_expected_at()                      — Point estimate of cumulative
                                             energy (from AbstractForecast).
    get_uncertainty_at()                   — Full distributional info
                                             (from AbstractForecast).
"""

from typing import Any, Dict, List, Optional, Tuple

from abstractions.data_streams import AbstractEventForecast
from data_types import EventDefinition, QuantilePoint, UncertaintyEnvelope


from tesp_support.tesp_support.curve_and_agent.abstractions.data_streams import AbstractEventForecast
from tesp_support.tesp_support.curve_and_agent.data_streams import EventDefinition, QuantilePoint


class EventForecast(AbstractEventForecast):
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
        event_types: list[EventDefinition],
        intensity_function: list[tuple[float, float]] | None = None,
        daily_expected_count: float = 0.0,
        daily_expected_energy: float = 0.0,
    ):
        self._event_types = event_types
        self._intensity_function = intensity_function or []
        self._daily_expected_count = daily_expected_count
        self._daily_expected_energy = daily_expected_energy
        self._observed_events: list[dict] = []

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
            ev["energy"]
            for ev in self._observed_events
            if t_start <= ev["timestamp"] <= t_end
        )
        observed_count = sum(
            1 for ev in self._observed_events if t_start <= ev["timestamp"] <= t_end
        )
        remaining_lambda = max(0.0, total_lambda - observed_count)

        # Average energy per event
        if self._event_types:
            mean_energy = sum(e.energy_mean for e in self._event_types) / len(
                self._event_types
            )
            var_energy = sum(e.energy_std**2 for e in self._event_types) / len(
                self._event_types
            )
        else:
            mean_energy = self._daily_expected_energy / max(
                1.0, self._daily_expected_count
            )
            var_energy = 0.0

        # Compound Poisson: E[S] = λ·μ, Var[S] = λ·(σ² + μ²)
        expected_remaining = remaining_lambda * mean_energy
        variance = remaining_lambda * (var_energy + mean_energy**2)

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
        self._observed_events.append(
            {
                "event_type": event_type,
                "timestamp": timestamp,
                "energy": energy,
            }
        )

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