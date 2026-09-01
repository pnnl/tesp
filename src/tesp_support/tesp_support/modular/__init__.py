"""Modular market protocol abstractions for TESP.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

This package defines clean interfaces for market design, device optimization,
and settlement structure. These abstractions enable market design experiments
without touching device physics, HELICS federation structure, or wholesale solvers.

Key interfaces:
  - Bid: Market offer with arbitrary value_function
  - ClearingMechanism: Clearing algorithm (curve intersection, auction, co-optimization, etc.)
  - MarketProtocol: Settlement structure, timing, and bidding deadlines
  - DeviceStrategy: Device optimization and bid formulation
  - PriceSignal: Price and constraint information published to participants
"""

from .market_protocol import (
    Bid,
    ClearingMechanism,
    MarketProtocol,
    MarketWindow,
)
from .device_strategy import DeviceStrategy
from .price_signal import PriceSignal
from .dsot_market_protocol import DSOTMarketProtocol, DSOTCurveIntersectionClearing
from .dsot_device_strategies import (
    DSOTDeviceStrategy,
    HVACDSOTStrategy,
    BatteryDSOTStrategy,
    EVDSOTStrategy,
    WaterHeaterDSOTStrategy,
    PVDSOTStrategy,
)
from .battery_adapter_example import BatteryDSOTStrategyAdapter
from .hvac_adapter import HVACDSOTStrategyAdapter
from .ev_adapter import EVDSOTStrategyAdapter
from .water_heater_adapter import WaterHeaterDSOTStrategyAdapter
from .pv_adapter import PVDSOTStrategyAdapter

__all__ = [
    # Abstract base classes
    "Bid",
    "ClearingMechanism",
    "MarketProtocol",
    "MarketWindow",
    "DeviceStrategy",
    "PriceSignal",
    # DSOT concrete implementations
    "DSOTMarketProtocol",
    "DSOTCurveIntersectionClearing",
    "DSOTDeviceStrategy",
    "HVACDSOTStrategy",
    "BatteryDSOTStrategy",
    "EVDSOTStrategy",
    "WaterHeaterDSOTStrategy",
    "PVDSOTStrategy",
    # Device strategy adapters (wrap legacy agents)
    "BatteryDSOTStrategyAdapter",
    "HVACDSOTStrategyAdapter",
    "EVDSOTStrategyAdapter",
    "WaterHeaterDSOTStrategyAdapter",
    "PVDSOTStrategyAdapter",
]
