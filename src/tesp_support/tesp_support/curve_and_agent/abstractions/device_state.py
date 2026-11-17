# ============================================================================
# FILE: abstractions/device_state.py
# PURPOSE: Abstract base class for device state representations.
#
# A device state is a snapshot of all physical variables that the agent
# needs to observe from the simulator at a single point in time.  Every
# device type (HVAC, water heater, EV charger, battery, generator, …)
# defines its own concrete state dataclass that inherits from this ABC.
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Produced by: AbstractSimulatorInterface.read_device_state()
#     - Consumed by: AbstractDeviceModel.estimate_flexibility()
#                    AbstractDeviceModel.translate_power_to_command()
#                    AbstractCommandArbiter.resolve_and_actuate()
#                    AbstractDeviceAgent.observe_device_state()
#
# IMPORTS FROM:
#     - enums_and_constants: DeviceType
#     No imports from other abstractions modules (leaf dependency).
# ============================================================================

"""Abstract device state — the common interface every device state must satisfy.

Concrete implementations are typically ``@dataclass`` containers with
device-specific fields (temperatures for HVAC, SOC for batteries, etc.).
This ABC requires only that every state can report its instantaneous
electrical power and its device type, since those are needed by every
downstream function regardless of the physical device.
"""

from abc import ABC, abstractmethod

from enums_and_constants import DeviceType



class AbstractDeviceState(ABC):
    """Abstract base for all device state representations.

    A device state is a snapshot of all physical variables that the agent
    needs to observe from the simulator at a single point in time.  Each
    device type defines its own concrete state class (HVACState,
    WaterHeaterState, EVChargerState, BatteryState, and future types
    such as GeneratorState).

    Concrete implementations are plain data containers (typically
    ``@dataclass``).  This ABC requires only that every state can
    report the instantaneous electrical power being consumed or
    produced, since that quantity is needed by every downstream
    function regardless of device type.
    """

    @property
    @abstractmethod
    def power_draw(self) -> float:
        """Current electrical power (kW).

        Sign convention:
            Positive = consuming from grid (load).
            Negative = exporting to grid (generation / battery discharge).

        Returns:
            Instantaneous electrical power in kW.
        """
        ...

    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """The type of device this state represents.

        Returns:
            A ``DeviceType`` enum member.
        """
        ...