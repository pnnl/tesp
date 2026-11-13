# ============================================================================
# FILE: abstractions/command_arbiter.py
# PURPOSE: Abstract base class for merging simultaneous delivery
#          obligations from multiple markets into a single physical
#          device command.
#
# The Command Arbiter is the ONLY component that calls
# AbstractSimulatorInterface.write_device_command() (F9).  No individual
# market handler actuates the device directly.
#
# The arbiter's resolve_and_actuate() method:
#     1. Computes economic profiles for all active deliveries (F15)
#     2. Runs the dispatch optimizer (F16)
#     3. Translates the optimal Q to a device command (F8)
#     4. Actuates via the simulator interface (F9)
#     5. Returns per-market fulfillment records
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Uses: AbstractSimulatorInterface (F9 actuation)
#             AbstractDeviceModel (F8 control translation)
#             AbstractDispatchOptimizer (F16 economic dispatch)
#             AbstractDeliveryValueCalculator (F15 delivery economics)
#             AbstractPreferenceCurve (amenity cost for optimizer)
#             AbstractPenaltyModel (penalty economics per delivery)
#             AbstractDeviceState (current state for translation)
#     - Used by: AbstractDeviceAgent._handle_delivery_tick()
#
# IMPORTS FROM:
#     - typing: Dict, Tuple
#     - abstractions.simulator_interface: AbstractSimulatorInterface
#     - abstractions.device_model: AbstractDeviceModel
#     - abstractions.device_state: AbstractDeviceState
#     - abstractions.dispatch_optimizer: AbstractDispatchOptimizer,
#                                        AbstractDeliveryValueCalculator
#     - abstractions.preference_curve: AbstractPreferenceCurve
#     - abstractions.penalty_model: AbstractPenaltyModel
#     - data_types: FulfillmentRecord
#     - enums_and_constants: DeviceType, MarketType, ProductType
# ============================================================================

"""Abstract command arbiter — single-actuation-point for the device.

Regardless of how many markets are simultaneously in delivery, the
device receives exactly one control command per timestep, produced by
this arbiter.  This is both a correctness requirement (a thermostat
has one setpoint) and a simplification (no race conditions).
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple

from abstractions.device_model import AbstractDeviceModel
from abstractions.device_state import AbstractDeviceState
from abstractions.dispatch_optimizer import (
    AbstractDeliveryValueCalculator,
    AbstractDispatchOptimizer,
)
from abstractions.penalty_model import AbstractPenaltyModel
from abstractions.preference_curve import AbstractPreferenceCurve
from abstractions.simulator_interface import AbstractSimulatorInterface
from data_types import FulfillmentRecord
from enums_and_constants import DeviceType, MarketType, ProductType

class AbstractCommandArbiter(ABC):
    """Abstract base for merging simultaneous delivery obligations into
    a single physical device command.

    The Command Arbiter is the **only** component that calls
    ``AbstractSimulatorInterface.write_device_command()`` (F9).  No
    individual market handler actuates directly.

    Args:
        device_type: Type of physical device.
        simulator: Simulator interface for actuation.
        device_model: Device physics model for control translation (F8).
        optimizer: Dispatch optimizer for economic resolution (F16).
        value_calculator: Delivery value calculator (F15).
    """

    def __init__(
        self,
        device_type: DeviceType,
        simulator: AbstractSimulatorInterface,
        device_model: AbstractDeviceModel,
        optimizer: AbstractDispatchOptimizer,
        value_calculator: AbstractDeliveryValueCalculator,
    ):
        self._device_type = device_type
        self._simulator = simulator
        self._device_model = device_model
        self._optimizer = optimizer
        self._value_calculator = value_calculator

    @abstractmethod
    def register_delivery(
        self,
        market_id: str,
        market_type: MarketType,
        product_type: ProductType,
        committed_qty: float,
        cleared_price: float,
        penalty_model: AbstractPenaltyModel,
        interval: Tuple[float, float],
    ) -> None:
        """Register a new active delivery.

        Called when a market enters the DELIVERY phase.

        Args:
            market_id: Market cycle identifier.
            market_type: Type of market.
            product_type: Product type.
            committed_qty: Committed power (kW).
            cleared_price: Clearing price.
            penalty_model: Applicable penalty model.
            interval: (start, end) of delivery window.
        """
        ...

    @abstractmethod
    def deregister_delivery(self, market_id: str) -> None:
        """Remove a delivery when its market exits DELIVERY.

        Args:
            market_id: Market cycle identifier.
        """
        ...

    @abstractmethod
    def update_signals(self, signals: Dict[str, float]) -> None:
        """Update real-time signals (regulation, reserve activation).

        Args:
            signals: Signal values.
                EXTERNAL: From MO or ISO.
        """
        ...

    @abstractmethod
    def resolve_and_actuate(
        self,
        device_state: AbstractDeviceState,
        preference_curve: AbstractPreferenceCurve,
        amenity_weight: float,
        current_time: float,
    ) -> Dict[str, FulfillmentRecord]:
        """Resolve all active deliveries into a single device command,
        then actuate the device.

        Steps:
            1. Compute economic profiles for all active deliveries (F15).
            2. Run dispatch optimization (F16).
            3. Translate optimal Q to device command (F8).
            4. Actuate device via simulator interface (F9).
            5. Return per-market fulfillment records.

        Args:
            device_state: Current state from F1.
            preference_curve: Customer preference curve from F3.
            amenity_weight: Weight on amenity cost (from *k*).
            current_time: Current simulation time.

        Returns:
            Dictionary mapping market_id to ``FulfillmentRecord``.
        """
        ...
