# ============================================================================
# FILE: markets/supply_curve.py
# PURPOSE: Represents the DSO's wholesale energy procurement cost curve.
#
# The supply curve encodes the marginal cost of energy at different
# quantity levels, as seen by the retail market.  It is the "supply
# side" that the Market Operator intersects with aggregate demand to
# determine the clearing price.
#
# The curve is constructed by the DSO from:
#     - Wholesale market energy prices (LMPs at the substation node)
#     - Transmission charges and losses
#     - Capacity and ancillary service cost allocations
#     - Any local generation resources (if applicable)
#
# The curve is upward-sloping: each additional kW of supply is more
# expensive than the last, reflecting the merit order of generation
# resources available to serve the distribution system.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     No abstract base — SupplyCurve is a standalone concrete class.
#     It could be given an ABC if multiple supply curve representations
#     are needed in the future (e.g., stochastic supply curves for
#     wind-heavy systems).
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - markets/market_operator.py: The MarketOperator holds a
#       SupplyCurve instance and calls its interpolation methods
#       during market clearing.
#     - main.py: The simulation harness constructs the SupplyCurve
#       from external wholesale market data and passes it to the MO
#       via set_supply_curve().
#     - data_types.py: Uses BidPoint for the price-quantity pairs
#       that define the curve.
#
# EXTERNAL DATA:
#     All curve data is EXTERNAL.  The SupplyCurve does not forecast
#     or generate prices — it is populated from wholesale market data
#     provided by the simulation harness or a wholesale market
#     interface.
# ============================================================================

"""Supply curve — the DSO's wholesale procurement cost curve.

Provides interpolation between discrete price-quantity points that
represent the merit order of available generation.  Used by the
Market Operator to determine the clearing price where aggregate
retail demand intersects available supply.
"""

from typing import List, Optional

from data_types import BidPoint

class SupplyCurve:
    """Supply curve representing the cost of wholesale energy procurement.

    This is the DSO's cost curve for procuring energy from the wholesale
    market to serve the retail load. It encodes the marginal cost of
    energy at different quantity levels.

    Attributes:
        points: Ordered list of (price, quantity) representing the
            supply stack. Price increases with quantity (upward-sloping).
            EXTERNAL: Constructed by the DSO from wholesale market data,
            transmission charges, and capacity allocations.
    """

    def __init__(self, points: list[BidPoint] | None = None):
        self.points = points or []

    def get_supply_at_price(self, price: float) -> float:
        """Interpolate supply quantity at a given price.

        Args:
            price: Price ($/kWh).

        Returns:
            Supply quantity available at that price (kW).
        """
        if not self.points:
            return 0.0
        if price <= self.points[0].price:
            return self.points[0].quantity
        if price >= self.points[-1].price:
            return self.points[-1].quantity
        for i in range(len(self.points) - 1):
            p0, p1 = self.points[i], self.points[i + 1]
            if p0.price <= price <= p1.price:
                f = (price - p0.price) / (p1.price - p0.price)
                return p0.quantity + f * (p1.quantity - p0.quantity)
        return self.points[-1].quantity

    def get_price_at_quantity(self, quantity: float) -> float:
        """Interpolate price at a given supply quantity.

        Args:
            quantity: Supply quantity (kW).

        Returns:
            Marginal price at that quantity ($/kWh).
        """
        if not self.points:
            return 0.0
        if quantity <= self.points[0].quantity:
            return self.points[0].price
        if quantity >= self.points[-1].quantity:
            return self.points[-1].price
        for i in range(len(self.points) - 1):
            p0, p1 = self.points[i], self.points[i + 1]
            if p0.quantity <= quantity <= p1.quantity:
                f = (quantity - p0.quantity) / (p1.quantity - p0.quantity)
                return p0.price + f * (p1.price - p0.price)
        return self.points[-1].price


