# ============================================================================
# FILE: abstractions/device_model.py
# PURPOSE: Abstract base class for the agent's internal physics model of
#          a device.
#
# The device model represents the agent's BELIEF about how the device
# responds to control actions and exogenous conditions.  It need not be
# high fidelity — the ground truth lives in the simulator.
#
# Every device model supports two core operations:
#     F2 — Flexibility estimation: given state + forecasts, compute
#           the feasible power range and baseline operating point.
#     F8 — Control translation: given a target power from the dispatch
#           optimizer, compute the device-specific control command.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Uses: AbstractDeviceState (input to both methods)
#     - Used by: AbstractCommandArbiter (calls translate_power_to_command)
#                AbstractPlanningOptimizer (uses for trajectory prediction)
#                AbstractDeviceAgent (calls estimate_flexibility)
#
# IMPORTS FROM:
#     - typing: Any, Dict, List
#     - abstractions.device_state: AbstractDeviceState
#     - data_types: DeviceCommand, FlexibilityEnvelope
#     - enums_and_constants: DeviceType
# ============================================================================

"""Abstract device model — the agent's internal physics engine.

Concrete subclasses implement device-specific physics:
    HVACModel         — 2-node equivalent thermal parameter model
    WaterHeaterModel  — Stratified tank thermal model
    EVChargerModel    — SOC dynamics with BMS taper
    BatteryModel      — Bidirectional SOC + degradation tracking
    (future) GeneratorModel — Heat rate curves + ramp dynamics
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from abstractions.device_state import AbstractDeviceState
from data_types import DeviceCommand, FlexibilityEnvelope
from enums_and_constants import DeviceType

class AbstractDeviceModel(ABC):
    """Abstract base for the agent's internal physics model of a device.

    The device model is the agent's *belief* about how the device
    responds to control actions and exogenous conditions.  It need not
    be high fidelity — the ground truth lives in the simulator.

    Every device model must support two core operations:

    1. **Flexibility estimation (F2):** Given the current state and
       forecasts, compute the feasible power range and the baseline
       (amenity-tracking) operating point for an upcoming market
       interval.

    2. **Control translation (F8):** Given a target power from the
       dispatch optimizer, compute the device-specific control command
       (setpoint, charge rate, etc.) that achieves approximately that
       power.

    Concrete subclasses add device-specific prediction methods (e.g.,
    ``predict_temperature`` for HVAC, ``predict_soc`` for EV/battery).
    """

    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """The device type this model represents.

        Returns:
            A ``DeviceType`` enum member.
        """
        ...

# -- F2: Flexibility Estimation ------------------------------------------

    @abstractmethod
    def estimate_flexibility(
        self,
        state: AbstractDeviceState,
        forecasts: Dict[str, Any],
        constraints: List[Any],
        interval_duration: float,
    ) -> FlexibilityEnvelope:
        """Estimate the feasible operating range for an upcoming interval.

        Args:
            state: Current device state from the simulator (F1 output).
                INTERNAL: From ``AbstractSimulatorInterface.read_device_state()``.
            forecasts: Relevant forecast data keyed by stream ID.
                INTERNAL: From ``AbstractDataStreamManager.get_forecast_bundle()``.
                Content varies by device type (weather for HVAC, draws
                for water heater, prices for battery, etc.).
            constraints: Active constraints for this interval.
                INTERNAL: From ``AbstractDataStreamManager.get_all_constraints()``.
                EXTERNAL origin: Customer input, building codes, BMS limits.
            interval_duration: Length of the market interval in seconds.

        Returns:
            ``FlexibilityEnvelope`` with Q_min, Q_max, Q_baseline, and
            confidence-level variants (p50, p90, p99).
        """
        ...

    # -- F8: Control Translation ---------------------------------------------

    @abstractmethod
    def translate_power_to_command(
        self,
        target_power: float,
        state: AbstractDeviceState,
        interval_duration: float,
    ) -> DeviceCommand:
        """Convert a target power level to a device-specific control command.

        This is the inverse of the flexibility model: given that we want
        the device to consume (or produce) ``target_power`` kW over the
        interval, what control command achieves that?

        Args:
            target_power: Desired electrical power (kW).
                Positive = consume, negative = produce (batteries/generators).
                INTERNAL: From dispatch optimizer (F16) or price response (F7).
            state: Current device state.
                INTERNAL: From F1.
            interval_duration: Market interval length (seconds).

        Returns:
            ``DeviceCommand`` ready to be sent to the simulator via
            ``AbstractSimulatorInterface.write_device_command()``.
        """
        ...