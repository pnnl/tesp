# ============================================================================
# FILE: forecasting/uncertainty_models.py
# PURPOSE: Concrete implementations of forecast uncertainty models that
#          define how forecast standard deviation (σ) grows with lead
#          time (τ).
#
# Every continuous-process forecast (temperature, price, solar irradiance,
# etc.) carries an uncertainty model that governs the width of its
# confidence intervals as a function of how far into the future the
# forecast looks.  Near-term forecasts are precise; far-future forecasts
# approach climatological uncertainty.
#
# This module provides three functional forms, each suited to different
# data availability and accuracy requirements:
#
# THREE UNCERTAINTY GROWTH MODELS:
#
#     SaturatingExpUncertaintyModel
#         σ(τ) = σ_∞ · (1 − e^{−τ/τ_c})
#
#         Parameters:
#             sigma_inf (float): Climatological standard deviation —
#                 the maximum possible uncertainty, representing what
#                 you'd have with no forecast at all, just knowing the
#                 season and location.  Units match the forecast variable
#                 (e.g., °F for temperature, $/kWh for price).
#                 EXTERNAL: Calibrated from historical data.
#
#             tau_c (float): Correlation time constant (seconds) — how
#                 quickly forecast skill decays toward climatology.
#                 A shorter τ_c means skill degrades faster.
#                 EXTERNAL: Calibrated from forecast verification data.
#
#         Behavior:
#             τ = 0:     σ = 0 (perfect knowledge of current state)
#             τ = τ_c:   σ ≈ 0.63 × σ_∞ (63% of max uncertainty)
#             τ → ∞:     σ → σ_∞ (no forecast skill, climatology only)
#
#         Best for:
#             General-purpose default.  Physically sensible — uncertainty
#             is bounded by climate variability.  One function covers the
#             full range from nowcast to long-range.  Good fit for
#             temperature, humidity, and other weather variables.
#
#     PowerLawUncertaintyModel
#         σ(τ) = min(σ_∞, σ_0 + α · τ^β)
#
#         Parameters:
#             sigma_0 (float): Observation/measurement uncertainty at
#                 τ = 0.  Accounts for sensor noise and initial-condition
#                 error.  Often small (e.g., 0.5°F for temperature).
#                 EXTERNAL: From instrument specifications.
#
#             alpha (float): Growth rate coefficient.  Controls how
#                 fast uncertainty grows with lead time.
#                 EXTERNAL: Calibrated from forecast verification.
#
#             beta (float): Growth exponent.  Typical values:
#                 0.5: diffusive growth (√τ), characteristic of chaotic
#                      systems at short lead times.
#                 1.0: linear growth, characteristic of systematic
#                      drift errors.
#                 EXTERNAL: From forecast error analysis.
#
#             sigma_inf (float): Climatological cap, same as above.
#                 EXTERNAL: From historical data.
#
#         Behavior:
#             τ = 0:     σ = σ_0 (measurement noise)
#             τ small:   σ ≈ σ_0 + α·τ^β (power-law growth)
#             τ large:   σ = σ_∞ (capped at climatology)
#
#         Best for:
#             When short-term and long-term forecast error dynamics
#             differ and the saturating exponential doesn't capture
#             the shape well.  Particularly useful for solar irradiance
#             (where cloud transients cause √τ-like growth at short
#             horizons) and wind speed.
#
#     EmpiricalUncertaintyModel
#         σ(τ) interpolated from a lookup table of (lead_time, sigma) pairs.
#
#         Parameters:
#             lead_time_sigma_table (List[Tuple[float, float]]): Ordered
#                 list of (lead_time_seconds, sigma) pairs.  The model
#                 linearly interpolates between points.
#                 EXTERNAL: Calibrated from historical forecast
#                 verification data — actual forecast errors binned
#                 by lead time.
#
#         Behavior:
#             Exactly matches the provided table at the given lead
#             times; linearly interpolates between them.  No functional
#             form assumption.
#
#         Best for:
#             When historical forecast verification data is available
#             and the error structure doesn't fit a simple parametric
#             model.  Captures nonlinear features like diurnal cycles
#             in forecast skill (e.g., temperature forecasts are more
#             accurate during stable nighttime hours and less accurate
#             during convectively active afternoons).  Also appropriate
#             for electricity price forecasts, which have highly non-
#             Gaussian, regime-dependent error structures.
#
# HOW UNCERTAINTY MODELS ARE CONSUMED:
#
#     Each ContinuousForecast (in forecasting/continuous_forecast.py)
#     holds a reference to one uncertainty model.  When the agent
#     queries a forecast at a future time, the forecast computes:
#
#         1. The point estimate (interpolated from the forecast series).
#         2. The lead time (query time − forecast issue time).
#         3. σ = uncertainty_model.sigma_at(lead_time).
#         4. Confidence intervals: value ± z_α × σ.
#         5. Quantiles (if the distribution type is known).
#
#     The resulting uncertainty envelope propagates through:
#
#         F2 (Flexibility Estimation):
#             Weather uncertainty → uncertain thermal load → uncertain
#             flexibility range.  The agent shrinks the flexibility
#             envelope by the forecast uncertainty, with the customer
#             preference k controlling how much shrinkage to apply:
#                 k → 0: full uncertainty margin (conservative)
#                 k → 1: minimal margin (aggressive)
#
#         F4 (Bid Formulation):
#             Price forecast uncertainty → risk in oversubscription
#             calculations.  Wider price uncertainty → more conservative
#             displacement decisions.
#
#         Planning Optimizer:
#             Weather and price uncertainty over the 24-hour horizon
#             affect the confidence in the optimal schedule.  The
#             planner may use quantile-based robust optimization when
#             uncertainty is high.
#
# TYPICAL CALIBRATED PARAMETERS BY FORECAST STREAM:
#
#     ┌─────────────────────┬────────┬──────────┬──────────────────────┐
#     │ Forecast Stream     │ σ_∞    │ τ_c      │ Notes                │
#     ├─────────────────────┼────────┼──────────┼──────────────────────┤
#     │ Outdoor air temp    │ 8–12°F │ 18–36 hr │ NWP verification     │
#     │ Solar irradiance    │ 200–   │ 4–8 hr   │ Highly variable;     │
#     │                     │ 300W/m²│          │ cloud transients     │
#     │ Humidity (dewpoint) │ 6–10°F │ 18–30 hr │ Similar to temp      │
#     │ Wind speed          │ 3–5m/s │ 6–12 hr  │ Lower predictability │
#     │ Electricity price   │ $0.02– │ 2–6 hr   │ Regime-dependent;    │
#     │                     │ 0.05   │          │ spikes hard to fcst  │
#     │ Inlet water temp    │ 5–8°F  │ ~720 hr  │ Quasi-static         │
#     │                     │        │(seasonal)│ (changes weekly)     │
#     └─────────────────────┴────────┴──────────┴──────────────────────┘
#
# RELATIONSHIP TO ABSTRACTIONS:
#     All three classes inherit from:
#         abstractions.data_streams.AbstractUncertaintyModel
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - forecasting/continuous_forecast.py:
#         Each ContinuousForecast holds a reference to one uncertainty
#         model.  The model's sigma_at() is called whenever the forecast
#         is queried at a future time to compute confidence intervals.
#
#     - main.py:
#         Uncertainty models are constructed with calibrated parameters
#         during simulation setup and injected into ContinuousForecast
#         objects.  The parameters come from external calibration data
#         (historical forecast verification) or reasonable defaults.
#
#     - forecasting/data_stream_manager.py:
#         The DataStreamManager does not interact with uncertainty models
#         directly — it holds ContinuousForecast objects which internally
#         hold uncertainty models.
#
#     - devices/*_model.py:
#         Device models do not interact with uncertainty models directly.
#         They receive forecast data (with uncertainty already computed)
#         through the forecasts dictionary passed to estimate_flexibility().
#
# DATA TYPES USED:
#     From abstractions/:
#         AbstractUncertaintyModel — the contract being implemented
#
# EXTERNAL INPUTS:
#     All parameters for all three models are EXTERNAL — they must be
#     calibrated from historical forecast verification data or set to
#     reasonable defaults based on the forecast variable type and the
#     geographic/climate context of the simulation.
#
#     The module itself does not perform calibration.  Parameter values
#     are provided at construction time by the simulation harness
#     (main.py) or a configuration file.
# ============================================================================

