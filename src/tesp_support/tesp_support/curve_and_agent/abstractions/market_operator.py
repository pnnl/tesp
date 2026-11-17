# ============================================================================
# FILE: abstractions/market_operator.py
# PURPOSE: Abstract base classes for the Market Operator (MO) and the
#          DSO's inflexible load estimation engine.
#
# Contains two ABCs:
#
#     AbstractMarketOperator
#         The entity that receives bids from device agents and the DSO,
#         clears the retail market, and propagates cleared prices.
#         Supports both informational and binding clearing iterations.
#
#     AbstractDSOLoadEstimationEngine
#         Estimates aggregate inflexible load for a feeder by combining
#         substation metering, weather-driven forecasts, network loss
#         models, and BTM solar estimates, then subtracting flexible
#         load already covered by device agent bids.
#
# These two classes are co-located because the DSO engine produces
# the inflexible load bid that the MO consumes, and they share the
# concept of "flexible committed" that flows from the MO back to the
# DSO to avoid double-counting.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - AbstractMarketOperator:
#           Receives bids from agents via AbstractMarketCommunication
#           Receives inflexible bid from AbstractDSOLoadEstimationEngine
#           Produces ClearingResult consumed by AbstractDeviceAgent
#     - AbstractDSOLoadEstimationEngine:
#           Queries AbstractMarketOperator.get_total_flexible_committed()
#           Produces inflexible bid consumed by AbstractMarketOperator
#
# IMPORTS FROM:
#     - typing: Any, Dict, Optional, Tuple
#     - data_types: BidCurve, ClearingResult
#     - enums_and_constants: MarketType
# ============================================================================

"""Abstract market operator and DSO load estimation engine.

The MO clears the retail market by intersecting aggregate demand
(flexible agent bids + DSO inflexible bid) with the supply curve
(DSO wholesale procurement).  The DSO engine ensures the inflexible
bid accurately represents non-controllable load without double-counting
the flexible load already bid by device agents.

Informational iterations allow the DSO and agents to converge:
each iteration gives the DSO better visibility into flexible
commitments, reducing the double-counting in subsequent rounds.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from data_types import BidCurve, ClearingResult
from enums_and_constants import MarketType

class AbstractMarketOperator(ABC):
    """Abstract base for the entity that clears the retail market.

    Receives bids from device agents and the DSO inflexible load bid,
    aggregates demand, intersects with supply, and propagates cleared
    prices.
    """

    @abstractmethod
    def submit_agent_bid(self, agent_id: str, bid: BidCurve) -> bool:
        """Receive a bid from a device agent.

        Args:
            agent_id: Submitting agent.
            bid: Price-quantity bid curve.

        Returns:
            ``True`` if accepted.
        """
        ...

    @abstractmethod
    def submit_dso_inflexible_bid(
        self,
        feeder_id: str,
        bid: Any,
    ) -> bool:
        """Receive the DSO's inflexible load bid.

        Args:
            feeder_id: Which feeder.
            bid: Inflexible load bid (perfectly inelastic demand).

        Returns:
            ``True`` if accepted.
        """
        ...

    @abstractmethod
    def clear_market(self) -> ClearingResult:
        """Clear the market.

        Returns:
            ``ClearingResult`` with clearing price and aggregate data.
        """
        ...

    @abstractmethod
    def propagate_results(self) -> Dict[str, ClearingResult]:
        """Compute and distribute per-agent clearing results.

        Returns:
            Dictionary mapping agent_id to ``ClearingResult``.
        """
        ...

    @abstractmethod
    def get_total_flexible_committed(self) -> float:
        """Sum of all agent cleared quantities.

        Used by the DSO to avoid double-counting when constructing the
        inflexible load bid for subsequent iterations.

        Returns:
            Total flexible kW committed.
        """
        ...

    @abstractmethod
    def step(
        self,
        current_time: float,
    ) -> Optional[Dict[str, ClearingResult]]:
        """Execute one MO timestep.

        Args:
            current_time: Simulation time.
                EXTERNAL: From simulation harness.

        Returns:
            Per-agent results if a clearing occurred, ``None`` otherwise.
        """
        ...


class AbstractDSOLoadEstimationEngine(ABC):
    """Abstract base for the DSO's inflexible load estimation.

    Estimates aggregate inflexible load for a feeder or pricing zone by
    combining substation metering, weather-driven load forecasts, network
    loss models, and BTM solar generation estimates, then subtracting
    the flexible load covered by device agent bids.
    """

    @abstractmethod
    def estimate_inflexible_load(
        self,
        interval: Tuple[float, float],
        total_load_forecast: float,
        flexible_committed: float,
        btm_solar_forecast: float,
        loss_factor: float,
    ) -> Any:
        """Compute the inflexible load bid for a market interval.

        Args:
            interval: Time interval.
            total_load_forecast: Forecasted total feeder load (kW).
                EXTERNAL: From substation metering + forecast model.
            flexible_committed: Sum of agent flexible commitments (kW).
                INTERNAL: From MO's aggregation of agent bids/clears.
            btm_solar_forecast: Aggregate BTM solar generation (kW).
                EXTERNAL: From solar forecast model.
            loss_factor: Distribution loss factor (fraction).
                EXTERNAL: From network loss model.

        Returns:
            Inflexible load bid (concrete type is ``DSOInflexibleLoadBid``).
        """
        ...

    @abstractmethod
    def update_with_metering(
        self,
        substation_load_actual: float,
        flexible_actual: float,
        timestamp: float,
    ) -> None:
        """Update the model with real-time metering data.

        Args:
            substation_load_actual: Measured total feeder load (kW).
                EXTERNAL: From substation SCADA.
            flexible_actual: Sum of actual device agent power (kW).
                INTERNAL: From MO metering.
            timestamp: Measurement time.
        """
        ...
