# ============================================================================
# FILE: gridlabd_interface.py
# PURPOSE: Abstraction layer for all GridLAB-D reads and writes.
#          This is the ONLY module that directly interacts with GridLAB-D.
#          All other modules interact with devices through this interface.
#
# EXTERNAL DEPENDENCY:
#     Requires a GridLAB-D co-simulation connection. This could be:
#     - FNCS (Framework for Network Co-Simulation)
#     - HELICS (Hierarchical Engine for Large-scale Infrastructure Co-Sim)
#     - Direct GridLAB-D Python API
#     The specific connection mechanism is injected at construction time.
#
# CONNECTION PROTOCOL:
#     The connection object must implement two methods:
#       get_value(key: str) -> str   — read a property by TESP topic key
#       set_value(key: str, val)     — write a property by TESP topic key
#     Keys use the TESP "#" convention: "object_name#property_name"
#     This abstraction works with HELICS, FNCS, or direct-API adapters.
# ============================================================================

from typing import Any, Optional
from data_types import (
    HVACState,
    WaterHeaterState,
    EVChargerState,
    BatteryState,
    DeviceCommand,
)
from enums_and_constants import DeviceType


class GridLABDInterface:
    """Abstraction layer for reading device state from and writing control
    commands to GridLAB-D simulation objects.

    This class encapsulates ALL GridLAB-D interaction. No other module
    in the agent should read from or write to GridLAB-D directly.

    The interface pattern is:
        read:  GridLAB-D object properties -> Python state dataclass
        write: Python DeviceCommand -> GridLAB-D object properties

    Args:
        connection: The GridLAB-D co-simulation connection object.
            Must expose ``get_value(key) -> str`` and
            ``set_value(key, value) -> None``.
            EXTERNAL: Must be provided by the simulation harness.
        object_name: The name of the GridLAB-D object this interface
            manages (e.g., "house_1", "waterheater_1").
            EXTERNAL: Must match the GridLAB-D model.
        device_type: The type of device, determines which properties
            are read/written.
    """

    def __init__(self, connection: Any, object_name: str, device_type: DeviceType):
        self._connection = connection
        self._object_name = object_name
        self._device_type = device_type

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _key(self, prop: str) -> str:
        """Build a TESP topic key: ``object_name#property``."""
        return f"{self._object_name}#{prop}"

    def _get_float(self, prop: str, default: float = 0.0) -> float:
        """Read a property from the connection and convert to float."""
        raw = self._connection.get_value(self._key(prop))
        if raw is None or raw == "":
            return default
        return float(raw)

    def _get_str(self, prop: str, default: str = "") -> str:
        """Read a property from the connection as a string."""
        raw = self._connection.get_value(self._key(prop))
        if raw is None:
            return default
        return str(raw).strip()

    def _get_bool(self, prop: str, default: bool = False) -> bool:
        """Read a property and interpret it as boolean."""
        raw = self._get_str(prop).upper()
        if raw in ("TRUE", "1", "ON", "YES"):
            return True
        if raw in ("FALSE", "0", "OFF", "NO", ""):
            return False
        return default

    def _set(self, prop: str, value: Any) -> None:
        """Write a value to a property on the connection."""
        self._connection.set_value(self._key(prop), value)

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def read_hvac_state(self) -> HVACState:
        """Read all HVAC-relevant properties from the GridLAB-D house object.

        GridLAB-D Properties Read:
            air_temperature, outdoor_temperature, cooling_setpoint/heating_setpoint,
            power_state, hvac_load, mass_temperature, Ua, Hm, Ca, Cm,
            cooling_COP, heating_COP, design_cooling_capacity,
            design_heating_capacity, solar_heatgain, internal_heatgain.

        Returns:
            HVACState populated from GridLAB-D properties.
        """
        mode_str = self._get_str("power_state", "OFF").upper()
        if "COOL" in mode_str:
            mode = "cooling"
        elif "HEAT" in mode_str or "AUX" in mode_str:
            mode = "heating"
        else:
            mode = "off"

        hvac_on = mode != "off"

        # Setpoint: use cooling or heating depending on current mode
        if mode == "cooling":
            setpoint = self._get_float("cooling_setpoint", 72.0)
        elif mode == "heating":
            setpoint = self._get_float("heating_setpoint", 68.0)
        else:
            setpoint = self._get_float("cooling_setpoint", 72.0)

        heating_type = self._get_str("heating_system_type", "HEAT_PUMP").upper()

        return HVACState(
            indoor_air_temp=self._get_float("air_temperature", 72.0),
            outdoor_air_temp=self._get_float("outdoor_temperature", 85.0),
            thermostat_setpoint=setpoint,
            hvac_mode=mode,
            power_draw=self._get_float("hvac_load", 0.0) / 1000.0,  # Btu/hr → approx kW
            hvac_on=hvac_on,
            thermal_mass_temp=self._get_float("mass_temperature", 72.0),
            air_mass=self._get_float("Ca", 1500.0),
            thermal_mass=self._get_float("Cm", 5000.0),
            UA_envelope=self._get_float("Ua", 500.0),
            UA_mass=self._get_float("Hm", 1500.0),
            cooling_COP=self._get_float("cooling_COP", 3.5),
            heating_COP=self._get_float("heating_COP", 3.0),
            rated_cooling_capacity=self._get_float("design_cooling_capacity", 36000.0),
            rated_heating_capacity=self._get_float("design_heating_capacity", 36000.0),
            has_heat_pump="HEAT_PUMP" in heating_type,
            solar_gain=self._get_float("solar_heatgain", 0.0),
            internal_gain=self._get_float("internal_heatgain", 0.0),
            humidity=self._get_float("humidity", 0.5),
            deadband=self._get_float("thermostat_deadband", 2.0),
            heating_system_type=heating_type,
            mass_internal_gain_fraction=self._get_float("mass_internal_gain_fraction", 0.5),
            mass_solar_gain_fraction=self._get_float("mass_solar_gain_fraction", 0.5),
            solar_heatgain_factor=self._get_float("solar_heatgain_factor", 40.0),
        )

    def read_water_heater_state(self) -> WaterHeaterState:
        """Read all water-heater-relevant properties from GridLAB-D.

        Uses the TESP convention of upper/lower tank temperature topics
        (UTTemp, LTTemp) and element state topics (UTState, LTState).

        Returns:
            WaterHeaterState populated from GridLAB-D properties.
        """
        upper_state = self._get_str("UTState", "OFF").upper()
        lower_state = self._get_str("LTState", "OFF").upper()
        element_on = "ON" in upper_state or "ON" in lower_state

        return WaterHeaterState(
            tank_temp_upper=self._get_float("UTTemp", 130.0),
            tank_temp_lower=self._get_float("LTTemp", 125.0),
            thermostat_setpoint=self._get_float("upper_tank_setpoint", 130.0),
            element_on=element_on,
            power_draw=self._get_float("WHLoad", 0.0),
            tank_volume=self._get_float("tank_volume", 50.0),
            tank_UA=self._get_float("tank_UA", 2.0),
            element_power=self._get_float("heating_element_capacity", 4.5),
            inlet_water_temp=self._get_float("inlet_water_temperature", 60.0),
            current_draw_rate=self._get_float("WDRate", 0.0),
            tank_height=self._get_float("tank_height", 4.0),
        )

    def read_ev_charger_state(self) -> EVChargerState:
        """Read EV charger properties from GridLAB-D.

        GridLAB-D may not have a native EV charger model; this may use
        a custom object or co-simulated external model.

        Returns:
            EVChargerState populated from GridLAB-D properties.
        """
        return EVChargerState(
            soc=self._get_float("SOC", 0.5),
            charge_rate=self._get_float("charge_rate", 0.0),
            battery_capacity=self._get_float("battery_capacity", 60.0),
            max_charge_rate=self._get_float("max_charge_rate", 7.2),
            charger_efficiency=self._get_float("charger_efficiency", 0.90),
            vehicle_plugged_in=self._get_bool("vehicle_connected", False),
            min_charge_rate=self._get_float("min_charge_rate", 1.0),
            soc_at_max_taper=self._get_float("soc_at_max_taper", 0.80),
        )

    def read_battery_state(self) -> BatteryState:
        """Read battery/inverter properties from GridLAB-D.

        Reads SOC from the battery object and power from the inverter.
        GridLAB-D sign convention: positive power_out = export/discharge.
        Agent convention: positive = charge. Converted here.

        Returns:
            BatteryState populated from GridLAB-D properties.
        """
        # GridLAB-D: p_out positive = export (discharge)
        # Agent: power positive = charge (consuming from grid)
        gld_p_out = self._get_float("p_out", 0.0)
        agent_power = -gld_p_out  # flip sign convention

        return BatteryState(
            soc=self._get_float("SOC", 0.5),
            power=agent_power,
            energy_capacity=self._get_float("battery_capacity", 13.5),
            max_charge_rate=self._get_float("rated_power", 5.0),
            max_discharge_rate=self._get_float("rated_power", 5.0),
            round_trip_efficiency=self._get_float("round_trip_efficiency", 0.90),
            cell_temperature=self._get_float("cell_temperature", 25.0),
            soc_min_bms=self._get_float("soc_min_bms", 0.10),
            soc_max_bms=self._get_float("soc_max_bms", 0.95),
            inverter_rated_power=self._get_float("inverter_rated_power", 5.0),
            state_of_health=self._get_float("state_of_health", 1.0),
        )

    def read_simulation_time(self) -> float:
        """Read the current simulation time from GridLAB-D.

        Returns:
            Current simulation time in seconds since epoch.
        """
        return self._get_float("clock", 0.0)

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def write_hvac_command(self, command: DeviceCommand) -> bool:
        """Write HVAC control command to GridLAB-D house object.

        Controls the HVAC by adjusting the thermostat setpoint. GridLAB-D's
        internal HVAC model determines on/off based on setpoint vs. indoor
        temperature.

        Args:
            command: DeviceCommand with setpoint and mode.

        Returns:
            True if write succeeded.
        """
        if command.mode == "cooling":
            self._set("cooling_setpoint", command.setpoint)
        elif command.mode == "heating":
            self._set("heating_setpoint", command.setpoint)
        else:
            # Default: write both setpoints
            self._set("cooling_setpoint", command.setpoint)
            self._set("heating_setpoint", command.setpoint)
        return True

    def write_water_heater_command(self, command: DeviceCommand) -> bool:
        """Write water heater control command to GridLAB-D.

        Sets the tank thermostat setpoint (upper and lower).

        Args:
            command: DeviceCommand with setpoint.

        Returns:
            True if write succeeded.
        """
        self._set("upper_tank_setpoint", command.setpoint)
        self._set("lower_tank_setpoint", command.setpoint)
        return True

    def write_ev_charger_command(self, command: DeviceCommand) -> bool:
        """Write EV charger control command to GridLAB-D.

        Sets the target charging power.

        Args:
            command: DeviceCommand with power_target.

        Returns:
            True if write succeeded.
        """
        self._set("charge_rate", command.power_target)
        return True

    def write_battery_command(self, command: DeviceCommand) -> bool:
        """Write battery/inverter control command to GridLAB-D.

        Agent convention: positive power_target = charge (consume from grid).
        GridLAB-D convention: positive p_out = export (discharge to grid).
        This method flips the sign.

        Args:
            command: DeviceCommand with power_target.
                Positive = charge, Negative = discharge.

        Returns:
            True if write succeeded.
        """
        gld_p_out = -command.power_target  # agent charge → GLD export negative
        self._set("p_out", gld_p_out)
        return True
