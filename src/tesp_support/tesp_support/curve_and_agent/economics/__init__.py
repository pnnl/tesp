# ============================================================================
# FILE: economics/__init__.py
# PURPOSE: Package-level exports for the economic decision-making
#          components of the agent framework.
#
# This package contains the modules that translate physical device
# flexibility and market signals into economic decisions: what to bid,
# how to respond to prices, how to allocate capacity across competing
# obligations, and how to plan across multiple time intervals.
#
# If the devices/ package answers "what CAN the device do?" and the
# markets/ package answers "what does the market want?", this package
# answers "what SHOULD the device do?"
#
# DEPENDENCY RULE:
#     Modules in this package import from:
#       - abstractions/ (the contracts they implement)
#       - data_types.py (shared dataclasses)
#       - enums_and_constants.py (shared enumerations)
#
#     Some modules hold references to abstractions from other packages
#     (AbstractSimulatorInterface, AbstractDeviceModel, AbstractPenaltyModel,
#     AbstractPreferenceCurve, AbstractDeviceState) but interact with
#     them ONLY through the abstract interface — never importing concrete
#     classes from devices/, simulators/, or markets/ directly.
#
#     The one structural coupling is that the CommandArbiter holds a
#     reference to AbstractSimulatorInterface for F9 actuation.  This
#     is by design — the arbiter is the single actuation point, and the
#     simulator interface is the single write path.  The coupling is
#     through the abstraction, not through a concrete implementation.
#
# PACKAGE CONTENTS:
#
#     preference_curves.py
#         Concrete preference / offer curves that map prices to desired
#         power quantities (agent function F3).
#
#         Two implementations encoding the fundamental amenity-vs-money
#         tradeoff parameterized by the customer preference factor k:
#
#         IsoelasticPreferenceCurve — for load-only devices (HVAC, WH, EV).
#             Standard isoelastic demand curve:
#                 Q(P) = Q_0 · (P / P_0)^{−ε}
#             Always positive quantity (consumption only).
#
#         BidirectionalPreferenceCurve — for batteries.
#             Sigmoid curve with degradation-driven dead band:
#                 Q(P) = Q_max · (1 − (P/P_thr)^ε) / (1 + (P/P_thr)^ε)
#             Extends to negative quantity (discharge) at high prices.
#             Dead band width = 2 × C_degradation + efficiency loss.
#
#         Both curves also provide get_amenity_cost() which enters the
#         dispatch optimizer's objective function as the "phantom penalty"
#         that protects customer comfort.
#
#         Classes:
#             IsoelasticPreferenceCurve(AbstractPreferenceCurve)
#             BidirectionalPreferenceCurve(AbstractPreferenceCurve)
#
#     penalty_models.py
#         Non-delivery penalty functions (agent function F14).  Define
#         the economic cost of failing to deliver on a cleared market
#         commitment.  Parameters are provided by the MO as market rules.
#
#         Four implementations covering common electricity market
#         penalty structures:
#
#         ProportionalPenaltyModel — rate × shortfall.
#             Used for RT and DA energy markets.
#         TieredPenaltyModel — escalating rates by shortfall band.
#             Used for markets tolerant of small deviations.
#         ScoredPenaltyModel — performance score degrades payment.
#             Used for frequency regulation (e.g., PJM RegD score).
#         CompoundPenaltyModel — fixed + proportional.
#             Used for spinning reserve (fixed penalty on activation
#             failure, proportional on capacity shortfall).
#
#         Classes:
#             ProportionalPenaltyModel(AbstractPenaltyModel)
#             TieredPenaltyModel(AbstractPenaltyModel)
#             ScoredPenaltyModel(AbstractPenaltyModel)
#             CompoundPenaltyModel(AbstractPenaltyModel)
#
#     flexibility_ledger.py
#         Capacity commitment tracking and availability queries
#         (agent function F6).  The single source of truth for how
#         much of the device's operating range is committed to markets.
#
#         Tracks commitments through their lifecycle:
#             TENTATIVE → ADVISORY → FIRM → RELEASED
#
#         Provides three-tier availability queries:
#             TIER 1 — HARD:     All commitments deducted.
#             TIER 2 — EXPECTED: Advisory weighted by confidence.
#             TIER 3 — ECONOMIC: Includes displaceable capacity.
#
#         Also defines supporting data structures:
#             DisplaceableBlock — a block of freeable capacity with cost.
#             EconomicEnvelope — extended availability with displacement
#                                supply curve.
#
#         Classes:
#             FlexibilityLedger(AbstractFlexibilityLedger)
#             DisplaceableBlock
#             EconomicEnvelope
#
#     dispatch_optimizer.py
#         Per-timestep economic dispatch optimization (agent functions
#         F15 and F16).  Two tightly-coupled classes that work in
#         sequence inside the Command Arbiter:
#
#         DeliveryValueCalculator (F15) — normalizes the heterogeneous
#             economics of energy, regulation, and reserve products
#             into a common DeliveryEconomics representation with
#             callable revenue_fn, penalty_fn, and net_value_fn.
#
#         DispatchOptimizer (F16) — solves the constrained net-value
#             maximization across all simultaneously active deliveries.
#             Produces the single optimal operating point Q* and the
#             per-market capacity allocation.
#
#         Together they replace the fixed priority table with
#         economically-driven dynamic dispatch priority.
#
#         Classes:
#             DeliveryValueCalculator(AbstractDeliveryValueCalculator)
#             DispatchOptimizer(AbstractDispatchOptimizer)
#
#     command_arbiter.py
#         Merges simultaneous delivery obligations from multiple
#         markets into a single physical device command (coordinates
#         agent functions F8, F9, F12, F15, F16).
#
#         The SINGLE ACTUATION POINT for the device.  Owns the
#         delivery registry, orchestrates the F15→F16→F8→F9 pipeline
#         every simulation timestep, and returns per-market
#         FulfillmentRecords for performance logging (F12).
#
#         Also defines:
#             DeliveryRecord — per-delivery data container tracked
#                              by the arbiter.
#
#         Classes:
#             CommandArbiter(AbstractCommandArbiter)
#             DeliveryRecord
#
#     planning_optimizer.py
#         Multi-interval schedule optimization (used during ACTIVE and
#         ASSESSMENT phases for markets with planning horizons longer
#         than a single interval).
#
#         Solves trajectory optimization across the planning horizon:
#             Battery:      LP/QP producing V_stored per interval.
#             HVAC:         Linearized LP for pre-conditioning schedule.
#             Water Heater: Scenario-based LP for pre-heating schedule.
#             EV:           LP for deadline-constrained charge scheduling.
#
#         ESSENTIAL for batteries (V_stored drives all charge/discharge
#         decisions).  BENEFICIAL for all other devices.
#
#         Re-run after each informational iteration as advisory prices
#         converge, producing increasingly accurate schedules.
#
#         Classes:
#             PlanningOptimizer(AbstractPlanningOptimizer)
#
# INTERACTION PATTERN BETWEEN MODULES IN THIS PACKAGE:
#
#     The typical execution flow during a delivery timestep:
#
#         CommandArbiter.resolve_and_actuate()
#             │
#             ├── for each active delivery:
#             │   └── DeliveryValueCalculator.compute()
#             │       └── uses PenaltyModel.compute_penalty()
#             │       └── uses PenaltyModel.marginal_penalty()
#             │       └── includes degradation_cost for batteries
#             │
#             ├── DispatchOptimizer.solve()
#             │   └── uses PreferenceCurve.get_amenity_cost()
#             │   └── maximizes Σ NV − C_amenity − C_degradation
#             │
#             ├── DeviceModel.translate_power_to_command()   [F8]
#             │
#             └── SimulatorInterface.write_device_command()  [F9]
#
#     The typical execution flow during bid formulation:
#
#         DeviceAgent.formulate_bid()
#             │
#             ├── FlexibilityLedger.expected_available()     [conservative]
#             │   or FlexibilityLedger.economic_available()  [aggressive]
#             │
#             ├── PreferenceCurve.sample_bid_curve()
#             │   └── uses PlanningOptimizer output (V_stored for batteries)
#             │
#             └── risk adjustment using PenaltyModel.marginal_penalty()
#
# USAGE:
#     Precise import (preferred inside framework):
#         from economics.dispatch_optimizer import DispatchOptimizer
#         from economics.flexibility_ledger import FlexibilityLedger
#         from economics.command_arbiter import CommandArbiter
#
#     Convenience import (acceptable in main.py):
#         from economics import DispatchOptimizer, FlexibilityLedger
# ============================================================================

