"""Price signal and market feedback data structures.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PriceSignal:
    """Market results and price signals published to participants.

    Attributes:
        market_id (str): Market identifier (e.g., 'DA', 'RT', 'intraday').
        time_step (int): Simulation time in seconds.
        period_start (int): Start of the settlement period (seconds).
        period_end (int): End of the settlement period (seconds).
        clearing_price (float): System marginal clearing price ($/MWh).
        participant_prices (Dict[str, float]): Per-participant clearing prices, if applicable.
        cleared_quantities (Dict[str, float]): Per-participant cleared quantities (MWh).
        constraints_active (Dict[str, bool]): Which transmission/distribution constraints are binding.
        metadata (Dict[str, Any]): Additional information (e.g., iteration count, convergence flags).
    """

    market_id: str
    time_step: int
    period_start: int
    period_end: int
    clearing_price: float
    participant_prices: Dict[str, float] = field(default_factory=dict)
    cleared_quantities: Dict[str, float] = field(default_factory=dict)
    constraints_active: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate price signal fields."""
        if self.clearing_price < 0:
            raise ValueError(f"Clearing price must be non-negative, got {self.clearing_price}")
        if self.period_start >= self.period_end:
            raise ValueError(
                f"Period start {self.period_start} must be before period end {self.period_end}"
            )
