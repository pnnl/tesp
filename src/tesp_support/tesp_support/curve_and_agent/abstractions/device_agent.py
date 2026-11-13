# ============================================================================
# FILE: abstractions/device_agent.py
# PURPOSE: Abstract base class for the top-level device agent — the
#          central orchestrator that manages all agent functions and
#          market participation.
#
# This is the class that the simulation harness instantiates and calls
# step() on every timestep.  It owns all sub-components (device model,
# flexibility ledger, command arbiter, planning optimizer, etc.) and
# manages the collection of MarketObject instances.
#
# The ABC defines the interface that ANY agent — whether managing a
# residential HVAC, a home battery, or (in future) a 500 MW combined-
# cycle plant — must implement.  Device-specific logic lives in the
# concrete device model, preference curve, and control translation;
# the agent orchestration pattern is universal.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     This is the top-level composition root.  It uses (directly or
#     indirectly) every other ABC in the package:
#
#     - AbstractSimulatorInterface  → F1 (read), F9 (write, via arbiter)
#     - AbstractDeviceModel         → F2 (flexibility), F8 (translation)
#     - AbstractPreferenceCurve     → F3 (generation), F7 (evaluation)
#     - AbstractFlexibilityLedger   → F6 (ledger queries and updates)
#     - AbstractMarketCommunication → F5 (bid submission, result reception)
#     - AbstractCommandArbiter      → Delivery tick (dispatch + actuate)
#     - AbstractPlanningOptimizer   → DA planning, assessment re-planning
#     - AbstractPriceForecastService→ Price tracking across iterations
#     - AbstractDataStreamManager   → Forecast/schedule/constraint access
#     - AbstractMarketObject        → State machine management
#     - AbstractPenaltyModel        → Risk-adjusted bidding, reconciliation
#
# IMPORTS FROM:
#     - typing: Any, Dict, List, Optional
#     - abstractions.simulator_interface: AbstractSimulatorInterface
#     - abstractions.device_state: AbstractDeviceState
#     - abstractions.device_model: AbstractDeviceModel
#     - abstractions.preference_curve: AbstractPreferenceCurve
#     - abstractions.penalty_model: AbstractPenaltyModel
#     - abstractions.flexibility_ledger: AbstractFlexibilityLedger
#     - abstractions.market_communication: AbstractMarketCommunication
#     - abstractions.market_object: AbstractMarketObject
#     - abstractions.data_streams: AbstractDataStreamManager
#     - data_types: BidCurve, DeviceCommand, FlexibilityEnvelope,
#                   FulfillmentRecord, MarketTimingParams, SettlementRecord
#     - enums_and_constants: DeviceType, MarketType, OperatingMode
# ============================================================================

