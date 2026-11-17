# ============================================================================
# FILE: markets/dso_load_engine.py
# PURPOSE: Concrete implementation of the DSO's inflexible load estimation
#          engine.
#
# This module estimates the aggregate non-price-responsive electrical
# load on a distribution feeder that must be bid into the retail market
# on behalf of all customers who either:
#     - Have no controllable devices (no device agent)
#     - Have controllable devices but also consume inflexible load
#       (lighting, refrigerators, cooking, plug loads, etc.)
#     - Are non-participating customers entirely
#
# The DSO bids this load as PERFECTLY INELASTIC DEMAND — a vertical
# line on the price-quantity curve.  The load will be consumed
# regardless of price.  It is the Market Operator's job to ensure
# sufficient supply is procured to serve it.
#
# THE ESTIMATION EQUATION:
#
#     Q_inflexible = Q_total_forecast
#                  - Q_flexible_committed
#                  + Q_losses
#                  - Q_btm_solar_export
#
#     Where:
#         Q_total_forecast     = forecasted gross feeder load (kW).
#                                Includes all customers, all end uses.
#         Q_flexible_committed = sum of all device agent cleared or bid
#                                quantities (kW).  Subtracted to avoid
#                                double-counting — these devices are
#                                already bidding their own load.
#         Q_losses             = distribution losses on the feeder (kW).
#                                = Q_total_forecast × loss_factor.
#                                Losses are load-dependent (I²R) and
#                                location-dependent.
#         Q_btm_solar_export   = aggregate behind-the-meter solar
#                                generation on the feeder (kW).
#                                Net export reduces the load the DSO
#                                must procure supply for.
#
# CONVERGENCE ACROSS INFORMATIONAL ITERATIONS:
#     In the first DA informational iteration, the DSO may not yet know
#     Q_flexible_committed (agents are bidding concurrently).  The DSO
#     uses a historical average for the flexible fraction, resulting in
#     some double-counting.  In subsequent iterations, the MO provides
#     the sum of agent cleared quantities from the previous iteration,
#     allowing the DSO to refine its estimate.  By the binding iteration,
#     double-counting is minimal because:
#         1. Agent bids have converged (stable Q_flexible_committed).
#         2. The DSO has subtracted them accurately.
#
#     For real-time (RT) markets, the DSO has an even better tool:
#     substation metering.  The actual feeder load is measured, the
#     actual flexible device power is known, and the DSO can compute
#     Q_inflexible_actual = Q_substation_actual - Q_flexible_actual.
#     This real-time correction feeds into the next RT cycle's bid.
#
# EXTERNAL DATA SOURCES:
#     This module does not generate any of its input data.  All inputs
#     are EXTERNAL and must be provided by the simulation harness or
#     by other DSO systems:
#
#     Q_total_forecast:
#         Source: Weather-driven load forecast model built from
#                 historical AMI (smart meter) data + outdoor
#                 temperature forecast + calendar features (day of
#                 week, holidays, seasonal patterns).
#         Update frequency: Every market cycle (RT: 5 min, DA: hourly).
#         Typical accuracy: ±2-5% at the feeder level (law of large
#                          numbers across hundreds of customers).
#
#     Q_flexible_committed:
#         Source: Market Operator's own records.  The MO aggregates
#                 all agent bids or cleared quantities.  Provided to
#                 the DSO via MarketOperator.get_total_flexible_committed().
#         INTERNAL to the market system (not external sensor data).
#         Available after the first market iteration clears.
#
#     Q_btm_solar_export:
#         Source: Solar generation forecast model built from solar
#                 irradiance forecast + aggregate PV system specs for
#                 all rooftop installations on the feeder (capacity,
#                 orientation, tilt, inverter efficiency).
#         Update frequency: Every 1-6 hours from weather service;
#                          real-time from inverter telemetry if available.
#
#     loss_factor:
#         Source: Distribution network power flow model.  Uses feeder
#                 topology, line impedances, transformer ratings, and
#                 expected loading level to compute the fraction of
#                 substation energy lost to resistive heating in the
#                 distribution network.
#         Typical values: 3-7% at normal loading, up to 10-15% at peak.
#         Update frequency: Recomputed when loading conditions change
#                          significantly.  May be a static lookup
#                          indexed by total feeder load level.
#
#     substation_load_actual (for real-time correction):
#         Source: Substation SCADA / metering.  Real-time measurement
#                 of total feeder power flow at the distribution
#                 substation transformer.
#         Update frequency: Every few seconds (SCADA scan rate).
#         Used during RT delivery to close the loop on forecast error.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from: abstractions.market_operator.AbstractDSOLoadEstimationEngine
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - markets/market_operator.py: The MarketOperator receives the
#       inflexible load bid produced by this engine.  The MO also
#       provides Q_flexible_committed back to this engine to avoid
#       double-counting.
#     - markets/market_communication.py: Not used directly.  The DSO
#       bid is passed to the MO through a direct method call
#       (submit_dso_inflexible_bid), not through the agent communication
#       interface.
#     - data_types.py: Uses the DSOInflexibleLoadBid dataclass to
#       package the bid with its component breakdown.
#     - main.py: The simulation harness is responsible for calling
#       estimate_inflexible_load() at the appropriate time before each
#       market clearing, and for providing the external input data.
#
# NOT CONSUMED BY:
#     Device agents do not interact with this module.  They are unaware
#     of the inflexible load bid.  The seam between flexible and
#     inflexible load is managed entirely within the MO and DSO.
# ============================================================================

