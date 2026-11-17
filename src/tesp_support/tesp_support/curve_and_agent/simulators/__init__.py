# ============================================================================
# FILE: simulators/__init__.py
# PURPOSE: Package-level exports for concrete simulator interface
#          implementations.
#
# This package contains the implementations that bridge the agent to
# specific physics simulators.  Every class here inherits from
# AbstractSimulatorInterface (defined in abstractions/simulator_interface.py)
# and is the ONLY code in the system that directly communicates with
# an external simulator process or API.
#
# The agent's two simulator-touching functions — F1 (state observation)
# and F9 (control actuation) — are routed exclusively through these
# interfaces.  All other agent modules interact with devices through
# the AbstractDeviceState and DeviceCommand data structures, never
# through simulator-specific calls.
#
# DEPENDENCY RULE:
#     Modules in this package import from:
#       - abstractions/ (the contracts they implement)
#       - data_types.py (shared dataclasses: DeviceCommand, device states)
#       - enums_and_constants.py (DeviceType)
#       - devices/states.py (concrete state classes they construct and return)
#       - The simulator's own client library (FNCS, HELICS, GridLAB-D
#         Python bindings, etc.) — this is the one EXTERNAL dependency.
#
#     No module in this package imports from economics/, markets/,
#     forecasting/, or agent.py.  Simulator interfaces are leaf
#     dependencies consumed (not consuming) by the rest of the framework.
#
# PACKAGE CONTENTS:
#
#     gridlabd_interface.py
#         Concrete interface for the GridLAB-D distribution system
#         simulator.  Supports communication via FNCS, HELICS, or the
#         direct GridLAB-D Python API.
#
#         Reads GridLAB-D object properties to construct concrete device
#         states (ConcreteHVACState, ConcreteWaterHeaterState, etc.) and
#         writes DeviceCommand fields back to GridLAB-D object properties
#         (thermostat setpoints, charge rates, inverter power).
#
#         Handles simulator-specific details such as:
#           - Property name mapping (GridLAB-D property names ↔ state fields)
#           - Sign convention conversion (GridLAB-D inverter positive =
#             export vs. agent positive = import for batteries)
#           - Unit conversion if necessary
#           - Connection lifecycle (connect, subscribe, publish, advance)
#
#         Classes:
#             GridLABDInterface(AbstractSimulatorInterface)
#
# EXTENDING TO NEW SIMULATORS:
#     To add a new simulator backend (e.g., a transmission-level tool
#     for bulk generators, or a hardware-in-the-loop testbed):
#
#     1. Create a new file in this package:
#            simulators/transmission_interface.py
#        or  simulators/hil_interface.py
#
#     2. Define a class that inherits from AbstractSimulatorInterface
#        and implements:
#            read_device_state()  → returns a concrete AbstractDeviceState
#            write_device_command() → writes a DeviceCommand to the simulator
#            read_simulation_time() → returns current sim clock
#
#     3. Register the new class in this __init__.py.
#
#     4. In main.py (or the simulation harness), instantiate the new
#        interface and pass it to a DeviceAgent.  No other code changes.
#
#     Example for a future transmission simulator:
#
#         # simulators/transmission_interface.py
#         from abstractions.simulator_interface import AbstractSimulatorInterface
#
#         class TransmissionSimInterface(AbstractSimulatorInterface):
#             def read_device_state(self) -> GeneratorState:
#                 ...  # read MW, MVAR, fuel level, ramp position, etc.
#             def write_device_command(self, command) -> bool:
#                 ...  # write dispatch setpoint, commitment status, etc.
#             def read_simulation_time(self) -> float:
#                 ...
#
#     Example for a hardware-in-the-loop testbed:
#
#         # simulators/hil_interface.py
#         from abstractions.simulator_interface import AbstractSimulatorInterface
#
#         class HILInterface(AbstractSimulatorInterface):
#             def read_device_state(self) -> AbstractDeviceState:
#                 ...  # read from physical sensors via Modbus/BACnet/API
#             def write_device_command(self, command) -> bool:
#                 ...  # write to physical actuators
#             def read_simulation_time(self) -> float:
#                 ...  # wall clock or test harness clock
#
# USAGE:
#     Precise import (preferred inside framework):
#         from simulators.gridlabd_interface import GridLABDInterface
#
#     Convenience import (acceptable in main.py):
#         from simulators import GridLABDInterface
# ============================================================================

"""Simulators package — concrete physics simulator interfaces.

Each simulator interface is the **only** code that touches a specific
external simulator.  The interface translates between the simulator's
native property model and the agent's generic data structures
(``AbstractDeviceState`` for reads, ``DeviceCommand`` for writes).

The current implementation supports GridLAB-D for distribution-level
simulation.  The package is designed for extension to transmission-level
tools, hardware-in-the-loop testbeds, or lightweight analytical models
for unit testing, all without modifying any other part of the framework.
"""

from simulators.gridlabd_interface import GridLABDInterface

__all__ = [
    "GridLABDInterface",
]