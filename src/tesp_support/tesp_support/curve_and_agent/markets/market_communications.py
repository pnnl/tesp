# ============================================================================
# FILE: markets/market_communication.py
# PURPOSE: Concrete implementation of the agent ↔ Market Operator
#          communication interface (agent function F5).
#
# This module provides the messaging layer that device agents use to
# submit bids, receive clearing results, and report reconciliation
# data to the Market Operator.  It is the agent-side endpoint of
# the market communication channel.
#
# THREE MESSAGE TYPES:
#
#     1. submit_bid(bid, market_id, interval_id) → bool
#        Direction: Agent → MO
#        Phase: NEGOTIATION
#        Content: A BidCurve (list of price-quantity points) for a
#                 specific market cycle and delivery interval.
#        Response: Acknowledgement (True/False).
#
#     2. receive_clear(market_id) → ClearingResult | None
#        Direction: MO → Agent
#        Phase: ASSESSMENT
#        Content: Cleared price, cleared quantity for this agent,
#                 iteration number, and iteration type (INFORMATIONAL
#                 or BINDING).
#        Behavior: May be blocking (poll) or non-blocking (check for
#                  available results), depending on the transport.
#                  Also supports callback registration for event-driven
#                  architectures.
#
#     3. submit_reconciliation(market_id, settlement) → bool
#        Direction: Agent → MO
#        Phase: RECONCILE
#        Content: SettlementRecord with actual delivery performance,
#                 penalties incurred, revenue earned, and displacement
#                 accounting.
#        Response: Acknowledgement (True/False).
#
# TRANSPORT ABSTRACTION:
#     The communication interface does not implement the transport
#     itself.  Instead, an opaque transport object is injected at
#     construction time.  This transport could be:
#
#     - Direct in-process reference:
#         The transport IS the MarketOperator object.  Method calls
#         are direct Python function calls within a single process.
#         This is the simplest mode, used for single-machine
#         simulations where all agents and the MO share a process.
#
#     - FNCS message bus:
#         The transport is an FNCS endpoint.  Bids are serialized
#         and published to FNCS topics.  Clearing results are
#         received by subscribing to MO-published topics.  Used in
#         GridLAB-D co-simulation via FNCS.
#
#     - HELICS message bus:
#         Similar to FNCS but using the HELICS co-simulation
#         framework.  Supports both value-based and message-based
#         communication patterns.
#
#     - REST API / HTTP:
#         The transport is an HTTP client.  Bids are POST requests,
#         clearing results are GET requests or webhook callbacks.
#         Used for distributed deployments where agents and the MO
#         run on separate machines.
#
#     - Message queue (ZMQ, RabbitMQ, etc.):
#         The transport is a queue client.  Supports asynchronous
#         communication patterns with guaranteed delivery.
#
#     The agent code is identical regardless of which transport is
#     used.  Only the construction of the transport object (in
#     main.py) and the concrete method implementations in this file
#     differ across deployment modes.
#
# ONE INSTANCE PER MARKET TYPE:
#     Each market product the agent participates in gets its own
#     MarketCommunicationInterface instance.  An agent participating
#     in RT_ENERGY and DA_ENERGY has two instances.  This ensures
#     that bid submission and result reception are scoped to the
#     correct market without requiring the agent to multiplex
#     messages across market types.
#
#     The agent holds these instances in a dictionary keyed by
#     MarketType and passes the appropriate one to each phase
#     handler based on the MarketObject's market_type.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from: abstractions.market_communication.AbstractMarketCommunication
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - markets/market_operator.py: The "other end" of the communication
#       channel.  In direct-reference mode, the transport IS a
#       MarketOperator instance and method calls delegate directly
#       to MarketOperator.submit_agent_bid(), etc.
#     - markets/market_object.py: MarketObject stores the submitted
#       bid (from submit_bid) and the clearing result (from
#       receive_clear) as part of its per-cycle data.
#     - agent.py (DeviceAgent):
#         _handle_negotiation() calls submit_bid()
#         _handle_assessment()  calls receive_clear()
#         _handle_reconcile()   calls submit_reconciliation()
#     - main.py: Constructs MarketCommunicationInterface instances
#       with the appropriate transport for each agent and market type,
#       then passes them to DeviceAgent.register_market().
#
# DATA TYPES USED:
#     From data_types.py:
#         BidCurve          — submitted by the agent during NEGOTIATION
#         ClearingResult    — received from the MO during ASSESSMENT
#         SettlementRecord  — submitted by the agent during RECONCILE
#     From enums_and_constants.py:
#         MarketType        — identifies which market product this
#                             interface connects to
#
# EXTERNAL DEPENDENCY:
#     The transport object is EXTERNAL — its type and construction
#     depend on the simulation framework or deployment environment.
#     This module imports only the abstract contract and shared data
#     types; it does not import any transport-specific library.
#     Transport-specific serialization, topic naming, and connection
#     management are encapsulated within the transport object itself.
# ============================================================================

"""Concrete agent ↔ Market Operator communication interface.

Provides the messaging layer through which device agents submit bids,
receive clearing results, and report reconciliation data.  The transport
mechanism is injected at construction time, making the agent's market
interaction logic independent of the communication infrastructure.

Key methods:
    submit_bid()            — Send a bid curve to the MO (NEGOTIATION phase).
    receive_clear()         — Receive a clearing result from the MO (ASSESSMENT phase).
    submit_reconciliation() — Report settlement data to the MO (RECONCILE phase).
    register_clear_callback() — For event-driven architectures, register a
                                callback invoked when a clearing result arrives.
"""

from typing import Any, Callable, Optional

from abstractions.market_communication import AbstractMarketCommunication
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
        self._on_clear_callback: Callable | None = None

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

    def receive_clear(self, market_id: str) -> ClearingResult | None:
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
