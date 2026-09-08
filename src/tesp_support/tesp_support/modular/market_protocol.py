"""Market protocol and clearing abstractions.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

Defines the core interfaces that separate market design decisions from
device physics and wholesale solvers:
  - Bid: Participant market offer with arbitrary value function
  - ClearingMechanism: Clearing algorithm (unified-price auction, pay-as-bid, etc.)
  - MarketWindow: A single settlement period's timing and mechanism
  - MarketProtocol: Complete settlement structure and timing rules
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class Bid:
    """Market offer with flexible value function.

    A Bid represents a market participant's offer to buy or sell energy.
    The value_function is an arbitrary callable that maps quantity to
    marginal $/MWh, enabling any bidding curve shape without hardcoding
    quadratic polynomials or other specific functional forms.

    Attributes:
        participant_id (str): Unique participant identifier.
        market_id (str): Market this bid is for (e.g., 'DA', 'RT', 'intraday').
        valid_from (int): Start of validity period (simulation time, seconds).
        valid_to (int): End of validity period (simulation time, seconds).
        quantity_min (float): Minimum quantity (MWh).
        quantity_max (float): Maximum quantity (MWh).
        value_function (Callable[[float], float]): Maps quantity Q (MWh) to marginal $/MWh.
                                                    Must be defined for all Q in [quantity_min, quantity_max].
        bid_type (str): 'supply' or 'demand'; optional, for transport layer hints.
        metadata (Dict[str, Any]): Additional bid details (e.g., ramp limits, minimum block size, device type).
    """

    participant_id: str
    market_id: str
    valid_from: int
    valid_to: int
    quantity_min: float
    quantity_max: float
    value_function: Callable[[float], float]
    bid_type: str = "supply"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate bid structure."""
        if self.quantity_min < 0 or self.quantity_max < 0:
            raise ValueError(
                f"Quantities must be non-negative: min={self.quantity_min}, max={self.quantity_max}"
            )
        if self.quantity_min > self.quantity_max:
            raise ValueError(
                f"quantity_min {self.quantity_min} must not exceed quantity_max {self.quantity_max}"
            )
        if self.valid_from >= self.valid_to:
            raise ValueError(
                f"valid_from {self.valid_from} must be before valid_to {self.valid_to}"
            )
        if self.bid_type not in ("supply", "demand"):
            raise ValueError(f"bid_type must be 'supply' or 'demand', got '{self.bid_type}'")
        if self.metadata is None:
            self.metadata = {}

    def marginal_value_at(self, quantity: float) -> float:
        """Evaluate the marginal value ($/MWh) at a given quantity.

        Args:
            quantity: Quantity in MWh.

        Returns:
            Marginal price in $/MWh.

        Raises:
            ValueError: If quantity is outside [quantity_min, quantity_max].
        """
        if not (self.quantity_min <= quantity <= self.quantity_max):
            raise ValueError(
                f"Quantity {quantity} outside valid range [{self.quantity_min}, {self.quantity_max}]"
            )
        return self.value_function(quantity)


@dataclass
class MarketWindow:
    """A single market session with timing and clearing rules.

    Attributes:
        market_id (str): Market identifier (e.g., 'DA', 'RT').
        window_number (int): Ordinal in the settlement structure (e.g., 0 for first DA, 1 for second RT, ...).
        settlement_period_start (int): Start of settlement period (simulation time, seconds).
        settlement_period_end (int): End of settlement period (simulation time, seconds).
        bid_submission_deadline (int): Latest time to submit bids (simulation time, seconds).
        clearing_time (int): When clearing is executed (simulation time, seconds).
        clearing_mechanism_name (str): Identifier for the clearing algorithm (e.g., 'curve_intersection', 'psst', 'uniform_price').
    """

    market_id: str
    window_number: int
    settlement_period_start: int
    settlement_period_end: int
    bid_submission_deadline: int
    clearing_time: int
    clearing_mechanism_name: str

    def __post_init__(self):
        """Validate market window timing."""
        if self.bid_submission_deadline > self.clearing_time:
            raise ValueError(
                f"bid_submission_deadline {self.bid_submission_deadline} must be <= "
                f"clearing_time {self.clearing_time}"
            )
        if self.settlement_period_start >= self.settlement_period_end:
            raise ValueError(
                f"settlement_period_start {self.settlement_period_start} must be < "
                f"settlement_period_end {self.settlement_period_end}"
            )

    @property
    def window_id(self) -> str:
        return f"{self.market_id}_{self.window_number}"


class ClearingMechanism(ABC):
    """Abstract base class for market clearing algorithms.

    A ClearingMechanism takes bids and produces a clearing result
    (cleared quantities and prices per participant). Different instances
    can implement curve intersection, uniform-price auction, pay-as-bid,
    PSST co-optimization, or other clearing rules.

    Subclasses must implement:
      - clear(): Takes list of Bid, returns dict of results.
    """

    @abstractmethod
    def clear(self, bids: List[Bid]) -> Dict[str, Tuple[float, float]]:
        """Clear the market.

        Args:
            bids: List of Bid objects submitted for this market window.

        Returns:
            Dict mapping participant_id → (cleared_quantity_mwh, clearing_price_per_mwh).
            A participant not in the dict is cleared at 0 MWh.

        Raises:
            ValueError: If bids are inconsistent or clearing fails to converge.
        """
        pass


class MarketProtocol(ABC):
    """Abstract base class for market settlement structures.

    A MarketProtocol defines:
      1. Settlement structure: which market windows occur, when, and how often.
      2. Bidding deadlines and clearing times.
      3. Clearing mechanism for each window.

    Subclasses implement specific market designs (e.g., DA + RT, three-settlement,
    double auction) without touching device agents or wholesale solvers.

    Subclasses must implement:
      - settlement_structure(): Returns the list of MarketWindow for a given time period.
      - get_clearing_mechanism(): Returns the ClearingMechanism for a given market window.
    """

    @abstractmethod
    def settlement_structure(
        self, period_start: int, period_end: int
    ) -> List[MarketWindow]:
        """Market windows active within a time period.

        Args:
            period_start: Start of the period (simulation time, seconds).
            period_end: End of the period (simulation time, seconds).

        Returns:
            List of MarketWindow objects ordered by clearing_time.
            If no markets occur in the period, returns an empty list.
        """
        pass

    @abstractmethod
    def get_clearing_mechanism(self, market_window: MarketWindow) -> ClearingMechanism:
        """Retrieve the clearing mechanism for a market window.

        Args:
            market_window: The MarketWindow to clear.

        Returns:
            A ClearingMechanism instance appropriate for this window.
        """
        pass

    def bid_submission_deadline(self, market_window: MarketWindow) -> int:
        """Latest time to submit bids for a market window.

        Default: returns the window's bid_submission_deadline.
        Can be overridden for complex auction rules (e.g., rolling submission windows).

        Args:
            market_window: The market window.

        Returns:
            Simulation time (seconds) after which bids are rejected.
        """
        return market_window.bid_submission_deadline

    @abstractmethod
    def publish_results(self, market_window: MarketWindow, clearing_result: Dict) -> Any:
        """Publish clearing results to participants.

        Default implementations override to return a PriceSignal or other
        market feedback structure for HELICS publication or other transport.

        Args:
            market_window: The cleared market window.
            clearing_result: Output from ClearingMechanism.clear().

        Returns:
            Market feedback object to be transmitted to participants
            (e.g., PriceSignal, dict, JSON).
        """
        pass
