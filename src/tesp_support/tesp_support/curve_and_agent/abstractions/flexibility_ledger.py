# ============================================================================
# FILE: abstractions/flexibility_ledger.py
# PURPOSE: Abstract base class for capacity commitment tracking and
#          availability queries (agent function F6).
#
# The flexibility ledger is the single source of truth for how much of
# the device's operating range is currently spoken for by market
# commitments.  It supports three tiers of availability queries:
#
#     TIER 1 — HARD:     All commitments deducted.  Zero conflict risk.
#     TIER 2 — EXPECTED: Advisory weighted by confidence, tentative by
#                         baseline probability.  Realistic planning.
#     TIER 3 — ECONOMIC: Identifies displaceable lower-value capacity.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Uses: (indirectly) AbstractPenaltyModel for displacement cost
#     - Used by: AbstractDeviceAgent._handle_active() (query availability)
#                AbstractDeviceAgent._handle_negotiation() (hold tentative)
#                AbstractDeviceAgent._handle_assessment() (update advisory)
#                AbstractDeviceAgent._handle_delivery_lead() (book firm)
#                AbstractDeviceAgent._handle_reconcile() (release)
#                AbstractDeviceAgent.formulate_bid() (economic availability)
#
# IMPORTS FROM:
#     - typing: Any, List, Optional, Tuple
#     - enums_and_constants: MarketType, ProductType
# ============================================================================

"""Abstract flexibility ledger — capacity accounting across all markets.

The ledger tracks commitments through their lifecycle:
    TENTATIVE → ADVISORY → FIRM → RELEASED
and provides queries at three levels of conservatism for different
use cases (bidding, planning, dispatch).
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

from enums_and_constants import MarketType, ProductType

class AbstractFlexibilityLedger(ABC):
    """Abstract base for capacity commitment tracking.

    The flexibility ledger is the single source of truth for how much
    of the device's operating range is currently committed to markets.

    It supports three tiers of availability queries:
        1. **Hard** — deducts all commitments (tentative + advisory + firm).
        2. **Expected** — weights advisory by confidence, tentative by
           a baseline probability.
        3. **Economic** — identifies capacity that could be freed by
           displacing lower-value commitments.

    Args:
        Q_min_device: Physical minimum power (kW).
        Q_max_device: Physical maximum power (kW).
    """

    def __init__(self, Q_min_device: float, Q_max_device: float):
        self._Q_min = Q_min_device
        self._Q_max = Q_max_device

    @abstractmethod
    def hold_tentative(
        self,
        market_id: str,
        market_type: MarketType,
        product_type: ProductType,
        quantity: float,
        interval: Tuple[float, float],
        **kwargs: Any,
    ) -> None:
        """Record a tentative commitment when a bid is submitted.

        Args:
            market_id: Market cycle identifier.
            market_type: Type of market product.
            product_type: Energy, regulation, or reserve.
            quantity: Bid quantity (kW).
            interval: (start_time, end_time) of delivery.
            **kwargs: Optional economic annotations (cleared_price, etc.).
        """
        ...

    @abstractmethod
    def update_advisory(
        self,
        market_id: str,
        quantity: float,
        interval: Tuple[float, float],
        confidence: float,
        cleared_price: float,
        iteration: int,
        **kwargs: Any,
    ) -> None:
        """Create or update an advisory commitment after an informational
        clear.

        Args:
            market_id: Market cycle identifier.
            quantity: Projected operating point (kW).
            interval: Delivery interval.
            confidence: Convergence confidence (0–1).
                INTERNAL: From convergence tracker.
            cleared_price: Informational clearing price ($/kWh).
                INTERNAL: From MO clearing result.
            iteration: Iteration number.
        """
        ...

    @abstractmethod
    def book_firm(
        self,
        market_id: str,
        quantity: float,
        interval: Tuple[float, float],
        cleared_price: float,
        **kwargs: Any,
    ) -> None:
        """Convert a commitment to FIRM after a binding clear.

        Args:
            market_id: Market cycle identifier.
            quantity: Cleared quantity (kW).
            interval: Delivery interval.
            cleared_price: Binding clearing price ($/kWh).
                INTERNAL: From MO binding clearing result.
        """
        ...

    @abstractmethod
    def release(self, market_id: str) -> None:
        """Release a commitment after reconciliation.

        Args:
            market_id: Market cycle identifier.
        """
        ...

    @abstractmethod
    def hard_available(
        self,
        time_interval: Tuple[float, float],
        excluding: Optional[str] = None,
    ) -> Tuple[float, float]:
        """TIER 1: Hard availability (all commitments deducted).

        Args:
            time_interval: Query interval.
            excluding: Market ID to exclude (for re-bidding).

        Returns:
            (Q_min_avail, Q_max_avail) in kW.
        """
        ...

    @abstractmethod
    def expected_available(
        self,
        time_interval: Tuple[float, float],
        excluding: Optional[str] = None,
    ) -> Tuple[float, float]:
        """TIER 2: Expected availability (advisory weighted by confidence).

        Args:
            time_interval: Query interval.
            excluding: Market ID to exclude.

        Returns:
            (Q_min_avail, Q_max_avail) in kW.
        """
        ...

    @abstractmethod
    def economic_available(
        self,
        time_interval: Tuple[float, float],
        candidate_value: float,
        candidate_penalty: float,
        excluding: Optional[str] = None,
    ) -> Any:
        """TIER 3: Economic availability with displacement options.

        Args:
            time_interval: Query interval.
            candidate_value: Marginal value of the proposed new use ($/kW).
            candidate_penalty: Marginal penalty of the proposed new use.
            excluding: Market ID to exclude.

        Returns:
            Economic envelope with hard availability plus displacement
            supply curve.  Concrete type is ``EconomicEnvelope``.
        """
        ...