"""Economics package — the decision-making core of the agent framework.

This package answers the central question: given what the device CAN do
(from devices/) and what the market WANTS (from markets/), what SHOULD
the device do?

The answer flows through a pipeline:
    1. Preference curves translate customer intent into price-responsive
       demand (or supply) curves.
    2. The planning optimizer determines the optimal multi-interval
       schedule, producing V_stored for batteries.
    3. The flexibility ledger ensures bids don't overcommit capacity.
    4. During delivery, the dispatch optimizer resolves competing
       obligations into a single optimal operating point.
    5. The command arbiter translates that point into a device command
       and actuates it — the only write to the simulator.

Penalty models thread through the entire pipeline: they shape bids
(risk adjustment), drive dispatch priority (which delivery to curtail),
and settle accounts (reconciliation).
"""

# -- Preference / Offer Curves -----------------------------------------------
from economics.preference_curves import (
    BidirectionalPreferenceCurve,
    IsoelasticPreferenceCurve,
)

# -- Penalty Models -----------------------------------------------------------
from economics.penalty_models import (
    CompoundPenaltyModel,
    ProportionalPenaltyModel,
    ScoredPenaltyModel,
    TieredPenaltyModel,
)

# -- Flexibility Ledger -------------------------------------------------------
from economics.flexibility_ledger import (
    DisplaceableBlock,
    EconomicEnvelope,
    FlexibilityLedger,
)

# -- Dispatch Optimizer (F15 + F16) -------------------------------------------
from economics.dispatch_optimizer import (
    DeliveryValueCalculator,
    DispatchOptimizer,
)

# -- Command Arbiter ----------------------------------------------------------
from economics.command_arbiter import (
    CommandArbiter,
    DeliveryRecord,
)

# -- Planning Optimizer -------------------------------------------------------
from economics.planning_optimizer import PlanningOptimizer

__all__ = [
    # Preference curves
    "IsoelasticPreferenceCurve",
    "BidirectionalPreferenceCurve",
    # Penalty models
    "ProportionalPenaltyModel",
    "TieredPenaltyModel",
    "ScoredPenaltyModel",
    "CompoundPenaltyModel",
    # Flexibility ledger
    "FlexibilityLedger",
    "DisplaceableBlock",
    "EconomicEnvelope",
    # Dispatch
    "DeliveryValueCalculator",
    "DispatchOptimizer",
    # Command arbiter
    "CommandArbiter",
    "DeliveryRecord",
    # Planning
    "PlanningOptimizer",
]