# ============================================================================
# FILE: command_arbiter.py
# PURPOSE: Merges simultaneous delivery obligations from multiple markets
#          into a single physical device command. Uses the dispatch optimizer
#          for economically-driven priority resolution.
#
# INTERNAL: This is the only component that calls F9 (device actuation).
# ============================================================================

from typing import Dict, List, Optional, Tuple
from data_types import (
    DeviceCommand, DispatchSolution, FulfillmentRecord, 
    DeliveryEconomics, PerformanceEntry
)
from dispatch_optimizer import DispatchOptimizer, DeliveryValueCalculator
from preference_curve import PreferenceCurve
from penalty_model import PenaltyModel
from gridlabd_interface import GridLABDInterface
from device_models import HVACModel, WaterHeaterModel, EVChargerModel, BatteryModel
from enums_and_constants import DeviceType


class DeliveryRecord:
    """Record of an active delivery tracked by the Command Arbiter.
    
    Attributes:
        market_id: ID of the market.
        market_type: Type of market product.
        product_type: Energy, regulation, or reserve.
        committed_qty: Committed quantity (kW or kW-band).
        cleared_price: Clearing price.
        penalty_model: Reference to the penalty model.
        interval: (start, end) of delivery.
        performance_log: Timestamped performance entries.
    """

    def __init__(
        self,
        market_id: str,
        market_type: str,
        product_type: str,
        committed_qty: float,
        cleared_price: float,
        penalty_model: PenaltyModel,
        interval: Tuple[float, float]
    ):
        self.market_id = market_id
        self.market_type = market_type
        self.product_type = product_type
        self.committed_qty = committed_qty
        self.cleared_price = cleared_price
        self.penalty_model = penalty_model
        self.interval = interval
        self.performance_log: List[PerformanceEntry] = []


class CommandArbiter:
    """Resolves simultaneous delivery obligations into a single device command.
    
    Uses the DispatchOptimizer to determine the economically optimal
    operating point, then translates it to a device-specific control
    command and actuates via the GridLAB-D interface.
    
    This is the ONLY component that writes to the device. No individual
    market handler actuates directly.
    
    Args:
        device_type: Type of physical device.
        gridlabd: GridLAB-D interface for device actuation.
            INTERNAL: Provided by the agent.
        device_model: Device-specific physics model for control translation.
            INTERNAL: One of HVACModel, WaterHeaterModel, etc.
        optimizer: Dispatch optimizer instance.
            INTERNAL: Created by the agent.
        value_calculator: Delivery value calculator.
            INTERNAL: Created by the agent.
    """

    def __init__(
        self,
        device_type: DeviceType,
        gridlabd: GridLABDInterface,
        device_model: any,
        optimizer: DispatchOptimizer,
        value_calculator: DeliveryValueCalculator
    ):
        self._device_type = device_type
        self._gridlabd = gridlabd
        self._device_model = device_model
        self._optimizer = optimizer
        self._value_calculator = value_calculator
        self._active_deliveries: Dict[str, DeliveryRecord] = {}

    def register_delivery(
        self,
        market_id: str,
        market_type: str,
        product_type: str,
        committed_qty: float,
        cleared_price: float,
        penalty_model: PenaltyModel,
        interval: Tuple[float, float]
    ) -> None:
        """Register a new active delivery.
        
        Called when a market enters the Delivery phase.
        
        Args:
            market_id: ID of the market.
            market_type: Type of market.
            product_type: Product type.
            committed_qty: Committed power (kW).
                INTERNAL: From MarketObject.cleared_quantity.
            cleared_price: Clearing price.
                INTERNAL: From MarketObject.cleared_price.
            penalty_model: Applicable penalty model.
                INTERNAL: From penalty model registry.
            interval: (start, end) of delivery window.
        """
        raise NotImplementedError

    def update_signals(
        self,
        signals: Dict[str, float]
    ) -> None:
        """Update real-time signals (regulation signal, reserve activation).
        
        Called every timestep with the latest market signals.
        
        Args:
            signals: Dictionary of signal values.
                EXTERNAL: From MO or ISO signal feed.
                Keys: 'regulation_signal' (float, -1 to +1),
                      'reserve_activated' (float, 0 or 1).
        """
        raise NotImplementedError

    def deregister_delivery(self, market_id: str) -> None:
        """Remove a delivery when its market exits the Delivery phase.
        
        Args:
            market_id: ID of the market to remove.
        """
        raise NotImplementedError

    def resolve_and_actuate(
        self,
        device_state: any,
        preference_curve: PreferenceCurve,
        amenity_weight: float,
        current_time: float
    ) -> Dict[str, FulfillmentRecord]:
        """Resolve all active deliveries into a single device command.
        
        This is the core method called every simulation timestep.
        It:
        1. Computes economic profiles for all active deliveries
        2. Runs the dispatch optimizer
        3. Translates the optimal Q to a device command
        4. Actuates the device via GridLAB-D
        5. Returns per-market fulfillment records
        
        Args:
            device_state: Current device state from F1.
                INTERNAL: From agent's state observation.
            preference_curve: Customer preference curve.
                INTERNAL: From PreferenceCurve (F3).
            amenity_weight: Weight on amenity cost.
                INTERNAL: From customer preference k.
            current_time: Current simulation time.
        
        Returns:
            Dictionary mapping market_id to FulfillmentRecord.
        """
        raise NotImplementedError