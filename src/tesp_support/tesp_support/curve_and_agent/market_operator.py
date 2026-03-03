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
from data_types import BidCurve, ClearingResult, BidPoint, MarketTimingParams
from enums_and_constants import MarketType, IterationType


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
        raise NotImplementedError

    def get_price_at_quantity(self, quantity: float) -> float:
        """Interpolate price at a given supply quantity.
        
        Args:
            quantity: Supply quantity (kW).
        
        Returns:
            Marginal price at that quantity ($/kWh).
        """
        raise NotImplementedError


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
        components: Optional[Dict[str, float]] = None
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

    def estimate_inflexible_load(
        self,
        interval: Tuple[float, float],
        total_load_forecast: float,
        flexible_committed: float,
        btm_solar_forecast: float,
        loss_factor: float
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
        raise NotImplementedError

    def update_with_metering(
        self,
        substation_load_actual: float,
        flexible_actual: float,
        timestamp: float
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
        raise NotImplementedError


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
        n_informational: int = 0
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
        raise NotImplementedError

    def submit_agent_bid(
        self,
        agent_id: str,
        bid: BidCurve
    ) -> bool:
        """Receive a bid from a device agent.
        
        Called by the agent's MarketCommunicationInterface.submit_bid().
        
        Args:
            agent_id: ID of the submitting agent.
            bid: The agent's price-quantity bid curve.
                INTERNAL (from agent's perspective): From F4.
        
        Returns:
            True if bid accepted.
        """
        raise NotImplementedError

    def submit_dso_inflexible_bid(
        self,
        feeder_id: str,
        bid: DSOInflexibleLoadBid
    ) -> bool:
        """Receive the DSO's inflexible load bid.
        
        Args:
            feeder_id: Which feeder.
            bid: The inflexible load bid.
                INTERNAL (from DSO's perspective): From DSOLoadEstimationEngine.
        
        Returns:
            True if accepted.
        """
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

    def get_agent_clearing(
        self,
        agent_id: str,
        clearing_price: float
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
        raise NotImplementedError

    def propagate_results(self) -> Dict[str, ClearingResult]:
        """Propagate clearing results to all participants.
        
        After clearing, computes per-agent results and makes them
        available for retrieval.
        
        Returns:
            Dictionary mapping agent_id to their ClearingResult.
        """
        raise NotImplementedError

    def get_total_flexible_committed(self) -> float:
        """Get the total flexible load committed by all agents.
        
        Used by the DSO Load Estimation Engine to avoid double-counting
        when constructing the inflexible load bid for subsequent
        iterations.
        
        Returns:
            Sum of all agent cleared quantities (kW).
        """
        raise NotImplementedError

    def determine_iteration_type(self) -> IterationType:
        """Determine if the current iteration is informational or binding.
        
        Uses the configured iteration_protocol:
        - fixed_count: iterations 1..N are informational, N+1 is binding.
        - convergence: check if prices have converged; if so, binding.
        
        Returns:
            IterationType.INFORMATIONAL or IterationType.BINDING.
        """
        raise NotImplementedError

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
        raise NotImplementedError