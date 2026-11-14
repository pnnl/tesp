# ============================================================================
# FILE: economics/flexibility_ledger.py
# PURPOSE: Concrete implementation of the capacity commitment tracking
#          and availability query system (agent function F6).
#
# The flexibility ledger is the single source of truth for how much of
# the device's operating range is currently committed to market
# obligations.  It prevents the agent from overcommitting its finite
# physical capacity across multiple simultaneously active markets.
#
# COMMITMENT LIFECYCLE:
#     Every capacity commitment progresses through four statuses:
#
#         TENTATIVE → ADVISORY → FIRM → RELEASED
#
#     TENTATIVE (created during NEGOTIATION):
#         A bid has been submitted but the market has not yet cleared.
#         The commitment is speculative — it may or may not become
#         real depending on the clearing outcome.  Used at a baseline
#         probability weight (default 0.3–0.5) in expected availability
#         calculations.
#
#     ADVISORY (created during ASSESSMENT, informational iteration):
#         An informational market clear has occurred.  The commitment
#         represents the agent's best estimate of what will become a
#         firm obligation if the market converges and clears bindingly.
#         Weighted by the convergence confidence (0.0–1.0) in expected
#         availability calculations.  Confidence increases with each
#         successive informational iteration as prices stabilize.
#
#     FIRM (created during DELIVERY_LEAD, binding iteration):
#         The market has cleared bindingly.  The commitment is
#         obligatory — the agent must deliver or pay a penalty.
#         Fully deducted from all availability tiers.  Cannot be
#         unilaterally released before reconciliation.
#
#     RELEASED (created during RECONCILE):
#         Delivery is complete and reconciled.  The capacity is freed
#         for future use.  Released commitments are retained briefly
#         for audit and then purged.
#
#     At each status transition, the previous status record for the
#     same market_id is replaced (not accumulated).  This means that
#     during informational iterations, each new advisory replaces the
#     previous one — the ledger always reflects the latest estimate.
#
# THREE-TIER AVAILABILITY QUERIES:
#
#     TIER 1 — HARD AVAILABILITY
#         hard_available(interval, excluding) → (Q_min_avail, Q_max_avail)
#
#         Deducts ALL commitments (tentative + advisory + firm) at
#         full face value.  This is the most conservative estimate:
#         "What is guaranteed to be free even if every pending
#         commitment materializes?"
#
#         Use cases:
#           - Delivery Lead: final feasibility check before booking firm.
#           - Dispatch optimizer: physical limits during delivery.
#
#     TIER 2 — EXPECTED AVAILABILITY
#         expected_available(interval, excluding) → (Q_min_avail, Q_max_avail)
#
#         Deducts firm commitments at 100%.
#         Deducts advisory commitments weighted by their confidence.
#         Deducts tentative commitments at a baseline probability.
#
#         This provides a realistic planning estimate that accounts
#         for probable future obligations without being as pessimistic
#         as the hard tier.
#
#         Use cases:
#           - Active phase: determining how much flexibility to show
#             in the upcoming bid.
#           - Negotiation: baseline for conservative bid formulation.
#
#     TIER 3 — ECONOMIC AVAILABILITY
#         economic_available(interval, candidate_value, candidate_penalty,
#                           excluding) → EconomicEnvelope
#
#         Starts from hard availability, then identifies existing
#         commitments that could be DISPLACED if the new use has
#         higher net value.  Displacement is profitable when:
#
#             candidate_value − displacement_cost > 0
#
#         Where displacement_cost = marginal_penalty − marginal_net_value
#         of the existing commitment.  For advisory commitments, the
#         expected penalty is discounted by (1 − confidence): if the
#         advisory may not become binding, the expected displacement
#         cost is lower.
#
#         Returns an EconomicEnvelope containing:
#           - Hard availability (the guaranteed-free portion)
#           - A sorted list of DisplaceableBlocks (cheapest first)
#           - Soft availability (hard + total displaceable)
#
#         This forms a displacement supply curve: a merit-order stack
#         of capacity that could be freed, ordered by the cost of
#         freeing it.
#
#         Use cases:
#           - Negotiation: risk-adjusted / aggressive bid formulation.
#             The agent may bid capacity that is already tentatively
#             or advisorily committed to another market if the expected
#             net gain (new revenue minus displacement penalty) is
#             positive.
#           - The customer preference parameter k modulates how far
#             up the displacement curve the agent is willing to go:
#             k=0 → uses only hard availability (no displacement risk)
#             k=1 → uses full economic availability (maximum aggression)
#
# ECONOMIC ANNOTATIONS ON COMMITMENTS:
#     Each commitment carries economic metadata that enables the
#     displacement cost calculation:
#
#         cleared_price   — the price at which this commitment was cleared.
#         marginal_nv     — marginal net value per kW of delivering this
#                           commitment (revenue minus cost, at cleared price).
#         marginal_pen    — marginal penalty per kW of non-delivery (from
#                           the applicable penalty model).
#         confidence      — for advisory commitments, the convergence
#                           confidence from the informational iteration.
#         iteration       — which iteration produced this commitment.
#         penalty_model_id— reference to the penalty model that governs
#                           this commitment's non-delivery cost.
#
#     These annotations are populated when the commitment is created
#     and used by the Tier 3 query to compute displacement costs
#     without needing to look up penalty models at query time.
#
# EXCLUDING PARAMETER:
#     All three availability methods accept an optional 'excluding'
#     market_id.  This is used when the agent is re-bidding for a
#     market that already has a tentative or advisory commitment on
#     the ledger.  Without exclusion, the market's own previous
#     commitment would be deducted from the availability shown to
#     its own bid formulation — the agent would be competing against
#     itself.  The excluding parameter removes the specified market's
#     commitment from the deduction, giving the bid formulation a
#     clean view of capacity available for that market.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from: abstractions.flexibility_ledger.AbstractFlexibilityLedger
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - agent.py (DeviceAgent):
#         _handle_active():       Calls expected_available() to determine
#                                 how much flexibility to expose.
#         _handle_negotiation():  Calls hold_tentative() after submitting
#                                 a bid.  May call economic_available()
#                                 for risk-adjusted bidding.
#         _handle_assessment():   Calls update_advisory() after an
#                                 informational clear.
#         _handle_delivery_lead():Calls book_firm() after a binding clear.
#                                 May call hard_available() for a final
#                                 feasibility check.
#         _handle_reconcile():    Calls release() to free the capacity.
#
#     - economics/dispatch_optimizer.py:
#         The dispatch optimizer does not query the ledger directly
#         during delivery.  Instead, it operates on the physical
#         device envelope (Q_min, Q_max from the device model).  The
#         ledger's role is upstream — it shapes what gets committed
#         in the first place.
#
#     - economics/penalty_models.py:
#         Penalty models are referenced (by ID) in commitment records
#         and their marginal_penalty() method is called during Tier 3
#         displacement cost calculations.
#
#     - economics/command_arbiter.py:
#         The command arbiter does not interact with the ledger.  It
#         operates on the set of active deliveries (which correspond
#         to firm commitments) but does not modify the ledger.
#
#     - forecasting/price_forecast_service.py:
#         Advisory commitments are valued using the price from the
#         informational clear.  The price forecast service may also
#         inform the marginal_nv annotation by providing expected
#         prices for future intervals.
#
# DATA TYPES USED:
#     From data_types.py:
#         EconomicCommitment — the commitment record stored in the ledger.
#     From enums_and_constants.py:
#         CommitmentStatus   — TENTATIVE, ADVISORY, FIRM, RELEASED.
#         MarketType         — identifies the market product.
#         ProductType        — ENERGY_BASE, REGULATION_UP/DOWN,
#                              RESERVE_UP/DOWN.
#     From economics/flexibility_ledger.py (this file):
#         DisplaceableBlock  — a block of capacity that could be freed.
#         EconomicEnvelope   — extended availability with displacement options.
#
# EXTERNAL INPUTS:
#     Q_min_device, Q_max_device:
#         Physical power limits of the device (kW).  Set once at
#         initialization from the first state observation.  For
#         batteries, Q_min is negative (max discharge).
#         INTERNAL: From FlexibilityEnvelope or device specifications.
#
#     All commitment data is INTERNAL — produced by the agent's own
#     bid formulation, assessment, and delivery lead processing.
#     No external system writes to the ledger directly.
# ============================================================================

