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
        params: Dict
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
        **kwargs
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
        raise NotImplementedError

    def marginal_penalty(
        self,
        committed_qty: float,
        cleared_price: float,
        interval_duration: float
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
        raise NotImplementedError