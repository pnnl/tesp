# ============================================================================
# FILE: device_agent.py
# PURPOSE: Main device agent class. Orchestrates all agent functions and
#          manages the collection of MarketObjects. This is the top-level
#          class that external code interacts with.
# ============================================================================

from typing import Dict, List, Optional, Any, Tuple
from enums_and_constants import (
    DeviceType, MarketType, MarketPhase, OperatingMode, IterationType
)
from data_types import (
    BidCurve, ClearingResult, DeviceCommand, FlexibilityEnvelope,
    FulfillmentRecord, SettlementRecord, AdvisoryRecord,
    MarketTimingParams, PerformanceEntry
)
from gridlabd_interface import GridLABDInterface
from data_streams import DataStreamManager
from preference_curve import PreferenceCurve
from penalty_model import PenaltyModel
from flexibility_ledger import FlexibilityLedger
from market_object import MarketObject
from market_communication import MarketCommunicationInterface
from command_arbiter import CommandArbiter
from dispatch_optimizer import DispatchOptimizer, DeliveryValueCalculator
from planning_optimizer import PlanningOptimizer
from price_forecast_service import PriceForecastService
from device_models import (
    HVACModel, WaterHeaterModel, EVChargerModel, BatteryModel
)


class DeviceAgent:
    """Top-level device agent that orchestrates market participation.
    
    This class owns all sub-components and implements the main
    simulation loop. It manages multiple MarketObjects (one per
    market product per cycle) and coordinates their progression
    through the market state machine.
    
    The agent follows a sense-decide-act loop each simulation timestep:
    1. Observe device state from GridLAB-D (F1)
    2. Check each MarketObject for state transitions
    3. Execute phase-appropriate functions for each transitioning market
    4. Resolve all active deliveries into a single device command
    5. Actuate the device via GridLAB-D (F9)
    
    Args:
        agent_id: Unique identifier for this agent.
        device_type: Type of physical device to manage.
        gridlabd: GridLAB-D interface for device state and control.
            EXTERNAL: Provided by the simulation harness. Must be
            connected to the appropriate GridLAB-D object.
        customer_preference_k: Customer preference factor (0=amenity,
            1=financial).
            EXTERNAL: Provided as customer input/configuration.
        data_stream_manager: Manager for all forecast/schedule/constraint
            data streams.
            EXTERNAL: Must be populated with forecast data from external
            sources (weather, customer schedules, etc.).
    """

    def __init__(
        self,
        agent_id: str,
        device_type: DeviceType,
        gridlabd: GridLABDInterface,
        customer_preference_k: float,
        data_stream_manager: DataStreamManager
    ):
        self._agent_id = agent_id
        self._device_type = device_type
        self._gridlabd = gridlabd
        self._k = customer_preference_k
        self._data_streams = data_stream_manager

        # Device-specific model
        self._device_model = self._create_device_model()

        # Market infrastructure
        self._market_objects: Dict[str, MarketObject] = {}
        self._market_comms: Dict[MarketType, MarketCommunicationInterface] = {}
        self._penalty_models: Dict[MarketType, PenaltyModel] = {}

        # Shared components
        self._flexibility_ledger: Optional[FlexibilityLedger] = None
        self._command_arbiter: Optional[CommandArbiter] = None
        self._planning_optimizer: Optional[PlanningOptimizer] = None
        self._price_forecast_service = PriceForecastService()

        # Current state cache
        self._current_state: Optional[Any] = None
        self._current_flexibility: Optional[FlexibilityEnvelope] = None
        self._current_preference_curve: Optional[PreferenceCurve] = None

    def _create_device_model(self) -> Any:
        """Instantiate the appropriate device physics model.
        
        Returns:
            Device-specific model instance (HVACModel, WaterHeaterModel,
            EVChargerModel, or BatteryModel).
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Initialization and Registration
    # ------------------------------------------------------------------

    def initialize(self, device_params: Dict[str, Any]) -> None:
        """Initialize the agent with device parameters and create
        shared components.
        
        Must be called before the simulation loop starts.
        
        Args:
            device_params: Device-specific parameters.
                For HVAC: {} (parameters come from GridLAB-D state)
                For Battery: {'replacement_cost': float, 
                              'rated_cycles': int, 
                              'rated_dod': float}
                EXTERNAL: From device specifications.
        """
        raise NotImplementedError

    def register_market(
        self,
        market_type: MarketType,
        timing_params: MarketTimingParams,
        operating_mode: OperatingMode,
        penalty_model: PenaltyModel,
        communication: MarketCommunicationInterface,
        iteration_protocol: str = "mo_signaled",
        n_informational: Optional[int] = None
    ) -> None:
        """Register participation in a market product.
        
        Creates the market communication interface and penalty model
        entries. Does NOT create the MarketObject yet — that happens
        when the first market cycle is spawned.
        
        Args:
            market_type: Type of market to participate in.
            timing_params: Timing for market phases.
                EXTERNAL: Defined by market rules from MO.
            operating_mode: How to participate (bidding, price-responsive).
                EXTERNAL: Configuration setting.
            penalty_model: Penalty structure for non-delivery.
                EXTERNAL: Defined by market rules from MO.
            communication: Communication interface to the MO.
                EXTERNAL: Provided by simulation harness.
            iteration_protocol: How informational iterations work.
                EXTERNAL: From market rules.
            n_informational: Number of informational iterations (if fixed).
                EXTERNAL: From market rules.
        """
        raise NotImplementedError

    def spawn_market_cycle(
        self,
        market_type: MarketType,
        clearing_time: float
    ) -> str:
        """Create a new MarketObject for an upcoming market cycle.
        
        Args:
            market_type: Type of market.
            clearing_time: When this cycle will clear (simulation time).
        
        Returns:
            market_id of the newly created MarketObject.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F1: Device State Observation
    # ------------------------------------------------------------------

    def observe_device_state(self) -> Any:
        """Read current device state from GridLAB-D.
        
        Dispatches to the appropriate GridLAB-D read method based on
        device_type.
        
        Returns:
            Device-specific state dataclass (HVACState, WaterHeaterState,
            EVChargerState, or BatteryState).
            
        Note: This is the ONLY function that reads from GridLAB-D.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F2: Flexibility Estimation
    # ------------------------------------------------------------------

    def estimate_flexibility(
        self,
        state: Any,
        interval_duration: float
    ) -> FlexibilityEnvelope:
        """Estimate the feasible operating range for the upcoming interval.
        
        Delegates to the device-specific model, providing it with
        relevant forecasts from the DataStreamManager.
        
        Args:
            state: Current device state from F1.
                INTERNAL: From self.observe_device_state().
            interval_duration: Market interval length (seconds).
        
        Returns:
            FlexibilityEnvelope with feasible power range and
            confidence-level variants.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F3: Preference Curve Generation
    # ------------------------------------------------------------------

    def generate_preference_curve(
        self,
        flexibility: FlexibilityEnvelope
    ) -> PreferenceCurve:
        """Generate the customer preference curve.
        
        Creates a PreferenceCurve anchored to the baseline operating
        point from the flexibility envelope and the reference price
        from the price forecast.
        
        Args:
            flexibility: Flexibility envelope from F2.
                INTERNAL: From self.estimate_flexibility().
        
        Returns:
            PreferenceCurve instance.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F4: Bid Formulation
    # ------------------------------------------------------------------

    def formulate_bid(
        self,
        market_obj: MarketObject,
        flexibility: FlexibilityEnvelope,
        preference_curve: PreferenceCurve
    ) -> BidCurve:
        """Formulate a price-quantity bid curve for a specific market.
        
        Combines the operating envelope with the preference curve,
        applies risk adjustment based on concurrent commitments and
        displacement economics, and produces a discretized bid curve.
        
        For batteries, includes degradation cost in the dead band.
        
        Args:
            market_obj: The MarketObject being bid for.
                INTERNAL: From self._market_objects.
            flexibility: Available flexibility for this market.
                INTERNAL: From F2, adjusted by FlexibilityLedger.
            preference_curve: Customer preference curve.
                INTERNAL: From F3.
        
        Returns:
            BidCurve with price-quantity points.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F7: Price-to-Operating-Point Response
    # ------------------------------------------------------------------

    def evaluate_price_response(
        self,
        price: float,
        curve: Any
    ) -> float:
        """Determine desired operating point from a price signal.
        
        Evaluates either the submitted bid curve (bidding mode) or
        the preference curve (price-responsive mode) at the given price.
        
        Args:
            price: Cleared or observed price ($/kWh).
                INTERNAL: From ClearingResult.cleared_price.
            curve: Either a BidCurve (bidding mode) or PreferenceCurve
                (price-responsive mode).
                INTERNAL: From MarketObject or F3.
        
        Returns:
            Desired power quantity (kW).
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F8: Control Signal Translation
    # ------------------------------------------------------------------

    def translate_to_control(
        self,
        target_power: float,
        state: Any
    ) -> DeviceCommand:
        """Convert target power to device-specific control command.
        
        Uses the device model's inverse function to map power to setpoint.
        
        Args:
            target_power: Desired power (kW).
                INTERNAL: From F7 or dispatch optimizer.
            state: Current device state.
                INTERNAL: From F1.
        
        Returns:
            DeviceCommand ready to be sent to GridLAB-D.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F12: Performance Monitoring
    # ------------------------------------------------------------------

    def log_performance(
        self,
        market_obj: MarketObject,
        fulfillment: FulfillmentRecord,
        timestamp: float
    ) -> None:
        """Log delivery performance for a market.
        
        Called every timestep during delivery for each active market.
        
        Args:
            market_obj: The market being delivered.
                INTERNAL: From self._market_objects.
            fulfillment: Fulfillment record from Command Arbiter.
                INTERNAL: From CommandArbiter.resolve_and_actuate().
            timestamp: Current simulation time.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F13: Reconciliation
    # ------------------------------------------------------------------

    def reconcile(self, market_obj: MarketObject) -> SettlementRecord:
        """Compute settlement for a completed delivery.
        
        Compares actual performance against commitment, computes
        penalties (including any deliberate displacement), and
        generates the settlement record.
        
        For batteries, includes degradation cost accounting.
        
        Args:
            market_obj: The market to reconcile.
                INTERNAL: From self._market_objects.
        
        Returns:
            SettlementRecord with financial outcomes.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Phase Handlers
    # ------------------------------------------------------------------

    def _handle_active(self, market_obj: MarketObject) -> None:
        """Execute Active phase logic for a market.
        
        Steps:
        1. Observe device state (F1)
        2. Estimate flexibility (F2)
        3. Generate preference curve (F3)
        4. Query flexibility ledger for available capacity (F6)
        5. Store results on MarketObject
        """
        raise NotImplementedError

    def _handle_negotiation(self, market_obj: MarketObject) -> None:
        """Execute Negotiation phase logic.
        
        If BIDDING mode:
            1. Formulate bid (F4)
            2. Submit bid to MO (F5)
            3. Record tentative commitment on ledger (F6)
        If PRICE_RESPONSIVE mode:
            No-op (preference curve IS the response function)
        """
        raise NotImplementedError

    def _handle_market_lead(self, market_obj: MarketObject) -> None:
        """Execute Market Lead phase logic.
        
        No agent operations. MO is processing.
        """
        raise NotImplementedError

    def _handle_assessment(
        self,
        market_obj: MarketObject,
        clearing_result: ClearingResult
    ) -> None:
        """Execute Assessment phase logic.
        
        Determines if clearing is informational or binding.
        
        If INFORMATIONAL:
            1. Evaluate projected response (F7, F8 — but don't actuate)
            2. Store AdvisoryRecord
            3. Update advisory commitment on ledger
            4. Update price forecast service
            5. Optionally re-run planning optimizer
            6. Transition back to Active for next iteration
        
        If BINDING:
            Transition to Delivery Lead.
        
        Args:
            market_obj: The market being assessed.
            clearing_result: The clearing result from MO.
                INTERNAL: From market communication (F5).
        """
        raise NotImplementedError

    def _handle_delivery_lead(
        self,
        market_obj: MarketObject,
        clearing_result: ClearingResult
    ) -> None:
        """Execute Delivery Lead phase logic.
        
        Steps:
        1. Receive binding clearing result (F5)
        2. Evaluate response — determine target operating point (F7)
        3. Translate to control command (F8)
        4. Book firm commitment on ledger (F6)
        5. Prepare command for Command Arbiter (but don't actuate yet)
        
        Args:
            market_obj: The market entering delivery lead.
            clearing_result: Binding clearing result.
                INTERNAL: From market communication (F5).
        """
        raise NotImplementedError

    def _handle_delivery_start(self, market_obj: MarketObject) -> None:
        """Execute logic when a market first enters Delivery.
        
        Registers the delivery with the Command Arbiter.
        """
        raise NotImplementedError

    def _handle_delivery_tick(self, timestamp: float) -> None:
        """Execute per-timestep logic during any active delivery.
        
        This is called every simulation timestep when at least one
        market is in the Delivery phase. It:
        1. Observes device state (F1)
        2. Recomputes delivery economics for all active deliveries (F15)
        3. Runs dispatch optimization via Command Arbiter
        4. Logs per-market fulfillment (F12)
        
        Args:
            timestamp: Current simulation time.
        """
        raise NotImplementedError

    def _handle_reconcile(self, market_obj: MarketObject) -> None:
        """Execute Reconcile phase logic.
        
        Steps:
        1. Compute settlement (F13)
        2. Release commitment from ledger (F6)
        3. Report to MO (F5)
        4. For batteries, update degradation tracking
        """
        raise NotImplementedError

    def _handle_expired(self, market_obj: MarketObject) -> None:
        """Execute Expired phase logic.
        
        1. Archive market object data
        2. If cyclic market, spawn next cycle's MarketObject
        3. Remove from active markets
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F11: Main Orchestration Loop
    # ------------------------------------------------------------------

    def step(self, current_time: float) -> None:
        """Execute one simulation timestep.
        
        This is the main entry point called by the simulation harness
        every timestep. It:
        
        1. Checks all MarketObjects for state transitions
        2. Executes phase handlers for any transitions
        3. If any deliveries are active, runs delivery tick
        
        Args:
            current_time: Current simulation time.
                EXTERNAL: From simulation harness / GridLAB-D.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Convergence and Confidence (for informational iterations)
    # ------------------------------------------------------------------

    def _compute_convergence(
        self,
        advisory_history: List[AdvisoryRecord]
    ) -> float:
        """Compute convergence metric from advisory history.
        
        Uses exponentially-weighted price volatility across iterations.
        
        Args:
            advisory_history: List of AdvisoryRecords from previous
                informational iterations.
                INTERNAL: From MarketObject.advisory_history.
        
        Returns:
            Convergence metric (0=no convergence, 1=fully converged).
        """
        raise NotImplementedError

    def _compute_confidence(
        self,
        advisory_history: List[AdvisoryRecord]
    ) -> float:
        """Compute advisory confidence from iteration count and convergence.
        
        Args:
            advisory_history: From MarketObject.advisory_history.
                INTERNAL.
        
        Returns:
            Confidence level (0–1).
        """
        raise NotImplementedError