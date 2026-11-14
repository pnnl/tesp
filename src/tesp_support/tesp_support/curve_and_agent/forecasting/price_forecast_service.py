# ============================================================================
# FILE: forecasting/price_forecast_service.py
# PURPOSE: Concrete implementation of the central price forecast store
#          that maintains and distributes evolving price estimates
#          across the agent framework.
#
# The PriceForecastService is a cross-cutting shared resource that
# aggregates price information from multiple sources and makes it
# available to every agent function that needs forward-looking price
# data.  It is the agent's answer to "what do I think electricity
# will cost at time T in market M?"
#
# WHY A DEDICATED SERVICE (NOT JUST ANOTHER CONTINUOUS FORECAST):
#
#     Price forecasts are structurally different from weather forecasts
#     in several ways that justify a dedicated service:
#
#     1. MULTIPLE UPDATE SOURCES:
#         A weather forecast comes from one source (weather service)
#         and is updated on a fixed schedule (every 1–6 hours).
#         A price forecast is updated from multiple, asynchronous sources:
#             - Informational market clears (primary, highest quality)
#             - External wholesale market price publications
#             - Historical pattern-based priors
#             - MO-provided indicative forecasts
#         The service must arbitrate between these sources, preferring
#         more recent and higher-confidence data.
#
#     2. MARKET-TYPE INDEXING:
#         Weather forecasts are indexed by time alone ("what's the
#         temperature at 3pm?").  Price forecasts are indexed by
#         market type AND time ("what's the RT energy price at 3pm?"
#         vs. "what's the DA energy price for the 3pm hour?").
#         Different markets have different price dynamics, different
#         update schedules, and different uncertainty profiles.
#
#     3. ITERATION-DRIVEN CONVERGENCE:
#         Informational market iterations produce a sequence of
#         improving price estimates for the same future interval.
#         The service tracks this convergence history (iteration
#         number, price at each iteration) and computes confidence
#         metrics that feed into advisory commitment weighting on
#         the flexibility ledger.
#
#     4. TRAJECTORY ACCESS:
#         The planning optimizer needs not just a single price at
#         a single time, but a complete price TRAJECTORY over the
#         planning horizon (e.g., 24 hourly prices for DA planning).
#         The service provides get_trajectory() which assembles this
#         from its per-interval records.
#
# PRICE FORECAST LIFECYCLE:
#
#     For a typical DA market cycle with 3 informational iterations:
#
#     Before any iteration:
#         Source: Historical prior or external wholesale forecast.
#         Confidence: Low (0.1–0.3).
#         The planning optimizer uses this as its initial price
#         trajectory — it's a rough guess but better than nothing.
#
#     After informational iteration 1:
#         Source: First advisory clearing prices (24 hourly values).
#         Confidence: Low-moderate (0.2–0.4).
#         Prices reflect the market's first collective estimate.
#         The planning optimizer re-runs with updated prices.
#         V_stored (for batteries) improves.
#
#     After informational iteration 2:
#         Source: Second advisory clearing prices.
#         Confidence: Moderate-high (0.5–0.7).
#         Prices are converging — agents have adjusted bids.
#         The planning optimizer re-runs again.
#         Bid formulation uses tighter price focus regions.
#
#     After informational iteration 3:
#         Source: Third advisory clearing prices.
#         Confidence: High (0.8–0.95).
#         Prices are nearly stable.  One more iteration to binding.
#
#     After binding clear:
#         The binding price replaces the advisory.  Confidence = 1.0.
#         This price is now the reference for RT market bidding
#         during the corresponding DA delivery interval.
#
# DATA STRUCTURE:
#
#     The service stores a dictionary of PriceForecast objects, keyed
#     by (market_type, interval) tuples:
#
#         key: (MarketType.DA_ENERGY, (t_start, t_end))
#         value: PriceForecast
#             price_estimate: 0.14           ($/kWh)
#             confidence: 0.85
#             source: 'informational_clear'
#             iteration: 3
#             history: [(1, 0.12), (2, 0.13), (3, 0.14)]
#
#     Multiple market types can have forecasts for overlapping time
#     intervals — the DA price for 3pm and the RT price for 3pm are
#     separate entries because they represent different products with
#     different clearing dynamics.
#
# CONSUMERS OF THE PRICE FORECAST:
#
#     F3 (Preference Curve Generation):
#         The reference price P_0 that anchors the isoelastic curve
#         is obtained from get_price().  A well-calibrated P_0 ensures
#         that the curve's baseline quantity Q_0 corresponds to the
#         expected market clearing price, so the agent's demand
#         response is centered on realistic conditions.
#
#     F4 (Bid Formulation):
#         Risk-adjusted bidding uses price forecasts for CONCURRENT
#         markets to estimate the probability that capacity committed
#         to one market will need to be displaced by another.  For
#         example, when bidding into regulation, the agent estimates
#         the RT energy price during the regulation delivery window
#         to assess the displacement cost if RT obligations conflict.
#
#     Planning Optimizer:
#         get_trajectory() provides the complete price trajectory
#         over the planning horizon.  For batteries, this is the
#         PRIMARY input — it drives V_stored, which drives every
#         charge/discharge decision.  For HVAC, it drives the
#         pre-conditioning schedule.  For EV, it drives the charge
#         scheduling.
#
#     Flexibility Ledger (indirectly):
#         Advisory commitments on the ledger carry the cleared_price
#         from the price forecast.  The ledger's economic availability
#         (Tier 3) uses these prices to compute displacement costs.
#         Better price forecasts → more accurate displacement costs →
#         better oversubscription decisions.
#
#     Convergence Tracking:
#         The advisory_confidence reported back to the market object
#         (and from there to the flexibility ledger) is derived from
#         the price history stored in the service.  If prices are
#         converging (small iteration-to-iteration deltas), confidence
#         is high.
#
# CLASSES IN THIS FILE:
#
#     PriceForecast
#         Data container for a single price estimate for a specific
#         market type and time interval.  Stores the point estimate,
#         confidence, source, iteration number, and the full history
#         of estimates across informational iterations.
#
#         Not an ABC — this is a simple concrete data structure
#         local to the service.
#
#     PriceForecastService(AbstractPriceForecastService)
#         The concrete service implementation.  Methods:
#
#             update(market_type, interval, price, confidence, source, iteration)
#                 Store or update a price estimate.  Called after each
#                 informational clear by the agent's _handle_assessment()
#                 method, and when external forecasts arrive.
#
#             get_forecast(market_type, interval) → PriceForecast | None
#                 Retrieve the full forecast record for a specific
#                 market-interval pair.  Includes history and confidence.
#
#             get_price(market_type, interval, default) → float
#                 Convenience: just the point estimate.  Used by F3
#                 for P_0 calibration.
#
#             get_trajectory(market_type, t_start, t_end, resolution) → List
#                 Assemble a price trajectory over a planning horizon.
#                 Returns a list of ((t_start, t_end), price) tuples at
#                 the specified resolution (default: 1 hour for DA,
#                 5 minutes for RT).  Used by the planning optimizer.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     PriceForecastService inherits from:
#         abstractions.price_forecast_service.AbstractPriceForecastService
#
#     PriceForecast has no abstract base — it is a local data structure.
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - agent.py (DeviceAgent):
#         _handle_assessment():
#             After each informational clear, calls update() with the
#             advisory clearing price for each interval.
#         generate_preference_curve() (F3):
#             Calls get_price() to obtain P_0 (reference price).
#         formulate_bid() (F4):
#             Calls get_price() for concurrent market intervals to
#             estimate displacement probabilities.
#
#     - economics/planning_optimizer.py:
#         The planning optimizer receives its price trajectory from
#         get_trajectory().  This is the primary input for battery
#         V_stored computation and pre-conditioning schedules.
#
#     - economics/flexibility_ledger.py:
#         Advisory commitments carry the cleared_price obtained from
#         this service.  The ledger does not call the service directly —
#         the price is passed through by the agent during update_advisory().
#
#     - forecasting/continuous_forecast.py:
#         The price forecast service is SEPARATE from the continuous
#         forecast for electricity price (if one exists).  The
#         continuous forecast provides a raw external forecast with
#         uncertainty bands.  The price forecast service provides the
#         best available estimate integrating informational clears
#         (which are higher quality than any external forecast).
#         They may coexist: the continuous forecast serves as the
#         prior before any informational iteration; the service
#         overrides it with advisory data as iterations proceed.
#
#     - forecasting/data_stream_manager.py:
#         The DataStreamManager may hold a continuous electricity_price
#         stream (the external forecast), but the PriceForecastService
#         is a separate object owned directly by the DeviceAgent.
#         This separation reflects their different update patterns
#         and access semantics.
#
#     - main.py:
#         The PriceForecastService is instantiated inside the
#         DeviceAgent during initialize() — it is not constructed
#         externally.  However, the simulation harness may seed it
#         with initial price estimates via the agent's interface.
#
# DATA TYPES USED:
#     From abstractions/:
#         AbstractPriceForecastService — the contract being implemented
#     From enums_and_constants.py:
#         MarketType — keys the forecast store by market product
#
# EXTERNAL INPUTS:
#     Informational clearing prices:
#         INTERNAL: From ClearingResult.cleared_price, passed by the
#         agent's _handle_assessment() after each informational iteration.
#         EXTERNAL origin: Market Operator clearing computation.
#
#     External price forecasts:
#         EXTERNAL: From wholesale market data services, MO-provided
#         indicative forecasts, or historical pattern models.
#         Pushed via update() by the simulation harness or a
#         forecasting subsystem.
#
#     Historical price data (for priors):
#         EXTERNAL: From historical market records.
#         Used to seed the service before any informational iteration
#         occurs.  The prior is progressively overwritten by advisory
#         data as iterations proceed.
# ============================================================================

