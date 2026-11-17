# ============================================================================
# FILE: abstractions/preference_curve.py
# PURPOSE: Abstract base class for mapping prices to desired power
#          quantities (agent function F3).
#
# For demand-side devices this is an isoelastic demand curve trading
# amenity for financial benefit.  For batteries it is a bidirectional
# sigmoid with a degradation-driven dead band.  For generators it
# would be a marginal-cost offer curve.
#
# Regardless of functional form, every preference curve must support:
#     - Evaluation at a given price → desired quantity
#     - Evaluation with physical bounds clamping
#     - Amenity / opportunity cost calculation
#     - Discretization into a bid curve (list of price-quantity points)
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Used by: AbstractDeviceAgent.generate_preference_curve() (F3)
#                AbstractDeviceAgent.formulate_bid() (F4)
#                AbstractDispatchOptimizer.solve() (amenity cost term)
#                AbstractCommandArbiter.resolve_and_actuate()
#
# IMPORTS FROM:
#     - typing: List, Optional
#     - data_types: BidPoint
# ============================================================================

"""Abstract preference / offer curve — the economic heart of the agent.

The preference curve encodes the customer's (or operator's) willingness
to trade amenity for financial benefit.  It is the single source of
economic truth for the customer and is consumed by both the bid
formulation (F4) and the price-response evaluation (F7).
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from data_types import BidPoint

class AbstractPreferenceCurve(ABC):
    """Abstract base for mapping prices to desired power quantities.

    For demand-side devices (HVAC, WH, EV), this is an isoelastic
    demand curve trading amenity for financial benefit.  For batteries,
    it is a bidirectional sigmoid with a degradation-driven dead band.
    For generators, it is a marginal-cost offer curve.

    Regardless of the underlying functional form, every preference
    curve must support evaluation at a given price and sampling into a
    discrete bid curve.

    Args:
        k: Customer (or operator) preference factor in [0, 1].
            0 = maximize amenity / minimize risk.
            1 = maximize financial return.
            EXTERNAL: Provided as a configuration input.
        P_0: Reference price used to anchor the curve ($/kWh).
            INTERNAL: From price forecast service or device economics.
        Q_0: Baseline quantity (kW) at the reference price.
            INTERNAL: From ``FlexibilityEnvelope.Q_baseline``.
    """

    def __init__(self, k: float, P_0: float, Q_0: float):
        self._k = k
        self._P_0 = P_0
        self._Q_0 = Q_0

    @property
    @abstractmethod
    def epsilon(self) -> float:
        """Effective elasticity parameter derived from *k*.

        Returns:
            Elasticity ε ≥ 0.
        """
        ...

    @abstractmethod
    def evaluate(self, price: float) -> float:
        """Evaluate the curve at a single price.

        Args:
            price: Market price ($/kWh).

        Returns:
            Desired power quantity (kW).
            Positive = consume, negative = produce.
        """
        ...

    @abstractmethod
    def evaluate_with_bounds(
        self,
        price: float,
        Q_min: float,
        Q_max: float,
    ) -> float:
        """Evaluate the curve, clamped to physical bounds.

        Args:
            price: Market price ($/kWh).
            Q_min: Minimum feasible power (kW).
                INTERNAL: From ``FlexibilityEnvelope``.
            Q_max: Maximum feasible power (kW).
                INTERNAL: From ``FlexibilityEnvelope``.

        Returns:
            Desired power clamped to [Q_min, Q_max].
        """
        ...

    @abstractmethod
    def get_amenity_cost(
        self,
        Q_actual: float,
        Q_preferred: float,
    ) -> float:
        """Compute the amenity (or opportunity) cost of deviating from the
        preferred operating point.

        For demand-side devices this represents comfort degradation.
        For generators this may represent wear, efficiency loss, or
        opportunity cost of not running at the economic optimum.

        Args:
            Q_actual: Actual operating point (kW).
            Q_preferred: Preferred (amenity-tracking) operating point (kW).
                INTERNAL: From ``FlexibilityEnvelope.Q_baseline``.

        Returns:
            Cost in $/timestep.
        """
        ...

    @abstractmethod
    def sample_bid_curve(
        self,
        price_min: float,
        price_max: float,
        n_points: int,
        Q_min: float,
        Q_max: float,
        price_focus: Optional[float] = None,
    ) -> List[BidPoint]:
        """Discretize the curve into a list of bid points.

        Args:
            price_min: Lower bound of the price sample range ($/kWh).
            price_max: Upper bound of the price sample range ($/kWh).
            n_points: Number of points on the bid curve.
            Q_min: Minimum feasible power (kW).
            Q_max: Maximum feasible power (kW).
            price_focus: If given, concentrate sample density near this
                price for better resolution around the expected clearing.
                INTERNAL: From ``AdvisoryRecord.cleared_price``.

        Returns:
            List of ``BidPoint`` ordered by decreasing price.
        """
        ...