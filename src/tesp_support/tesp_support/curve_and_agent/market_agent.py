# ============================================================================
# FILE: market_communication.py
# PURPOSE: Abstract interface for agent-MO communication (Agent Function F5).
#          Handles bid submission and clearing result reception.
#
# EXTERNAL DEPENDENCY:
#     The communication mechanism depends on the simulation framework:
#     - In-process function calls (for single-process simulation)
#     - Message bus (FNCS, HELICS)
#     - REST API (for distributed deployment)
#     The specific transport is injected at construction time.
# ============================================================================

from typing import Any, Optional, Callable
from data_types import BidCurve, ClearingResult, SettlementRecord
from enums_and_constants import MarketType


class MarketCommunicationInterface:
    """Abstract interface for submitting bids to and receiving results
    from a Market Operator.

    Each market the agent participates in gets its own instance of
    this interface.

    Args:
        transport: The communication transport object.
            EXTERNAL: Provided by the simulation harness.
            Could be a direct reference to the MO object (in-process),
            a FNCS/HELICS endpoint, or an HTTP client.
        agent_id: Unique identifier for this agent.
        market_type: Type of market this interface connects to.
    """

    def __init__(self, transport: Any, agent_id: str, market_type: MarketType):
        self._transport = transport
        self._agent_id = agent_id
        self._market_type = market_type
        self._on_clear_callback: Optional[Callable] = None

    def submit_bid(self, bid: BidCurve, market_id: str, interval_id: str) -> bool:
        """Submit a bid curve to the Market Operator.

        Args:
            bid: The price-quantity bid curve.
                INTERNAL: From bid formulation (F4).
            market_id: ID of the specific market cycle.
            interval_id: ID of the delivery interval.

        Returns:
            True if submission was acknowledged by MO.
        """
        return bool(
            self._transport.submit(
                agent_id=self._agent_id,
                market_type=self._market_type,
                bid=bid,
                market_id=market_id,
                interval_id=interval_id,
            )
        )

    def receive_clear(self, market_id: str) -> Optional[ClearingResult]:
        """Receive a clearing result from the Market Operator.

        This may be blocking (poll) or non-blocking (check for
        available results). Behavior depends on the transport.

        Args:
            market_id: ID of the market cycle to check for results.

        Returns:
            ClearingResult if available, None otherwise.
        """
        result = self._transport.receive(
            agent_id=self._agent_id,
            market_id=market_id,
        )
        if result is not None and self._on_clear_callback is not None:
            self._on_clear_callback(result)
        return result

    def submit_reconciliation(
        self, market_id: str, settlement: SettlementRecord
    ) -> bool:
        """Submit reconciliation/settlement data to the MO.

        Args:
            market_id: ID of the market cycle.
            settlement: Settlement record with performance data.
                INTERNAL: From reconciliation function (F13).

        Returns:
            True if accepted by MO.
        """
        return bool(
            self._transport.submit(
                agent_id=self._agent_id,
                market_type=self._market_type,
                settlement=settlement,
                market_id=market_id,
            )
        )

    def register_clear_callback(
        self, callback: Callable[[ClearingResult], None]
    ) -> None:
        """Register a callback to be invoked when a clearing result arrives.

        For event-driven architectures. The callback is invoked with
        the ClearingResult as its argument.

        Args:
            callback: Function to call on clearing result arrival.
        """
        self._on_clear_callback = callback
