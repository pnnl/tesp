# ============================================================================
# FILE: economics/penalty_model.py
# PURPOSE: Concrete implementations of non-delivery penalty functions
#          (agent function F14).
#
# This module provides four penalty model implementations covering
# the penalty structures used by common electricity market products.
# Each model defines the economic cost a device agent incurs for
# failing to deliver on a cleared market commitment.
#
# Penalty models are provided by the Market Operator as part of
# market registration — the agent does not choose or configure them.
# They are an input that encodes market rules.
#
# FOUR PENALTY STRUCTURES:
#
#     ProportionalPenaltyModel
#         penalty = rate × |committed − actual| × Δt
#
#         The rate is either a fixed value ($/kWh) or a multiple of
#         the cleared price (e.g., 2× the cleared price).
#
#         Typical use: RT energy (2× cleared price), DA energy
#         (1.0–1.5× the RT-DA price differential).
#
#         This is the simplest and most common structure.  Every kW
#         of shortfall costs the same amount.  There is no threshold
#         below which shortfall is forgiven, and no escalation for
#         large shortfalls.
#
#     TieredPenaltyModel
#         penalty = Σ_tier (rate_tier × shortfall_in_tier × Δt)
#
#         Different penalty rates apply to different bands of shortfall
#         as a fraction of the committed quantity.  For example:
#             First 10% shortfall:  1.0× cleared price
#             10–25% shortfall:     2.0× cleared price
#             Beyond 25% shortfall: 5.0× cleared price
#
#         Typical use: Markets that tolerate small deviations but
#         penalize large ones severely.  Encourages agents to deliver
#         "most" of their commitment even if they can't deliver all.
#
#         The tiers are defined as a list of (threshold_fraction, rate)
#         tuples, ordered by increasing threshold.  The rate applies
#         to shortfall between the previous threshold and this one.
#
#     ScoredPenaltyModel
#         score = score_fn(committed, actual, signal)  → float ∈ [0, 1]
#         penalty = score_to_cost_fn(score, capacity_payment)
#
#         Instead of a direct financial penalty per kW of shortfall,
#         the penalty is indirect: poor performance degrades a
#         continuous quality score, which reduces the capacity
#         payment the agent receives.  A perfect score (1.0) means
#         full payment; a zero score means no payment.
#
#         Typical use: Frequency regulation markets (e.g., PJM's
#         RegD performance score).  The score measures how accurately
#         the device followed the regulation signal:
#             score = correlation(actual_response, requested_response)
#                   × delay_penalty × precision_penalty
#
#         The score_fn and score_to_cost_fn are provided as callables
#         in the params dictionary, since their exact form varies by
#         ISO/RTO and market design.
#
#         For the dispatch optimizer, the marginal penalty is
#         approximated by linearizing the score function around the
#         current operating point.
#
#     CompoundPenaltyModel
#         penalty = fixed_penalty (if triggered)
#                 + proportional_rate × |committed − actual| × Δt
#
#         Combines a one-time fixed penalty (triggered when shortfall
#         exceeds a threshold or when a specific event occurs) with
#         a proportional component.
#
#         Typical use: Spinning reserve markets.
#             - If reserve is NOT activated: only an availability
#               penalty applies (proportional to capacity shortfall).
#               The fixed_penalty is zero.
#             - If reserve IS activated and the device fails to
#               deliver: a large fixed penalty is assessed (reliability
#               event) PLUS a proportional energy shortfall penalty.
#
#         The activation status is passed via **kwargs in
#         compute_penalty() (key: 'activated', value: bool).
#
# MARGINAL PENALTY:
#     All four models implement marginal_penalty(), which returns the
#     marginal penalty rate ($/kW) at the first kW of shortfall.  This
#     is used for fast comparison across products in:
#
#     - The dispatch optimizer's objective function (F16): penalty
#       terms for each active delivery.
#     - The flexibility ledger's displacement cost calculation (F6):
#       comparing the cost of displacing one market's commitment
#       against the value of another.
#     - Risk-adjusted bid formulation (F4): estimating the expected
#       penalty from oversubscription.
#
#     For ProportionalPenaltyModel, marginal_penalty equals the rate.
#     For TieredPenaltyModel, it equals the first tier's rate.
#     For ScoredPenaltyModel, it is a linearized approximation.
#     For CompoundPenaltyModel, it equals the proportional rate
#     (the fixed component is not marginal).
#
# RELATIONSHIP TO ABSTRACTIONS:
#     All four classes inherit from:
#         abstractions.penalty_model.AbstractPenaltyModel
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - agent.py (DeviceAgent):
#         register_market() stores the penalty model for each market
#         product.  The model is passed through to:
#             formulate_bid() (F4) — for risk-adjusted bidding, the
#                 agent queries the penalty model to estimate the cost
#                 of potential non-delivery.
#             reconcile() (F13) — the agent calls compute_penalty()
#                 with the actual delivery profile to determine the
#                 financial settlement.
#
#     - economics/dispatch_optimizer.py:
#         DeliveryValueCalculator (F15) calls compute_penalty() and
#         marginal_penalty() to build the penalty_fn inside each
#         DeliveryEconomics structure.  The dispatch optimizer (F16)
#         evaluates these functions at candidate operating points.
#
#     - economics/command_arbiter.py:
#         The command arbiter passes penalty models to the delivery
#         value calculator when computing economics for each active
#         delivery during resolve_and_actuate().
#
#     - economics/flexibility_ledger.py:
#         The ledger's economic_available() (Tier 3) query calls
#         marginal_penalty() on existing commitments to compute
#         displacement costs.  A commitment with a high marginal
#         penalty is expensive to displace; one with a low marginal
#         penalty is cheap to displace.
#
#     - markets/market_operator.py:
#         The MO does not use penalty models directly.  It defines
#         them (as part of market rules) and provides them to agents
#         during market registration.
#
#     - main.py:
#         The simulation harness constructs penalty model instances
#         with parameters from market rules and passes them to
#         DeviceAgent.register_market().
#
# DATA TYPES USED:
#     From abstractions/:
#         AbstractPenaltyModel — the contract being implemented
#     From enums_and_constants.py:
#         MarketType           — identifies which market product the
#                                penalty applies to
#         PenaltyStructureType — classification of penalty structure
#                                (used for introspection / logging,
#                                not for dispatch)
#
# EXTERNAL INPUTS:
#     All penalty parameters are EXTERNAL, provided by the Market
#     Operator as part of market rules:
#
#     ProportionalPenaltyModel:
#         rate_reference: 'fixed' or 'cleared_price_multiple'
#         multiplier: float (e.g., 2.0 for 2× cleared price)
#         base_rate: float ($/kWh, if rate_reference='fixed')
#
#     TieredPenaltyModel:
#         tiers: List[Tuple[float, float]]
#             Each tuple is (shortfall_fraction_threshold, rate).
#             Example: [(0.10, 1.0), (0.25, 2.0), (1.0, 5.0)]
#
#     ScoredPenaltyModel:
#         score_params: Dict containing:
#             score_function: Callable(committed, actual, signal) → score
#             score_to_cost: Callable(score, capacity_payment) → penalty
#             These are ISO/RTO-specific and provided as part of the
#             market product definition.
#
#     CompoundPenaltyModel:
#         fixed_penalty: float ($) — one-time penalty per event
#         proportional_rate: float ($/kWh) — per-unit shortfall rate
# ============================================================================

