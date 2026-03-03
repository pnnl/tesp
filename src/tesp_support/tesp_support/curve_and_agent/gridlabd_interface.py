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
# ============================================================================

from typing import Any, Optional
from data_types import (
    HVACState, WaterHeaterState, EVChargerState, BatteryState, DeviceCommand
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
            This is an opaque handle whose type depends on the
            co-simulation framework (FNCS, HELICS, direct API).
            EXTERNAL: Must be provided by the simulation harness.
        object_name: The name of the GridLAB-D object this interface
            manages (e.g., "house_1", "waterheater_1").
            EXTERNAL: Must match the GridLAB-D model.
        device_type: The type of device, determines which properties
            are read/written.
    """

    def __init__(
        self,
        connection: Any,
        object_name: str,
        device_type: DeviceType
    ):
        self._connection = connection
        self._object_name = object_name
        self._device_type = device_type

    def read_hvac_state(self) -> HVACState:
        """Read all HVAC-relevant properties from the GridLAB-D house object.
        
        GridLAB-D Properties Read:
            - air_temperature (°F)
            - outdoor_temperature (°F) [from climate object]
            - heating_setpoint / cooling_setpoint (°F)
            - system_mode (OFF, HEAT, COOL, AUX)
            - hvac_power (kW) [from meter or house]
            - hvac_load (Btu/hr)
            - mass_temperature (°F)
            - Ua (Btu/hr·°F) [envelope conductance]
            - Hm (Btu/hr·°F) [mass-air conductance]
            - Ca (Btu/°F) [air thermal capacitance]
            - Cm (Btu/°F) [mass thermal capacitance]
            - cooling_COP, heating_COP
            - design_cooling_capacity (Btu/hr)
            - design_heating_capacity (Btu/hr)
            - solar_heatgain (Btu/hr)
            - internal_heatgain (Btu/hr)
        
        Returns:
            HVACState populated from GridLAB-D properties.
        """
        raise NotImplementedError

    def read_water_heater_state(self) -> WaterHeaterState:
        """Read all water-heater-relevant properties from GridLAB-D.
        
        GridLAB-D Properties Read:
            - temperature (°F) [may be single or upper/lower]
            - Tset (°F) [thermostat setpoint]
            - is_waterheater_on (boolean)
            - waterheater_power (kW) [from meter]
            - tank_volume (gal)
            - tank_UA (Btu/hr·°F)
            - heating_element_capacity (kW)
            - inlet_water_temperature (°F)
            - water_demand (gal/min)
            - tank_height (ft)
        
        Returns:
            WaterHeaterState populated from GridLAB-D properties.
        """
        raise NotImplementedError

    def read_ev_charger_state(self) -> EVChargerState:
        """Read EV charger properties from GridLAB-D.
        
        GridLAB-D Properties Read:
            Note: GridLAB-D may not have a native EV charger model.
            This may require a custom GridLAB-D object or a 
            co-simulated external EV model. Properties expected:
            - battery_SOC (fraction)
            - charge_rate (kW)
            - battery_capacity (kWh)
            - max_charge_rate (kW)
            - charger_efficiency (fraction)
            - vehicle_connected (boolean)
        
        Returns:
            EVChargerState populated from GridLAB-D properties.
        """
        raise NotImplementedError

    def read_battery_state(self) -> BatteryState:
        """Read battery/inverter properties from GridLAB-D.
        
        GridLAB-D Properties Read:
            From the battery object:
            - state_of_charge (fraction)
            - battery_capacity (kWh)
            - rated_power (kW) [max charge/discharge]
            - round_trip_efficiency (fraction)
            - battery_type, battery_state
            From the inverter object:
            - power_out (kW) [positive = export, negative = import]
            - rated_power (kW)
            Additional (if modeled):
            - cell_temperature (°C)
            - state_of_health (fraction)
        
        Returns:
            BatteryState populated from GridLAB-D properties.
        """
        raise NotImplementedError

    def write_hvac_command(self, command: DeviceCommand) -> bool:
        """Write HVAC control command to GridLAB-D house object.
        
        GridLAB-D Properties Written:
            - cooling_setpoint (°F) [if cooling mode]
            - heating_setpoint (°F) [if heating mode]
            
        The agent controls the HVAC by adjusting the thermostat
        setpoint. GridLAB-D's internal HVAC model then determines
        whether the unit turns on or off based on the setpoint
        and current indoor temperature.
        
        Args:
            command: DeviceCommand with setpoint and mode.
        
        Returns:
            True if write succeeded.
        """
        raise NotImplementedError

    def write_water_heater_command(self, command: DeviceCommand) -> bool:
        """Write water heater control command to GridLAB-D.
        
        GridLAB-D Properties Written:
            - Tset (°F) [tank thermostat setpoint]
            OR
            - re_override (ON/OFF) [direct element control]
        
        Args:
            command: DeviceCommand with setpoint.
        
        Returns:
            True if write succeeded.
        """
        raise NotImplementedError

    def write_ev_charger_command(self, command: DeviceCommand) -> bool:
        """Write EV charger control command to GridLAB-D.
        
        GridLAB-D Properties Written:
            - charge_rate (kW) [target charging power]
            OR
            - charger_state (ON/OFF)
        
        Args:
            command: DeviceCommand with power_target.
        
        Returns:
            True if write succeeded.
        """
        raise NotImplementedError

    def write_battery_command(self, command: DeviceCommand) -> bool:
        """Write battery/inverter control command to GridLAB-D.
        
        GridLAB-D Properties Written:
            To the inverter object:
            - power_out (kW) [positive = discharge/export,
              negative = charge/import]
            OR
            - P_Out (kW), Q_Out (kVAR) [for four-quadrant inverter]
        
        Note: Sign conventions may differ between the agent
        (positive = consuming from grid) and GridLAB-D 
        (positive = exporting to grid). This method handles
        the conversion.
        
        Args:
            command: DeviceCommand with power_target.
                Positive = charge, Negative = discharge.
        
        Returns:
            True if write succeeded.
        """
        raise NotImplementedError

    def read_simulation_time(self) -> float:
        """Read the current simulation time from GridLAB-D.
        
        Returns:
            Current simulation time in seconds since epoch.
        """
        raise NotImplementedError