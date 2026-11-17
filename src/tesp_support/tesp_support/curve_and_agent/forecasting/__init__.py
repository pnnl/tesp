# ============================================================================
# FILE: forecasting/__init__.py
# PURPOSE: Package-level exports for all concrete forecasting, uncertainty
#          modeling, constraint handling, and data stream management
#          components.
#
# This package provides the agent's interface to all exogenous
# information about the world outside the device.  If the devices/
# package answers "what is the device doing NOW?" (via simulator reads),
# this package answers "what do we expect the world to do NEXT?"
#
# The package is organized around three forecasting paradigms and the
# manager that ties them together:
#
#     CONTINUOUS paradigm (continuous_forecast.py, uncertainty_models.py):
#         For smoothly varying physical quantities (temperature, price,
#         solar irradiance).  Point forecasts with horizon-dependent
#         uncertainty envelopes.  Uncertainty growth is modeled by
#         pluggable functions (saturating exponential, power law, or
#         empirical lookup).
#
#     EVENT paradigm (event_forecast.py):
#         For discrete random occurrences (showers, EV arrivals,
#         occupancy transitions).  Intensity functions with per-event
#         energy distributions, cumulative energy distributions, and
#         real-time Bayesian conditioning on observations.
#
#     CONSTRAINT paradigm (constraint_stream.py):
#         For hard boundaries that must not be violated (minimum tank
#         temperature, EV departure SOC, battery backup reserve).
#         Binary feasibility checks and continuous slack measurement.
#
#     MANAGEMENT (data_stream_manager.py):
#         Central registry that stores all streams, routes updates,
#         and bundles data for consumption by device models and the
#         planning optimizer.
#
#     PRICE ESTIMATION (price_forecast_service.py):
#         Specialized service that aggregates price information from
#         informational market clears, external forecasts, and
#         historical data into a queryable store with convergence
#         tracking.  Separate from the DataStreamManager because of
#         its unique multi-source, iteration-driven update pattern.
#
# DEPENDENCY RULE:
#     Modules in this package import from:
#       - abstractions/ (the contracts they implement)
#       - data_types.py (shared dataclasses: ContinuousDataPoint,
#         EventDefinition, QuantilePoint, UncertaintyEnvelope)
#       - enums_and_constants.py (DeviceType, ForecastParadigm,
#         MarketType)
#
#     No module in this package imports from devices/, simulators/,
#     markets/, or economics/.  Forecast components are pure data
#     providers — they do not consume device state, market results,
#     or economic decisions.  Information flows one way: from this
#     package outward to the rest of the agent.
#
#     The one conceptual coupling is that the PriceForecastService is
#     updated by the agent's _handle_assessment() method with
#     informational clearing prices — but that update flows INTO
#     this package via the service's update() method, not out of it.
#
# PACKAGE CONTENTS:
#
#     uncertainty_models.py
#         Three pluggable models of how forecast σ grows with lead time:
#
#         SaturatingExpUncertaintyModel — σ(τ) = σ_∞·(1 − e^{−τ/τ_c})
#             Best default for most weather variables.
#
#         PowerLawUncertaintyModel — σ(τ) = min(σ_∞, σ_0 + α·τ^β)
#             Best for solar irradiance and wind speed.
#
#         EmpiricalUncertaintyModel — σ(τ) from lookup table.
#             Best when historical verification data is available
#             (electricity prices, diurnal skill variation).
#
#         Classes:
#             SaturatingExpUncertaintyModel(AbstractUncertaintyModel)
#             PowerLawUncertaintyModel(AbstractUncertaintyModel)
#             EmpiricalUncertaintyModel(AbstractUncertaintyModel)
#
#     continuous_forecast.py
#         Time series of point estimates with horizon-dependent
#         uncertainty envelopes for smoothly varying quantities.
#         Holds a reference to one uncertainty model.  Supports
#         series update, time-point interpolation, interval queries,
#         and non-Gaussian quantile storage.
#
#         Used for weather (temperature, solar, humidity, wind),
#         market signals (electricity price), device parameters
#         (inlet water temp, BTM solar, household net load), and
#         customer schedules (thermostat setpoint, preferred SOC).
#
#         Classes:
#             ContinuousForecast(AbstractContinuousForecast)
#
#     event_forecast.py
#         Stochastic point process model for discrete random events.
#         Intensity function λ(t), per-event energy distributions,
#         cumulative energy distributions, and Bayesian conditioning
#         on real-time observations.
#
#         Used for hot water draws (showers, dishes), EV arrivals,
#         and occupancy transitions.  The key output is the
#         distribution of total energy consumed over an interval —
#         often multimodal for few-event scenarios like morning
#         showers.
#
#         Classes:
#             EventForecast(AbstractEventForecast)
#
#     constraint_stream.py
#         Hard boundaries that the agent must not violate.  Supports
#         continuous constraints (all times), deadline constraints
#         (by a specific time), minimum, maximum, and equality types.
#         Provides binary feasibility checks and continuous slack
#         measurement.
#
#         Used for tank temperature minimum (120°F), EV departure SOC,
#         battery backup reserve, BMS limits, and DSO network limits.
#
#         Classes:
#             ConstraintStream(AbstractConstraintStream)
#
#     data_stream_manager.py
#         Central registry for all forecast, schedule, and constraint
#         streams.  Provides type-safe retrieval by stream ID, routes
#         updates from external sources, and bundles multiple streams
#         into a single dictionary for device models and the planning
#         optimizer.
#
#         Does not generate forecasts — stores, routes, interpolates,
#         and bundles data from external sources.
#
#         Classes:
#             DataStreamManager(AbstractDataStreamManager)
#
#     price_forecast_service.py
#         Specialized price estimate store updated from informational
#         market clears, external forecasts, and historical data.
#         Tracks convergence across iterations and provides complete
#         price trajectories for the planning optimizer.
#
#         Separate from the DataStreamManager because price forecasts
#         have unique multi-source, iteration-driven update semantics
#         and market-type-indexed storage.
#
#         Classes:
#             PriceForecast (data container, no ABC)
#             PriceForecastService(AbstractPriceForecastService)
#
# HOW THIS PACKAGE IS CONSUMED:
#
#     agent.py (DeviceAgent):
#         _handle_active():
#             dsm.get_forecast_bundle() → feeds F2 (flexibility)
#             dsm.get_all_constraints() → feeds F2 (hard limits)
#             dsm.get_schedule('hvac_setpoint_schedule') → feeds F3 (baseline)
#         generate_preference_curve() (F3):
#             pfs.get_price() → P_0 for isoelastic curve
#         formulate_bid() (F4):
#             pfs.get_price() → concurrent market prices for risk assessment
#         _handle_assessment():
#             pfs.update() → push advisory clearing prices
#         _handle_delivery_tick():
#             event_forecast.condition_on_observation() → real-time Bayesian update
#
#     devices/*_model.py:
#         estimate_flexibility() receives the forecast bundle as a Dict.
#         Each model extracts the streams it needs:
#             HVACModel: outdoor_air_temp, solar_irradiance, hvac_setpoint_schedule
#             WaterHeaterModel: hot_water_draw, inlet_water_temp, tank_temp_minimum
#             EVChargerModel: ev_arrival, ev_departure_soc, ev_preferred_soc
#             BatteryModel: electricity_price, btm_solar, household_net_load, soc_reserve
#
#     economics/planning_optimizer.py:
#         Receives the full forecast bundle + constraint list.
#         Uses weather for HVAC trajectory prediction, draws for WH
#         scheduling, prices for battery V_stored computation.
#
# ALL DATA IS EXTERNAL:
#     This package stores and provides access but does not generate,
#     learn, or predict.  Every data point originates from:
#         Weather service API          → temperature, solar, humidity, wind
#         Historical sensor data       → draw patterns, arrival patterns, occupancy
#         Customer input               → schedules, constraints, preferences
#         Building codes               → tank temperature minimum
#         Device specifications        → BMS limits, charge rate taper
#         DSO signals                  → network power limits
#         Market Operator              → clearing prices (via agent)
#         Wholesale market data        → initial price priors
#
# USAGE:
#     Precise import (preferred inside framework):
#         from forecasting.continuous_forecast import ContinuousForecast
#         from forecasting.event_forecast import EventForecast
#         from forecasting.uncertainty_models import SaturatingExpUncertaintyModel
#
#     Convenience import (acceptable in main.py):
#         from forecasting import (
#             ContinuousForecast, EventForecast, ConstraintStream,
#             DataStreamManager, PriceForecastService
#         )
# ============================================================================

