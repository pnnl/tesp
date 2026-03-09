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
    DeviceCommand,
    DispatchSolution,
    FulfillmentRecord,
    DeliveryEconomics,
    PerformanceEntry,
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
        interval: Tuple[float, float],
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
        value_calculator: DeliveryValueCalculator,
    ):
        self._device_type = device_type
        self._gridlabd = gridlabd
        self._device_model = device_model
        self._optimizer = optimizer
        self._value_calculator = value_calculator
        self._active_deliveries: Dict[str, DeliveryRecord] = {}
        self._signals: Dict[str, float] = {}

    def register_delivery(
        self,
        market_id: str,
        market_type: str,
        product_type: str,
        committed_qty: float,
        cleared_price: float,
        penalty_model: PenaltyModel,
        interval: Tuple[float, float],
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
        self._active_deliveries[market_id] = DeliveryRecord(
            market_id=market_id,
            market_type=market_type,
            product_type=product_type,
            committed_qty=committed_qty,
            cleared_price=cleared_price,
            penalty_model=penalty_model,
            interval=interval,
        )

    def update_signals(self, signals: Dict[str, float]) -> None:
        """Update real-time signals (regulation signal, reserve activation).

        Called every timestep with the latest market signals.

        Args:
            signals: Dictionary of signal values.
                EXTERNAL: From MO or ISO signal feed.
                Keys: 'regulation_signal' (float, -1 to +1),
                      'reserve_activated' (float, 0 or 1).
        """
        self._signals.update(signals)

    def deregister_delivery(self, market_id: str) -> None:
        """Remove a delivery when its market exits the Delivery phase.

        Args:
            market_id: ID of the market to remove.
        """
        self._active_deliveries.pop(market_id, None)

    def resolve_and_actuate(
        self,
        device_state: any,
        preference_curve: PreferenceCurve,
        amenity_weight: float,
        current_time: float,
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
        if not self._active_deliveries:
            return {}

        # 1. Build DeliveryEconomics for each active delivery
        economics: Dict[str, DeliveryEconomics] = {}
        for mid, rec in self._active_deliveries.items():
            interval_duration = rec.interval[1] - rec.interval[0]
            economics[mid] = self._value_calculator.compute(
                market_id=mid,
                product_type=rec.product_type,
                committed_qty=rec.committed_qty,
                cleared_price=rec.cleared_price,
                penalty_model=rec.penalty_model,
                interval_duration=interval_duration,
                signals=self._signals,
            )

        # 2. Get device flexibility bounds from device model
        try:
            envelope = self._device_model.estimate_flexibility(
                state=device_state, interval_duration=300.0
            )
            Q_min = envelope.Q_min
            Q_max = envelope.Q_max
        except (AttributeError, NotImplementedError):
            Q_min = 0.0
            Q_max = 10.0

        # 3. Run dispatch optimizer
        solution = self._optimizer.solve(
            economics=economics,
            Q_min=Q_min,
            Q_max=Q_max,
            preference_curve=preference_curve,
            amenity_weight=amenity_weight,
            current_signals=self._signals if self._signals else None,
        )

        # 4. Translate optimal Q to device command and actuate
        command = self._translate_to_command(solution.Q, device_state)
        self._actuate(command)

        # 5. Build per-market fulfillment records
        fulfillments: Dict[str, FulfillmentRecord] = {}
        for mid, rec in self._active_deliveries.items():
            actual = solution.allocation.get(mid, 0.0)
            shortfall = max(0.0, rec.committed_qty - actual)
            revenue = actual * rec.cleared_price
            penalty = 0.0
            if shortfall > 0 and mid in economics:
                econ = economics[mid]
                if econ.penalty_fn is not None:
                    penalty = econ.penalty_fn(actual)

            fulfillments[mid] = FulfillmentRecord(
                market_id=mid,
                committed=rec.committed_qty,
                actual=actual,
                shortfall=shortfall,
                revenue=revenue,
                penalty=penalty,
                net_value=revenue - penalty,
                displaced_by=solution.displacement_chain.get(mid),
            )

            # Log performance entry
            rec.performance_log.append(
                PerformanceEntry(
                    timestamp=current_time,
                    committed=rec.committed_qty,
                    actual=actual,
                    shortfall=shortfall,
                    revenue=revenue,
                    penalty=penalty,
                    net_value=revenue - penalty,
                    was_displaced=mid in solution.displacement_chain,
                    displaced_by=solution.displacement_chain.get(mid),
                )
            )

        return fulfillments

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _translate_to_command(
        self, target_Q: float, device_state: any
    ) -> DeviceCommand:
        """Translate an optimal power target to a device-specific command."""
        if self._device_type in (DeviceType.HVAC_AC_ONLY, DeviceType.HVAC_HEAT_PUMP):
            try:
                setpoint = self._device_model.power_to_setpoint(
                    target_power_kw=target_Q,
                    state=device_state,
                    outdoor_temp=device_state.outdoor_air_temp,
                    interval_duration=300.0,
                )
            except (AttributeError, NotImplementedError):
                setpoint = 72.0
            mode = getattr(device_state, "hvac_mode", "cooling")
            return DeviceCommand(
                device_type=self._device_type,
                setpoint=setpoint,
                mode=mode,
                power_target=target_Q,
            )
        elif self._device_type == DeviceType.WATER_HEATER:
            try:
                setpoint = self._device_model.power_to_setpoint(
                    target_power_kw=target_Q,
                    state=device_state,
                    interval_duration=300.0,
                )
            except (AttributeError, NotImplementedError):
                setpoint = 130.0
            return DeviceCommand(
                device_type=self._device_type,
                setpoint=setpoint,
                power_target=target_Q,
            )
        elif self._device_type == DeviceType.EV_CHARGER:
            try:
                charge_rate = self._device_model.power_to_command(
                    target_power_kw=target_Q,
                    state=device_state,
                )
            except (AttributeError, NotImplementedError):
                charge_rate = target_Q
            return DeviceCommand(
                device_type=self._device_type,
                power_target=charge_rate,
            )
        else:
            # Battery or unknown
            return DeviceCommand(
                device_type=self._device_type,
                power_target=target_Q,
            )

    def _actuate(self, command: DeviceCommand) -> bool:
        """Send the command to the physical device via GridLAB-D."""
        if self._device_type in (DeviceType.HVAC_AC_ONLY, DeviceType.HVAC_HEAT_PUMP):
            return self._gridlabd.write_hvac_command(command)
        elif self._device_type == DeviceType.WATER_HEATER:
            return self._gridlabd.write_water_heater_command(command)
        elif self._device_type == DeviceType.EV_CHARGER:
            return self._gridlabd.write_ev_charger_command(command)
        elif self._device_type == DeviceType.BATTERY:
            return self._gridlabd.write_battery_command(command)
        return False
