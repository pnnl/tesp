# ============================================================================
# FILE: market_operator.py
# PURPOSE: Stub for the Distribution System Operator's Market Operator (MO).
#          Receives bids from device agents and the DSO inflexible load bid,
#          clears the retail market, and propagates cleared prices back to
#          all participants.
#
# EXTERNAL DEPENDENCIES:
#     - Supply curve: from DSO's wholesale procurement.
#     - Inflexible load bid: from DSO's load estimation engine.
#     - Agent bids: from device agents via communication interfaces.
# ============================================================================

from ..data_types import BidCurve, BidPoint, ClearingResult, MarketTimingParams
from ..enums_and_constants import IterationType, MarketType



class MarketOperator:
    """The DSO's Market Operator that clears the retail energy market.

    Receives bids from device agents and the DSO inflexible load bid,
    aggregates demand, intersects with the supply curve, and propagates
    cleared prices back to all participants.

    Supports both informational and binding clearing iterations.

    Args:
        market_type: Type of market this MO operates.
        timing_params: Timing for market phases.
            EXTERNAL: Market design parameters.
        iteration_protocol: How informational iterations are managed.
            'fixed_count': run N informational + 1 binding.
            'convergence': run informational until convergence, then binding.
        n_informational: Number of informational iterations (for fixed_count).
    """

    def __init__(
        self,
        market_type: MarketType,
        timing_params: MarketTimingParams,
        iteration_protocol: str = "fixed_count",
        n_informational: int = 0,
    ):
        self._market_type = market_type
        self._timing_params = timing_params
        self._iteration_protocol = iteration_protocol
        self._n_informational = n_informational

        # Registered participants
        self._agent_bids: dict[str, BidCurve] = {}
        self._dso_bids: dict[str, DSOInflexibleLoadBid] = {}
        self._supply_curve: SupplyCurve | None = None

        # Iteration tracking
        self._current_iteration: int = 0
        self._clearing_history: list[ClearingResult] = []

    def set_supply_curve(self, supply_curve: SupplyCurve) -> None:
        """Set the supply curve for this market cycle.

        Args:
            supply_curve: The DSO's wholesale procurement cost curve.
                EXTERNAL: Constructed by the DSO from wholesale market
                data, transmission charges, capacity allocations, and
                any local generation resources.
        """
        self._supply_curve = supply_curve

    def submit_agent_bid(self, agent_id: str, bid: BidCurve) -> bool:
        """Receive a bid from a device agent.

        Called by the agent's MarketCommunicationInterface.submit_bid().

        Args:
            agent_id: ID of the submitting agent.
            bid: The agent's price-quantity bid curve.
                INTERNAL (from agent's perspective): From F4.

        Returns:
            True if bid accepted.
        """
        self._agent_bids[agent_id] = bid
        return True

    def submit_dso_inflexible_bid(
        self, feeder_id: str, bid: DSOInflexibleLoadBid
    ) -> bool:
        """Receive the DSO's inflexible load bid.

        Args:
            feeder_id: Which feeder.
            bid: The inflexible load bid.
                INTERNAL (from DSO's perspective): From DSOLoadEstimationEngine.

        Returns:
            True if accepted.
        """
        self._dso_bids[feeder_id] = bid
        return True

    def aggregate_demand(self) -> list[BidPoint]:
        """Aggregate all demand bids into a single demand curve.

        Horizontally sums:
        - All agent flexible bid curves
        - All DSO inflexible load bids (as vertical lines)

        The result is a downward-sloping aggregate demand curve where
        quantity decreases as price increases (elastic agents reduce
        consumption at higher prices) but never drops below the
        inflexible base (the vertical component).

        Returns:
            List of BidPoint representing aggregate demand,
            ordered by decreasing price.
        """
        # Collect all unique price levels from agent bids
        price_set = set()
        for bid in self._agent_bids.values():
            for pt in bid.points:
                price_set.add(pt.price)
        if not price_set:
            price_set.add(0.0)
        prices = sorted(price_set, reverse=True)

        # Total inflexible demand (vertical component)
        inflexible_total = sum(b.quantity for b in self._dso_bids.values())

        agg = []
        for price in prices:
            flexible_total = 0.0
            for bid in self._agent_bids.values():
                flexible_total += self._interpolate_bid(bid, price)
            agg.append(
                BidPoint(
                    price=price,
                    quantity=flexible_total + inflexible_total,
                )
            )
        return agg

    @staticmethod
    def _interpolate_bid(bid: BidCurve, price: float) -> float:
        """Interpolate a single agent bid curve at a given price."""
        pts = bid.points
        if not pts:
            return 0.0
        # Points ordered by decreasing price
        if price >= pts[0].price:
            return pts[0].quantity
        if price <= pts[-1].price:
            return pts[-1].quantity
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            if p0.price >= price >= p1.price:
                f = (p0.price - price) / (p0.price - p1.price)
                return p0.quantity + f * (p1.quantity - p0.quantity)
        return pts[-1].quantity

    def clear_market(self) -> ClearingResult:
        """Clear the market by intersecting aggregate demand with supply.

        Steps:
        1. Aggregate all demand bids (agent flexible + DSO inflexible)
        2. Intersect aggregate demand with supply curve
        3. Determine clearing price (where supply meets demand)
        4. Determine each participant's cleared quantity at the
           clearing price
        5. Determine iteration type (informational or binding)
        6. Package results

        Returns:
            ClearingResult with clearing price, quantities, and
            iteration type.
        """
        self._current_iteration += 1
        iteration_type = self.determine_iteration_type()

        demand_curve = self.aggregate_demand()
        if not demand_curve or self._supply_curve is None:
            result = ClearingResult(
                iteration=self._current_iteration,
                iteration_type=iteration_type,
            )
            self._clearing_history.append(result)
            return result

        # Find intersection: sweep price levels LOW → HIGH.
        # Demand decreases with price, supply increases with price.
        # The clearing price is the lowest price where supply >= demand.
        cleared_price = 0.0
        cleared_qty = 0.0

        # Sample at demand curve prices + supply curve prices
        price_levels = sorted(
            {pt.price for pt in demand_curve}
            | {pt.price for pt in self._supply_curve.points}
        )

        prev_excess = None
        prev_price = None
        for price in price_levels:
            supply_q = self._supply_curve.get_supply_at_price(price)
            # Interpolate demand at this price
            inflexible = sum(b.quantity for b in self._dso_bids.values())
            flexible = sum(
                self._interpolate_bid(bid, price) for bid in self._agent_bids.values()
            )
            demand_q = inflexible + flexible

            excess = supply_q - demand_q  # positive = oversupply
            if excess >= 0:
                # Interpolate between previous (undersupplied) and this price
                if (
                    prev_excess is not None
                    and prev_price is not None
                    and prev_excess < 0
                ):
                    frac = -prev_excess / (excess - prev_excess)
                    cleared_price = prev_price + frac * (price - prev_price)
                else:
                    cleared_price = price
                # Recompute demand at the interpolated clearing price
                inflexible = sum(b.quantity for b in self._dso_bids.values())
                flexible = sum(
                    self._interpolate_bid(bid, cleared_price)
                    for bid in self._agent_bids.values()
                )
                cleared_qty = inflexible + flexible
                break
            prev_excess = excess
            prev_price = price

        if cleared_price == 0.0 and price_levels:
            # Supply never catches up — use highest supply point
            cleared_price = price_levels[-1]
            cleared_qty = self._supply_curve.get_supply_at_price(cleared_price)

        result = ClearingResult(
            cleared_price=cleared_price,
            cleared_quantity=cleared_qty,
            iteration=self._current_iteration,
            iteration_type=iteration_type,
            aggregate_demand=cleared_qty,
            aggregate_supply=self._supply_curve.get_supply_at_price(cleared_price),
        )
        self._clearing_history.append(result)
        self._last_clearing = result
        return result

    def get_agent_clearing(
        self, agent_id: str, clearing_price: float
    ) -> ClearingResult:
        """Compute an individual agent's cleared quantity.

        Given the market clearing price, evaluates the agent's
        submitted bid curve to determine their cleared quantity.

        Args:
            agent_id: ID of the agent.
            clearing_price: Market clearing price ($/kWh).
                INTERNAL: From self.clear_market().

        Returns:
            ClearingResult specific to this agent.
        """
        bid = self._agent_bids.get(agent_id)
        if bid is None:
            return ClearingResult(
                cleared_price=clearing_price,
                cleared_quantity=0.0,
            )
        qty = self._interpolate_bid(bid, clearing_price)
        return ClearingResult(
            cleared_price=clearing_price,
            cleared_quantity=qty,
            iteration=self._current_iteration,
            iteration_type=self.determine_iteration_type(),
        )

    def propagate_results(self) -> dict[str, ClearingResult]:
        """Propagate clearing results to all participants.

        After clearing, computes per-agent results and makes them
        available for retrieval.

        Returns:
            Dictionary mapping agent_id to their ClearingResult.
        """
        if not self._clearing_history:
            return {}
        last = self._clearing_history[-1]
        results = {}
        for agent_id in self._agent_bids:
            results[agent_id] = self.get_agent_clearing(agent_id, last.cleared_price)
        return results

    def get_total_flexible_committed(self) -> float:
        """Get the total flexible load committed by all agents.

        Used by the DSO Load Estimation Engine to avoid double-counting
        when constructing the inflexible load bid for subsequent
        iterations.

        Returns:
            Sum of all agent cleared quantities (kW).
        """
        if not self._clearing_history:
            return 0.0
        last = self._clearing_history[-1]
        total = 0.0
        for bid in self._agent_bids.values():
            total += self._interpolate_bid(bid, last.cleared_price)
        return total

    def determine_iteration_type(self) -> IterationType:
        """Determine if the current iteration is informational or binding.

        Uses the configured iteration_protocol:
        - fixed_count: iterations 1..N are informational, N+1 is binding.
        - convergence: check if prices have converged; if so, binding.

        Returns:
            IterationType.INFORMATIONAL or IterationType.BINDING.
        """
        if self._iteration_protocol == "fixed_count":
            if self._current_iteration <= self._n_informational:
                return IterationType.INFORMATIONAL
            return IterationType.BINDING
        # convergence protocol: check if prices converged
        if len(self._clearing_history) >= 2:
            last = self._clearing_history[-1]
            prev = self._clearing_history[-2]
            if abs(last.cleared_price - prev.cleared_price) < 0.001:
                return IterationType.BINDING
        return IterationType.INFORMATIONAL

    def step(self, current_time: float) -> dict[str, ClearingResult] | None:
        """Execute one MO timestep.

        Called by the simulation harness. Checks if it's time to
        clear the market, and if so, executes the clearing process.

        Args:
            current_time: Current simulation time.
                EXTERNAL: From simulation harness.

        Returns:
            Per-agent ClearingResults if a clearing occurred, None otherwise.
        """
        if current_time < self._timing_params.t_clear:
            return None
        result = self.clear_market()  # TODO: find way to return clearing result as well
        return result, self.propagate_results()
