# ============================================================================
# FILE: forecasting/continuous_forecast.py
# PURPOSE: Concrete implementation of forecasts for continuously varying
#          physical quantities (agent function F2 and F3 input).
#
# A continuous forecast provides a time series of point estimates with
# horizon-dependent uncertainty envelopes for variables that always have
# a well-defined value at every point in time.  This is the appropriate
# forecast paradigm for smoothly varying quantities — as opposed to
# discrete random events (showers, EV arrivals), which use the event
# forecast paradigm in event_forecast.py.
#
# VARIABLES REPRESENTED BY CONTINUOUS FORECASTS:
#
#     Weather:
#         outdoor_air_temp    — Primary driver of HVAC load (°F).
#         solar_irradiance    — Drives cooling load and BTM solar output (W/m²).
#         humidity            — Affects latent cooling load (°F dewpoint).
#         wind_speed          — Affects building infiltration rate (m/s).
#
#     Market:
#         electricity_price   — Retail energy price forecast ($/kWh).
#                               Initially from historical data or MO-provided
#                               forecast; updated by informational market
#                               clears via PriceForecastService.
#
#     Device/Building:
#         inlet_water_temp    — Cold water supply temperature (°F).
#                               Slow-moving seasonal quantity.
#         btm_solar_generation— Behind-the-meter PV output (kW).
#                               Derived from solar irradiance + PV specs.
#         household_net_load  — Non-controllable household consumption (kW).
#                               Net of BTM solar, excludes flexible devices.
#
#     Customer Schedules (represented as low-uncertainty forecasts):
#         hvac_setpoint_schedule  — Thermostat program (°F).
#         ev_preferred_soc        — Desired EV charge level (fraction).
#         battery_preferred_soc   — Desired battery reserve level (fraction).
#
#         Schedules are forecast objects with very low (near-zero)
#         uncertainty because they represent customer-declared intent
#         rather than predictions of uncontrollable variables.  Using
#         the same ContinuousForecast class for schedules avoids
#         duplicating the time-series interpolation and querying logic.
#
# FORECAST STRUCTURE:
#
#     Each ContinuousForecast holds:
#
#         series: List[ContinuousDataPoint]
#             Time-ordered list of forecast data points, each containing:
#                 timestamp  — simulation time this point refers to.
#                 lead_time  — seconds from forecast issue time.
#                 value      — point estimate (the "best guess").
#                 sigma      — standard deviation from the uncertainty model.
#                 quantiles  — distribution percentiles (5th, 25th, 50th,
#                              75th, 95th) for non-Gaussian variables.
#
#         uncertainty_model: AbstractUncertaintyModel
#             Governs how σ grows with lead time.  One of:
#                 SaturatingExpUncertaintyModel
#                 PowerLawUncertaintyModel
#                 EmpiricalUncertaintyModel
#             (defined in forecasting/uncertainty_models.py)
#
#     When queried at a specific time via get_at(timestamp):
#         1. The point estimate is interpolated from the series.
#         2. The lead time is computed: τ = timestamp − forecast_issue_time.
#         3. σ = uncertainty_model.sigma_at(τ).
#         4. Quantiles are computed from value ± z_α × σ (Gaussian) or
#            from stored non-Gaussian quantiles if available.
#         5. A ContinuousDataPoint is returned with all fields populated.
#
# FORECAST UPDATES:
#
#     The update() method replaces the entire series with new data.
#     This is called when:
#
#         - A new weather forecast arrives (every 1–6 hours from the
#           weather service).
#         - An informational market clear updates the price forecast
#           (the PriceForecastService calls update() on the price
#           stream after each informational iteration).
#         - The customer changes their thermostat schedule (rare,
#           but the mechanism is the same).
#         - A sensor reading corrects the near-term forecast (e.g.,
#           actual outdoor temperature differs from the weather
#           forecast — the series is re-anchored to the observation).
#
#     After update(), subsequent queries reflect the new data.  Old
#     data points are replaced, not accumulated.
#
# NON-GAUSSIAN DISTRIBUTIONS:
#
#     The Gaussian approximation (value ± z × σ) is appropriate for
#     most weather variables.  However, some variables have non-Gaussian
#     error distributions:
#
#         Electricity prices — heavily right-skewed (price spikes).
#         Solar irradiance  — bimodal on partly cloudy days
#                             (clear sky vs. overcast).
#         Wind speed        — Weibull-distributed.
#
#     For these variables, the quantiles field in ContinuousDataPoint
#     can be populated directly from the external forecast source
#     rather than derived from σ.  The get_uncertainty_at() method
#     returns whichever representation is available — stored quantiles
#     take precedence over Gaussian-derived quantiles.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from:
#         abstractions.data_streams.AbstractContinuousForecast
#     Which itself inherits from:
#         abstractions.data_streams.AbstractForecast
#
#     Uses:
#         abstractions.data_streams.AbstractUncertaintyModel
#             (held as a reference; concrete type injected at construction)
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - forecasting/uncertainty_models.py:
#         Each ContinuousForecast holds a reference to one concrete
#         uncertainty model (SaturatingExp, PowerLaw, or Empirical).
#         The model's sigma_at() is called on every query.
#
#     - forecasting/data_stream_manager.py:
#         The DataStreamManager holds ContinuousForecast instances in
#         its continuous_streams and schedules dictionaries.  Agents
#         access them via get_continuous() and get_schedule().
#
#     - forecasting/price_forecast_service.py:
#         The PriceForecastService may hold or update ContinuousForecast
#         instances for price streams.  After each informational market
#         clear, the service calls update() with new price data.
#
#     - devices/hvac_model.py:
#         HVACModel.estimate_flexibility() and predict_temperature()
#         receive outdoor_air_temp, solar_irradiance, and
#         internal_heat_gain forecasts as ContinuousDataPoint lists
#         extracted from ContinuousForecast objects via get_series().
#
#     - devices/battery_model.py:
#         BatteryModel consumes price forecasts (via the planning
#         optimizer) and BTM solar forecasts to inform charging
#         strategy.
#
#     - economics/planning_optimizer.py:
#         The planning optimizer receives a forecast bundle from the
#         DataStreamManager containing ContinuousForecast series for
#         all relevant variables over the planning horizon.
#
#     - economics/preference_curves.py:
#         The reference price P_0 in the isoelastic curve comes from
#         the price ContinuousForecast's get_at() for the relevant
#         market interval.
#
#     - agent.py (DeviceAgent):
#         generate_preference_curve() (F3) queries the price schedule
#         to obtain P_0.
#         _handle_active() queries weather and schedule forecasts to
#         feed into estimate_flexibility() (F2).
#
#     - main.py:
#         The simulation harness constructs ContinuousForecast objects
#         with appropriate uncertainty models and initial series data,
#         then registers them with the DataStreamManager.
#
# DATA TYPES USED:
#     From data_types.py:
#         ContinuousDataPoint — individual forecast point (timestamp,
#                               lead_time, value, sigma, quantiles)
#         UncertaintyEnvelope — full distributional info at a time
#     From abstractions/:
#         AbstractContinuousForecast — the contract being implemented
#         AbstractUncertaintyModel   — held reference for σ computation
#
# EXTERNAL INPUTS:
#     All forecast CONTENT is external.  This module provides storage,
#     interpolation, and uncertainty computation — not forecasting.
#
#     series (initial and updates):
#         Source varies by variable:
#             Weather:  Weather service API (NWS, ECMWF, commercial).
#             Price:    Historical patterns, MO-provided forecast,
#                       informational market clears.
#             Solar:    Derived from irradiance forecast + PV specs.
#             Net load: Learned model from AMI/meter history.
#             Schedules: Customer thermostat program, EV app, etc.
#
#     uncertainty_model:
#         Injected at construction with calibrated parameters.
#         EXTERNAL: Calibrated from historical forecast verification.
# ============================================================================

