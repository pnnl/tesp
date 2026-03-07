# ============================================================================
# FILE: market_object.py
# PURPOSE: Market state machine and per-market-cycle data tracking.
#          One MarketObject is instantiated per market product per cycle.
# ============================================================================

from typing import Dict, List, Optional, Any, Tuple
from data_types import (
    BidCurve, ClearingResult, AdvisoryRecord, SettlementRecord,
    PerformanceEntry, MarketTimingParams, DeviceCommand
)
from enums_and_constants import (
    MarketType, MarketPhase, OperatingMode, IterationType,
    CommitmentStatus
)

# Legal transitions: map from current phase to set of allowed next phases
_LEGAL_TRANSITIONS = {
    MarketPhase.INACTIVE: {MarketPhase.ACTIVE},
    MarketPhase.ACTIVE: {MarketPhase.NEGOTIATION},
    MarketPhase.NEGOTIATION: {MarketPhase.MARKET_LEAD},
    MarketPhase.MARKET_LEAD: {MarketPhase.ASSESSMENT},
    MarketPhase.ASSESSMENT: {MarketPhase.ACTIVE, MarketPhase.DELIVERY_LEAD},
    MarketPhase.DELIVERY_LEAD: {MarketPhase.DELIVERY},
    MarketPhase.DELIVERY: {MarketPhase.RECONCILE},
    MarketPhase.RECONCILE: {MarketPhase.EXPIRED},
    MarketPhase.EXPIRED: set(),
}

# Map phase to the timing param that triggers the *next* phase transition
_PHASE_TO_NEXT_TIME = {
    MarketPhase.INACTIVE: 't_activate',
    MarketPhase.ACTIVE: 't_negotiate',
    MarketPhase.NEGOTIATION: 't_market_lead',
    MarketPhase.MARKET_LEAD: 't_clear',
    MarketPhase.ASSESSMENT: 't_delivery_start',
    MarketPhase.DELIVERY_LEAD: 't_delivery_start',
    MarketPhase.DELIVERY: 't_delivery_end',
    MarketPhase.RECONCILE: 't_reconcile_end',
}

_PHASE_TO_NEXT_PHASE = {
    MarketPhase.INACTIVE: MarketPhase.ACTIVE,
    MarketPhase.ACTIVE: MarketPhase.NEGOTIATION,
    MarketPhase.NEGOTIATION: MarketPhase.MARKET_LEAD,
    MarketPhase.MARKET_LEAD: MarketPhase.ASSESSMENT,
    MarketPhase.DELIVERY_LEAD: MarketPhase.DELIVERY,
    MarketPhase.DELIVERY: MarketPhase.RECONCILE,
    MarketPhase.RECONCILE: MarketPhase.EXPIRED,
}


