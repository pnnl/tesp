# Copyright (C) 2024 Battelle Memorial Institute
# file: ETP.py
"""
The Equivalent Thermal Parameters model is a single zone thermodynamic model
commonly used for modeling residential structures. The model is a second 
derived from a second order differential equation but has an algebraic 
solution, producing very quick solution times. It is most commonly used
to model large populations of houses where computational speed is valued 
more than high degrees of accuracy.

Being a single zone model, it has limited application for structures with
multiple HVAC zones though it has been used to in the past to reasonably 
approximate some of these buildings (e.g. strip malls, big box stores).
Higher-fidelity modeling software such as Energy+ may be a good alternative
for these types of structures.

The ETP model has three nodes modeling three temperatures: outside air,
interior air temperature, and mass temperature. The temperatures are coupled
through the exterior envelope (outside air temp to interior air temp) and
and the mass-air interface between the interior air and the mass of the house.
Heat is added (or removed) from both the interior air of the house and the 
mass of the house through solar radiation, electrical loads, and the HVAC
system. Both the interior air temperature and mass temperature have a delayed
response to this heat flow (temperature lags heat flow) with the lag in the
mass temperature being much more significant than that of the air.

Here's the electrical circuit model that is solved with the key parameters
identified. Note that all of the user-facing device parameters map into these
model parameters in one way or another.

                        ------                  ------
                       /      \                /      \
                       |  Qa   |               |  Qm   |
                       \      /                \      /
                        ------                  ------
                           |                       |
                           |                       |
           Ua              |          Hm           |
       /\    /\    /\      v     /\    /\    /\    v     
  To--/  \  /  \  /  \----Ta----/  \  /  \  /  \---Tm
          \/    \/         |        \/    \/       |
                           |                       |
                           |                       |
                        -------  Ca             -------  Cm
                        _______                 _______
                           |                       |
                           |                       |
                         -----                   -----
                          ---                     ---
                           -                       -

To - outdoor air temperature
Ua - Thermal conductivity of the building envelope
Ta - Indoor air temperature
Qa - Heat gains (or losses) from solar radiation, HVAC system, load heating
Ca - Thermal mass/inertia of air in house (relatively small)
Hm - Thermal conductivity of the mass of house to the indoor air
        (related to the surface area of the mass)
Qm - Heat gains modeled as directly happening on the mass of house
        (rather than heating the air)
Tm - Temperature of the mass of the house
Cm - Thermal mass/inertia of the mass of the house 
"""

import argparse
import logging
import math
import pprint
import sys

# Setting up logging
logger = logging.getLogger(__name__)

# Setting up pretty printing, mostly for debugging.
pp = pprint.PrettyPrinter(indent=4)

def _open_file(file_path: str, type='r'):
    """Utilty function to open file with reasonable error handling.

    Args:
        file_path (str) - Path to the file to be opened

        type (str) - Type of the open method. Default is read ('r')


    Returns:
        fh (file object) - File handle for the open file
    """
    try:
        fh = open(file_path, type)
    except IOError:
        logger.error('Unable to open {}'.format(file_path))
    else:
        return fh


