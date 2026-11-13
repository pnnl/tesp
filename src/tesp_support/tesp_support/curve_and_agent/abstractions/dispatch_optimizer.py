# ============================================================================
# FILE: abstractions/dispatch_optimizer.py
# PURPOSE: Abstract base classes for the per-timestep dispatch optimization
#          (agent functions F15 and F16).
#
# Contains two ABCs:
#     AbstractDeliveryValueCalculator (F15)
#         Computes per-delivery economic profiles (revenue, penalty,
#         net-value functions) that normalize the heterogeneous economics
#         of energy, regulation, and reserve products.
#
#     AbstractDispatchOptimizer (F16)
#         Determines the optimal device operating point by maximizing
#         total net value across all simultaneously active deliveries.
#
# These two classes are co-located because they have a tight producer–
# consumer relationship: the calculator exists solely to feed the
# optimizer.  They are always used together and reference each other's
# output types.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - AbstractDeliveryValueCalculator uses: AbstractPenaltyModel
#     - AbstractDispatchOptimizer uses: AbstractPreferenceCurve (amenity cost)
#     - Both used by: AbstractCommandArbiter.resolve_and_actuate()
#
# IMPORTS FROM:
#     - typing: Dict, Optional
#     - abstractions.preference_curve: AbstractPreferenceCurve
#     - abstractions.penalty_model: AbstractPenaltyModel
#     - data_types: DeliveryEconomics, DispatchSolution
#     - enums_and_constants: ProductType
# ============================================================================

"""Abstract dispatch optimizer and delivery value calculator.

The delivery value calculator (F15) normalizes per-market economics
into a common representation.  The dispatch optimizer (F16) consumes
those economics and solves for the single operating point that
maximizes total net value across all active deliveries, subject to
physical device limits.

Together they replace the fixed-priority dispatch logic with
economically-driven dynamic priority resolution.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from abstractions.penalty_model import AbstractPenaltyModel
from abstractions.preference_curve import AbstractPreferenceCurve
from data_types import DeliveryEconomics, DispatchSolution
from enums_and_constants import ProductType

class AbstractDispatchOptimizer(ABC):
    """Abstract base for the per-timestep dispatch optimization (F16).

    The dispatch optimizer determines the optimal device operating point
    by maximizing total net value across all simultaneously active
    deliveries.
    """

    @abstractmethod
    def solve(
        self,
        economics: Dict[str, DeliveryEconomics],
        Q_min: float,
        Q_max: float,
        preference_curve: AbstractPreferenceCurve,
        amenity_weight: float,
        current_signals: Optional[Dict[str, float]] = None,
    ) -> DispatchSolution:
        """Solve the dispatch optimization for the current timestep.

        Args:
            economics: Per-market delivery economics.
                INTERNAL: From ``AbstractDeliveryValueCalculator.compute()``.
            Q_min: Physical minimum operating point (kW).
            Q_max: Physical maximum operating point (kW).
            preference_curve: For amenity / opportunity cost.
                INTERNAL: From F3.
            amenity_weight: Weight on the amenity cost term.
                INTERNAL: Derived from customer preference *k*.
            current_signals: Real-time signals for fast-response products.
                EXTERNAL: From MO or ISO (regulation signal, reserve flag).

        Returns:
            ``DispatchSolution`` with optimal Q, per-market allocation,
            displacement chain, and total net value.
        """
        ...


class AbstractDeliveryValueCalculator(ABC):
    """Abstract base for computing per-delivery economic profiles (F15).

    Normalizes the economics of different product types into a common
    ``DeliveryEconomics`` representation consumed by the dispatch
    optimizer.
    """

    @abstractmethod
    def compute(
        self,
        market_id: str,
        product_type: ProductType,
        committed_qty: float,
        cleared_price: float,
        penalty_model: AbstractPenaltyModel,
        interval_duration: float,
        signals: Optional[Dict[str, float]] = None,
        degradation_cost: float = 0.0,
    ) -> DeliveryEconomics:
        """Compute delivery economics for one active delivery.

        Args:
            market_id: Market identifier.
            product_type: Energy, regulation, or reserve.
            committed_qty: Committed power (kW).
            cleared_price: Clearing price ($/kWh or $/kW).
            penalty_model: Applicable penalty model.
                INTERNAL: From penalty model registry.
            interval_duration: Delivery interval length (seconds).
            signals: Real-time market signals.
                EXTERNAL: From MO or ISO.
            degradation_cost: For batteries / wear-sensitive assets,
                marginal degradation cost ($/kWh).
                INTERNAL: From device model.

        Returns:
            ``DeliveryEconomics`` with revenue, penalty, and net value
            functions.
        """
        ...