class MarketObject:
    """State machine and data container for one market cycle.
    
    Each market product the agent participates in is represented by
    a MarketObject instance. The object tracks its own state machine
    (INACTIVE → ACTIVE → ... → EXPIRED) independently of other
    market objects.
    
    For cyclic markets (RT energy every 5 minutes), a new MarketObject
    is created for each cycle. Multiple MarketObjects for the same
    market type may be alive simultaneously in different phases.
    
    Args:
        market_id: Unique identifier for this market cycle.
            Format suggestion: "{market_type}_{clearing_time}".
        market_type: Type of market product.
        timing_params: When each phase begins and ends.
            EXTERNAL: Defined by market rules, provided at registration.
        operating_mode: BIDDING, PRICE_RESPONSIVE, or OVERRIDE.
            EXTERNAL: Configured per market product by the agent operator.
        iteration_protocol: How informational iterations are managed.
            'fixed_count': n_informational iterations then binding.
            'mo_signaled': MO indicates iteration type in clearing result.
            'time_gated': All clears before t_binding are informational.
            EXTERNAL: Defined by market rules.
        n_informational_planned: For 'fixed_count' protocol, how many
            informational iterations before the binding one.
            EXTERNAL: Defined by market rules.
    """

    def __init__(
        self,
        market_id: str,
        market_type: MarketType,
        timing_params: MarketTimingParams,
        operating_mode: OperatingMode = OperatingMode.BIDDING,
        iteration_protocol: str = "mo_signaled",
        n_informational_planned: Optional[int] = None
    ):
        self.market_id = market_id
        self.market_type = market_type
        self.timing_params = timing_params
        self.operating_mode = operating_mode
        self.iteration_protocol = iteration_protocol
        self.n_informational_planned = n_informational_planned

        # State machine
        self.current_phase: MarketPhase = MarketPhase.INACTIVE
        self.current_iteration: int = 0
        self.current_iteration_type: IterationType = IterationType.INFORMATIONAL

        # Data populated during Active phase
        self.available_flexibility: Optional[Any] = None
        self.preference_curve: Optional[Any] = None

        # Data populated during Negotiation
        self.submitted_bid: Optional[BidCurve] = None
        self.negotiation_round: int = 0

        # Data populated during Delivery Lead
        self.cleared_price: float = 0.0
        self.cleared_quantity: float = 0.0
        self.target_operating_point: float = 0.0
        self.control_command: Optional[DeviceCommand] = None

        # Data populated during Delivery
        self.performance_log: List[PerformanceEntry] = []

        # Data populated during Reconcile
        self.settlement_record: Optional[SettlementRecord] = None

        # Advisory history (informational iterations)
        self.advisory_history: List[AdvisoryRecord] = []
        self.latest_advisory: Optional[AdvisoryRecord] = None
        self.advisory_confidence: float = 0.0

    def transition_to(self, new_phase: MarketPhase) -> None:
        """Execute a state transition.
        
        Validates that the transition is legal per the state machine
        definition, then updates current_phase.
        
        Args:
            new_phase: The target phase.
        
        Raises:
            ValueError: If the transition is not legal from the 
                current phase.
        """
        allowed = _LEGAL_TRANSITIONS.get(self.current_phase, set())
        if new_phase not in allowed:
            raise ValueError(
                f"Illegal transition from {self.current_phase.name} "
                f"to {new_phase.name}")
        self.current_phase = new_phase

    def get_next_event_time(self, current_time: float) -> Optional[float]:
        """Compute when the next state transition should occur.
        
        Based on current_phase and timing_params, returns the
        simulation time at which the next transition should fire.
        
        Args:
            current_time: Current simulation time.
        
        Returns:
            Time of next transition, or None if in terminal state.
        """
        if self.current_phase == MarketPhase.EXPIRED:
            return None
        attr = _PHASE_TO_NEXT_TIME.get(self.current_phase)
        if attr is None:
            return None
        return getattr(self.timing_params, attr)

    def should_transition(self, current_time: float) -> Optional[MarketPhase]:
        """Check if a transition should occur at the current time.
        
        Args:
            current_time: Current simulation time.
        
        Returns:
            Target phase if a transition should occur, None otherwise.
        """
        if self.current_phase == MarketPhase.EXPIRED:
            return None
        next_time = self.get_next_event_time(current_time)
        if next_time is not None and current_time >= next_time:
            next_phase = _PHASE_TO_NEXT_PHASE.get(self.current_phase)
            return next_phase
        return None

    def is_informational_iteration(self, clearing_result: ClearingResult) -> bool:
        """Determine if a clearing result is informational or binding.
        
        Uses the configured iteration_protocol to make the determination.
        
        Args:
            clearing_result: The clearing result from the MO.
                INTERNAL: From market communication interface (F5).
        
        Returns:
            True if this is an informational iteration.
        """
        if self.iteration_protocol == "mo_signaled":
            return clearing_result.iteration_type == IterationType.INFORMATIONAL
        elif self.iteration_protocol == "fixed_count":
            n = self.n_informational_planned or 0
            return self.current_iteration <= n
        return False