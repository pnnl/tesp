# ============================================================================
# FILE: economics/command_arbiter.py
# PURPOSE: Concrete implementation of the command arbiter that merges
#          simultaneous delivery obligations from multiple markets into
#          a single physical device command (agent functions F8, F9,
#          F12, F15, and F16 coordinated).
#
# The Command Arbiter is the SINGLE ACTUATION POINT for the device.
# Regardless of how many markets are simultaneously in the DELIVERY
# phase, the device receives exactly one control command per simulation
# timestep, produced by this arbiter.  No individual market handler,
# no phase handler, and no other agent function writes to the device
# directly.
#
# This constraint is both a correctness requirement (a thermostat has
# one setpoint, an inverter has one power target) and a simplification
# (no race conditions, no conflicting writes, no need to sequence
# actuations within a timestep).
#
# WHAT HAPPENS EVERY TIMESTEP DURING DELIVERY:
#
#     The arbiter's resolve_and_actuate() method is called once per
#     simulation timestep whenever at least one market is in DELIVERY.
#     It executes the following pipeline:
#
#     Step 1 — Compute delivery economics (F15):
#         For each active delivery, the DeliveryValueCalculator
#         computes a DeliveryEconomics structure containing:
#             revenue_fn(actual_qty) → revenue ($)
#             penalty_fn(actual_qty) → penalty ($)
#             net_value_fn(actual_qty) → net value ($)
#         These functions encode the heterogeneous economics of
#         energy, regulation, and reserve products in a common form.
#
#     Step 2 — Solve dispatch optimization (F16):
#         The DispatchOptimizer receives all delivery economics plus
#         the device's physical limits and the customer's amenity cost
#         function, and solves:
#
#             Maximize: Σ NV_m(Q_m) − C_amenity(Q) − C_degradation(Q)
#             Subject to: Q_min ≤ Q ≤ Q_max
#                         regulation band constraints
#                         reserve capacity constraints
#
#         The solution is a DispatchSolution containing:
#             Q         — optimal device operating point (kW)
#             allocation— per-market actual delivered quantity
#             displacement_chain — which market displaced which
#             total_net_value — objective function value
#
#         This optimization is what replaces the fixed priority table
#         (Reserve > Regulation > RT > DA) with economically-driven
#         dynamic priority.  The "priority" of a market product is
#         an emergent outcome of its current cleared price relative
#         to the non-delivery penalty of every other active product.
#
#     Step 3 — Translate to device command (F8):
#         The optimal Q from the dispatch solution is passed to the
#         device model's translate_power_to_command() method, which
#         converts it to a device-specific control action:
#             HVAC:    Q → thermostat setpoint (°F)
#             WH:      Q → tank thermostat setpoint (°F)
#             EV:      Q → charge rate (kW)
#             Battery: Q → inverter power setpoint (kW)
#
#     Step 4 — Actuate the device (F9):
#         The DeviceCommand is written to the simulator via
#         AbstractSimulatorInterface.write_device_command().
#         This is the ONLY place in the entire agent where a
#         simulator write occurs.
#
#     Step 5 — Build fulfillment records (F12 input):
#         For each active delivery, a FulfillmentRecord is created
#         comparing the committed quantity against the actual
#         allocated quantity.  These records are returned to the
#         agent orchestrator, which appends them to each market
#         object's performance log (F12).
#
# ACTIVE DELIVERY REGISTRY:
#     The arbiter maintains a dictionary of DeliveryRecord objects,
#     one per market currently in the DELIVERY phase.  Deliveries
#     are registered when a market transitions from DELIVERY_LEAD to
#     DELIVERY, and deregistered when the market transitions from
#     DELIVERY to RECONCILE.
#
#     At any moment, the registry might contain:
#         - One DA energy delivery (spanning 24 hours)
#         - One RT energy delivery (spanning 5 minutes)
#         - One regulation delivery (spanning seconds)
#         - One reserve delivery (capacity being held)
#
#     All are resolved into a single Q every timestep.
#
# REAL-TIME SIGNAL HANDLING:
#     For fast-response products (regulation, reserve), the arbiter
#     receives real-time signals via update_signals():
#
#         regulation_signal: float ∈ [−1.0, +1.0]
#             −1.0 = full regulation down (increase consumption)
#             +1.0 = full regulation up (decrease consumption)
#             Received from the MO or ISO every few seconds.
#
#         reserve_activated: float (0.0 or 1.0)
#             0.0 = reserve not called (hold capacity available)
#             1.0 = reserve activated (deploy immediately)
#
#     These signals feed into the dispatch optimizer's constraint set
#     and the delivery value calculator's revenue/penalty functions.
#     When a regulation signal changes, the optimizer re-solves and
#     the device command updates accordingly — all within the same
#     resolve_and_actuate() call.
#
# CLASSES IN THIS FILE:
#
#     DeliveryRecord
#         Data container for one active delivery tracked by the arbiter.
#         Stores the market_id, market_type, product_type, committed
#         quantity, cleared price, penalty model reference, delivery
#         interval, and a timestamped performance log.
#
#         Not an ABC — this is a simple concrete data structure local
#         to the arbiter.
#
#     CommandArbiter(AbstractCommandArbiter)
#         The concrete arbiter implementation.  Owns the delivery
#         registry, holds references to the simulator interface,
#         device model, dispatch optimizer, and delivery value
#         calculator.  Implements:
#
#             register_delivery()    — Add a market to the active registry.
#                                      Called by DeviceAgent._handle_delivery_start().
#
#             deregister_delivery()  — Remove a market from the registry.
#                                      Called by DeviceAgent._handle_reconcile()
#                                      (before reconciliation releases the
#                                      ledger commitment).
#
#             update_signals()       — Receive real-time regulation/reserve
#                                      signals.  Called every timestep by the
#                                      agent orchestrator (or more frequently
#                                      if the signal update rate exceeds the
#                                      simulation timestep).
#                                      EXTERNAL: Signals from MO or ISO.
#
#             resolve_and_actuate()  — The core method.  Steps 1–5 above.
#                                      Called every simulation timestep by
#                                      DeviceAgent._handle_delivery_tick().
#                                      Returns Dict[market_id → FulfillmentRecord].
#
# RELATIONSHIP TO ABSTRACTIONS:
#     CommandArbiter inherits from:
#         abstractions.command_arbiter.AbstractCommandArbiter
#
#     AbstractCommandArbiter's constructor receives:
#         AbstractSimulatorInterface  — for F9 (device actuation)
#         AbstractDeviceModel         — for F8 (control translation)
#         AbstractDispatchOptimizer   — for F16 (economic dispatch)
#         AbstractDeliveryValueCalculator — for F15 (delivery economics)
#
#     The arbiter interacts with these only through their abstract
#     interfaces.  It does not know whether the simulator is GridLAB-D
#     or a transmission tool, or whether the device is an HVAC or a
#     generator.
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - agent.py (DeviceAgent):
#         Owns the CommandArbiter instance.  Creates it during
#         initialize() with references to the device model, simulator,
#         and optimizer.
#
#         _handle_delivery_start(): calls register_delivery() when a
#             market enters DELIVERY.
#         _handle_delivery_tick(): calls resolve_and_actuate() every
#             simulation timestep, receives FulfillmentRecords, and
#             passes them to log_performance() (F12).
#         _handle_reconcile(): calls deregister_delivery() when a
#             market exits DELIVERY.
#
#     - economics/dispatch_optimizer.py:
#         The arbiter holds a reference to the DispatchOptimizer and
#         the DeliveryValueCalculator.  It calls:
#             DeliveryValueCalculator.compute() — once per active delivery
#             DispatchOptimizer.solve() — once per timestep
#
#     - economics/penalty_models.py:
#         Each DeliveryRecord holds a reference to its penalty model.
#         The penalty model is passed through to the delivery value
#         calculator, which calls compute_penalty() and marginal_penalty()
#         to build the penalty_fn in DeliveryEconomics.
#
#     - economics/preference_curves.py:
#         The arbiter receives the PreferenceCurve as an argument to
#         resolve_and_actuate() and passes it to the dispatch optimizer
#         for the amenity cost term.
#
#     - devices/*_model.py:
#         The arbiter holds a reference to the device model and calls
#         translate_power_to_command() (F8) to convert the optimizer's
#         optimal Q into a device-specific control command.
#
#     - simulators/gridlabd_interface.py:
#         The arbiter holds a reference to the simulator interface and
#         calls write_device_command() (F9) to actuate the device.
#         This is the ONLY call path to the simulator write method.
#
#     - economics/flexibility_ledger.py:
#         The arbiter does NOT interact with the ledger.  The ledger
#         tracks commitments (what was promised); the arbiter tracks
#         deliveries (what is being executed).  They operate on
#         overlapping but distinct data: the ledger is updated by
#         phase handlers (NEGOTIATION, ASSESSMENT, DELIVERY_LEAD,
#         RECONCILE), while the arbiter is updated by delivery
#         lifecycle events (DELIVERY start/end) and delivery ticks.
#
# DATA TYPES USED:
#     From data_types.py:
#         DeviceCommand       — the control command written to the simulator
#         DispatchSolution    — output of the dispatch optimizer
#         DeliveryEconomics   — per-delivery economic profile
#         FulfillmentRecord   — per-delivery per-timestep performance
#         PerformanceEntry    — timestamped log entry (stored on DeliveryRecord)
#     From enums_and_constants.py:
#         DeviceType          — determines which F8 translation to use
#         MarketType          — identifies the market product
#         ProductType         — ENERGY_BASE, REGULATION_UP/DOWN, RESERVE_UP/DOWN
#     From abstractions/:
#         AbstractCommandArbiter          — the contract being implemented
#         AbstractSimulatorInterface      — for F9
#         AbstractDeviceModel             — for F8
#         AbstractDispatchOptimizer       — for F16
#         AbstractDeliveryValueCalculator — for F15
#         AbstractPreferenceCurve         — passed through to F16
#         AbstractPenaltyModel            — stored on DeliveryRecord
#         AbstractDeviceState             — passed in per timestep
#
# EXTERNAL INPUTS:
#     regulation_signal:
#         Real-time regulation signal from the MO or ISO.
#         Float ∈ [−1.0, +1.0].  Updated via update_signals().
#         EXTERNAL: From MO signal feed, ISO AGC system, or
#         co-simulation message bus.
#
#     reserve_activated:
#         Reserve activation flag from the MO or ISO.
#         Float: 0.0 (not activated) or 1.0 (activated).
#         Updated via update_signals().
#         EXTERNAL: Same source as regulation signal.
# ============================================================================

