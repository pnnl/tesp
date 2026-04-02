# ============================================================================
# FILE: penalty_model.py
# PURPOSE: Non-delivery penalty models (Agent Function F14).
#          Defines the economic cost of failing to deliver on a market
#          commitment.
#
# EXTERNAL DEPENDENCIES:
#     Penalty structures and parameters are defined by market rules,
#     provided as part of market registration by the MO.
# ============================================================================

from typing import Dict, Optional, List, Tuple, Callable
from enums_and_constants import PenaltyStructureType, MarketType


class PenaltyModel:
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
        params: Dict,
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