"""Concrete DSO inflexible load estimation engine.

Estimates aggregate non-controllable load for a distribution feeder and
packages it as a perfectly inelastic demand bid for the retail market.
The DSO is the balancing responsible party for inflexible load forecast
errors — individual customers are not penalized for the inherent
unpredictability of turning on a toaster.

Key methods:
    estimate_inflexible_load()  — Compute the inflexible bid for a market interval.
    update_with_metering()      — Real-time correction from substation SCADA.
"""

from typing import Any, Dict, Optional, Tuple

from abstractions.market_operator import AbstractDSOLoadEstimationEngine
from data_types import BidPoint

class DSOLoadEstimationEngine(AbstractDSOLoadEstimationEngine):
    """Estimates aggregate inflexible load for a feeder or pricing zone.

    Uses substation metering, AMI data, weather forecasts, and network
    models to produce the inflexible load bid that the DSO submits to
    the MO on behalf of all non-participating and inflexible load.

    EXTERNAL DATA SOURCES:
        - Substation real-time metering: actual feeder load
        - AMI / smart meter historical data: per-customer load profiles
        - Weather forecast: temperature, solar, humidity
        - Network loss model: topology, impedances, loading-dependent losses
        - BTM solar aggregate: estimated total rooftop solar on feeder
        - Flexible device commitments: sum of agent bids/clears
          (from MO's own records)

    Args:
        feeder_id: Which feeder this engine serves.
    """

    def __init__(self, feeder_id: str):
        self._feeder_id = feeder_id
        self._correction_factor = 1.0
        self._last_predicted_inflexible = None
        self._last_timestamp = 0.0

    def estimate_inflexible_load(
        self,
        interval: tuple[float, float],
        total_load_forecast: float,
        flexible_committed: float,
        btm_solar_forecast: float,
        loss_factor: float,
    ) -> DSOInflexibleLoadBid:
        """Compute the inflexible load bid for a market interval.

        Q_inflexible = total_load_forecast
                     - flexible_committed
                     + losses
                     - btm_solar_export

        Args:
            interval: Time interval to estimate for.
            total_load_forecast: Forecasted total feeder load (kW).
                EXTERNAL: From substation metering + forecast model.
            flexible_committed: Sum of all device agent flexible
                commitments for this interval (kW).
                INTERNAL: From MO's aggregation of agent bids/clears.
            btm_solar_forecast: Forecasted aggregate BTM solar
                generation on this feeder (kW).
                EXTERNAL: From solar forecast model.
            loss_factor: Distribution loss factor (fraction, e.g., 0.05).
                EXTERNAL: From network loss model.

        Returns:
            DSOInflexibleLoadBid with the computed quantity.
        """
        losses = total_load_forecast * loss_factor
        q_inflexible = (
            total_load_forecast - flexible_committed + losses - btm_solar_forecast
        )
        # Apply correction factor from metering feedback
        q_inflexible *= self._correction_factor
        self._last_predicted_inflexible = q_inflexible

        return DSOInflexibleLoadBid(
            feeder_id=self._feeder_id,
            quantity=q_inflexible,
            interval=interval,
            components={
                "total_forecast": total_load_forecast,
                "flexible": flexible_committed,
                "solar": btm_solar_forecast,
                "losses": losses,
            },
        )

    def update_with_metering(
        self, substation_load_actual: float, flexible_actual: float, timestamp: float
    ) -> None:
        """Update estimation model with real-time metering data.

        Called during real-time market operation. Allows the DSO to
        correct its forecast based on actual observed load.

        Args:
            substation_load_actual: Measured total feeder load (kW).
                EXTERNAL: From substation SCADA/metering.
            flexible_actual: Sum of actual device agent power (kW).
                INTERNAL: From MO's metering of device agents.
            timestamp: Measurement time.
        """
        actual_inflexible = substation_load_actual - flexible_actual
        if not hasattr(self, "_correction_factor"):
            self._correction_factor = 1.0
            self._last_predicted_inflexible = None
        if (
            self._last_predicted_inflexible is not None
            and self._last_predicted_inflexible > 0
        ):
            self._correction_factor = (
                actual_inflexible / self._last_predicted_inflexible
            )
        self._last_timestamp = timestamp
