# ============================================================================
# FILE: markets/__init__.py
# PURPOSE: Package-level exports for concrete market infrastructure
#          components.
#
# This package contains the implementations of market-facing entities:
# the Market Operator that clears the retail market, the communication
# interface between agents and the MO, the per-market-cycle state
# machine, the DSO's inflexible load estimation engine, and the
# wholesale supply curve.
#
# DEPENDENCY RULE:
#     Modules in this package import from:
#       - abstractions/ (the contracts they implement)
#       - data_types.py (shared dataclasses: BidCurve, ClearingResult,
#         DSOInflexibleLoadBid, BidPoint, MarketTimingParams, etc.)
#       - enums_and_constants.py (MarketType, MarketPhase, OperatingMode,
#         IterationType, etc.)
#
#     No module in this package imports from devices/, simulators/,
#     economics/, or forecasting/.  Market components interact with
#     device agents only through the abstract interfaces and shared
#     data types — specifically through BidCurve (received from agents),
#     ClearingResult (sent to agents), and SettlementRecord (received
#     from agents during reconciliation).
#
#     The one exception is the MarketOperator's step() method, which
#     is called by the simulation harness (main.py), not by any agent.
#     The MO does not import agent code; agents import the MO's
#     communication interface.
#
# PACKAGE CONTENTS:
#
#     market_object.py
#         Per-market-cycle state machine and data container.  One
#         MarketObject is instantiated per market product per cycle.
#         Tracks progression through INACTIVE → ACTIVE → NEGOTIATION →
#         MARKET_LEAD → ASSESSMENT → DELIVERY_LEAD → DELIVERY →
#         RECONCILE → EXPIRED, with the informational loop-back from
#         ASSESSMENT to ACTIVE for non-binding iterations.
#
#         Stores all per-cycle data: submitted bids, clearing results,
#         advisory history, performance logs, settlement records.
#
#         MarketObjects are owned by the DeviceAgent (one collection
#         per agent) and their state transitions are checked every
#         simulation timestep by the agent orchestrator.
#
#         Classes:
#             MarketObject(AbstractMarketObject)
#
#     market_communication.py
#         Agent ↔ Market Operator messaging interface.  Abstracts the
#         transport layer so that the agent's bidding and response logic
#         is independent of whether the MO is an in-process object, a
#         FNCS/HELICS co-simulation peer, or a remote REST service.
#
#         Each market product the agent participates in gets its own
#         communication interface instance.  The agent holds one per
#         registered market type.
#
#         Handles three message types:
#             submit_bid()            — agent → MO (during NEGOTIATION)
#             receive_clear()         — MO → agent (during ASSESSMENT)
#             submit_reconciliation() — agent → MO (during RECONCILE)
#
#         Classes:
#             MarketCommunicationInterface(AbstractMarketCommunication)
#
#     market_operator.py
#         The DSO's Market Operator that clears the retail energy market.
#         Receives bids from device agents (flexible, price-elastic) and
#         the DSO's inflexible load bid (perfectly inelastic), aggregates
#         demand, intersects with the supply curve, and propagates
#         cleared prices back to all participants.
#
#         Supports both informational and binding clearing iterations.
#         Tracks iteration count and determines when to transition from
#         informational to binding based on the configured protocol
#         (fixed_count, convergence, or time_gated).
#
#         Also provides get_total_flexible_committed() which the DSO
#         load estimation engine uses to avoid double-counting.
#
#         Classes:
#             MarketOperator(AbstractMarketOperator)
#
#     dso_load_engine.py
#         DSO's inflexible load estimation engine.  Estimates aggregate
#         non-controllable load for a feeder by combining substation
#         metering, weather-driven load forecasts, network loss models,
#         and BTM solar generation estimates, then subtracting flexible
#         load already covered by device agent bids.
#
#         Produces a DSOInflexibleLoadBid (defined in data_types.py)
#         that the MarketOperator consumes as perfectly inelastic demand.
#
#         Supports real-time correction via update_with_metering() using
#         substation SCADA measurements during RT market operation.
#
#         Classes:
#             DSOLoadEstimationEngine(AbstractDSOLoadEstimationEngine)
#
#     supply_curve.py
#         The DSO's wholesale energy procurement cost curve.  Represents
#         the merit order of generation resources available to serve
#         the distribution system.  Constructed externally from wholesale
#         market data and passed to the MarketOperator.
#
#         Provides interpolation methods for market clearing:
#             get_supply_at_price()   — quantity available at a given price
#             get_price_at_quantity() — marginal price at a given quantity
#
#         Classes:
#             SupplyCurve
#
# DATA TYPES USED BY THIS PACKAGE (defined elsewhere):
#     From data_types.py:
#         BidCurve, BidPoint, ClearingResult, DSOInflexibleLoadBid,
#         MarketTimingParams, SettlementRecord, AdvisoryRecord,
#         PerformanceEntry, DeviceCommand
#     From enums_and_constants.py:
#         MarketType, MarketPhase, OperatingMode, IterationType,
#         CommitmentStatus
#
# USAGE:
#     Precise import (preferred inside framework):
#         from markets.market_operator import MarketOperator
#         from markets.market_object import MarketObject
#         from markets.supply_curve import SupplyCurve
#
#     Convenience import (acceptable in main.py):
#         from markets import MarketOperator, MarketObject, SupplyCurve
# ============================================================================

"""Markets package — retail market infrastructure components.

This package implements the market-facing side of the agent framework:
the state machines that track market cycle progression, the communication
layer between agents and the Market Operator, the MO itself (which clears
the retail market), the DSO's inflexible load estimation engine (which
bids non-controllable load on behalf of customers), and the wholesale
supply curve that represents the cost of energy procurement.

The market clearing process:
    1. Device agents submit flexible, price-elastic bid curves via
       MarketCommunicationInterface.submit_bid().
    2. The DSOLoadEstimationEngine computes the inflexible load bid and
       submits it via MarketOperator.submit_dso_inflexible_bid().
    3. The MarketOperator aggregates all demand (flexible + inflexible),
       intersects with the SupplyCurve, and determines the clearing price.
    4. Per-agent clearing results are propagated back via
       MarketCommunicationInterface.receive_clear().
    5. For informational iterations, agents refine bids and the DSO
       refines its inflexible estimate; for the binding iteration,
       agents proceed to delivery.
"""

# -- Market State Machine ----------------------------------------------------
from markets.market_object import MarketObject

# -- Agent ↔ MO Communication ------------------------------------------------
from markets.market_communication import MarketCommunicationInterface

# -- Market Operator ----------------------------------------------------------
from markets.market_operator import MarketOperator

# -- DSO Load Estimation ------------------------------------------------------
from markets.dso_load_engine import DSOLoadEstimationEngine

# -- Supply Curve -------------------------------------------------------------
from markets.supply_curve import SupplyCurve

__all__ = [
    "MarketObject",
    "MarketCommunicationInterface",
    "MarketOperator",
    "DSOLoadEstimationEngine",
    "SupplyCurve",
]