"""Forecasting package — the agent's window into the future.

This package provides all forward-looking information the agent needs:
weather forecasts, event predictions, customer schedules, hard
constraints, and price estimates.  It does not generate forecasts —
it stores, routes, interpolates, and distributes data from external
sources to the rest of the agent framework.

Three forecasting paradigms:
    CONTINUOUS — smoothly varying quantities with Gaussian-like uncertainty
                 that grows with lead time.
    EVENT      — discrete random occurrences modeled as stochastic point
                 processes with intensity functions and Bayesian conditioning.
    CONSTRAINT — hard boundaries with binary feasibility checks.

Plus two management components:
    DataStreamManager    — central registry for all streams.
    PriceForecastService — specialized iteration-aware price store.
"""

# -- Uncertainty Models -------------------------------------------------------
from forecasting.uncertainty_models import (
    EmpiricalUncertaintyModel,
    PowerLawUncertaintyModel,
    SaturatingExpUncertaintyModel,
)

# -- Continuous Forecasts -----------------------------------------------------
from forecasting.continuous_forecast import ContinuousForecast

# -- Event Forecasts ----------------------------------------------------------
from forecasting.event_forecast import EventForecast

# -- Constraints --------------------------------------------------------------
from forecasting.constraint_stream import ConstraintStream

# -- Data Stream Manager ------------------------------------------------------
from forecasting.data_stream_manager import DataStreamManager

# -- Price Forecast Service ---------------------------------------------------
from forecasting.price_forecast_service import (
    PriceForecast,
    PriceForecastService,
)

__all__ = [
    # Uncertainty models
    "SaturatingExpUncertaintyModel",
    "PowerLawUncertaintyModel",
    "EmpiricalUncertaintyModel",
    # Continuous forecasts
    "ContinuousForecast",
    # Event forecasts
    "EventForecast",
    # Constraints
    "ConstraintStream",
    # Stream management
    "DataStreamManager",
    # Price forecasting
    "PriceForecast",
    "PriceForecastService",
]