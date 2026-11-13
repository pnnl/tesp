# ============================================================================
# FILE: abstractions/price_forecast_service.py
# PURPOSE: Abstract base class for the central price forecast store.
#
# Maintains and distributes evolving price estimates that are updated
# by informational market clears and external forecast sources.
#
# The price forecast service is a cross-cutting shared resource consumed
# by multiple agent functions:
#     - F3 (preference curve): reference price P₀ calibration
#     - F4 (bid formulation): risk assessment for concurrent markets
#     - Planning optimizer: price trajectory for schedule optimization
#     - Flexibility ledger: advisory commitment valuation
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Used by: AbstractDeviceAgent.generate_preference_curve() (P₀)
#                AbstractDeviceAgent.formulate_bid() (risk assessment)
#                AbstractPlanningOptimizer.solve() (price trajectory)
#     - Updated by: AbstractDeviceAgent._handle_assessment()
#                   (informational clear prices)
#
# IMPORTS FROM:
#     - typing: List, Optional, Tuple
#     - enums_and_constants: MarketType
# ============================================================================

"""Abstract price forecast service — the central store for price estimates.

Informational market iterations are the primary source of increasingly
accurate price estimates.  This service makes those estimates available
to all agent functions that need forward-looking price information.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from enums_and_constants import MarketType

class AbstractPriceForecastService(ABC):
    """Abstract base for the central price forecast store.

    Maintains evolving price estimates updated by informational market
    clears and external forecast sources.  Consumed by bid formulation,
    risk assessment, preference curve calibration, and the planning
    optimizer.
    """

    @abstractmethod
    def update(
        self,
        market_type: MarketType,
        interval: Tuple[float, float],
        price: float,
        confidence: float,
        source: str,
        iteration: int = 0,
    ) -> None:
        """Update the price forecast for a market-interval pair.

        Args:
            market_type: Which market.
            interval: Time interval.
            price: Price estimate ($/kWh).
                INTERNAL: From informational clearing result.
                OR EXTERNAL: From wholesale data or MO forecast.
            confidence: Confidence in the estimate (0–1).
            source: Where this came from.
            iteration: Iteration number (for informational clears).
        """
        ...

    @abstractmethod
    def get_price(
        self,
        market_type: MarketType,
        interval: Tuple[float, float],
        default: float = 0.0,
    ) -> float:
        """Get the point estimate price for a market and interval.

        Args:
            market_type: Which market.
            interval: Time interval.
            default: Fallback value.

        Returns:
            Price estimate or *default*.
        """
        ...

    @abstractmethod
    def get_trajectory(
        self,
        market_type: MarketType,
        t_start: float,
        t_end: float,
        resolution: float = 3600.0,
    ) -> List[Tuple[Tuple[float, float], float]]:
        """Get a price trajectory over a planning horizon.

        Args:
            market_type: Which market.
            t_start: Start of horizon.
            t_end: End of horizon.
            resolution: Interval length (seconds).

        Returns:
            List of ((t_start, t_end), price_estimate) tuples.
        """
        ...