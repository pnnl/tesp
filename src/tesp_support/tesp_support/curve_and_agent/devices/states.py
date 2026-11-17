# ============================================================================
# FILE: devices/states.py
# PURPOSE: Concrete device state classes that satisfy the AbstractDeviceState
#          contract for each supported device type.
#
# Each class uses multiple inheritance to combine:
#     1. A field-rich dataclass from data_types.py (HVACState, BatteryState,
#        etc.) that defines all the physical variables read from GridLAB-D.
#     2. The AbstractDeviceState ABC from abstractions/device_state.py that
#        requires every state to expose a device_type property and a
#        power_draw property.
#
# This design keeps the data container definitions in data_types.py (where
# they are shared across the codebase as simple structures) while adding
# the behavioral contract required by the agent's generic functions here.
#
# WHY MULTIPLE INHERITANCE:
#     The dataclass provides the FIELDS (indoor_air_temp, soc, etc.).
#     The ABC provides the CONTRACT (device_type, power_draw).
#     The concrete state class provides the GLUE — the property
#     implementations that map device-specific fields to the generic
#     interface.  For example, BatteryState has a field called 'power'
#     (which can be positive or negative), and ConcreteBatteryState
#     maps that to the power_draw property expected by the ABC.
#
# RELATIONSHIP TO ABSTRACTIONS:
#     Inherits from: abstractions.device_state.AbstractDeviceState
#
# RELATIONSHIP TO DATA TYPES:
#     Inherits from: data_types.HVACState
#                    data_types.WaterHeaterState
#                    data_types.EVChargerState
#                    data_types.BatteryState
#
# RELATIONSHIP TO OTHER CONCRETE MODULES:
#     - simulators/gridlabd_interface.py: The GridLABDInterface.read_device_state()
#       method constructs and returns one of these concrete state objects
#       populated from GridLAB-D property reads.
#     - devices/hvac_model.py: HVACModel methods receive AbstractDeviceState
#       and downcast to access HVAC-specific fields.
#     - devices/water_heater_model.py: Same pattern for water heater fields.
#     - devices/ev_charger_model.py: Same pattern for EV fields.
#     - devices/battery_model.py: Same pattern for battery fields.
#     - agent.py: DeviceAgent.observe_device_state() returns one of these.
#
# USAGE:
#     # Created by the simulator interface after reading GridLAB-D:
#     state = ConcreteHVACState(
#         indoor_air_temp=73.5,
#         outdoor_air_temp=92.0,
#         thermostat_setpoint=72.0,
#         hvac_mode="cooling",
#         power_draw=3.2,
#         hvac_on=True,
#         thermal_mass_temp=73.0,
#         # ... remaining fields from GridLAB-D ...
#     )
#
#     # Consumed generically by agent functions:
#     print(state.device_type)   # DeviceType.HVAC_AC_ONLY
#     print(state.power_draw)    # 3.2
#
#     # Consumed specifically by the HVAC model:
#     print(state.indoor_air_temp)  # 73.5  (HVAC-specific field)
#     print(state.cooling_COP)      # 3.5   (HVAC-specific field)
# ============================================================================

"""Concrete device states — bridge between data containers and the ABC contract.

Each class is both a fully-populated dataclass (with all device-specific
physical variables) and a valid ``AbstractDeviceState`` (with the generic
``device_type`` and ``power_draw`` properties that every agent function
can rely on).
"""

from abstractions.device_state import AbstractDeviceState
from data_types import (
    BatteryState,
    EVChargerState,
    HVACState,
    WaterHeaterState,
)
from enums_and_constants import DeviceType


class ConcreteHVACState(HVACState, AbstractDeviceState):
    """Concrete HVAC state satisfying the AbstractDeviceState contract.

    Inherits all fields from ``data_types.HVACState`` (indoor_air_temp,
    outdoor_air_temp, thermostat_setpoint, hvac_mode, power_draw,
    hvac_on, thermal_mass_temp, air_mass, thermal_mass, UA_envelope,
    UA_mass, cooling_COP, heating_COP, rated_cooling_capacity,
    rated_heating_capacity, has_heat_pump, solar_gain, internal_gain).

    The ``device_type`` property returns HVAC_HEAT_PUMP or HVAC_AC_ONLY
    based on the ``has_heat_pump`` field, which is read from the
    GridLAB-D house object configuration.

    The ``power_draw`` property delegates to the ``power_draw`` field
    already defined on the HVACState dataclass.  This value is always
    non-negative (HVAC systems only consume power).

    GridLAB-D source properties:
        power_draw       ← house.hvac_power or meter.measured_real_power
        indoor_air_temp  ← house.air_temperature
        outdoor_air_temp ← climate.temperature (or house.outdoor_temperature)
        hvac_on          ← derived from house.system_mode != OFF
        has_heat_pump    ← house configuration (static after init)
    """

    @property
    def power_draw(self) -> float:
        """Current HVAC electrical power consumption (kW).

        Always non-negative.  Zero when the HVAC unit is off.
        Includes compressor, fan, and auxiliary heat (if active).
        """
        # HVACState dataclass has a power_draw field; access it directly.
        # We use object.__getattribute__ to avoid infinite recursion with
        # the property, since the dataclass field and the ABC property
        # share the same name.
        return HVACState.power_draw.fget(self) if callable(getattr(HVACState, 'power_draw', None)) else self.__dict__.get('power_draw', 0.0)

    @property
    def device_type(self) -> DeviceType:
        """HVAC_HEAT_PUMP if the system has a heat pump, else HVAC_AC_ONLY.

        This distinction affects the heating-mode COP used by the
        HVAC device model: heat pumps use heating_COP (typically 2.5–4.0),
        while AC-only systems use resistive backup (effective COP = 1.0).
        """
        if self.has_heat_pump:
            return DeviceType.HVAC_HEAT_PUMP
        return DeviceType.HVAC_AC_ONLY