"""Concrete price forecast service — the central price estimate store.

Aggregates price information from informational market clears, external
forecasts, and historical data into a single queryable store.  Provides
point estimates, confidence levels, convergence history, and complete
price trajectories over planning horizons.

Unlike a raw weather forecast that comes from one source on a fixed
schedule, price forecasts are updated asynchronously from multiple
sources with increasing confidence as informational market iterations
converge.  This service tracks that convergence and makes the best
available estimate accessible to every agent function that needs it.

Classes:
    PriceForecast         — Data container for one market-interval estimate
                            (price, confidence, source, iteration history).
    PriceForecastService  — The queryable store.  update(), get_price(),
                            get_forecast(), get_trajectory().
"""

from typing import Dict, List, Optional, Tuple

from abstractions.price_forecast_service import AbstractPriceForecastService
from enums_and_constants import MarketType


class PriceForecast:
    """Price forecast for a specific market type and time interval.

    Attributes:
        market_type: Which market's price this forecasts.
        interval: (start, end) of the interval.
        price_estimate: Current best estimate ($/kWh or $/kW).
        confidence: How confident the estimate is (0–1).
        source: Where the estimate came from.
        iteration: Which informational iteration produced it.
        history: List of (iteration, price) showing convergence.
    """

    def __init__(
        self,
        market_type: MarketType,
        interval: tuple[float, float],
        price_estimate: float = 0.0,
        confidence: float = 0.0,
        source: str = "prior",
        iteration: int = 0,
    ):
        self.market_type = market_type
        self.interval = interval
        self.price_estimate = price_estimate
        self.confidence = confidence
        self.source = source
        self.iteration = iteration
        self.history: list[tuple[int, float]] = []