"""Concrete command arbiter — single-actuation-point for the device.

The arbiter is the nexus where market economics meet physical reality.
It takes the abstract question "how should this device operate given
all its market obligations?" and produces a concrete answer: one
control command, written once, to one device, every timestep.

The economically-driven dispatch optimization within the arbiter is
what enables dynamic priority: instead of a fixed hierarchy
(reserve > regulation > RT > DA), the relative penalty costs and
revenue values of each active delivery determine which obligations
get fulfilled and which get curtailed when the device cannot satisfy
all of them simultaneously.

Classes:
    DeliveryRecord   — Per-delivery data container (market_id, committed
                       quantity, cleared price, penalty model, performance log).
    CommandArbiter   — The arbiter itself.  Owns the delivery registry,
                       coordinates F15→F16→F8→F9 pipeline, returns
                       per-market FulfillmentRecords.
"""

from typing import Any, Dict, List, Optional, Tuple

from abstractions.command_arbiter import AbstractCommandArbiter
from abstractions.device_model import AbstractDeviceModel
from abstractions.device_state import AbstractDeviceState
from abstractions.dispatch_optimizer import (
    AbstractDeliveryValueCalculator,
    AbstractDispatchOptimizer,
)
from abstractions.penalty_model import AbstractPenaltyModel
from abstractions.preference_curve import AbstractPreferenceCurve
from abstractions.simulator_interface import AbstractSimulatorInterface
from data_types import (
    DeliveryEconomics,
    DeviceCommand,
    DispatchSolution,
    FulfillmentRecord,
    PerformanceEntry,
)
from enums_and_constants import DeviceType, MarketType, ProductType