class ETP():
    """


    """

    def __init__(self):
        # TODO: update inputs for class
        """ Initializes the class
        """
        # TODO: update attributes of class
        self.name = key
        self.solver = solver
        self.air_temp = 72.0
        self.mass_temp = 72.0
        self.hvac_kw = 100.0
        self.wh_kw = 0.0
        self.house_kw = 5.0
        self.mtr_v = 120.0
        self.hvac_on = False
        # self.hvac_demand = 1.0
        self.minute = 0
        self.hour = 0
        self.day = 0
        self.Qi = 0.0
        self.Qh = 0.0
        self.Qa_ON = 0.0
        self.Qa_OFF = 0.0
        self.Qm = 0.0
        self.Qs = 0.0

        self.bid_quantity = 0.0
        self.bid_quantity_rt = 0.0

        self.thermostat_mode = 'OFF'  # can be 'Cooling' or 'Heating' or 'OFF'
        self.cleared_price = 0.0
        self.bid_rt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
        self.bid_da = [[[0., 0.], [0., 0.], [0., 0.], [0., 0.]]] * 48
        self.quantity_curve = [0 for _ in range(10)]
        self.temp_curve = [0]
        # House model parameters
        self.sqft = float(house_properties['sqft'])
        self.stories = float(house_properties['stories'])
        self.doors = float(house_properties['doors'])
        self.thermal_integrity = house_properties['thermal_integrity']
        self.Rroof = float(house_properties['Rroof'])
        self.Rwall = float(house_properties['Rwall'])
        self.Rfloor = float(house_properties['Rfloor'])
        self.Rdoors = float(house_properties['Rdoors'])
        self.airchange_per_hour = float(house_properties['airchange_per_hour'])
        self.ceiling_height = int(house_properties['ceiling_height'])
        self.thermal_mass_per_floor_area = float(house_properties['thermal_mass_per_floor_area'])
        self.aspect_ratio = float(house_properties['aspect_ratio'])
        self.exterior_ceiling_fraction = float(house_properties['exterior_ceiling_fraction'])
        self.exterior_floor_fraction = float(house_properties['exterior_floor_fraction'])
        self.exterior_wall_fraction = float(house_properties['exterior_wall_fraction'])
        self.window_energy_transfer_coeff = float(house_properties['window_exterior_transmission_coefficient'])
        self.glazing_layers = int(house_properties['glazing_layers'])
        self.glass_type = int(house_properties['glass_type'])
        self.window_frame = int(house_properties['window_frame'])
        self.glazing_treatment = int(house_properties['glazing_treatment'])
        self.cooling_COP = 3.5  # float(house_properties['cooling_COP'])
        self.heating_COP = 2.5
        self.cooling_cop_adj_rt = 3.5
        self.heating_cop_adj_rt = 2.5
        self.cooling_cop_adj = [self.cooling_COP for _ in range(self.windowLength)]
        self.heating_cop_adj = [self.heating_COP for _ in range(self.windowLength)]
        # Coefficients to adjust COP and capacity
        self.cooling_COP_K0 = -0.01363961
        self.cooling_COP_K1 = 0.01066989
        self.cooling_COP_limit = 40

        self.heating_COP_K0 = 2.03914613
        self.heating_COP_K1 = -0.03906753
        self.heating_COP_K2 = 0.00045617
        self.heating_COP_K3 = -0.00000203
        self.heating_COP_limit = 80
        self.heating_COP = float(house_properties['cooling_COP']) - 1
        # TODO: need to know source of cooling COP and why not heating
        self.cooling_capacity_K0 = 1.48924533
        self.cooling_capacity_K1 = -0.00514995
        self.cooling_COP = float(house_properties['cooling_COP'])

        self.latent_load_fraction = 0.3
        self.latent_factor = [self.latent_load_fraction for _ in self.TIME]
        self.cooling_design_temperature = 95.0
        self.design_cooling_setpoint = 75.0
        self.design_internal_gains = 167.09 * self.sqft ** 0.442
        self.design_peak_solar = 195.0
        self.over_sizing_factor = float(house_properties['over_sizing_factor'])
        self.heating_system_type = (house_properties['heating'])
        self.cooling_system_type = (house_properties['cooling'])
        self.design_heating_setpoint = 70.0
        self.heating_design_temperature = 0.0  # TODO: not sure where to get this (guess for now)

        self.heating_capacity_K0 = 0.34148808
        self.heating_capacity_K1 = 0.00894102
        self.heating_capacity_K2 = 0.00010787

        self.design_heating_capacity = 0.0
        self.design_cooling_capacity = 0.0

        # weather variables
        self.solar_direct = 0.0
        self.solar_diffuse = 0.0
        self.outside_air_temperature = 80.0
        self.humidity = 0.8

        # TODO: for debugging only
        self.moh = 0
        self.hod = 0
        self.dow = 0
        self.FirstTime = True
        # variables to be used in solargain calculation
        self.surface_angles = {
            'H': 360,
            'N': 180,
            'NE': 135,
            'E': 90,
            'SE': 45,
            'S': 0,
            'SW': -45,
            'W': -90,
            'NW': -135
        }

        # GridLAB-D default values
        self.int_ext_wall_ratio = 1.5
        self.int_heat_transfer_coeff = 1.46
        self.mass_int_gain_fraction = 0.5 
        self.mass_solar_gain_fraction = 0.5
        self.window_wall_ratio =0.15
        self.one_door_area = 19.5
        self.VHa = 0.0735 * 0.2402  # air_density*air_heat_capacity

        # calculated during init_etp_model
        self.ceiling_area = 0
        self.floor_area = 0
        self.ext_perimeter = 0
        self.ext_wall_area = 0  
        self.window_area = 0
        self.ext_net_wall_area = 0
        self.Vterm
        
        # calculated in calc_etp_model
        self.UA = 0.
        self.CA = 0.
        self.HM = 0.
        self.CM = 0.
        
        
        self.solar_heatgain_factor = 0.
        self.solar_gain = 0.0

        self.check_for_parameter_zeros()     

        self.init_etp_model()

        self.calc_etp_model()

        self.temp_room_init = 72.0
        self.temp_room_previous_cool = 85.0
        self.temp_room_previous_heat = 55.0
        self.temp_outside_init = 80.0
        self.eps = 0.
        self.COP = 0.
        self.K1 = 0.
        self.K2 = 0.
        self.eps = math.exp(-self.UA / (self.CM + self.CA) * 1.0)  # using 1 fixed for time constant

        # Check that user-provided parameter values are within reasonable ranges
        self.check_parameter_in_bounds("Rroof", 2, 60)
        self.check_parameter_in_bounds("Rwall", 2, 40)
        self.check_parameter_in_bounds("Rfloor", 2, 40)
        self.check_parameter_in_bounds("Rdoor", 1, 20)
        self.check_parameter_in_bounds("air_change_per_hour", 0.1, 6.5)
        self.check_parameter_in_bounds("glazing_layers", 1, 3)
        self.check_parameter_in_bounds("cooling_COP", 1, 10)

    def check_for_parameter_zeros(self):
        """
        These are hard-coded GLD default values
        """
        if self.aspect_ratio == 0.0:  # footprint x/y ratio
            self.aspect_ratio = 1.5
        if self.exterior_ceiling_fraction == 0.0:
            self.exterior_ceiling_fraction = 1.0
        if self.exterior_floor_fraction == 0.0:
            self.exterior_floor_fraction = 1.0
        if self.exterior_wall_fraction == 0.0:
            self.exterior_wall_fraction = 1.0
        if self.window_energy_transfer_coeff <= 0.0:
            self.window_energy_transfer_coeff = 0.6

    def check_parameter_in_bounds(self, parameter_name: str, 
                                  min_value: float, 
                                  max_value: float) -> None:
        """
        Checks that the passed-in parameter name for the class attribute is
        within the passed-in values. If the value is outside the specified
        bounds, a low-priority message is logged. The value is not coerced and
        the message is not considered a warning or error.
        """
        parameter_value = getattr(self, parameter_name)
        if not (min_value <= parameter_value <= max_value):
            logger.info(f'{self.name} "init" --  {parameter_name} is {parameter_value}, outside of nominal range of
                         {min_value} to {max_value}')

    def set_window_insulation(self, glass_type: int, glazing_layers: int, window_frame: int) -> float:
        """
        Defines Rg based on glass type, number of layers, and window frame type

        TODO: Update glass_type parameter from an int to an enumeration
        TODO: Update window_fram parameter from an int to an enumeration
        
        """
        if glass_type == 2:
            if glazing_layers == 1:
                logging.error("error: no value for one pane of low-e glass")
                raise ValueError("No value for Rg for glazing_layers = 1, glass_type = 2 (low-e glass)")
            elif glazing_layers == 2:
                if window_frame == 0:
                    Rg = 1.0 / 0.30
                elif window_frame == 1:
                    Rg = 1.0 / 0.67
                elif window_frame == 2:
                    Rg = 1.0 / 0.47
                elif window_frame == 3:
                    Rg = 1.0 / 0.41
                elif window_frame == 4:
                    Rg = 1.0 / 0.33
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            elif glazing_layers == 3:
                if window_frame == 0:
                    Rg = 1.0 / 0.27
                elif window_frame == 1:
                    Rg = 1.0 / 0.64
                elif window_frame == 2:
                    Rg = 1.0 / 0.43
                elif window_frame == 3:
                    Rg = 1.0 / 0.37
                elif window_frame == 4:
                    Rg = 1.0 / 0.31
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            else:
                logger.error(f"glazing_layers defined as {glazing_layers}; valid values are '1', '2', or '3'.")
        elif glass_type == 1:
            if glazing_layers == 1:
                if window_frame == 0:
                    Rg = 1.0 / 1.04
                elif window_frame == 1:
                    Rg = 1.0 / 1.27
                elif window_frame == 2:
                    Rg = 1.0 / 1.08
                elif window_frame == 3:
                    Rg = 1.0 / 0.90
                elif window_frame == 4:
                    Rg = 1.0 / 0.81
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            elif glazing_layers == 2:
                if window_frame == 0:
                    Rg = 1.0 / 0.48
                elif window_frame == 1:
                    Rg = 1.0 / 0.81
                elif window_frame == 2:
                    Rg = 1.0 / 0.60
                elif window_frame == 3:
                    Rg = 1.0 / 0.53
                elif window_frame == 4:
                    Rg = 1.0 / 0.44
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            elif glazing_layers == 3:
                if window_frame == 0:
                    Rg = 1.0 / 0.31
                elif window_frame == 1:
                    Rg = 1.0 / 0.67
                elif window_frame == 2:
                    Rg = 1.0 / 0.46
                elif window_frame == 3:
                    Rg = 1.0 / 0.40
                elif window_frame == 4:
                    Rg = 1.0 / 0.34
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            else:
                logger.error(f"glazing_layers defined as {glazing_layers}; valid values are '1', '2', or '3'.")
        elif glass_type == 0:
            Rg = 2.0
        else:
            logger.error(f"glass_type defined as {glass_type}; valid values are '2', '1', or '0'.")
        
        return Rg
        
    def set_window_something(self, glazing_layers: int, glazing_treatment: int, window_frame: int) -> float:
        """
        I don't know what "Wg" is but this method sets its

        TODO: update glazing_treatment parameter from int to enumeration
        TODO: update window_frame parameter from int to enumeration
        """
        if glazing_layers == 1:
            if glazing_treatment == 1:
                if window_frame == 0:
                    Wg = 0.86
                elif window_frame == 1 or window_frame == 2:
                    Wg = 0.75
                elif window_frame == 3 or window_frame == 4:
                    Wg = 0.64
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            elif glazing_treatment == 2:
                if window_frame == 0:
                    Wg = 0.73
                elif window_frame == 1 or window_frame == 2:
                    Wg = 0.64
                elif window_frame == 3 or window_frame == 4:
                    Wg = 0.54
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            elif glazing_treatment == 3:
                if window_frame == 0:
                    Wg = 0.31
                elif window_frame == 1 or window_frame == 2:
                    Wg = 0.28
                elif window_frame == 3 or window_frame == 4:
                    Wg = 0.24
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            else:
                logger.error(f"glazing_treatment defined as {glazing_treatment}; valid values are '1', '2', or '3'.")
        elif glazing_layers == 2:
            if glazing_treatment == 1:
                if window_frame == 0:
                    Wg = 0.76
                elif window_frame == 1 or window_frame == 2:
                    Wg = 0.67
                elif window_frame == 3 or window_frame == 4:
                    Wg = 0.57
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            elif glazing_treatment == 2:
                if window_frame == 0:
                    Wg = 0.62
                elif window_frame == 1 or window_frame == 2:
                    Wg = 0.55
                elif window_frame == 3 or window_frame == 4:
                    Wg = 0.46
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            elif glazing_treatment == 3:
                if window_frame == 0:
                    Wg = 0.29
                elif window_frame == 1 or window_frame == 2:
                    Wg = 0.27
                elif window_frame == 3 or window_frame == 4:
                    Wg = 0.22
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            else:
                logger.error(f"glazing_treatment defined as {glazing_treatment}; valid values are '1', '2', or '3'.")
        elif glazing_layers == 3:
            if glazing_treatment == 1:
                if window_frame == 0:
                    Wg = 0.68
                elif window_frame == 1 or window_frame == 2:
                    Wg = 0.60
                elif window_frame == 3 or window_frame == 4:
                    Wg = 0.51
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            elif glazing_treatment == 2:
                if window_frame == 0:
                    Wg = 0.34
                elif window_frame == 1 or window_frame == 2:
                    Wg = 0.31
                elif window_frame == 3 or window_frame == 4:
                    Wg = 0.26
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            elif glazing_treatment == 3:
                if window_frame == 0:
                    Wg = 0.34
                elif window_frame == 1 or window_frame == 2:
                    Wg = 0.31
                elif window_frame == 3 or window_frame == 4:
                    Wg = 0.26
                else:
                    logger.error(f"window_frame defined as {window_frame}; valid values are '0', '1', '2', '3', or '4'.")
            else:
                logger.error(f"glazing_treatment defined as {glazing_treatment}; valid values are '1', '2', or '3'.")
        else:
            logger.error(f"glazing_layers defined as {glazing_layers}; valid values are '1', '2', or '3'.")

        return Wg

    def div(self, x, y, def_val_if_zero_denom=0):
        """
        Special divsion function that returns zero if the denominator is zero.

        This is useful in calculating ETP models
        """
        return x / y if y != 0 else def_val_if_zero_denom

    def init_etp_model(self):
        """
        Calculate values that are not expected to change during update of the
        ETP model (e.g. ceiling area, square footage of the house)
        """
        
        self.Vterm = self.sqft * self.ceiling_height * self.VHa
        self.Rg = self.set_window_insulation(self.glazing_layers, self.glazing_treatment, self.window_frame)
        self.Wg = self.set_window_something(self.glazing_layers, self.glazing_treatment, self.window_frame)
        self.ceiling_area = (self.sqft / self.stories) * self.exterior_ceiling_fraction
        self.floor_area = (self.sqft / self.stories) * self.exterior_floor_fraction
        self.ext_perimeter = 2 * (1 + self.aspect_ratio) * math.sqrt(self.ceiling_area / self.aspect_ratio) 
        self.ext_wall_area = self.stories * self.ceiling_height * self.ext_perimeter  
        self.window_area = self.window_wall_ratio * self.ext_wall_area * self.exterior_wall_fraction  # gross window area
        self.door_area =  self.doors * self.one_door_area 
        self.net_ext_wall_area = self.ext_wall_area * self.window_area * self.door_area
        self.UA = self.div(self.ceiling_area, self.Rroof) \
            + self.div(self.floor_area, self.Rfloor) \
            + self.div(self.ext_net_wall_area, self.Rwall) \
            + self.div(self.window_area, self.Rg) \
            + self.div(self.door_area, self.Rdoors) \
            + self.Vterm * self.airchange_per_hour

    def calc_etp_model(self):
        """ Sets the ETP parameters from configuration data

        References:
            `Thermal Integrity Table Inputs and Defaults <http://gridlab-d.shoutwiki.com/wiki/Residential_module_user%27s_guide#Thermal_Integrity_Table_Inputs_and_Defaults>`_
        """

        




        self.CA = 3 * Vterm
        self.HM = self.int_heat_transfer_coeff \
                * (self.window_area / self.exterior_wall_fraction + self.ext_wall_area * self.int_ext_wall_ratio + self.ceiling_area * self.stories / self.exterior_ceiling_fraction)
        self.CM = self.sqft * self.thermal_mass_per_floor_area - 2 * Vterm

        self.solar_heatgain_factor = Ag * self.Wg * self.window_energy_transfer_coeff

        self.design_cooling_capacity = ((1.0 + self.over_sizing_factor) * (1.0 + self.latent_load_fraction) *
                                        (self.UA * (self.cooling_design_temperature - self.design_cooling_setpoint) +
                                            self.design_internal_gains +
                                            (self.design_peak_solar * self.solar_heatgain_factor)))
        round_value = self.design_cooling_capacity / 6000.0
        self.design_cooling_capacity = math.ceil(round_value) * 6000.0

        if self.heating_system_type == 'HEAT_PUMP':
            self.design_heating_capacity = self.design_cooling_capacity
        else:
            self.design_heating_capacity = ((1.0 + self.over_sizing_factor) * self.UA *
                                            (self.design_heating_setpoint - self.heating_design_temperature))
            round_value = self.design_heating_capacity / 10000.0
            self.design_heating_capacity = math.ceil(round_value) * 10000.0

        logger.debug('ETP model ' + self.name)
        logger.debug('  UA -> {:.2f}'.format(self.UA))
        # print('  UA -> {:.2f}'.format(self.UA))
        logger.debug('  CA -> {:.2f}'.format(self.CA))
        # print('  CA -> {:.2f}'.format(self.CA))
        logger.debug('  HM -> {:.2f}'.format(self.HM))
        logger.debug('  CM -> {:.2f}'.format(self.CM))
        # print('  CM -> {:.2f}'.format(self.CM))
            
    def _auto_run(args):
        pass

if __name__ == '__main__':
    # This slightly complex mess allows lower importance messages
    # to be sent to the log file and ERROR messages to additionally
    # be sent to the console as well. Thus, when bad things happen
    # the user will get an error message in both places which,
    # hopefully, will aid in trouble-shooting.
    fileHandle = logging.FileHandler("etp.log",'w')
    fileHandle.setLevel(logging.DEBUG)
    streamHandle = logging.StreamHandler(sys.stdout)
    streamHandle.setLevel(logging.ERROR)
    logging.basicConfig(level=logging.DEBUG,
                        handlers=[fileHandle, streamHandle])
    parser = argparse.ArgumentParser(description="Evaluates disk space used,"
                                     "writes results to disk, and makes a graph.")
    parser.add_argument('-g', '--graph',
                        help="flag to only create a graph of the historic data"
                                "(no data collection)",
                        action=argparse.BooleanOptionalAction)
    parser.add_argument('-i', '--input_paths',
                        help="paths of folders to get sizes of, one per line",
                        nargs='?',
                        default="folder_paths_to_size.txt")
    args = parser.parse_args()
    _auto_run(args)