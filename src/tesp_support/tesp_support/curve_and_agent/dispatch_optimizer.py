# ============================================================================
# FILE: dispatch_optimizer.py
# PURPOSE: Single-timestep economic dispatch optimization.
#          Replaces fixed-priority resolution in the Command Arbiter.
#          Determines optimal device operating point by maximizing total
#          net value across simultaneously active deliveries.
#
# INTERNAL: Consumed by CommandArbiter.resolve_and_actuate().
# ============================================================================

from typing import Dict, List, Optional, Tuple
from data_types import (
    DeliveryEconomics, DispatchSolution, FlexibilityEnvelope
)
from preference_curve import PreferenceCurve


class DispatchOptimizer:
    """Solves the per-timestep dispatch optimization.
    
    Maximizes:
        Σ revenue_m(Q_m) - Σ penalty_m(committed_m, actual_m) - C_amenity(Q)
    
    Subject to:
        Q_min ≤ Q ≤ Q_max
        Regulation and reserve capacity constraints
        Signal-following constraints for regulation
    
    For ≤2 simultaneous products: solved analytically.
    For 3+ products: solved as LP/QP.
    """

    def solve(
        self,
        economics: Dict[str, DeliveryEconomics],
        Q_min: float,
        Q_max: float,
        preference_curve: PreferenceCurve,
        amenity_weight: float,
        current_signals: Optional[Dict[str, float]] = None
    ) -> DispatchSolution:
        """Solve the dispatch optimization for the current timestep.
        
        Args:
            economics: Per-market delivery economics.
                INTERNAL: From DeliveryValueCalculator (F15).
                Keys are market_ids, values are DeliveryEconomics.
            Q_min: Physical minimum operating point (kW).
                For batteries, negative (max discharge).
                INTERNAL: From device state / FlexibilityEnvelope.
            Q_max: Physical maximum operating point (kW).
                INTERNAL: From device state / FlexibilityEnvelope.
            preference_curve: Customer preference curve for amenity cost.
                INTERNAL: From PreferenceCurve (F3).
            amenity_weight: Weight on amenity cost, derived from k.
                INTERNAL: From customer preference.
            current_signals: Real-time signals for fast-response products.
                Keys: 'regulation_signal' (float, -1 to +1),
                      'reserve_activated' (bool as float).
                EXTERNAL: From MO or ISO signal feed.
        
        Returns:
            DispatchSolution with optimal Q, per-market allocation,
            displacement chain, and total net value.
        """
        raise NotImplementedError


class DeliveryValueCalculator:
    """Computes per-delivery economic profiles for the dispatch optimizer
    (Agent Function F15).
    
    Normalizes the heterogeneous economics of different product types
    (energy, regulation, reserve) into a common DeliveryEconomics
    representation.
    """

    def compute(
        self,
        market_id: str,
        product_type: str,
        committed_qty: float,
        cleared_price: float,
        penalty_model: 'PenaltyModel',
        interval_duration: float,
        signals: Optional[Dict[str, float]] = None,
        degradation_cost: float = 0.0
    ) -> DeliveryEconomics:
        """Compute delivery economics for one active delivery.
        
        Args:
            market_id: ID of the market.
            product_type: Energy, regulation, or reserve.
                INTERNAL: From MarketObject.
            committed_qty: Committed power (kW).
                INTERNAL: From MarketObject.cleared_quantity.
            cleared_price: Clearing price ($/kWh or $/kW).
                INTERNAL: From MarketObject.cleared_price.
            penalty_model: Applicable penalty model.
                INTERNAL: From PenaltyModel registry.
            interval_duration: Delivery interval length (seconds).
            signals: Real-time market signals (regulation signal value,
                reserve activation flag).
                EXTERNAL: From MO or ISO.
            degradation_cost: For batteries, marginal degradation cost.
                INTERNAL: From BatteryModel.marginal_degradation_cost().
        
        Returns:
            DeliveryEconomics with revenue, penalty, and net value functions.
        """
        raise NotImplementedError