from ..data_types import (
    DeliveryEconomics,
    DeviceCommand,
    FulfillmentRecord,
    PerformanceEntry,
)
from tesp_support.tesp_support.curve_and_agent.abstractions.command_arbiter import AbstractCommandArbiter
from .dispatch_optimizer import DeliveryValueCalculator, DispatchOptimizer
from ..enums_and_constants import DeviceType
from ..simulators.gridlabd_interface import GridLABDInterface
from .penalty_model import PenaltyModel
from .preference_curves import PreferenceCurve


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
        interval: tuple[float, float],
    ):
        self.market_id = market_id
        self.market_type = market_type
        self.product_type = product_type
        self.committed_qty = committed_qty
        self.cleared_price = cleared_price
        self.penalty_model = penalty_model
        self.interval = interval
        self.performance_log: list[PerformanceEntry] = []


class CommandArbiter(AbstractCommandArbiter):
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
        self._active_deliveries: dict[str, DeliveryRecord] = {}
        self._signals: dict[str, float] = {}

    def register_delivery(
        self,
        market_id: str,
        market_type: str,
        product_type: str,
        committed_qty: float,
        cleared_price: float,
        penalty_model: PenaltyModel,
        interval: tuple[float, float],
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

    def update_signals(self, signals: dict[str, float]) -> None:
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
    ) -> dict[str, FulfillmentRecord]:
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
        economics: dict[str, DeliveryEconomics] = {}
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
        except (AttributeError, NotImplementedError, TypeError):
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
        fulfillments: dict[str, FulfillmentRecord] = {}
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
