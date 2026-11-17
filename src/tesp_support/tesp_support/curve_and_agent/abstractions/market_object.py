# ============================================================================
# FILE: abstractions/market_object.py
# PURPOSE: Abstract base class for the per-market-cycle state machine
#          and data container.
#
# Each market product the agent participates in is represented by a
# MarketObject instance that owns its own state machine.  The object
# tracks its progression through the market phases:
#
#     INACTIVE → ACTIVE → NEGOTIATION → MARKET_LEAD → ASSESSMENT
#         ↑ (informational loop)                          │
#         └────────────────────────────────── or ─────────┘
#                                                         ↓
#     DELIVERY_LEAD → DELIVERY → RECONCILE → EXPIRED
#
# Multiple MarketObjects for the same market type may be alive
# simultaneously in different phases (e.g., RT cycle N in DELIVERY
# while RT cycle N+1 is in NEGOTIATION).
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Used by: AbstractDeviceAgent (owns a collection of MarketObjects,
#                dispatches phase handlers based on current_phase)
#     - Consumes: ClearingResult (to determine iteration type)
#
# IMPORTS FROM:
#     - typing: Optional
#     - data_types: ClearingResult
#     - enums_and_constants: MarketPhase, MarketType, OperatingMode,
#                            IterationType
# ============================================================================

"""Abstract market object — state machine for one market cycle.

The MarketObject's state transitions are independent of other
MarketObjects.  Cross-market coordination is handled by the
FlexibilityLedger (capacity accounting) and CommandArbiter
(delivery merging), not by coupling state machines.
"""

from abc import ABC, abstractmethod
from typing import Optional

from data_types import ClearingResult
from enums_and_constants import (
    IterationType,
    MarketPhase,
    MarketType,
    OperatingMode,
)

class AbstractMarketObject(ABC):
    """Abstract base for the per-market-cycle state machine and data
    container.

    Each market product the agent participates in is represented by a
    ``MarketObject`` instance that owns its own state machine.  Multiple
    objects for the same market type may be alive simultaneously in
    different phases.
    """

    @property
    @abstractmethod
    def market_id(self) -> str:
        """Unique identifier for this market cycle."""
        ...

    @property
    @abstractmethod
    def market_type(self) -> MarketType:
        """Type of market product."""
        ...

    @property
    @abstractmethod
    def current_phase(self) -> MarketPhase:
        """Current state machine phase."""
        ...

    @property
    @abstractmethod
    def operating_mode(self) -> OperatingMode:
        """How the agent participates in this market."""
        ...

    @abstractmethod
    def transition_to(self, new_phase: MarketPhase) -> None:
        """Execute a state transition.

        Args:
            new_phase: Target phase.

        Raises:
            ValueError: If the transition is illegal from the current phase.
        """
        ...

    @abstractmethod
    def should_transition(
        self,
        current_time: float,
    ) -> Optional[MarketPhase]:
        """Check if a transition should occur at the current time.

        Args:
            current_time: Simulation time.

        Returns:
            Target phase if a transition is due, ``None`` otherwise.
        """
        ...

    @abstractmethod
    def is_informational_iteration(
        self,
        clearing_result: ClearingResult,
    ) -> bool:
        """Determine whether a clearing result is informational or binding.

        Args:
            clearing_result: From the MO.

        Returns:
            ``True`` if informational.
        """
        ...