"""Concrete non-delivery penalty models for electricity market products.

Every market product defines a penalty structure that the device agent
must account for in its bidding, dispatch, and reconciliation.  The
penalty model is the economic encoding of "what happens if you don't
deliver what you promised."

These penalties serve three roles in the agent:
    1. **Bidding (F4):** Risk-adjusted bid formulation estimates the
       expected penalty from potential non-delivery when deciding
       whether to oversubscribe capacity.
    2. **Dispatch (F16):** The dispatch optimizer includes penalty terms
       in its objective function, ensuring that the device prioritizes
       deliveries with high penalties over those with low penalties
       when capacity is constrained.
    3. **Reconciliation (F13):** After delivery, the actual penalty is
       computed for financial settlement.

Four implementations:
    ProportionalPenaltyModel — rate × shortfall (RT/DA energy)
    TieredPenaltyModel       — escalating rates by shortfall band
    ScoredPenaltyModel       — performance score (regulation)
    CompoundPenaltyModel     — fixed + proportional (reserves)
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from abstractions.penalty_model import AbstractPenaltyModel
from enums_and_constants import MarketType, PenaltyStructureType

class PenaltyModel(AbstractPenaltyModel):
    """Defines the penalty function for non-delivery of a market commitment.

    Each market product type has its own penalty model, provided by the
    Market Operator as part of market registration.

    Args:
        market_type: The market product this penalty applies to.
        structure_type: How penalties are calculated.
        params: Structure-specific parameters.
            EXTERNAL: Provided by the MO / market rules.

            For PROPORTIONAL:
                base_rate (float): Fixed penalty rate ($/kWh or $/kW).
                rate_reference (str): 'fixed' or 'cleared_price_multiple'.
                multiplier (float): If rate_reference='cleared_price_multiple',
                    penalty_rate = multiplier × cleared_price.
            For TIERED:
                tiers (List[Tuple[float, float]]): List of
                    (shortfall_fraction_threshold, penalty_rate).
            For SCORED:
                score_function: Callable(committed, actual, signal) -> score.
                score_to_cost: Callable(score, capacity_payment) -> penalty.
            For COMPOUND:
                fixed_penalty (float): Fixed $ penalty per event.
                proportional_rate (float): Additional proportional rate.
    """

    def __init__(
        self,
        market_type: MarketType,
        structure_type: PenaltyStructureType,
        params: dict,
    ):
        self._market_type = market_type
        self._structure_type = structure_type
        self._params = params

    def compute_penalty(
        self,
        committed_qty: float,
        actual_qty: float,
        cleared_price: float,
        interval_duration: float,
        **kwargs,
    ) -> float:
        """Compute the penalty for a given shortfall.

        Args:
            committed_qty: What was committed (kW).
            actual_qty: What was actually delivered (kW).
            cleared_price: The clearing price ($/kWh or $/kW).
            interval_duration: Duration of the delivery interval (seconds).
            **kwargs: Additional arguments for scored penalties
                (regulation signal, etc.).

        Returns:
            Penalty cost ($).
        """
        shortfall = max(0.0, committed_qty - actual_qty)
        if shortfall <= 0.0:
            return 0.0

        interval_hours = interval_duration / 3600.0

        if self._structure_type == PenaltyStructureType.PROPORTIONAL:
            ref = self._params.get("rate_reference", "fixed")
            if ref == "cleared_price_multiple":
                rate = self._params["multiplier"] * cleared_price
            else:
                rate = self._params.get("base_rate", self._params.get("rate", 0.0))
            return rate * shortfall * interval_hours

        elif self._structure_type == PenaltyStructureType.TIERED:
            tiers = self._params["tiers"]
            total_cost = 0.0
            remaining_shortfall = shortfall
            for i, (threshold, rate) in enumerate(tiers):
                tier_start = threshold * committed_qty
                if i + 1 < len(tiers):
                    tier_end = tiers[i + 1][0] * committed_qty
                else:
                    tier_end = committed_qty
                tier_width = tier_end - tier_start
                kw_in_tier = min(remaining_shortfall, tier_width)
                if kw_in_tier <= 0:
                    break
                total_cost += rate * kw_in_tier * interval_hours
                remaining_shortfall -= kw_in_tier
            return total_cost

        elif self._structure_type == PenaltyStructureType.SCORED:
            score = actual_qty / committed_qty if committed_qty > 0 else 1.0
            score = max(0.0, min(1.0, score))
            max_penalty = self._params["max_penalty"]
            exponent = self._params["exponent"]
            energy = committed_qty * interval_hours
            return max_penalty * ((1.0 - score) ** exponent) * energy

        elif self._structure_type == PenaltyStructureType.COMPOUND:
            fixed = self._params["fixed_penalty"]
            prop_rate = self._params["proportional_rate"]
            energy_shortfall = shortfall * interval_hours
            return fixed + prop_rate * energy_shortfall

        return 0.0

    def marginal_penalty(
        self, committed_qty: float, cleared_price: float, interval_duration: float
    ) -> float:
        """Marginal penalty rate at the first kW of shortfall.

        Used for quick comparison across products in the dispatch
        optimizer and flexibility ledger displacement calculations.

        Args:
            committed_qty: Committed quantity (kW).
            cleared_price: Clearing price.
            interval_duration: Interval duration (seconds).

        Returns:
            Marginal penalty rate ($/kW).
        """
        interval_hours = interval_duration / 3600.0

        if self._structure_type == PenaltyStructureType.PROPORTIONAL:
            ref = self._params.get("rate_reference", "fixed")
            if ref == "cleared_price_multiple":
                rate = self._params["multiplier"] * cleared_price
            else:
                rate = self._params.get("base_rate", self._params.get("rate", 0.0))
            return rate * interval_hours

        elif self._structure_type == PenaltyStructureType.TIERED:
            tiers = self._params["tiers"]
            return tiers[0][1] * interval_hours

        elif self._structure_type == PenaltyStructureType.SCORED:
            max_penalty = self._params["max_penalty"]
            exponent = self._params["exponent"]
            return max_penalty * exponent * interval_hours

        elif self._structure_type == PenaltyStructureType.COMPOUND:
            return self._params["proportional_rate"] * interval_hours

        return 0.0
