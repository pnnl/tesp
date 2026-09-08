"""Device participant strategy interface.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

Defines the DeviceStrategy abstraction, which decouples device optimization
and bid formulation from market protocol details.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from .market_protocol import Bid, MarketWindow
from .price_signal import PriceSignal


class DeviceStrategy(ABC):
    """Abstract base class for device participation in energy markets.

    A DeviceStrategy encapsulates the logic for how a device (HVAC, battery, EV, etc.)
    observes market prices, forecasts needs, optimizes its operation, and formulates
    bids. Different strategy implementations can represent different device types,
    optimization algorithms (optimal, rule-based, RL), or physical constraints
    (thermal mass, state-of-charge, recharge time).

    Device physics (thermal dynamics, battery chemistry, etc.) should be encapsulated
    within concrete implementations, not exposed to the MarketProtocol.

    Subclasses must implement:
      - observe_prices(): Update the strategy with new price signals.
      - formulate_bid(): Generate a Bid for a market window.

    Optionally override:
      - initialize(): Called once at simulation start.
      - finalize(): Called at simulation end.
    """

    def __init__(self, device_id: str, device_type: str):
        """Initialize a device strategy.

        Args:
            device_id: Unique identifier for this device instance.
            device_type: Device class (e.g., 'HVAC', 'Battery', 'EV', 'Thermostat').
        """
        self.device_id = device_id
        self.device_type = device_type

    def initialize(self) -> None:
        """Called once at the start of the simulation.

        Override to set up initial state, load historical data, or initialize
        optimization solver instances.
        """
        pass

    def finalize(self) -> None:
        """Called once at the end of the simulation.

        Override to clean up resources, log final state, or generate reports.
        """
        pass

    @abstractmethod
    def observe_prices(self, price_signal: PriceSignal) -> None:
        """Observe a price signal and update device state.

        Called after each market clearing. The device uses the cleared prices
        and feedback to refine expectations and prepare bids for future markets.

        Args:
            price_signal: Market results and prices from the most recent clearing.
        """
        pass

    @abstractmethod
    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Generate a bid for a market window.

        Called before the bid submission deadline. The device must return a Bid
        that specifies its quantity range and value function. The value_function
        is arbitrary and can represent any bidding curve shape (quadratic, piecewise,
        step function, etc.).

        Args:
            market_window: The market window for which a bid is requested.

        Returns:
            A Bid object with participant_id, market_id, quantity range, and value_function.

        Raises:
            ValueError: If the device cannot formulate a valid bid for this window.
        """
        pass

    def formulate_bids_for_windows(
        self, market_windows: list["MarketWindow"]
    ) -> Dict[str, Bid]:
        """Generate bids for multiple market windows.

        Default implementation calls formulate_bid() for each window.
        Override if a device wants to co-optimize across multiple windows
        (e.g., DA and RT simultaneously).

        Args:
            market_windows: List of MarketWindow objects.

        Returns:
            Dict mapping market_id → Bid. Only windows with successfully
            formulated bids are included.
        """
        result = {}
        for window in market_windows:
            try:
                bid = self.formulate_bid(window)
                result[window.market_id] = bid
            except ValueError:
                # Device opts out of this market window; skip it.
                pass
        return result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(device_id={self.device_id!r}, device_type={self.device_type!r})"
