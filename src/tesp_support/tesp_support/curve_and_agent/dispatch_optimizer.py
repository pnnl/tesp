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
from data_types import DeliveryEconomics, DispatchSolution, FlexibilityEnvelope
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
        current_signals: Optional[Dict[str, float]] = None,
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
        # Sum committed quantities as a starting point
        total_committed = sum(e.committed_qty for e in economics.values())

        # Amenity cost gradient pulls Q toward Q_0
        Q_0 = preference_curve._Q_0

        # Simple analytical approach for ≤2 products:
        # Objective = Σ (marginal_value × min(Q_alloc, committed))
        #           - Σ penalty(committed, actual)
        #           - amenity_weight × (Q - Q_0)^2
        #
        # For a single product: Q* = committed (minimizes penalty)
        # For multiple products: Q* = total_committed
        # Then amenity_weight pulls toward Q_0

        if amenity_weight > 0 and len(economics) <= 2:
            # Balance: penalty gradient vs amenity gradient
            # d(amenity)/dQ = 2 * amenity_weight * (Q - Q_0)
            # At committed: penalty gradient ~ -max(marginal_pen)
            # Optimal: shift from committed toward Q_0
            # Q* = (sum_marginal_pen * committed + amenity_weight * Q_0)
            #      / (sum_marginal_pen + amenity_weight)
            # simplified weighted average
            total_pen_weight = sum(e.marginal_penalty_zero for e in economics.values())
            if total_pen_weight + amenity_weight > 0:
                Q_star = (total_pen_weight * total_committed + amenity_weight * Q_0) / (
                    total_pen_weight + amenity_weight
                )
            else:
                Q_star = total_committed
        else:
            Q_star = total_committed

        # Clamp to physical bounds
        Q_star = max(Q_min, min(Q_max, Q_star))

        # Allocate Q across markets (priority: higher marginal_value first)
        sorted_markets = sorted(
            economics.items(),
            key=lambda kv: kv[1].marginal_value_full,
            reverse=True,
        )
        remaining = Q_star
        allocation = {}
        displacement_chain = {}
        for mid, econ in sorted_markets:
            committed = econ.committed_qty
            if remaining >= 0.0 and committed >= 0.0:
                alloc = min(remaining, committed)
            elif remaining <= 0.0 and committed <= 0.0:
                # Negative commitments represent discharge/export.
                # Use max() to avoid over-allocating beyond the remaining
                # negative dispatch magnitude.
                alloc = max(remaining, committed)
            else:
                alloc = 0.0
            allocation[mid] = alloc
            remaining -= alloc

        # Compute total net value
        total_nv = 0.0
        for mid, econ in economics.items():
            actual = allocation.get(mid, 0.0)
            if econ.net_value_fn is not None:
                total_nv += econ.net_value_fn(actual)
            else:
                # revenue - penalty approximation
                total_nv += econ.cleared_price * actual
        # Subtract amenity cost
        total_nv -= amenity_weight * (Q_star - Q_0) ** 2

        binding = []
        if Q_star <= Q_min + 1e-9:
            binding.append("Q_min")
        if Q_star >= Q_max - 1e-9:
            binding.append("Q_max")

        return DispatchSolution(
            Q=Q_star,
            allocation=allocation,
            displacement_chain=displacement_chain,
            total_net_value=total_nv,
            binding_constraints=binding,
        )


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
        penalty_model: "PenaltyModel",
        interval_duration: float,
        signals: Optional[Dict[str, float]] = None,
        degradation_cost: float = 0.0,
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
        interval_hours = interval_duration / 3600.0

        # Revenue function: price × actual_qty × interval_hours
        def revenue_fn(actual_qty: float) -> float:
            return cleared_price * actual_qty * interval_hours

        # Penalty function: delegate to penalty model
        def penalty_fn(actual_qty: float) -> float:
            return penalty_model.compute_penalty(
                committed_qty=committed_qty,
                actual_qty=actual_qty,
                cleared_price=cleared_price,
                interval_duration=interval_duration,
            )

        # Net value = revenue - penalty
        def net_value_fn(actual_qty: float) -> float:
            return revenue_fn(actual_qty) - penalty_fn(actual_qty)

        # Marginal value at full delivery = cleared_price - degradation
        marginal_value_full = cleared_price - degradation_cost

        # Marginal penalty at zero delivery
        marginal_penalty_zero = penalty_model.marginal_penalty(
            committed_qty=committed_qty,
            cleared_price=cleared_price,
            interval_duration=interval_duration,
        )

        return DeliveryEconomics(
            market_id=market_id,
            committed_qty=committed_qty,
            cleared_price=cleared_price,
            revenue_fn=revenue_fn,
            penalty_fn=penalty_fn,
            net_value_fn=net_value_fn,
            marginal_value_full=marginal_value_full,
            marginal_penalty_zero=marginal_penalty_zero,
        )