"""Concrete flexibility ledger — capacity accounting across all markets.

The ledger ensures that the agent never promises more capacity than
the device physically has.  It provides three levels of availability
query to support different decision contexts:

    HARD     — absolute ceiling, all commitments deducted
    EXPECTED — realistic planning, advisory weighted by confidence
    ECONOMIC — aggressive bidding, includes displaceable capacity

The ledger is the shared resource (along with the Command Arbiter) that
provides cross-market consistency.  Individual market state machines
are independent; the ledger is where their interactions are accounted for.
"""

from typing import Any, Dict, List, Optional, Tuple

from abstractions.flexibility_ledger import AbstractFlexibilityLedger
from data_types import EconomicCommitment
from enums_and_constants import CommitmentStatus, MarketType, ProductType

from tesp_support.tesp_support.curve_and_agent.abstractions.abstract_bases import AbstractFlexibilityLedger

from ..data_types import EconomicCommitment
from ..enums_and_constants import CommitmentStatus, MarketType, ProductType


class DisplaceableBlock:
    """A block of capacity that could be freed by displacing an existing
    commitment, along with the cost of doing so.

    Attributes:
        source_market: Market ID of the commitment that could be displaced.
        source_status: Current status of that commitment.
        quantity: How much capacity could be freed (kW).
        displacement_cost: Net cost of displacing ($/kW).
            = marginal_penalty - marginal_net_value of the displaced commitment.
        net_gain: Expected net gain from displacement ($/kW).
            = candidate_value - displacement_cost.
    """

    def __init__(
        self,
        source_market: str,
        source_status: CommitmentStatus,
        quantity: float,
        displacement_cost: float,
        net_gain: float,
    ):
        self.source_market = source_market
        self.source_status = source_status
        self.quantity = quantity
        self.displacement_cost = displacement_cost
        self.net_gain = net_gain


