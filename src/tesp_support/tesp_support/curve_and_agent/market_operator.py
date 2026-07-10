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

from typing import Dict, List, Optional, Tuple, Any
from .data_types import BidCurve, ClearingResult, BidPoint, MarketTimingParams
from .enums_and_constants import MarketType, IterationType


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

    def __init__(self, points: Optional[List[BidPoint]] = None):
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


class DSOInflexibleLoadBid:
    """Represents the DSO's bid for all inflexible load on a feeder.

    This is a perfectly inelastic demand bid (vertical line) at the
    estimated aggregate inflexible load.

    The DSO constructs this by:
    1. Forecasting total feeder gross load
    2. Subtracting expected flexible device consumption (from agent
       bids and advisory commitments)
    3. Adding distribution losses
    4. Subtracting aggregate BTM solar export

    Attributes:
        feeder_id: Which distribution feeder this bid covers.
        quantity: Perfectly inelastic demand (kW).
            EXTERNAL: From DSO's load estimation engine.
        interval: Time interval this bid covers.
        components: Breakdown of the bid quantity.
    """

    def __init__(
        self,
        feeder_id: str,
        quantity: float,
        interval: Tuple[float, float],
        components: Optional[Dict[str, float]] = None,
    ):
        self.feeder_id = feeder_id
        self.quantity = quantity
        self.interval = interval
        self.components = components or {}


class DSOLoadEstimationEngine:
    """Estimates aggregate inflexible load for a feeder or pricing zone.

    Uses substation metering, AMI data, weather forecasts, and network
    models to produce the inflexible load bid that the DSO submits to
    the MO on behalf of all non-participating and inflexible load.

    EXTERNAL DATA SOURCES:
        - Substation real-time metering: actual feeder load
        - AMI / smart meter historical data: per-customer load profiles
        - Weather forecast: temperature, solar, humidity
        - Network loss model: topology, impedances, loading-dependent losses
        - BTM solar aggregate: estimated total rooftop solar on feeder
        - Flexible device commitments: sum of agent bids/clears
          (from MO's own records)

    Args:
        feeder_id: Which feeder this engine serves.
    """

    def __init__(self, feeder_id: str):
        self._feeder_id = feeder_id
        self._correction_factor = 1.0
        self._last_predicted_inflexible = None
        self._last_timestamp = 0.0

    def estimate_inflexible_load(
        self,
        interval: Tuple[float, float],
        total_load_forecast: float,
        flexible_committed: float,
        btm_solar_forecast: float,
        loss_factor: float,
    ) -> DSOInflexibleLoadBid:
        """Compute the inflexible load bid for a market interval.

        Q_inflexible = total_load_forecast
                     - flexible_committed
                     + losses
                     - btm_solar_export

        Args:
            interval: Time interval to estimate for.
            total_load_forecast: Forecasted total feeder load (kW).
                EXTERNAL: From substation metering + forecast model.
            flexible_committed: Sum of all device agent flexible
                commitments for this interval (kW).
                INTERNAL: From MO's aggregation of agent bids/clears.
            btm_solar_forecast: Forecasted aggregate BTM solar
                generation on this feeder (kW).
                EXTERNAL: From solar forecast model.
            loss_factor: Distribution loss factor (fraction, e.g., 0.05).
                EXTERNAL: From network loss model.

        Returns:
            DSOInflexibleLoadBid with the computed quantity.
        """
        losses = total_load_forecast * loss_factor
        q_inflexible = (
            total_load_forecast - flexible_committed + losses - btm_solar_forecast
        )
        # Apply correction factor from metering feedback
        q_inflexible *= self._correction_factor
        self._last_predicted_inflexible = q_inflexible

        return DSOInflexibleLoadBid(
            feeder_id=self._feeder_id,
            quantity=q_inflexible,
            interval=interval,
            components={
                "total_forecast": total_load_forecast,
                "flexible": flexible_committed,
                "solar": btm_solar_forecast,
                "losses": losses,
            },
        )

    def update_with_metering(
        self, substation_load_actual: float, flexible_actual: float, timestamp: float
    ) -> None:
        """Update estimation model with real-time metering data.

        Called during real-time market operation. Allows the DSO to
        correct its forecast based on actual observed load.

        Args:
            substation_load_actual: Measured total feeder load (kW).
                EXTERNAL: From substation SCADA/metering.
            flexible_actual: Sum of actual device agent power (kW).
                INTERNAL: From MO's metering of device agents.
            timestamp: Measurement time.
        """
        actual_inflexible = substation_load_actual - flexible_actual
        if not hasattr(self, "_correction_factor"):
            self._correction_factor = 1.0
            self._last_predicted_inflexible = None
        if (
            self._last_predicted_inflexible is not None
            and self._last_predicted_inflexible > 0
        ):
            self._correction_factor = (
                actual_inflexible / self._last_predicted_inflexible
            )
        self._last_timestamp = timestamp


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
        self._agent_bids: Dict[str, BidCurve] = {}
        self._dso_bids: Dict[str, DSOInflexibleLoadBid] = {}
        self._supply_curve: Optional[SupplyCurve] = None

        # Iteration tracking
        self._current_iteration: int = 0
        self._clearing_history: List[ClearingResult] = []

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

    def aggregate_demand(self) -> List[BidPoint]:
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
            set(pt.price for pt in demand_curve)
            | set(pt.price for pt in self._supply_curve.points),
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

    def propagate_results(self) -> Dict[str, ClearingResult]:
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
        for agent_id, bid in self._agent_bids.items():
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

    def step(self, current_time: float) -> Optional[Dict[str, ClearingResult]]:
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
        result = self.clear_market()
        return self.propagate_results()
