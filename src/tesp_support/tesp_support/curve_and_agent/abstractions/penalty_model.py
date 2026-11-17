# ============================================================================
# FILE: abstractions/penalty_model.py
# PURPOSE: Abstract base class for non-delivery penalty functions
#          (agent function F14).
#
# Each market product has its own penalty structure that defines the
# economic cost of failing to deliver on a cleared commitment.  The
# structure is provided by the Market Operator as part of market
# registration.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Used by: AbstractFlexibilityLedger (displacement cost calculation)
#                AbstractDeliveryValueCalculator (penalty_fn in economics)
#                AbstractDispatchOptimizer (penalty terms in objective)
#                AbstractCommandArbiter (passes to value calculator)
#                AbstractDeviceAgent.formulate_bid() (risk-adjusted bidding)
#                AbstractDeviceAgent.reconcile() (settlement computation)
#
# IMPORTS FROM:
#     - typing: Any
#     - enums_and_constants: MarketType
# ============================================================================

"""Abstract penalty model — defines the cost of non-delivery.

Concrete implementations support different penalty structures:
    ProportionalPenaltyModel — rate × shortfall (RT/DA energy)
    TieredPenaltyModel       — band-dependent rates
    ScoredPenaltyModel       — performance score (regulation)
    CompoundPenaltyModel     — fixed + proportional (reserves)
"""

from abc import ABC, abstractmethod
from typing import Any

from enums_and_constants import MarketType

class AbstractPenaltyModel(ABC):
    """Abstract base for non-delivery penalty functions.

    Every market product has a penalty model that defines the economic
    cost of failing to deliver on a cleared commitment.  The model is
    provided by the Market Operator as part of market registration.

    Args:
        market_type: The market product this penalty applies to.
            EXTERNAL: From MO market rules.
    """

    def __init__(self, market_type: MarketType):
        self._market_type = market_type

    @abstractmethod
    def compute_penalty(
        self,
        committed_qty: float,
        actual_qty: float,
        cleared_price: float,
        interval_duration: float,
        **kwargs: Any,
    ) -> float:
        """Compute the penalty for a given shortfall.

        Args:
            committed_qty: What was committed (kW).
            actual_qty: What was delivered (kW).
            cleared_price: The market clearing price ($/kWh or $/kW).
            interval_duration: Duration of the delivery interval (seconds).
            **kwargs: Product-specific extras (e.g., regulation signal
                for scored penalties).

        Returns:
            Penalty cost ($).
        """
        ...

    @abstractmethod
    def marginal_penalty(
        self,
        committed_qty: float,
        cleared_price: float,
        interval_duration: float,
    ) -> float:
        """Marginal penalty rate at the first kW of shortfall.

        Used for fast comparison across products in the dispatch optimizer
        and flexibility ledger displacement cost calculations.

        Args:
            committed_qty: Committed quantity (kW).
            cleared_price: Clearing price ($/kWh or $/kW).
            interval_duration: Interval duration (seconds).

        Returns:
            Marginal penalty rate ($/kW).
        """
        ...