"""Concrete forecast uncertainty models — how σ grows with lead time.

Three implementations covering the spectrum from simple parametric
models to fully empirical lookup tables:

    SaturatingExpUncertaintyModel — one-parameter exponential saturation.
        Best default for most weather variables.

    PowerLawUncertaintyModel — flexible power-law growth with cap.
        Best for variables with distinct short-term and long-term error
        dynamics (solar irradiance, wind speed).

    EmpiricalUncertaintyModel — lookup table with linear interpolation.
        Best when historical verification data is available and the
        error structure is complex (electricity prices, diurnal skill
        variation).

Each model is injected into a ContinuousForecast at construction time
and called whenever the forecast is queried at a future time to compute
the appropriate confidence interval width.
"""

from typing import Any, Dict, List, Tuple

from abstractions.data_streams import AbstractUncertaintyModel

from tesp_support.tesp_support.curve_and_agent.abstractions.data_streams import AbstractUncertaintyModel


class UncertaintyModel(AbstractUncertaintyModel):
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

    def __init__(self, model_type: str, params: dict):
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
            return min(sigma_inf, sigma_0 + alpha * (lead_time**beta))

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


class SaturatingExpUncertaintyModel(AbstractUncertaintyModel):
    """σ(τ) = σ_∞ · (1 − e^{−τ/τ_c})"""
    def sigma_at(self, lead_time: float) -> float:
        raise NotImplementedError

class PowerLawUncertaintyModel(AbstractUncertaintyModel):
    """σ(τ) = min(σ_∞, σ_0 + α·τ^β)"""
    def sigma_at(self, lead_time: float) -> float:
        raise NotImplementedError

class EmpiricalUncertaintyModel(AbstractUncertaintyModel):
    """σ(τ) interpolated from a lookup table."""
    def sigma_at(self, lead_time: float) -> float:
        raise NotImplementedError