class EconomicEnvelope:
    """Extended flexibility envelope including displaceable capacity.

    Attributes:
        hard_Q_min_avail: Hard minimum (all commitments deducted).
        hard_Q_max_avail: Hard maximum (all commitments deducted).
        displaceable_blocks: Sorted list of capacity that could be freed.
        total_displaceable: Sum of all displaceable kW.
        soft_Q_max_avail: hard_Q_max + total_displaceable.
    """

    def __init__(
        self,
        hard_Q_min_avail: float,
        hard_Q_max_avail: float,
        displaceable_blocks: list[DisplaceableBlock] | None = None,
        total_displaceable: float = 0.0,
        soft_Q_max_avail: float = 0.0,
    ):
        self.hard_Q_min_avail = hard_Q_min_avail
        self.hard_Q_max_avail = hard_Q_max_avail
        self.displaceable_blocks = displaceable_blocks or []
        self.total_displaceable = total_displaceable
        self.soft_Q_max_avail = soft_Q_max_avail


class FlexibilityLedger(AbstractFlexibilityLedger):
    """Tracks capacity commitments across all markets and provides
    three-tier availability queries.

    This is the single source of truth for "how much of the device's
    operating range is currently spoken for."

    The three tiers:
    1. HARD: Physical capacity minus ALL commitments (tentative,
       advisory, and firm). Guarantees zero conflict.
    2. EXPECTED: Deducts firm fully, advisory weighted by confidence,
       tentative at a baseline probability. Realistic planning estimate.
    3. ECONOMIC: Capacity that could be freed by displacing lower-value
       commitments, net of penalty costs.

    Args:
        Q_min_device: Physical minimum power (kW). For batteries, negative.
        Q_max_device: Physical maximum power (kW).
    """

    def __init__(self, Q_min_device: float, Q_max_device: float):
        self._Q_min = Q_min_device
        self._Q_max = Q_max_device
        self._commitments: list[EconomicCommitment] = []
        self._tentative_weight: float = 0.4

    def hold_tentative(
        self,
        market_id: str,
        market_type: MarketType,
        product_type: ProductType,
        quantity: float,
        interval: tuple[float, float],
        cleared_price: float = 0.0,
        penalty_model_id: str = "",
    ) -> None:
        """Record a tentative commitment when a bid is submitted.

        Replaces any existing tentative/advisory for the same market_id.

        Args:
            market_id: ID of the market.
            market_type: Type of market product.
            product_type: Energy, reg up/down, reserve up/down.
            quantity: Bid quantity (kW).
            interval: (start_time, end_time) of delivery.
            cleared_price: Expected price (for economic calculations).
            penalty_model_id: Reference to applicable penalty model.
        """
        self._commitments = [c for c in self._commitments if c.market_id != market_id]
        self._commitments.append(
            EconomicCommitment(
                market_id=market_id,
                market_type=market_type,
                product_type=product_type,
                quantity=quantity,
                interval=interval,
                status=CommitmentStatus.TENTATIVE,
                cleared_price=cleared_price,
                penalty_model_id=penalty_model_id,
            )
        )

    def update_advisory(
        self,
        market_id: str,
        quantity: float,
        interval: tuple[float, float],
        confidence: float,
        cleared_price: float,
        penalty_model_id: str,
        iteration: int,
        marginal_nv: float = 0.0,
        marginal_pen: float = 0.0,
    ) -> None:
        """Create or update an advisory commitment after informational clear.

        Replaces any existing tentative/advisory for the same market_id.

        Args:
            market_id: ID of the market.
            quantity: Projected operating point (kW).
            interval: Delivery interval.
            confidence: Convergence confidence (0–1).
                INTERNAL: From convergence tracker computation.
            cleared_price: Informational clearing price.
                INTERNAL: From MO clearing result.
            penalty_model_id: Penalty model reference.
            iteration: Iteration number.
            marginal_nv: Marginal net value ($/kW).
            marginal_pen: Marginal penalty ($/kW).
        """
        self._commitments = [c for c in self._commitments if c.market_id != market_id]
        self._commitments.append(
            EconomicCommitment(
                market_id=market_id,
                quantity=quantity,
                interval=interval,
                status=CommitmentStatus.ADVISORY,
                confidence=confidence,
                cleared_price=cleared_price,
                penalty_model_id=penalty_model_id,
                iteration=iteration,
                marginal_nv=marginal_nv,
                marginal_pen=marginal_pen,
            )
        )

    def book_firm(
        self,
        market_id: str,
        quantity: float,
        interval: tuple[float, float],
        cleared_price: float,
        penalty_model_id: str,
        marginal_nv: float = 0.0,
        marginal_pen: float = 0.0,
    ) -> None:
        """Convert a commitment to firm status after binding clear.

        Args:
            market_id: ID of the market.
            quantity: Cleared quantity (kW).
            interval: Delivery interval.
            cleared_price: Binding clearing price.
                INTERNAL: From MO binding clearing result.
            penalty_model_id: Penalty model reference.
            marginal_nv: Marginal net value at cleared price.
            marginal_pen: Marginal penalty rate.
        """
        self._commitments = [c for c in self._commitments if c.market_id != market_id]
        self._commitments.append(
            EconomicCommitment(
                market_id=market_id,
                quantity=quantity,
                interval=interval,
                status=CommitmentStatus.FIRM,
                cleared_price=cleared_price,
                penalty_model_id=penalty_model_id,
                marginal_nv=marginal_nv,
                marginal_pen=marginal_pen,
            )
        )

    def release(self, market_id: str) -> None:
        """Release a commitment after reconciliation.

        Args:
            market_id: ID of the market to release.
        """
        self._commitments = [c for c in self._commitments if c.market_id != market_id]

    def hard_available(
        self, time_interval: tuple[float, float], excluding: str | None = None
    ) -> tuple[float, float]:
        """TIER 1: Hard availability. Deducts ALL commitments.

        Args:
            time_interval: (start, end) of the query interval.
            excluding: Market ID to exclude from the calculation.
                Used when re-bidding for the same market.

        Returns:
            (Q_min_avail, Q_max_avail) in kW.
        """
        committed = 0.0
        for c in self._overlapping(time_interval, excluding):
            committed += c.quantity
        return (self._Q_min, self._Q_max - committed)

    def expected_available(
        self, time_interval: tuple[float, float], excluding: str | None = None
    ) -> tuple[float, float]:
        """TIER 2: Expected availability. Weights advisory by confidence.

        Args:
            time_interval: Query interval.
            excluding: Market ID to exclude.

        Returns:
            (Q_min_avail, Q_max_avail) in kW.
        """
        weighted = 0.0
        for c in self._overlapping(time_interval, excluding):
            if c.status == CommitmentStatus.FIRM:
                weighted += c.quantity
            elif c.status == CommitmentStatus.ADVISORY:
                weighted += c.quantity * c.confidence
            elif c.status == CommitmentStatus.TENTATIVE:
                weighted += c.quantity * self._tentative_weight
        return (self._Q_min, self._Q_max - weighted)

    def economic_available(
        self,
        time_interval: tuple[float, float],
        candidate_value: float,
        candidate_penalty: float,
        excluding: str | None = None,
    ) -> EconomicEnvelope:
        """TIER 3: Economic availability including displaceable capacity.

        Args:
            time_interval: Query interval.
            candidate_value: Marginal value of the proposed new use ($/kW).
            candidate_penalty: Marginal penalty of the proposed new use.
            excluding: Market ID to exclude.

        Returns:
            EconomicEnvelope with hard availability plus displacement options.
        """
        _, hard_max = self.hard_available(time_interval, excluding)
        hard_min = self._Q_min

        blocks = []
        for c in self._overlapping(time_interval, excluding):
            if c.status in (CommitmentStatus.ADVISORY, CommitmentStatus.TENTATIVE):
                disp_cost = c.marginal_pen - c.marginal_nv
                net_gain = candidate_value - disp_cost
                if net_gain > 0:
                    blocks.append(
                        DisplaceableBlock(
                            source_market=c.market_id,
                            source_status=c.status,
                            quantity=c.quantity,
                            displacement_cost=disp_cost,
                            net_gain=net_gain,
                        )
                    )
        blocks.sort(key=lambda b: b.displacement_cost)
        total_disp = sum(b.quantity for b in blocks)

        return EconomicEnvelope(
            hard_Q_min_avail=hard_min,
            hard_Q_max_avail=hard_max,
            displaceable_blocks=blocks,
            total_displaceable=total_disp,
            soft_Q_max_avail=hard_max + total_disp,
        )

    def get_commitments_overlapping(
        self, time_interval: tuple[float, float]
    ) -> list[EconomicCommitment]:
        """Get all commitments that overlap a time interval.

        Args:
            time_interval: (start, end) to check.

        Returns:
            List of overlapping EconomicCommitment records.
        """
        return self._overlapping(time_interval)

    def _overlapping(
        self, time_interval: tuple[float, float], excluding: str | None = None
    ) -> list[EconomicCommitment]:
        """Internal: commitments overlapping interval, optionally excluding one."""
        t_start, t_end = time_interval
        result = []
        for c in self._commitments:
            if excluding and c.market_id == excluding:
                continue
            c_start, c_end = c.interval
            if c_start < t_end and c_end > t_start:
                result.append(c)
        return result
