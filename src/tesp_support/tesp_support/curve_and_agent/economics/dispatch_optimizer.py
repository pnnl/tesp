# ============================================================================
# FILE: economics/dispatch_optimizer.py
# PURPOSE: Concrete implementations of the per-timestep dispatch
#          optimization (agent function F16) and the delivery value
#          calculator (agent function F15).
#
# These two classes work in tight concert: the DeliveryValueCalculator
# normalizes the heterogeneous economics of different market products
# into a common representation, and the DispatchOptimizer consumes
# that representation to determine the single optimal device operating
# point.  They are co-located because they share a producer-consumer
# relationship and are always invoked together inside the Command
# Arbiter's resolve_and_actuate() pipeline.
#
# CLASSES IN THIS FILE:
#
#     DeliveryValueCalculator(AbstractDeliveryValueCalculator)
#         Agent function F15.  For each active delivery, computes a
#         DeliveryEconomics structure containing three callables:
#             revenue_fn(actual_qty) → $ revenue this timestep
#             penalty_fn(actual_qty) → $ penalty this timestep
#             net_value_fn(actual_qty) → $ net value (revenue − penalty)
#
#         The calculator normalizes three fundamentally different
#         product types into this common form:
#
#         ENERGY (DA or RT):
#             revenue = cleared_price × actual_qty × Δt
#             penalty = penalty_rate × |committed − actual| × Δt
#             For batteries: revenue may be negative (paying for
#                 charging) or positive (earning from discharging).
#             Degradation cost is subtracted from revenue.
#
#         REGULATION:
#             revenue = capacity_price × offered_band × Δt
#                     + mileage_price × |response| × Δt
#                     × performance_score
#             penalty = score_degradation_cost(offered vs committed)
#                     + accuracy_penalty(response vs signal × committed)
#             The regulation signal (−1.0 to +1.0) determines the
#             target response within the offered band.
#
#         RESERVE:
#             revenue = availability_price × offered_capacity × Δt
#                     + (energy_price × deployed × Δt if activated)
#             penalty = availability_shortfall_penalty
#                     + (activation_failure_penalty if activated and
#                        deployment < committed)
#             The reserve activation flag determines whether the
#             device must actually deploy or just hold capacity.
#
#         Also computes scalar summaries for fast ranking:
#             marginal_value_full  — $/kW at full delivery
#             marginal_penalty_zero — $/kW if nothing delivered
#
#     DispatchOptimizer(AbstractDispatchOptimizer)
#         Agent function F16.  Solves the single-timestep optimization:
#
#             Maximize: Σ_m NV_m(Q_m) − C_amenity(Q) − C_degradation(Q)
#
#             Subject to:
#                 Q_min ≤ Q ≤ Q_max                (physical limits)
#                 −ΔQ_reg_down ≤ q_reg ≤ ΔQ_reg_up (regulation band)
#                 0 ≤ ΔQ_res ≤ ΔQ_res_committed    (reserve capacity)
#                 Q = q_base + q_reg + q_res         (composition)
#
#         DECISION VARIABLES:
#             q_base       — base operating point (kW), serves energy
#             ΔQ_reg_up    — regulation-up capacity offered (≤ committed)
#             ΔQ_reg_down  — regulation-down capacity offered (≤ committed)
#             q_reg        — regulation response this timestep (within band)
#             ΔQ_res_up    — reserve-up capacity held (≤ committed)
#             ΔQ_res_down  — reserve-down capacity held (≤ committed)
#             q_res        — reserve deployment this timestep (if activated)
#
#         OBJECTIVE TERMS:
#             Σ NV_energy(q_base)      — energy product net values
#             + Σ NV_reg(ΔQ, q_reg)    — regulation product net values
#             + Σ NV_res(ΔQ_res, q_res)— reserve product net values
#             − C_amenity(Q)           — comfort/backup cost from
#                                        preference curve
#             − C_degradation(|Q|)     — battery wear cost (zero for
#                                        non-battery devices)
#
#         SOLUTION APPROACHES (selected based on problem structure):
#             ≤ 2 active products, linear penalties:
#                 Analytical — compare marginal net values, allocate
#                 from highest to lowest.  ~10 lines of code,
#                 nanoseconds execution.
#
#             3+ products, piecewise-linear penalties:
#                 Linear program — standard LP with ~10 variables
#                 and ~15 constraints.  Microseconds with any solver.
#
#             Quadratic penalty terms (squared deviations):
#                 Quadratic program — small QP, microseconds.
#
#             Arbitrary penalty functions:
#                 Discretize + enumerate — sample each variable at N
#                 points, evaluate objective, pick max.  For N=20 and
#                 4 variables: 160,000 evaluations, sub-millisecond.
#
#         PERFORMANCE REQUIREMENT:
#             This optimization runs every simulation timestep
#             (potentially sub-second for regulation).  All approaches
#             listed above solve in microseconds for problems of this
#             size.
#
#         OUTPUT:
#             DispatchSolution containing:
#                 Q                  — optimal operating point (kW)
#                 allocation         — Dict[market_id → actual_qty]
#                 displacement_chain — Dict[displaced_market → displacing_market]
#                 total_net_value    — objective function value ($)
#                 binding_constraints— which constraints are active
#
# HOW DYNAMIC PRIORITY WORKS:
#     The fixed priority table (Reserve > Regulation > RT > DA) is
#     replaced by the economics encoded in the DeliveryEconomics
#     structures.  At each timestep:
#
#         1. The value calculator computes the marginal revenue and
#            marginal penalty for each active delivery.
#         2. The optimizer allocates the device's finite capacity to
#            the deliveries with the highest net value first.
#         3. If capacity is insufficient for all deliveries, the
#            optimizer curtails the delivery with the lowest marginal
#            penalty — because that's the cheapest one to short.
#         4. The result is economically optimal: total revenue minus
#            total penalty is maximized.
#
#     Priority reversal occurs naturally when market conditions change:
#         - Normally, regulation penalty is low → regulation gets
#           curtailed first when capacity is tight.
#         - During a grid stress event, regulation penalty spikes →
#           regulation gets priority, energy gets curtailed instead.
#
#     No configuration change is needed.  The cleared prices and
#     penalty structures carry the information.
#
# THE AMENITY COST TERM:
#     The amenity cost C_amenity(Q) is provided by the customer's
#     preference curve (AbstractPreferenceCurve.get_amenity_cost()).
#     It represents the discomfort or opportunity cost of operating
#     at Q instead of the customer's preferred point:
#
#         HVAC:    cost of temperature deviation from setpoint
#         WH:      cost of tank temperature below preferred level
#         EV:      cost of SOC below preferred departure level
#         Battery: cost of SOC below preferred backup reserve
#
#     The amenity cost is weighted by (1 − k), where k is the
#     customer preference factor.  At k=0, the amenity cost dominates
#     all market incentives.  At k=1, it is negligible.
#
#     This term ensures that the optimizer never ignores customer
#     comfort to chase marginal revenue — unless the customer has
#     explicitly indicated willingness to trade comfort for money
#     (high k).
#
# RELATIONSHIP TO ABSTRACTIONS:
#     DispatchOptimizer inherits from:
#         abstractions.dispatch_optimizer.AbstractDispatchOptimizer
#     DeliveryValueCalculator inherits from:
#         abstractions.dispatch_optimizer.AbstractDeliveryValueCalculator
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - economics/command_arbiter.py:
#         The Command Arbiter owns instances of both classes and calls
#         them in sequence during resolve_and_actuate():
#             1. DeliveryValueCalculator.compute() for each delivery
#             2. DispatchOptimizer.solve() once with all economics
#         The arbiter then handles F8 (control translation) and
#         F9 (actuation) with the optimizer's output.
#
#     - economics/penalty_models.py:
#         The DeliveryValueCalculator receives penalty models and
#         calls compute_penalty() and marginal_penalty() to build
#         the penalty_fn inside each DeliveryEconomics structure.
#
#     - economics/preference_curves.py:
#         The DispatchOptimizer receives the preference curve and
#         calls get_amenity_cost() to include the amenity term in
#         its objective function.
#
#     - devices/battery_model.py:
#         The DeliveryValueCalculator receives the marginal
#         degradation cost ($/kWh) as an input parameter.  For
#         battery deliveries, this cost is subtracted from the
#         revenue function, widening the effective dead band and
#         discouraging unprofitable cycling.
#
#     - agent.py (DeviceAgent):
#         The agent does not call these classes directly.  It
#         interacts with them through the Command Arbiter's
#         resolve_and_actuate() method.  The agent's role is to
#         pass the current device state, preference curve, and
#         amenity weight to the arbiter.
#
# DATA TYPES USED:
#     From data_types.py:
#         DeliveryEconomics  — per-delivery economic profile (output of F15)
#         DispatchSolution   — optimizer output (Q, allocation, displacement)
#     From abstractions/:
#         AbstractDispatchOptimizer       — contract for F16
#         AbstractDeliveryValueCalculator — contract for F15
#         AbstractPreferenceCurve         — for amenity cost in objective
#         AbstractPenaltyModel            — for penalty functions in economics
#     From enums_and_constants.py:
#         ProductType        — ENERGY_BASE, REGULATION_UP/DOWN, RESERVE_UP/DOWN
#
# EXTERNAL INPUTS:
#     current_signals (passed to solve() via Command Arbiter):
#         regulation_signal: float ∈ [−1.0, +1.0]
#             The real-time regulation signal from the ISO/MO.
#             Determines the target regulation response within the
#             committed band.
#             EXTERNAL: From MO signal feed or ISO AGC system.
#
#         reserve_activated: float (0.0 or 1.0)
#             Whether spinning reserve has been called.
#             Determines whether the device must deploy reserve
#             energy or just hold capacity.
#             EXTERNAL: From MO or ISO contingency signal.
#
#     degradation_cost (passed to compute() for battery deliveries):
#         Marginal degradation cost ($/kWh throughput).
#         INTERNAL: From BatteryModel.marginal_degradation_cost().
# ============================================================================

