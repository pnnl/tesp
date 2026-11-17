# ============================================================================
# FILE: abstractions/simulator_interface.py
# PURPOSE: Abstract base class for the boundary between the agent and the
#          physics simulator that represents "reality."
#
# In the reference implementation the simulator is GridLAB-D, but this
# ABC allows substitution of any simulator backend:
#     - GridLAB-D (distribution-level, via FNCS/HELICS)
#     - Transmission-level tools (for bulk generators)
#     - Hardware-in-the-loop testbeds
#     - Lightweight analytical models (for unit testing)
#
# Only two operations cross this boundary:
#     read  — observe current device state (agent function F1)
#     write — actuate a control command    (agent function F9)
#
# RELATIONSHIP TO OTHER ABSTRACTIONS:
#     - Uses: AbstractDeviceState (return type of read_device_state)
#     - Used by: AbstractCommandArbiter (calls write_device_command for F9)
#                AbstractDeviceAgent (calls read_device_state for F1)
#
# IMPORTS FROM:
#     - typing: Any
#     - abstractions.device_state: AbstractDeviceState
#     - data_types: DeviceCommand
#     - enums_and_constants: DeviceType
# ============================================================================

"""Abstract simulator interface — the only module that touches the physics simulator.

No other module in the agent should read from or write to the simulator
directly.  All device state observation (F1) and control actuation (F9)
flow through this interface.
"""

from abc import ABC, abstractmethod
from typing import Any

from abstractions.device_state import AbstractDeviceState
from data_types import DeviceCommand
from enums_and_constants import DeviceType

class AbstractSimulatorInterface(ABC):
    """Abstract base for the boundary between the agent and the physics
    simulator that represents "reality."

    In the reference implementation the simulator is GridLAB-D, but
    this ABC allows substitution of any simulator (e.g., a
    transmission-level tool for bulk generators, a hardware-in-the-loop
    testbed, or a lightweight analytical model for unit testing).

    **Only two operations cross this boundary:**
        * **read** — observe the current device state (F1).
        * **write** — actuate a control command on the device (F9).

    No other module in the agent should read from or write to the
    simulator directly.

    Args:
        connection: Opaque handle to the simulator.
            EXTERNAL: Provided by the simulation harness.
        object_name: Identifier of the simulated object.
            EXTERNAL: Must match the simulator model.
        device_type: The kind of device being managed.
    """

    def __init__(
        self,
        connection: Any,
        object_name: str,
        device_type: DeviceType,
    ):
        self._connection = connection
        self._object_name = object_name
        self._device_type = device_type

    # -- F1: State Observation -----------------------------------------------

    @abstractmethod
    def read_device_state(self) -> AbstractDeviceState:
        """Read the current physical state of the device from the simulator.

        This is the **only** read path into the simulator.  All downstream
        agent functions receive device state through the return value of
        this method.

        Returns:
            A concrete ``AbstractDeviceState`` subclass populated from
            the simulator's current object properties.
        """
        ...
        
    # -- F9: Control Actuation -----------------------------------------------

    @abstractmethod
    def write_device_command(self, command: DeviceCommand) -> bool:
        """Write a control command to the device in the simulator.

        This is the **only** write path into the simulator.  Only the
        ``CommandArbiter`` should call this method; no individual market
        handler actuates directly.

        Args:
            command: The device-specific control command.
                INTERNAL: Produced by the Command Arbiter after dispatch
                optimization.

        Returns:
            ``True`` if the write was acknowledged by the simulator.
        """
        ...

    # -- Time ----------------------------------------------------------------

    @abstractmethod
    def read_simulation_time(self) -> float:
        """Read the current simulation clock.

        Returns:
            Current simulation time in seconds since the simulation epoch.
        """
        ...

class GridLABDInterface(AbstractSimulatorInterface):
    """Concrete GridLAB-D simulator interface.

    Implements AbstractSimulatorInterface for the GridLAB-D distribution
    system simulator via FNCS, HELICS, or direct Python API.
    """

    def read_device_state(self) -> AbstractDeviceState:
        """Read from GridLAB-D object properties.

        Dispatches internally to device-type-specific read logic.

        GridLAB-D Properties Read (varies by device_type):
            HVAC: air_temperature, outdoor_temperature, cooling_setpoint,
                  heating_setpoint, system_mode, hvac_power, mass_temperature,
                  Ua, Hm, Ca, Cm, cooling_COP, heating_COP,
                  design_cooling_capacity, design_heating_capacity,
                  solar_heatgain, internal_heatgain
            WH:   temperature, Tset, is_waterheater_on, waterheater_power,
                  tank_volume, tank_UA, heating_element_capacity,
                  inlet_water_temperature, water_demand
            EV:   battery_SOC, charge_rate, battery_capacity,
                  max_charge_rate, charger_efficiency, vehicle_connected
            Batt: state_of_charge, battery_capacity, rated_power,
                  round_trip_efficiency, (inverter) power_out
        """
        raise NotImplementedError

    def write_device_command(self, command: DeviceCommand) -> bool:
        """Write to GridLAB-D object properties.

        GridLAB-D Properties Written (varies by device_type):
            HVAC: cooling_setpoint, heating_setpoint
            WH:   Tset (or re_override ON/OFF)
            EV:   charge_rate (or charger_state ON/OFF)
            Batt: (inverter) power_out
        """
        raise NotImplementedError

    def read_simulation_time(self) -> float:
        raise NotImplementedError