"""Abstract device agent — the top-level orchestrator.

The agent follows a sense–decide–act loop each simulation timestep:
    1. Observe device state from the simulator (F1)
    2. Check each MarketObject for state transitions
    3. Execute phase-appropriate functions for each transitioning market
    4. Resolve all active deliveries into a single device command
    5. Actuate the device via the simulator (F9)

The orchestration pattern is identical for all device types.  Device-
specific behavior is encapsulated in the concrete implementations of
AbstractDeviceModel, AbstractPreferenceCurve, and the simulator
interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from abstractions.data_streams import AbstractDataStreamManager
from abstractions.device_state import AbstractDeviceState
from abstractions.market_communication import AbstractMarketCommunication
from abstractions.market_object import AbstractMarketObject
from abstractions.penalty_model import AbstractPenaltyModel
from abstractions.preference_curve import AbstractPreferenceCurve
from abstractions.simulator_interface import AbstractSimulatorInterface
from data_types import (
    BidCurve,
    DeviceCommand,
    FlexibilityEnvelope,
    FulfillmentRecord,
    MarketTimingParams,
    SettlementRecord,
)
from enums_and_constants import DeviceType, MarketType, OperatingMode

class AbstractDeviceAgent(ABC):
    """Abstract base for the top-level device agent.

    Orchestrates all agent functions and manages the collection of
    ``MarketObject`` instances.  This is the class that the simulation
    harness instantiates and calls ``step()`` on every timestep.

    The ABC defines the interface that any agent — whether managing a
    residential HVAC or a 500 MW combined-cycle plant — must implement.

    Args:
        agent_id: Unique identifier.
        device_type: Type of device managed.
        simulator: Simulator interface (GridLAB-D, transmission tool, etc.).
            EXTERNAL: Provided by simulation harness.
        customer_preference_k: Preference factor (0=amenity, 1=financial).
            EXTERNAL: Customer / operator configuration.
        data_stream_manager: Manager for exogenous data.
            EXTERNAL: Must be populated with forecast data.
    """

    def __init__(
        self,
        agent_id: str,
        device_type: DeviceType,
        simulator: AbstractSimulatorInterface,
        customer_preference_k: float,
        data_stream_manager: AbstractDataStreamManager,
    ):
        self._agent_id = agent_id
        self._device_type = device_type
        self._simulator = simulator
        self._k = customer_preference_k
        self._data_streams = data_stream_manager

    # -- Initialization ------------------------------------------------------

    @abstractmethod
    def initialize(self, device_params: Dict[str, Any]) -> None:
        """Initialize the agent with device parameters and create
        shared components (ledger, arbiter, optimizer, etc.).

        Must be called before the simulation loop starts.

        Args:
            device_params: Device-specific configuration.
                EXTERNAL: From device specifications.
        """
        ...

    @abstractmethod
    def register_market(
        self,
        market_type: MarketType,
        timing_params: MarketTimingParams,
        operating_mode: OperatingMode,
        penalty_model: AbstractPenaltyModel,
        communication: AbstractMarketCommunication,
        iteration_protocol: str = "mo_signaled",
        n_informational: Optional[int] = None,
    ) -> None:
        """Register participation in a market product.

        Args:
            market_type: Type of market.
            timing_params: Phase timing.
                EXTERNAL: From MO market rules.
            operating_mode: Bidding, price-responsive, or override.
                EXTERNAL: Agent configuration.
            penalty_model: Non-delivery penalty structure.
                EXTERNAL: From MO market rules.
            communication: Communication interface to the MO.
                EXTERNAL: From simulation harness.
            iteration_protocol: How informational iterations work.
            n_informational: Number of informational iterations (if fixed).
        """
        ...

    @abstractmethod
    def spawn_market_cycle(
        self,
        market_type: MarketType,
        clearing_time: float,
    ) -> str:
        """Create a new ``MarketObject`` for an upcoming cycle.

        Args:
            market_type: Type of market.
            clearing_time: When this cycle clears (simulation time).

        Returns:
            market_id of the new ``MarketObject``.
        """
        ...

    # -- F1: State Observation -----------------------------------------------

    @abstractmethod
    def observe_device_state(self) -> AbstractDeviceState:
        """Read current device state from the simulator.

        Returns:
            Concrete device state.
        """
        ...

    # -- F2: Flexibility Estimation ------------------------------------------

    @abstractmethod
    def estimate_flexibility(
        self,
        state: AbstractDeviceState,
        interval_duration: float,
    ) -> FlexibilityEnvelope:
        """Estimate feasible operating range for the upcoming interval.

        Args:
            state: Current device state from F1.
            interval_duration: Market interval (seconds).

        Returns:
            ``FlexibilityEnvelope``.
        """
        ...

    # -- F3: Preference Curve ------------------------------------------------

    @abstractmethod
    def generate_preference_curve(
        self,
        flexibility: FlexibilityEnvelope,
    ) -> AbstractPreferenceCurve:
        """Generate the customer / operator preference curve.

        Args:
            flexibility: From F2.

        Returns:
            Concrete ``AbstractPreferenceCurve`` subclass.
        """
        ...

    # -- F4: Bid Formulation -------------------------------------------------

    @abstractmethod
    def formulate_bid(
        self,
        market_obj: AbstractMarketObject,
        flexibility: FlexibilityEnvelope,
        preference_curve: AbstractPreferenceCurve,
    ) -> BidCurve:
        """Formulate a bid curve for a specific market.

        Args:
            market_obj: The market being bid into.
            flexibility: Available flexibility.
            preference_curve: Customer preference curve.

        Returns:
            ``BidCurve``.
        """
        ...

    # -- F7: Price Response --------------------------------------------------

    @abstractmethod
    def evaluate_price_response(
        self,
        price: float,
        curve: Any,
    ) -> float:
        """Determine desired operating point from a price signal.

        Args:
            price: Cleared or observed price ($/kWh).
            curve: Bid curve (bidding mode) or preference curve
                (price-responsive mode).

        Returns:
            Desired power (kW).
        """
        ...

    # -- F8: Control Translation ---------------------------------------------

    @abstractmethod
    def translate_to_control(
        self,
        target_power: float,
        state: AbstractDeviceState,
    ) -> DeviceCommand:
        """Convert target power to device-specific control command.

        Args:
            target_power: Desired power (kW).
            state: Current device state.

        Returns:
            ``DeviceCommand``.
        """
        ...

    # -- F12: Performance Monitoring -----------------------------------------

    @abstractmethod
    def log_performance(
        self,
        market_obj: AbstractMarketObject,
        fulfillment: FulfillmentRecord,
        timestamp: float,
    ) -> None:
        """Log delivery performance for a market.

        Args:
            market_obj: The market being delivered.
            fulfillment: From Command Arbiter.
            timestamp: Current simulation time.
        """
        ...

    # -- F13: Reconciliation -------------------------------------------------

    @abstractmethod
    def reconcile(
        self,
        market_obj: AbstractMarketObject,
    ) -> SettlementRecord:
        """Compute settlement for a completed delivery.

        Args:
            market_obj: The market to reconcile.

        Returns:
            ``SettlementRecord``.
        """
        ...

    # -- F11: Main Loop ------------------------------------------------------

    @abstractmethod
    def step(self, current_time: float) -> None:
        """Execute one simulation timestep.

        This is the main entry point called by the simulation harness
        every timestep.

        Args:
            current_time: Current simulation time.
                EXTERNAL: From simulation harness.
        """
        ...