"""Concrete continuous-process forecast implementation.

Provides time series of point estimates with horizon-dependent
uncertainty envelopes for smoothly varying physical quantities.
Each forecast holds a reference to an uncertainty model that governs
how confidence intervals widen with lead time.

Used for weather variables (temperature, solar, humidity, wind),
market signals (electricity price), device parameters (inlet water
temperature, BTM solar generation, household net load), and customer
schedules (thermostat setpoint, preferred SOC levels).

Key methods:
    update()              — Replace the forecast series with new data.
    get_at()              — Interpolate forecast at a specific time,
                            with uncertainty computed from lead time.
    get_series()          — Return forecast over an interval, optionally
                            resampled to a given resolution.
    get_expected_at()     — Point estimate only (from AbstractForecast).
    get_uncertainty_at()  — Full distributional info (from AbstractForecast).
"""

from typing import Dict, List, Optional

from abstractions.data_streams import (
    AbstractContinuousForecast,
    AbstractUncertaintyModel,
)
from data_types import ContinuousDataPoint, UncertaintyEnvelope

class ContinuousForecast(AbstractContinuousForecast):
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
        series: list[ContinuousDataPoint] | None = None,
    ):
        self._variable_name = variable_name
        self._unit = unit
        self._uncertainty_model = uncertainty_model
        self._series = series or []

    def update(self, new_series: list[ContinuousDataPoint]) -> None:
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
            sigma = self._uncertainty_model.sigma_at(
                abs(timestamp - self._series[0].timestamp)
            )
            return ContinuousDataPoint(
                timestamp=timestamp, value=self._series[0].value, sigma=sigma
            )
        # Clamp to endpoints
        if timestamp <= self._series[0].timestamp:
            sigma = self._uncertainty_model.sigma_at(0.0)
            return ContinuousDataPoint(
                timestamp=timestamp, value=self._series[0].value, sigma=sigma
            )
        if timestamp >= self._series[-1].timestamp:
            lead = timestamp - self._series[0].timestamp
            sigma = self._uncertainty_model.sigma_at(lead)
            return ContinuousDataPoint(
                timestamp=timestamp, value=self._series[-1].value, sigma=sigma
            )
        # Linear interpolation
        for i in range(len(self._series) - 1):
            t0 = self._series[i].timestamp
            t1 = self._series[i + 1].timestamp
            if t0 <= timestamp <= t1:
                f = (timestamp - t0) / (t1 - t0) if t1 != t0 else 0.0
                val = self._series[i].value + f * (
                    self._series[i + 1].value - self._series[i].value
                )
                lead = timestamp - self._series[0].timestamp
                sigma = self._uncertainty_model.sigma_at(lead)
                return ContinuousDataPoint(timestamp=timestamp, value=val, sigma=sigma)
        return ContinuousDataPoint(timestamp=timestamp)

    def get_series(
        self, t_start: float, t_end: float, resolution: float | None = None
    ) -> list[ContinuousDataPoint]:
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
        return [
            self.get_at(pt.timestamp)
            for pt in self._series
            if t_start <= pt.timestamp <= t_end
        ]