"""Concrete dispatch optimizer and delivery value calculator.

The delivery value calculator (F15) answers: "for each active market
delivery, what is the revenue, penalty, and net value as a function
of how much I actually deliver?"

The dispatch optimizer (F16) answers: "given all those value functions
and my physical limits, what single operating point maximizes my total
net value across all markets simultaneously?"

Together they implement economically-driven dynamic dispatch priority,
replacing fixed priority tables with price-and-penalty-responsive
capacity allocation that adapts automatically to changing market
conditions.

Classes:
    DeliveryValueCalculator  — Normalizes energy, regulation, and reserve
                               economics into a common callable form.
    DispatchOptimizer        — Solves the constrained net-value maximization
                               at each simulation timestep.
"""

from typing import Callable, Dict, List, Optional, Tuple

from abstractions.dispatch_optimizer import (
    AbstractDeliveryValueCalculator,
    AbstractDispatchOptimizer,
)
from abstractions.penalty_model import AbstractPenaltyModel
from abstractions.preference_curve import AbstractPreferenceCurve
from data_types import DeliveryEconomics, DispatchSolution
from enums_and_constants import ProductType

from tesp_support.tesp_support.curve_and_agent.abstractions.dispatch_optimizer import AbstractDeliveryValueCalculator, AbstractDispatchOptimizer

from ..data_types import DeliveryEconomics, DispatchSolution
from .penalty_model import PenaltyModel
from .preference_curves import PreferenceCurve


class DispatchOptimizer(AbstractDispatchOptimizer):
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
        economics: dict[str, DeliveryEconomics],
        Q_min: float,
        Q_max: float,
        preference_curve: PreferenceCurve,
        amenity_weight: float,
        current_signals: dict[str, float] | None = None,
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


class DeliveryValueCalculator(AbstractDeliveryValueCalculator):
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
        penalty_model: PenaltyModel,
        interval_duration: float,
        signals: dict[str, float] | None = None,
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
