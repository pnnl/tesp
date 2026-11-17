# ============================================================================
# FILE: devices/__init__.py
# PURPOSE: Package-level exports for all concrete device models and states.
#
# This package contains the device-specific implementations that provide
# the agent's internal belief about device physics.  Every class here
# inherits from an abstract base defined in the abstractions/ package
# and depends only on:
#     - abstractions/ (the contracts it implements)
#     - data_types.py (shared dataclasses)
#     - enums_and_constants.py (shared enumerations)
#
# No module in this package imports from other concrete packages
# (simulators/, markets/, economics/, forecasting/).  Device models
# are consumed by the agent orchestrator (agent.py) and the economics
# package (planning_optimizer.py, command_arbiter.py) through the
# abstract interface, not through direct import of these concrete
# classes — except at the composition root (main.py) where concrete
# types must be selected and wired together.
#
# PACKAGE CONTENTS:
#
#     states.py
#         Concrete device state dataclasses that pair the field-rich
#         data_types.py dataclasses (HVACState, WaterHeaterState, etc.)
#         with the AbstractDeviceState contract (device_type property,
#         power_draw property).
#
#         Classes:
#             ConcreteHVACState
#             ConcreteWaterHeaterState
#             ConcreteEVChargerState
#             ConcreteBatteryState
#
#     hvac_model.py
#         2-node Equivalent Thermal Parameter (ETP) model for buildings
#         with HVAC systems.  Supports both heat-pump and AC-only
#         configurations.  Consumes weather forecasts (outdoor temp,
#         solar irradiance, humidity) and the customer's thermostat
#         setpoint schedule.
#
#         Classes:
#             HVACModel(AbstractDeviceModel)
#
#     water_heater_model.py
#         Stratified tank thermal model for electric resistance water
#         heaters.  Unique in that its primary uncertainty source is an
#         event-process forecast (hot water draws) rather than a
#         continuous forecast (weather).  Consumes draw event forecasts
#         and enforces a hard minimum tank temperature constraint.
#
#         Classes:
#             WaterHeaterModel(AbstractDeviceModel)
#
#     ev_charger_model.py
#         SOC dynamics model with BMS-imposed charge rate taper at high
#         SOC and EVSE minimum charge rate step.  Flexibility is
#         dominated by the departure deadline constraint: as departure
#         approaches, the charger becomes increasingly must-run.
#         Consumes arrival forecasts, departure constraints, and
#         preferred SOC schedules.
#
#         Classes:
#             EVChargerModel(AbstractDeviceModel)
#
#     battery_model.py
#         Bidirectional SOC dynamics model with three-tier degradation
#         tracking (throughput, stress-factor, Wöhler cycle-depth).
#         The only device type with meaningful operational cost from
#         cycling.  Produces marginal degradation costs that drive the
#         dead band in the bidirectional preference curve.  Requires
#         the planning optimizer to produce V_stored — the marginal
#         value of stored energy — which is essential for all charge/
#         discharge decisions.
#
#         Classes:
#             BatteryModel(AbstractDeviceModel)
#
# USAGE:
#     Precise import (preferred inside framework):
#         from devices.hvac_model import HVACModel
#         from devices.states import ConcreteHVACState
#
#     Convenience import (acceptable in main.py):
#         from devices import HVACModel, ConcreteHVACState
# ============================================================================

"""Devices package — concrete device models and state representations.

Each device model implements the ``AbstractDeviceModel`` contract,
providing two core operations:

    estimate_flexibility() — F2
        Given current state and forecasts, compute the feasible power
        range (Q_min, Q_max) and baseline operating point (Q_baseline)
        for an upcoming market interval.

    translate_power_to_command() — F8
        Given a target power from the dispatch optimizer, compute the
        device-specific control command (thermostat setpoint, charge
        rate, inverter power) that achieves approximately that power.

Device-specific methods (predict_temperature, predict_soc,
marginal_degradation_cost, etc.) extend beyond the abstract contract
and are used by the planning optimizer and device-specific agent logic.
"""

# -- Device States -----------------------------------------------------------
from devices.states import (
    ConcreteBatteryState,
    ConcreteEVChargerState,
    ConcreteHVACState,
    ConcreteWaterHeaterState,
)

# -- Device Models -----------------------------------------------------------
from devices.battery_model import BatteryModel
from devices.ev_charger_model import EVChargerModel
from devices.hvac_model import HVACModel
from devices.water_heater_model import WaterHeaterModel

__all__ = [
    # States
    "ConcreteHVACState",
    "ConcreteWaterHeaterState",
    "ConcreteEVChargerState",
    "ConcreteBatteryState",
    # Models
    "HVACModel",
    "WaterHeaterModel",
    "EVChargerModel",
    "BatteryModel",
]