class ConcreteWaterHeaterState(WaterHeaterState, AbstractDeviceState):
    """Concrete water heater state satisfying the AbstractDeviceState contract.

    Inherits all fields from ``data_types.WaterHeaterState``
    (tank_temp_upper, tank_temp_lower, thermostat_setpoint, element_on,
    power_draw, tank_volume, tank_UA, element_power, inlet_water_temp,
    current_draw_rate, tank_height).

    The ``power_draw`` property delegates to the ``power_draw`` field.
    Water heater power is binary: either 0 (element off) or
    ``element_power`` (element on, typically 4.5 kW).

    GridLAB-D source properties:
        power_draw       ← waterheater.actual_power or meter reading
        tank_temp_upper  ← waterheater.temperature (upper thermostat)
        tank_temp_lower  ← waterheater.temperature (lower, if modeled)
        element_on       ← waterheater.is_waterheater_on
        current_draw_rate← waterheater.water_demand
        inlet_water_temp ← waterheater.inlet_water_temperature
    """

    @property
    def power_draw(self) -> float:
        """Current heating element electrical power (kW).

        Either 0.0 (element off) or element_power (element on).
        Water heaters are binary-switched loads — there is no
        intermediate power level.
        """
        return self.__dict__.get('power_draw', 0.0)

    @property
    def device_type(self) -> DeviceType:
        """Always WATER_HEATER."""
        return DeviceType.WATER_HEATER


class ConcreteEVChargerState(EVChargerState, AbstractDeviceState):
    """Concrete EV charger state satisfying the AbstractDeviceState contract.

    Inherits all fields from ``data_types.EVChargerState`` (soc,
    charge_rate, battery_capacity, max_charge_rate, charger_efficiency,
    vehicle_plugged_in, min_charge_rate, soc_at_max_taper).

    The ``power_draw`` property maps to ``charge_rate``.  EV chargers
    are unidirectional loads (no V2G in this model), so power_draw
    is always non-negative.  When no vehicle is plugged in,
    charge_rate is 0.

    GridLAB-D source properties:
        charge_rate       ← evcharger.charge_rate (or custom object)
        soc               ← evcharger.battery_SOC
        vehicle_plugged_in← evcharger.vehicle_connected
        battery_capacity  ← evcharger.battery_capacity (static per vehicle)
        max_charge_rate   ← evcharger.max_charge_rate (EVSE rating)
    """

    @property
    def power_draw(self) -> float:
        """Current AC charging power at the EVSE (kW).

        Always non-negative.  Zero when no vehicle is plugged in or
        charging is paused.  The DC power delivered to the battery is
        charge_rate × charger_efficiency.
        """
        return self.charge_rate

    @property
    def device_type(self) -> DeviceType:
        """Always EV_CHARGER."""
        return DeviceType.EV_CHARGER


class ConcreteBatteryState(BatteryState, AbstractDeviceState):
    """Concrete battery state satisfying the AbstractDeviceState contract.

    Inherits all fields from ``data_types.BatteryState`` (soc, power,
    energy_capacity, max_charge_rate, max_discharge_rate,
    round_trip_efficiency, cell_temperature, soc_min_bms, soc_max_bms,
    inverter_rated_power, state_of_health).

    The ``power_draw`` property maps to the ``power`` field.  Unlike
    all other device types, this value can be NEGATIVE (discharging /
    exporting to grid).  The sign convention is:
        Positive = charging (consuming from grid) = load behavior
        Negative = discharging (exporting to grid) = generation behavior

    GridLAB-D source properties:
        power            ← inverter.power_out (sign-flipped: GLD positive
                           = export, agent positive = import)
        soc              ← battery.state_of_charge
        energy_capacity  ← battery.battery_capacity
        cell_temperature ← battery.temperature (if modeled) or ambient
        state_of_health  ← battery.state_of_health (if modeled, else 1.0)
        max_charge_rate  ← min(battery.rated_power, inverter.rated_power)
        max_discharge_rate← same
    """

    @property
    def power_draw(self) -> float:
        """Current power flow at the AC meter point (kW).

        Positive = charging (consuming from grid).
        Negative = discharging (exporting to grid).

        This is the only device state where power_draw can be negative.
        The bidirectional nature of batteries is what necessitates the
        extended bid curve and the degradation cost model.
        """
        return self.power

    @property
    def device_type(self) -> DeviceType:
        """Always BATTERY."""
        return DeviceType.BATTERY