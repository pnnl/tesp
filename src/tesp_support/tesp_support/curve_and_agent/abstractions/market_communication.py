# ============================================================================
# FILE: abstractions/market_communication.py
# PURPOSE: Abstract base class for agent ↔ Market Operator communication
#          (agent function F5).
#
# Handles three message types:
#     1. Bid submission (agent → MO)
#     2. Clearing result reception (MO → agent)
#     3. Reconciliation / settlement reporting (agent → MO)
#
# The transport mechanism is injected at construction time and is
# opaque to the agent.  Concrete implementations may use in-process
# function calls, FNCS/HELICS message bus, REST API, etc.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Used by: AbstractDeviceAgent._handle_negotiation() (submit bid)
#                AbstractDeviceAgent._handle_assessment() (receive clear)
#                AbstractDeviceAgent._handle_reconcile() (report settlement)
#     - Connects to: AbstractMarketOperator (the other end of the channel)
#
# IMPORTS FROM:
#     - typing: Any, Optional
#     - data_types: BidCurve, ClearingResult, SettlementRecord
#     - enums_and_constants: MarketType
# ============================================================================

"""Abstract market communication — the messaging layer between agent and MO.

The communication interface abstracts away the transport so that the
agent's bidding and response logic is independent of whether the MO
is an in-process object, a remote service, or a co-simulation peer.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from data_types import BidCurve, ClearingResult, SettlementRecord
from enums_and_constants import MarketType

class AbstractMarketCommunication(ABC):
    """Abstract base for agent–MO communication (F5).

    Handles bid submission, clearing result reception, and
    reconciliation reporting.  The transport mechanism is injected
    at construction time and is opaque to the agent.

    Args:
        transport: Communication transport object.
            EXTERNAL: Provided by the simulation harness.
        agent_id: Unique identifier for this agent.
        market_type: Type of market this interface connects to.
    """

    def __init__(
        self,
        transport: Any,
        agent_id: str,
        market_type: MarketType,
    ):
        self._transport = transport
        self._agent_id = agent_id
        self._market_type = market_type

    @abstractmethod
    def submit_bid(
        self,
        bid: BidCurve,
        market_id: str,
        interval_id: str,
    ) -> bool:
        """Submit a bid curve to the Market Operator.

        Args:
            bid: The price-quantity bid curve.
                INTERNAL: From bid formulation (F4).
            market_id: Market cycle identifier.
            interval_id: Delivery interval identifier.

        Returns:
            ``True`` if submission acknowledged.
        """
        ...

    @abstractmethod
    def receive_clear(self, market_id: str) -> Optional[ClearingResult]:
        """Receive a clearing result from the Market Operator.

        Args:
            market_id: Market cycle identifier.

        Returns:
            ``ClearingResult`` if available, ``None`` otherwise.
        """
        ...

    @abstractmethod
    def submit_reconciliation(
        self,
        market_id: str,
        settlement: SettlementRecord,
    ) -> bool:
        """Submit reconciliation / settlement data to the MO.

        Args:
            market_id: Market cycle identifier.
            settlement: Settlement record with performance data.
                INTERNAL: From reconciliation function (F13).

        Returns:
            ``True`` if accepted.
        """
        ...