class PriceForecastService:
    """Central service for maintaining price forecasts across all markets.

    Updated by informational market clears and external forecast sources.
    Consumed by bid formulation, risk assessment, preference curve
    calibration, and the planning optimizer.
    """

    def __init__(self):
        self._forecasts: dict[
            tuple[MarketType, tuple[float, float]], PriceForecast
        ] = {}

    def update(
        self,
        market_type: MarketType,
        interval: tuple[float, float],
        price: float,
        confidence: float,
        source: str,
        iteration: int = 0,
    ) -> None:
        """Update the price forecast for a market-interval combination.

        Called after each informational clear, or when an external
        price forecast is received.

        Args:
            market_type: Which market.
            interval: Time interval this price applies to.
            price: Price estimate ($/kWh).
                INTERNAL: From ClearingResult.cleared_price after
                    informational iteration.
                OR EXTERNAL: From wholesale market data, MO forecast.
            confidence: Confidence in this estimate (0–1).
                INTERNAL: From convergence tracker.
            source: Where this came from ('informational_clear',
                'external', 'historical').
            iteration: Iteration number (for informational clears).
        """
        key = (market_type, interval)
        if key in self._forecasts:
            fc = self._forecasts[key]
            fc.history.append((iteration, price))
            fc.price_estimate = price
            fc.confidence = confidence
            fc.source = source
            fc.iteration = iteration
        else:
            fc = PriceForecast(
                market_type=market_type,
                interval=interval,
                price_estimate=price,
                confidence=confidence,
                source=source,
                iteration=iteration,
            )
            fc.history.append((iteration, price))
            self._forecasts[key] = fc

    def get_forecast(
        self, market_type: MarketType, interval: tuple[float, float]
    ) -> PriceForecast | None:
        """Get the price forecast for a specific market and interval.

        Args:
            market_type: Which market.
            interval: Time interval.

        Returns:
            PriceForecast or None if no forecast exists.
        """
        return self._forecasts.get((market_type, interval))

    def get_price(
        self,
        market_type: MarketType,
        interval: tuple[float, float],
        default: float = 0.0,
    ) -> float:
        """Convenience: get the point estimate price.

        Args:
            market_type: Which market.
            interval: Time interval.
            default: Value to return if no forecast exists.

        Returns:
            Price estimate or default.
        """
        fc = self.get_forecast(market_type, interval)
        if fc is not None:
            return fc.price_estimate
        return default

    def get_trajectory(
        self,
        market_type: MarketType,
        t_start: float,
        t_end: float,
        resolution: float = 3600.0,
    ) -> list[tuple[tuple[float, float], float]]:
        """Get a price trajectory over a planning horizon.

        Used by the planning optimizer to optimize battery schedules
        and pre-conditioning strategies.

        Args:
            market_type: Which market.
            t_start: Start of horizon.
            t_end: End of horizon.
            resolution: Interval length (seconds).

        Returns:
            List of (interval, price_estimate) tuples.
        """
        result = []
        t = t_start
        while t < t_end:
            interval = (t, t + resolution)
            fc = self.get_forecast(market_type, interval)
            if fc is not None:
                result.append((interval, fc.price_estimate))
            t += resolution
        return result
