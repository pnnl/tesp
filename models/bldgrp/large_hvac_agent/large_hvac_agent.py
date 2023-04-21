# Copyright (C) 2017-2022 Battelle Memorial Institute
# file large_hvac_agent.py
"""
    Test Class that that implements large Commercial Building HVAC Agent.
The main goal of the agent is to approximate power consumption of the building, given user settings such as temperature
setpoint of the zone. In doing so, the agent develops relationship between different components of the building, so as to
later try to perform a day-ahead and real-time power approximation and bidding.
1. __init__() initializes the respective components' parameters, inputs an EP result file, declares whether to train or test
2. get_simulation_data() reads the EP result file and places them in pandas dataframe for later manipulation
3. get_coefficients() perform regression over the collected data from EP result file and its dependent variables.
   It also saves these coefficients to be used later on in the generic approximation
4. get_approximation() depending upon testing or training scenario, uses the relationship deveopled in the
   get_coefficient() function to obtain approximate power of chillers, fans and pumps.

The main tasks of this approximation is that it measures zone temperature setpoint and hvac schedule from previous steps
and the prediction of Setpoint, internal loads and outside temperature for the next step, we calculate the mass-flow rate.
Using that mass-flow rate fan powers, chiller powers and pumps powers are approximated
To process data for regression, visualizing results and saving coefficients, some helper modules are also included
"""
import os
import numpy as np
import pandas as pd
import datetime
from datetime import timedelta
import time
from statsmodels.formula.api import ols
import matplotlib.pyplot as plt
import process_data as process_data
import perform_regressions as regress
import perform_approximation as approximate
import process_plots as plotting
#import save_coefficients as save
import math
class LargeHVACAgent (object):

    def __init__(self, eplus_file_name, t_start, scenario):
        skip_rows = range(1, t_start)
        self.data_raw = pd.read_csv(eplus_file_name, skiprows=skip_rows)
        if scenario == 1:
            print(eplus_file_name + " loaded for Training")
            print(self.data_raw.info())
        elif scenario == 2:
            print(eplus_file_name + " loaded for Testing")
            print(self.data_raw.info())
        else:
            print("===wrong scenario chosen===")

#    TODO: to be read from the JSON configuration file
        # ======= Chiller Parameters ===================
        self.parameters_chiller_COP_ref = 4.9
        self.parameters_chiller_P_ref_chiller1_Watts = 998359.76
        self.parameters_chiller_P_ref_chiller2_Watts = 998359.76
        self.parameters_chiller_chilled_water_temp = 6.7
        # CAPFT
        self.parameters_chiller_a0 = 0.9061150
        self.parameters_chiller_a1_Tchws_1 = 0.0292277
        self.parameters_chiller_a2_Tchws_2 = -0.0003647
        self.parameters_chiller_a3_Tcnds_1 = -0.0009709
        self.parameters_chiller_a4_Tcnds_2 = -0.0000905
        self.parameters_chiller_a5_Tchws_Tcnds = 0.0002527
        # EIRFT
        self.parameters_chiller_b0 = 0.3617105
        self.parameters_chiller_b1_Tchws_1 = -0.0229833
        self.parameters_chiller_b2_Tchws_2 = 0.0009519
        self.parameters_chiller_b3_Tcnds_1 = 0.0131889
        self.parameters_chiller_b4_Tcnds_2 = 0.0003752
        self.parameters_chiller_b5_Tchws_Tcnds = -0.0007059

        # EIRFPLR
        self.parameters_chiller_c0 = -1.360532E-01
        self.parameters_chiller_c1_Tcnds_1 = 8.642703E-03
        self.parameters_chiller_c2_Tcnds_2 = 3.855583E-06
        self.parameters_chiller_c3_PLR_1 = 1.024034E+00
        self.parameters_chiller_c4_PLR_2 = 6.047444E-02
        self.parameters_chiller_c5_Tcnds_PLR = -8.947860E-03
        self.parameters_chiller_c6_PLR_3 = 5.706602E-02


        # ===== Cooling Tower Parameters ========
        self.parameters_condenser_leaving_temperature_min = 21
        self.parameters_condenser_leaving_temperature_max = 35
        self.parameters_Fan_Power_CoolTower_Max_Power = 2.912e4
        # ===== VAV Fan Parameters =============
        self.parameters_vav_cp = 1005
        self.parameters_vav_Tsupply = 12.6
        self.parameters_bottom_vav_max_flow = 12
        self.parameters_mid_vav_max_flow = 116
        self.parameters_top_vav_max_flow = 60
        self.parameters_basement_cav_max_power = 9423
        # ===== Pump Parameters =====================
        self.parameters_primary_pump_max_power = 6636
        self.parameters_secondary_pump_max_power = 2.043e4

    def get_simulation_data(self):

        columnsList = pd.Series(self.data_raw.columns)


        self.sim_data_EnvironmentVar = self.data_raw[list(columnsList[(columnsList.str.startswith("Environment"))])]
        self.sim_data_Temperature_Outside = self.sim_data_EnvironmentVar[
            (self.sim_data_EnvironmentVar.columns[self.sim_data_EnvironmentVar.columns.str.contains("Site Outdoor Air Drybulb Temperature")])]
        self.sim_data_Air_Humidity_Ratio = self.sim_data_EnvironmentVar[
            (self.sim_data_EnvironmentVar.columns[self.sim_data_EnvironmentVar.columns.str.contains("Site Outdoor Air Relative Humidity")])]
        self.sim_data_Temperature_WetBulb = self.sim_data_EnvironmentVar[
            (self.sim_data_EnvironmentVar.columns[self.sim_data_EnvironmentVar.columns.str.contains("Site Outdoor Air Wetbulb Temperature")])]
        # ====== ZONE TEMPERATURES =====================
        self.sim_data_ZoneTemperatures = self.data_raw[
            list(columnsList[(columnsList.str.endswith("Zone Mean Air Temperature [C](TimeStep)"))])]

        # >>>>> BASEMENT FLOOR <<<<<<
        self.sim_data_ZoneTemperature_Basement = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[self.sim_data_ZoneTemperatures.columns.str.startswith("BASEMENT")])]

        # >>>>> BOTTOM FLOOR <<<<<<
        self.sim_data_ZoneTemperature_Bottom_Core = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[self.sim_data_ZoneTemperatures.columns.str.contains("CORE_BOTTOM")])]
        self.sim_data_ZoneTemperature_Bottom_Zone1 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_BOT_ZN_1")])]
        self.sim_data_ZoneTemperature_Bottom_Zone2 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_BOT_ZN_2")])]
        self.sim_data_ZoneTemperature_Bottom_Zone3 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_BOT_ZN_3")])]
        self.sim_data_ZoneTemperature_Bottom_Zone4 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_BOT_ZN_4")])]

        # >>>>> MID FLOOR <<<<<<
        self.sim_data_ZoneTemperature_Mid_Core = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[self.sim_data_ZoneTemperatures.columns.str.contains("CORE_MID")])]
        self.sim_data_ZoneTemperature_Mid_Zone1 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_MID_ZN_1")])]
        self.sim_data_ZoneTemperature_Mid_Zone2 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_MID_ZN_2")])]
        self.sim_data_ZoneTemperature_Mid_Zone3 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_MID_ZN_3")])]
        self.sim_data_ZoneTemperature_Mid_Zone4 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_MID_ZN_4")])]

        # >>>>> TOP FLOOR <<<<<<
        self.sim_data_ZoneTemperature_Top_Core = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[self.sim_data_ZoneTemperatures.columns.str.contains("CORE_TOP")])]
        self.sim_data_ZoneTemperature_Top_Zone1 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_TOP_ZN_1")])]
        self.sim_data_ZoneTemperature_Top_Zone2 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_TOP_ZN_2")])]
        self.sim_data_ZoneTemperature_Top_Zone3 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_TOP_ZN_3")])]
        self.sim_data_ZoneTemperature_Top_Zone4 = self.sim_data_ZoneTemperatures[(
            self.sim_data_ZoneTemperatures.columns[
                self.sim_data_ZoneTemperatures.columns.str.contains("PERIMETER_TOP_ZN_4")])]

        # ========= Zone Temperatures Setpoints =================
        self.sim_data_ZoneTemperatures_Setpoints = self.data_raw[
            list(columnsList[(columnsList.str.endswith("Zone Thermostat Cooling Setpoint Temperature [C](TimeStep)"))])]

        # >>>>> BASEMENT FLOOR <<<<<<
        self.sim_data_ZoneTemperature_Setpoint_Basement_Core = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("Basement")])]

        # >>>>> BOTTOM FLOOR <<<<<<
        self.sim_data_ZoneTemperature_Setpoint_Bottom_Core = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("CORE_BOTTOM")])]
        self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone1 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_BOT_ZN_1")])]
        self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone2 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_BOT_ZN_2")])]
        self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone3 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_BOT_ZN_3")])]
        self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone4 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_BOT_ZN_4")])]

        # >>>>> MID FLOOR <<<<<<
        self.sim_data_ZoneTemperature_Setpoint_Mid_Core = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("CORE_MID")])]
        self.sim_data_ZoneTemperature_Setpoint_Mid_Zone1 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_MID_ZN_1")])]
        self.sim_data_ZoneTemperature_Setpoint_Mid_Zone2 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_MID_ZN_2")])]
        self.sim_data_ZoneTemperature_Setpoint_Mid_Zone3 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_MID_ZN_3")])]
        self.sim_data_ZoneTemperature_Setpoint_Mid_Zone4 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_MID_ZN_4")])]

        # >>>>> TOP FLOOR <<<<<<
        self.sim_data_ZoneTemperature_Setpoint_Top_Core = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("CORE_TOP")])]
        self.sim_data_ZoneTemperature_Setpoint_Top_Zone1 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_TOP_ZN_1")])]
        self.sim_data_ZoneTemperature_Setpoint_Top_Zone2 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_TOP_ZN_2")])]
        self.sim_data_ZoneTemperature_Setpoint_Top_Zone3 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_TOP_ZN_3")])]
        self.sim_data_ZoneTemperature_Setpoint_Top_Zone4 = self.sim_data_ZoneTemperatures_Setpoints[(
            self.sim_data_ZoneTemperatures_Setpoints.columns[
                self.sim_data_ZoneTemperatures_Setpoints.columns.str.contains("PERIMETER_TOP_ZN_4")])]


        # ===================== COOLING SYSTEM DATA ======================================

        # >>>>>>>>>>> Chiller 1 <<<<<<<<<<<<<<
        self.sim_data_Chiller1 = self.data_raw[list(columnsList[(columnsList.str.startswith("COOLSYS1 CHILLER1:"))])]
        self.sim_data_Condenser_Leaving_Temperature_Chiller1 = self.sim_data_Chiller1[(
            self.sim_data_Chiller1.columns[
                self.sim_data_Chiller1.columns.str.contains("Condenser Inlet Temperature")])]
        self.sim_data_Evaporator_Load_Chiller1 = self.sim_data_Chiller1[(
            self.sim_data_Chiller1.columns[
                self.sim_data_Chiller1.columns.str.contains("Chiller Evaporator Cooling Rate")])]
        self.sim_data_Chiller1_Power = self.sim_data_Chiller1[(
            self.sim_data_Chiller1.columns[
                self.sim_data_Chiller1.columns.str.contains("Chiller Electric Power")])]

        # >>>>>>>>>>> Chiller 2 <<<<<<<<<<<<<<
        self.sim_data_Chiller2 = self.data_raw[list(columnsList[(columnsList.str.startswith("COOLSYS1 CHILLER2:"))])]
        self.sim_data_Condenser_Leaving_Temperature_Chiller2 = self.sim_data_Chiller2[(
            self.sim_data_Chiller2.columns[
                self.sim_data_Chiller2.columns.str.contains("Condenser Inlet Temperature")])]
        self.sim_data_Evaporator_Load_Chiller2 = self.sim_data_Chiller2[(
            self.sim_data_Chiller2.columns[
                self.sim_data_Chiller2.columns.str.contains("Chiller Evaporator Cooling Rate")])]
        self.sim_data_Chiller2_Power = self.sim_data_Chiller2[(
            self.sim_data_Chiller2.columns[
                self.sim_data_Chiller2.columns.str.contains("Chiller Electric Power")])]


        # ====================== FAN POWERs ====================================
        self.sim_data_Fan_Powers = self.data_raw[
            list(columnsList[(columnsList.str.endswith("Fan Electric Power [W](TimeStep)"))])]
        # ====================== CoolingTower1
        self.sim_data_Fan_Power_CoolTower1 =  self.sim_data_Fan_Powers[(
            self.sim_data_Fan_Powers.columns[
                self.sim_data_Fan_Powers.columns.str.contains("TOWERWATERSYS COOLTOWER 1")])]
        # ====================== CoolingTower2
        self.sim_data_Fan_Power_CoolTower2 = self.sim_data_Fan_Powers[(
            self.sim_data_Fan_Powers.columns[
                self.sim_data_Fan_Powers.columns.str.startswith("TOWERWATERSYS COOLTOWER 2")])]

        # >>>>>> CAV BASEMENT
        self.sim_data_CAV_Power_Basement = self.sim_data_Fan_Powers[(
            self.sim_data_Fan_Powers.columns[
                self.sim_data_Fan_Powers.columns.str.contains("CAV_BAS FAN")])]
        # >>>>>>> VAV BOTTOM
        self.sim_data_VAV_Power_Bottom = self.sim_data_Fan_Powers[(
            self.sim_data_Fan_Powers.columns[
                self.sim_data_Fan_Powers.columns.str.contains("VAV_BOT WITH REHEAT FAN")])]
        # >>>>>>> VAV MID
        self.sim_data_VAV_Power_Mid = self.sim_data_Fan_Powers[(
            self.sim_data_Fan_Powers.columns[
                self.sim_data_Fan_Powers.columns.str.contains("VAV_MID WITH REHEAT FAN")])]
        # >>>>>>> VAV TOP
        self.sim_data_VAV_Power_Top = self.sim_data_Fan_Powers[(
            self.sim_data_Fan_Powers.columns[
                self.sim_data_Fan_Powers.columns.str.contains("VAV_TOP WITH REHEAT FAN")])]

        # ===================== MASS FLOW ======================================
        self.sim_data_MassFlows = self.data_raw[
            list(columnsList[(columnsList.str.endswith("System Node Mass Flow Rate [kg/s](TimeStep)"))])]
        # >> BASEMENT <<
        self.sim_data_MassFlow_Basement_CAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("BASEMENT")])]

        # >> BOTTOM FLOOR <<
        self.sim_data_MassFlow_Bottom_Core_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("CORE_BOTTOM")])]
        self.sim_data_MassFlow_Bottom_Zone1_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_BOT_ZN_1")])]
        self.sim_data_MassFlow_Bottom_Zone2_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_BOT_ZN_2")])]
        self.sim_data_MassFlow_Bottom_Zone3_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_BOT_ZN_3")])]
        self.sim_data_MassFlow_Bottom_Zone4_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_BOT_ZN_4")])]

        # >> MID FLOOR <<
        self.sim_data_MassFlow_Mid_Core_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("CORE_MID")])]
        self.sim_data_MassFlow_Mid_Zone1_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_MID_ZN_1")])]
        self.sim_data_MassFlow_Mid_Zone2_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_MID_ZN_2")])]
        self.sim_data_MassFlow_Mid_Zone3_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_MID_ZN_3")])]
        self.sim_data_MassFlow_Mid_Zone4_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_MID_ZN_4")])]

        # >> TOP FLOOR <<
        self.sim_data_MassFlow_Top_Core_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("CORE_TOP")])]
        self.sim_data_MassFlow_Top_Zone1_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_TOP_ZN_1")])]
        self.sim_data_MassFlow_Top_Zone2_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_TOP_ZN_2")])]
        self.sim_data_MassFlow_Top_Zone3_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_TOP_ZN_3")])]
        self.sim_data_MassFlow_Top_Zone4_VAV = self.sim_data_MassFlows[
            (self.sim_data_MassFlows.columns[self.sim_data_MassFlows.columns.str.contains("PERIMETER_TOP_ZN_4")])]

        # ===================== INTERNAL LOADS ======================================
        self.sim_data_InternalLoads = self.data_raw[
            list(columnsList[(columnsList.str.endswith("Zone Total Internal Total Heating Rate [W](TimeStep)"))])]
        # >>> BASEMENT <<<<<<<<<
        self.sim_data_Internal_Load_Basement = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[self.sim_data_InternalLoads.columns.str.startswith("BASEMENT")])]
        # >> BOTTOM FLOOR <<
        self.sim_data_Internal_Load_Bottom_Core = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[self.sim_data_InternalLoads.columns.str.contains("CORE_BOTTOM")])]
        self.sim_data_Internal_Load_Bottom_Zone1 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_BOT_ZN_1")])]
        self.sim_data_Internal_Load_Bottom_Zone2 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_BOT_ZN_2")])]
        self.sim_data_Internal_Load_Bottom_Zone3 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_BOT_ZN_3")])]
        self.sim_data_Internal_Load_Bottom_Zone4 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_BOT_ZN_4")])]

        # >> MID FLOOR <<
        self.sim_data_Internal_Load_Mid_Core = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[self.sim_data_InternalLoads.columns.str.contains("CORE_MID")])]
        self.sim_data_Internal_Load_Mid_Zone1 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_MID_ZN_1")])]
        self.sim_data_Internal_Load_Mid_Zone2 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_MID_ZN_2")])]
        self.sim_data_Internal_Load_Mid_Zone3 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_MID_ZN_3")])]
        self.sim_data_Internal_Load_Mid_Zone4 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_MID_ZN_4")])]

        # >> TOP FLOOR <<
        self.sim_data_Internal_Load_Top_Core = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[self.sim_data_InternalLoads.columns.str.contains("CORE_TOP")])]
        self.sim_data_Internal_Load_Top_Zone1 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_TOP_ZN_1")])]
        self.sim_data_Internal_Load_Top_Zone2 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_TOP_ZN_2")])]
        self.sim_data_Internal_Load_Top_Zone3 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_TOP_ZN_3")])]
        self.sim_data_Internal_Load_Top_Zone4 = self.sim_data_InternalLoads[
            (self.sim_data_InternalLoads.columns[
                self.sim_data_InternalLoads.columns.str.contains("PERIMETER_TOP_ZN_4")])]

        # ------------ HVAC SCHEDULE ---------------
        self.sim_data_HVACSchedule = self.data_raw[list(
            columnsList[(columnsList.str.endswith("Availability Manager Night Cycle Control Status [](TimeStep)"))])]
        # >> BOTTOM FLOOR <<
        self.sim_data_HVAC_Availability_Bottom = (2 - self.sim_data_HVACSchedule[(self.sim_data_HVACSchedule.columns[ self.sim_data_HVACSchedule.columns.str.contains("VAV_BOT")])])/2 # I tried making this as a 1-0 on/off schedule, even though there are values here like 0.25 0.5 etc.
        # >> MID FLOOR <<
        self.sim_data_HVAC_Availability_Mid = (2 - self.sim_data_HVACSchedule[(self.sim_data_HVACSchedule.columns[ self.sim_data_HVACSchedule.columns.str.contains("VAV_MID")])])/2 # I tried making this as a 1-0 on/off schedule, even though there are values here like 0.25 0.5 etc.
        # >> TOP FLOOR
        self.sim_data_HVAC_Availability_Top = (2 - self.sim_data_HVACSchedule[(self.sim_data_HVACSchedule.columns[ self.sim_data_HVACSchedule.columns.str.contains("VAV_MID")])])/2 # I tried making this as a 1-0 on/off schedule, even though there are values here like 0.25 0.5 etc.

        # ======= PUMP POWER ========
        self.sim_data_Pumps = self.data_raw[list(columnsList[(columnsList.str.contains("PUMP"))])]
        # >>>>>>> Primary Pump <<<<<<<<<<<
        self.sim_data_Pump_Power_Primary = self.sim_data_Pumps[(self.sim_data_Pumps.columns[self.sim_data_Pumps.columns.str.contains("COOLSYS1 PUMP:Pump Electric Power")])]
        # >>>>>>> Secondary Pump <<<<<<<<<
        self.sim_data_Pump_Power_Secondary = self.sim_data_Pumps[(self.sim_data_Pumps.columns[self.sim_data_Pumps.columns.str.contains("COOLSYS1 PUMP SECONDARY")])]


        # ============ TOTAL POWERS ==================================================
        self.sim_data_Total_Chiller_Power = pd.DataFrame(self.sim_data_Chiller1_Power.values + self.sim_data_Chiller2_Power.values)
        self.sim_data_Total_Chiller_Power.columns = ['TOTAL_CHILLERS_POWER_E+']

        self.sim_data_Total_Fan_Power = pd.DataFrame(self.sim_data_VAV_Power_Mid.values
                                      + self.sim_data_VAV_Power_Top.values
                                      + self.sim_data_VAV_Power_Bottom.values
                                      + self.sim_data_CAV_Power_Basement.values
                                      + self.sim_data_Fan_Power_CoolTower1.values
                                      + self.sim_data_Fan_Power_CoolTower2.values)
        self.sim_data_Total_Fan_Power.columns = ['TOTAL_FANS_POWER_E+']
        self.sim_data_Total_Pump_Power = pd.DataFrame(self.sim_data_Pump_Power_Secondary.values + self.sim_data_Pump_Power_Primary.values)
        self.sim_data_Total_Pump_Power.columns = ['TOTAL_PUMP_POWER_E+']

    def get_coefficients(self,saving):
        # ============ Wet bulb temperature =======================================

        df = process_data.process_bicubic_Twetbulb(
            self.sim_data_Temperature_WetBulb,
            self.sim_data_Temperature_Outside,
            self.sim_data_Air_Humidity_Ratio,
            self.sim_data_Temperature_WetBulb.columns[0])

        self.coefficient_Twetbulb = regress.get_Twetbulb_bicubic_coefficients(
            self.sim_data_Temperature_WetBulb, df)

        # # ============ MassFlows =======================================
        # bottom_core_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Core_VAV, self.sim_data_ZoneTemperature_Bottom_Core,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Core,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Core,
            self.sim_data_HVAC_Availability_Bottom)
        self.coefficients_MassFlow_Bottom_Core_VAV = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Bottom_Core_VAV.columns[0])
       # bottom_zone_1_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Zone1_VAV, self.sim_data_ZoneTemperature_Bottom_Zone1,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone1,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Zone1,
            self.sim_data_HVAC_Availability_Bottom)
        self.coefficients_MassFlow_Bottom_Zone1 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4,self.sim_data_MassFlow_Bottom_Zone1_VAV.columns[0])
        # bottom_zone_2_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Zone2_VAV, self.sim_data_ZoneTemperature_Bottom_Zone2,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone2,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Zone2,
            self.sim_data_HVAC_Availability_Bottom)
        self.coefficients_MassFlow_Bottom_Zone2 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Bottom_Zone2_VAV.columns[0])
        # bottom_zone_3_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Zone3_VAV, self.sim_data_ZoneTemperature_Bottom_Zone3,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone3,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Zone3,
            self.sim_data_HVAC_Availability_Bottom)
        self.coefficients_MassFlow_Bottom_Zone3 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Bottom_Zone3_VAV.columns[0])

        # bottom_Zone_4_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Zone4_VAV, self.sim_data_ZoneTemperature_Bottom_Zone4,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone4,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Zone4,
            self.sim_data_HVAC_Availability_Bottom)
        self.coefficients_MassFlow_Bottom_Zone4 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Bottom_Zone4_VAV.columns[0])

        # mid_core_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Core_VAV, self.sim_data_ZoneTemperature_Mid_Core,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Core,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Core,
            self.sim_data_HVAC_Availability_Mid)
        self.coefficients_MassFlow_Mid_Core_VAV = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Mid_Core_VAV.columns[0])
        # mid_zone_1_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Zone1_VAV, self.sim_data_ZoneTemperature_Mid_Zone1,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Zone1,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Zone1,
            self.sim_data_HVAC_Availability_Mid)
        self.coefficients_MassFlow_Mid_Zone1 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Mid_Zone1_VAV.columns[0])

        # mid_zone_2_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Zone2_VAV, self.sim_data_ZoneTemperature_Mid_Zone2,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Zone2,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Zone2,
            self.sim_data_HVAC_Availability_Mid)
        self.coefficients_MassFlow_Mid_Zone2 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Mid_Zone2_VAV.columns[0])

        # mid_zone_3_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Zone3_VAV, self.sim_data_ZoneTemperature_Mid_Zone3,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Zone3,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Zone3,
            self.sim_data_HVAC_Availability_Mid)
        self.coefficients_MassFlow_Mid_Zone3 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Mid_Zone3_VAV.columns[0])

        # mid_Zone_4_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Zone4_VAV, self.sim_data_ZoneTemperature_Mid_Zone4,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Zone4,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Zone4,
            self.sim_data_HVAC_Availability_Mid)
        self.coefficients_MassFlow_Mid_Zone4 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Mid_Zone4_VAV.columns[0])

        # top_core_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Core_VAV, self.sim_data_ZoneTemperature_Top_Core,
            self.sim_data_ZoneTemperature_Setpoint_Top_Core,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Core,
            self.sim_data_HVAC_Availability_Top)
        self.coefficients_MassFlow_Top_Core_VAV = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Top_Core_VAV.columns[0])

        # top_zone_1_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Zone1_VAV, self.sim_data_ZoneTemperature_Top_Zone1,
            self.sim_data_ZoneTemperature_Setpoint_Top_Zone1,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Zone1,
            self.sim_data_HVAC_Availability_Top)
        self.coefficients_MassFlow_Top_Zone1 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Top_Zone1_VAV.columns[0])

        # top_zone_2_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Zone2_VAV, self.sim_data_ZoneTemperature_Top_Zone2,
            self.sim_data_ZoneTemperature_Setpoint_Top_Zone2,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Zone2,
            self.sim_data_HVAC_Availability_Top)
        self.coefficients_MassFlow_Top_Zone2 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Top_Zone2_VAV.columns[0])

        # top_zone_3_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Zone3_VAV, self.sim_data_ZoneTemperature_Top_Zone3,
            self.sim_data_ZoneTemperature_Setpoint_Top_Zone3,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Zone3,
            self.sim_data_HVAC_Availability_Top)
        self.coefficients_MassFlow_Top_Zone3 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Top_Zone3_VAV.columns[0])

        # top_Zone_4_VAV
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Zone4_VAV, self.sim_data_ZoneTemperature_Top_Zone4,
            self.sim_data_ZoneTemperature_Setpoint_Top_Zone4,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Zone4,
            self.sim_data_HVAC_Availability_Top)
        self.coefficients_MassFlow_Top_Zone4 = \
            regress.get_mass_flow_coefficients(y, x1, x2, x3, x4, self.sim_data_MassFlow_Top_Zone4_VAV.columns[0])

        # Collect Floor MassFlows
        # Bottom
        self.sim_data_MassFlow_Bottom_Floor = pd.DataFrame(self.sim_data_MassFlow_Bottom_Core_VAV.values  \
                                            + self.sim_data_MassFlow_Bottom_Zone1_VAV.values \
                                            + self.sim_data_MassFlow_Bottom_Zone2_VAV.values  \
                                            + self.sim_data_MassFlow_Bottom_Zone3_VAV.values  \
                                            + self.sim_data_MassFlow_Bottom_Zone4_VAV.values )
        self.sim_data_MassFlow_Bottom_Floor.columns = ['MASS_FLOWS_BOTTOM_VAV']

        y, df = process_data.process_vav_floor_data_for_regression(self.sim_data_VAV_Power_Bottom,
                                                                   self.sim_data_MassFlow_Bottom_Floor)
        self.coefficients_VAV_Power_Bottom_Floor = regress.get_VAV_Power_Coefficient(y, df)

        # Top
        self.sim_data_MassFlow_Top_Floor = pd.DataFrame(self.sim_data_MassFlow_Top_Core_VAV.values  \
                                                  + self.sim_data_MassFlow_Top_Zone1_VAV.values  \
                                                  + self.sim_data_MassFlow_Top_Zone2_VAV.values  \
                                                  + self.sim_data_MassFlow_Top_Zone3_VAV.values  \
                                                  + self.sim_data_MassFlow_Top_Zone4_VAV.values )
        self.sim_data_MassFlow_Top_Floor.columns = ['MASS_FLOWS_TOP_VAV']

        y, df = process_data.process_vav_floor_data_for_regression(self.sim_data_VAV_Power_Top,
                                                                   self.sim_data_MassFlow_Top_Floor)
        self.coefficients_VAV_Power_Top = regress.get_VAV_Power_Coefficient(y, df)

        # Mid
        self.sim_data_MassFlow_Mid_Floor = pd.DataFrame(self.sim_data_MassFlow_Mid_Core_VAV.values  \
                                               + self.sim_data_MassFlow_Mid_Zone1_VAV.values  \
                                               + self.sim_data_MassFlow_Mid_Zone2_VAV.values  \
                                               + self.sim_data_MassFlow_Mid_Zone3_VAV.values  \
                                               + self.sim_data_MassFlow_Mid_Zone4_VAV.values )
        self.sim_data_MassFlow_Mid_Floor.columns = ['MASS_FLOWS_MID_VAV']
        y, df = process_data.process_vav_floor_data_for_regression(self.sim_data_VAV_Power_Mid,
                                                                   self.sim_data_MassFlow_Mid_Floor)
        self.coefficients_VAV_Power_Mid = regress.get_VAV_Power_Coefficient(y, df)

        y, df = process_data.process_basement_power_for_regression(
            self.sim_data_CAV_Power_Basement, self.sim_data_Internal_Load_Basement,
            self.sim_data_ZoneTemperature_Basement)
        self.coefficients_CAV_Power_Basement = regress.get_basement_cav_coefficient(y, df)

        # FAN POWERS
        self.sim_data_CAV_VAV_Fan_Power = pd.DataFrame(self.sim_data_CAV_Power_Basement.values \
                                                       + self.sim_data_VAV_Power_Bottom.values \
                                                       + self.sim_data_VAV_Power_Mid.values \
                                                       + self.sim_data_VAV_Power_Top.values)
        self.sim_data_CAV_VAV_Fan_Power.columns = ['Total_VAV_CAV_FAN_POWER_E+']


        # ============ Evaporator Load =======================
        # >>>>>>>>>>>> Evaporator 1 <<<<<<<<<<<<<<<<<

        y, df = process_data.process_evaporator_load_chiller_for_regression(
            self.sim_data_Evaporator_Load_Chiller1, self.sim_data_CAV_VAV_Fan_Power,
            self.sim_data_Temperature_WetBulb)
        self.coefficients_Evaporator_Load_Chiller1 = regress.get_evaporator_load_chiller(y, df)

        # >>>>>>>>>>>> Evaporator 2 <<<<<<<<<<<<<<<<<
        y, df = process_data.process_evaporator_load_chiller_for_regression(
            self.sim_data_Evaporator_Load_Chiller2, self.sim_data_CAV_VAV_Fan_Power,
            self.sim_data_Temperature_WetBulb)
        self.coefficients_Evaporator_Load_Chiller2 = regress.get_evaporator_load_chiller(y, df)

        # ============ Condenser Leaving Temp =======================
        # >>>>>> Condenser 1 <<<<<<<<
        y, df = process_data.process_condenser1_leaving_temp(
            self.sim_data_Condenser_Leaving_Temperature_Chiller1,
            self.sim_data_Evaporator_Load_Chiller1 / self.sim_data_Evaporator_Load_Chiller1.max(axis=0),
            self.sim_data_Temperature_WetBulb / self.sim_data_Temperature_WetBulb.max(axis=0))
        self.coefficients_Condenser_Leaving_Temperature_Chiller1 = regress.get_condenser_leaving_temp(y, df)

        # >>>>>> Condenser 2 <<<<<<<<
        y, df = process_data.process_condenser2_leaving_temp(
            self.sim_data_Condenser_Leaving_Temperature_Chiller2,
            self.sim_data_Evaporator_Load_Chiller2 / self.sim_data_Evaporator_Load_Chiller2.max(axis=0),
            self.sim_data_Temperature_WetBulb / self.sim_data_Temperature_WetBulb.max(axis=0))
        self.coefficients_Condenser_Leaving_Temperature_Chiller2 = regress.get_condenser_leaving_temp(y, df)

        # ========= COOLING TOWER FAN ============
        # >>>>>>>>>>> Tower 1 <<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_cooling_tower_fan(
            self.sim_data_Fan_Power_CoolTower1,
            self.sim_data_Chiller1_Power,
            self.sim_data_Temperature_WetBulb)
        self.coefficients_Fan_Power_CoolTower1 = regress.get_cooling_fan_power(y, df)

        # >>>>>>>>>>> Tower 2 <<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_cooling_tower_fan(
            self.sim_data_Fan_Power_CoolTower2,
            self.sim_data_Chiller2_Power,
            self.sim_data_Temperature_WetBulb)
        self.coefficients_Fan_Power_CoolTower2 = regress.get_cooling_fan_power(y, df)

        # ========= Pump Power ============
        # >>>>>>>>>>> Primary <<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_pump_power(
            self.sim_data_Pump_Power_Primary,
            self.sim_data_Chiller1_Power,
            self.sim_data_Temperature_WetBulb)
        self.coefficients_Pump_Power_Primary = regress.get_pump_power(y, df)

        # >>>>>>>>>>> Secondary <<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_pump_power(
            self.sim_data_Pump_Power_Secondary,
            self.sim_data_Chiller1_Power,
            self.sim_data_Temperature_WetBulb)
        self.coefficients_Pump_Power_Secondary = regress.get_pump_power(y, df)

        # if saving == 1:
        #     save.save_co(self.coefficient_Twetbulb, 'coefficient_Twetbulb')
        #     save.save_co(self.coefficients_MassFlow_Bottom_Core_VAV, 'coefficients_MassFlow_Bottom_Core_VAV')
        #     save.save_co(self.coefficients_MassFlow_Bottom_Zone1, 'coefficients_MassFlow_Bottom_Zone1')
        #     save.save_co(self.coefficients_MassFlow_Bottom_Zone2, 'coefficients_MassFlow_Bottom_Zone2')
        #     save.save_co(self.coefficients_MassFlow_Bottom_Zone3, 'coefficients_MassFlow_Bottom_Zone3')
        #     save.save_co(self.coefficients_MassFlow_Bottom_Zone4, 'coefficients_MassFlow_Bottom_Zone4')
        #     save.save_co(self.coefficients_MassFlow_Mid_Core_VAV, 'coefficients_MassFlow_Mid_Core_VAV')
        #     save.save_co(self.coefficients_MassFlow_Mid_Zone1, 'coefficients_MassFlow_Mid_Zone1')
        #     save.save_co(self.coefficients_MassFlow_Mid_Zone2, 'coefficients_MassFlow_Mid_Zone2')
        #     save.save_co(self.coefficients_MassFlow_Mid_Zone3, 'coefficients_MassFlow_Mid_Zone3')
        #     save.save_co(self.coefficients_MassFlow_Mid_Zone4, 'coefficients_MassFlow_Mid_Zone4')
        #     save.save_co(self.coefficients_MassFlow_Top_Core_VAV, 'coefficients_MassFlow_Top_Core_VAV')
        #     save.save_co(self.coefficients_MassFlow_Top_Zone2, 'coefficients_MassFlow_Top_Zone2')
        #     save.save_co(self.coefficients_MassFlow_Top_Zone3, 'coefficients_MassFlow_Top_Zone3')
        #     save.save_co(self.coefficients_MassFlow_Top_Zone4, 'coefficients_MassFlow_Top_Zone4')
        #     save.save_co(self.coefficients_VAV_Power_Bottom_Floor, 'coefficients_VAV_Power_Bottom_Floor')
        #     save.save_co(self.coefficients_VAV_Power_Top, 'coefficients_VAV_Power_Top')
        #     save.save_co(self.coefficients_CAV_Power_Basement, 'coefficients_CAV_Power_Basement')
        #     save.save_co(self.coefficients_Evaporator_Load_Chiller1, 'coefficients_Evaporator_Load_Chiller1')
        #     save.save_co(self.coefficients_Evaporator_Load_Chiller2, 'coefficients_Evaporator_Load_Chiller2')
        #     save.save_co(self.coefficients_Condenser_Leaving_Temperature_Chiller2, 'coefficients_Condenser_Leaving_Temperature_Chiller2')
        #     save.save_co(self.coefficients_Fan_Power_CoolTower1, 'coefficients_Fan_Power_CoolTower1')
        #     save.save_co(self.coefficients_Fan_Power_CoolTower2, 'coefficients_Fan_Power_CoolTower2')
        #     save.save_co(self.coefficients_Pump_Power_Primary, 'coefficients_Pump_Power_Primary')
        #     save.save_co(self.coefficients_Pump_Power_Secondary, 'coefficients_Pump_Power_Secondary')

    def get_approximations(self, scenario, plot_approximation):
        # for scenario 2, we load, for 1 we just use the saved coefficients
        if scenario == 2:
            self.coefficient_Twetbulb = pd.read_pickle(os.path.join("./coefficients", 'coefficient_Twetbulb'))
            self.coefficients_MassFlow_Bottom_Core_VAV = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Bottom_Core_VAV'))
            self.coefficients_MassFlow_Bottom_Zone1 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Bottom_Zone1'))
            self.coefficients_MassFlow_Bottom_Zone2 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Bottom_Zone2'))
            self.coefficients_MassFlow_Bottom_Zone3 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Bottom_Zone3'))
            self.coefficients_MassFlow_Bottom_Zone4 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Bottom_Zone4'))
            self.coefficients_MassFlow_Mid_Core_VAV = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Mid_Core_VAV'))
            self.coefficients_MassFlow_Mid_Zone1 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Mid_Zone1'))
            self.coefficients_MassFlow_Mid_Zone2 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Mid_Zone2'))
            self.coefficients_MassFlow_Mid_Zone3 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Mid_Zone3'))
            self.coefficients_MassFlow_Mid_Zone4 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Mid_Zone4'))
            self.coefficients_MassFlow_Top_Core_VAV = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Top_Core_VAV'))
            self.coefficients_MassFlow_Top_Zone1 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Top_Zone1'))
            self.coefficients_MassFlow_Top_Zone2 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Top_Zone2'))
            self.coefficients_MassFlow_Top_Zone3 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Top_Zone3'))
            self.coefficients_MassFlow_Top_Zone4 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_MassFlow_Top_Zone4'))
            self.coefficients_VAV_Power_Bottom_Floor = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_VAV_Power_Bottom_Floor'))
            self.coefficients_VAV_Power_Top = pd.read_pickle(os.path.join("./coefficients", 'coefficients_VAV_Power_Top'))
            self.coefficients_VAV_Power_Mid = pd.read_pickle(os.path.join("./coefficients", 'coefficients_VAV_Power_Mid'))
            self.coefficients_CAV_Power_Basement = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_CAV_Power_Basement'))
            self.coefficients_Evaporator_Load_Chiller1 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_Evaporator_Load_Chiller1'))
            self.coefficients_Evaporator_Load_Chiller2 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_Evaporator_Load_Chiller2'))
            self.coefficients_Condenser_Leaving_Temperature_Chiller1 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_Condenser_Leaving_Temperature_Chiller1'))
            self.coefficients_Condenser_Leaving_Temperature_Chiller2 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_Condenser_Leaving_Temperature_Chiller2'))
            self.coefficients_Fan_Power_CoolTower1 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_Fan_Power_CoolTower1'))
            self.coefficients_Fan_Power_CoolTower1 = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_Fan_Power_CoolTower1'))
            self.coefficients_Pump_Power_Primary = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_Pump_Power_Primary'))
            self.coefficients_Pump_Power_Secondary = pd.read_pickle(
                os.path.join("./coefficients", 'coefficients_Pump_Power_Secondary'))
        # ================= TwetBulb =================================================
        data = process_data.process_bicubic_Twetbulb(
            self.sim_data_Temperature_WetBulb,
            self.sim_data_Temperature_Outside,
            self.sim_data_Air_Humidity_Ratio,
            self.sim_data_Temperature_WetBulb.columns[0])
        self.approx_Twet_bulb = approximate.approximate_bicubic(data, self.coefficient_Twetbulb)
        self.approx_Twet_bulb = pd.DataFrame(self.approx_Twet_bulb)
        self.approx_Twet_bulb.columns = ['Twet_bulb_Approx']
        # plotting.plot_approximation(self.sim_data_Temperature_WetBulb, self.approx_Twet_bulb,
        #                                  self.sim_data_Temperature_WetBulb.columns[0])


        # ================= Mass Flows =================================================

        # ============ BOTTOM FLOOR ====================================
        # >>>>>> CORE <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Core_VAV, self.sim_data_ZoneTemperature_Bottom_Core,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Core,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Core,
            self.sim_data_HVAC_Availability_Bottom)
        self.approx_MassFlow_Bottom_Core_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Bottom_Core_VAV,
                                                                                  self.sim_data_MassFlow_Bottom_Core_VAV.columns[0])

        self.approx_MassFlow_Bottom_Core_VAV = np.insert(self.approx_MassFlow_Bottom_Core_VAV, 0, self.sim_data_MassFlow_Bottom_Core_VAV.values[0])
        # plotting.plot_approximation(y, self.approx_MassFlow_Bottom_Core_VAV,
        #                                  self.sim_data_MassFlow_Bottom_Core_VAV.columns[0])

        # >>>>>> ZONE1 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Zone1_VAV, self.sim_data_ZoneTemperature_Bottom_Zone1,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone1,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Zone1,
            self.sim_data_HVAC_Availability_Bottom)
        self.approx_MassFlow_Bottom_Zone1_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Bottom_Zone1,
                                                                                  self.sim_data_MassFlow_Bottom_Zone1_VAV.columns[0])
        self.approx_MassFlow_Bottom_Zone1_VAV = np.insert(self.approx_MassFlow_Bottom_Zone1_VAV, 0, self.sim_data_MassFlow_Bottom_Zone1_VAV.values[0])

        # >>>>>> ZONE2 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Zone2_VAV, self.sim_data_ZoneTemperature_Bottom_Zone2,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone2,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Zone2,
            self.sim_data_HVAC_Availability_Bottom)
        self.approx_MassFlow_Bottom_Zone2_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Bottom_Zone2,
                                                                                  self.sim_data_MassFlow_Bottom_Zone2_VAV.columns[
                                                                                      0])
        self.approx_MassFlow_Bottom_Zone2_VAV = np.insert(self.approx_MassFlow_Bottom_Zone2_VAV, 0,
                                                         self.sim_data_MassFlow_Bottom_Zone2_VAV.values[0])

        # >>>>>> Zone3 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Zone3_VAV, self.sim_data_ZoneTemperature_Bottom_Zone3,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone3,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Zone3,
            self.sim_data_HVAC_Availability_Bottom)
        self.approx_MassFlow_Bottom_Zone3_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Bottom_Zone3,
                                                                                  self.sim_data_MassFlow_Bottom_Zone3_VAV.columns[
                                                                                      0])
        self.approx_MassFlow_Bottom_Zone3_VAV = np.insert(self.approx_MassFlow_Bottom_Zone3_VAV, 0,
                                                         self.sim_data_MassFlow_Bottom_Zone3_VAV.values[0])

        # >>>>>> Zone4 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Bottom_Zone4_VAV, self.sim_data_ZoneTemperature_Bottom_Zone4,
            self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone4,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Bottom_Zone4,
            self.sim_data_HVAC_Availability_Bottom)
        self.approx_MassFlow_Bottom_Zone4_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Bottom_Zone4,
                                                                                  self.sim_data_MassFlow_Bottom_Zone4_VAV.columns[
                                                                                      0])
        self.approx_MassFlow_Bottom_Zone4_VAV = np.insert(self.approx_MassFlow_Bottom_Zone4_VAV, 0,
                                                         self.sim_data_MassFlow_Bottom_Zone4_VAV.values[0])

        # BOTTOM FLOOR VAV MASS FLOWS
        self.approx_MassFlow_Bottom_Floor = self.approx_MassFlow_Bottom_Core_VAV \
                                            + self.approx_MassFlow_Bottom_Zone1_VAV \
                                            + self.approx_MassFlow_Bottom_Zone2_VAV \
                                            + self.approx_MassFlow_Bottom_Zone3_VAV \
                                            + self.approx_MassFlow_Bottom_Zone4_VAV

        if scenario == 2:
            self.approx_MassFlow_Bottom_Floor = self.approx_MassFlow_Bottom_Floor - self.coefficients_MassFlow_Bottom_Core_VAV['x1'] * (
                        24 * np.ones((1488)) - np.array(self.sim_data_ZoneTemperature_Setpoint_Bottom_Core.values.T)) \
            - self.coefficients_MassFlow_Bottom_Zone1['x1'] * (
                        24 * np.ones((1488)) - np.array(self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone1.values.T)) \
            - self.coefficients_MassFlow_Bottom_Zone2['x1'] * (
                        24 * np.ones((1488)) - np.array(self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone2.values.T)) \
            - self.coefficients_MassFlow_Bottom_Zone3['x1'] * (
                        24 * np.ones((1488)) - np.array(self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone3.values.T)) \
            - self.coefficients_MassFlow_Bottom_Zone4['x1'] * (
                        24 * np.ones((1488)) - np.array(self.sim_data_ZoneTemperature_Setpoint_Bottom_Zone4.values.T))
        self.approx_MassFlow_Bottom_Floor[self.approx_MassFlow_Bottom_Floor> self.parameters_bottom_vav_max_flow] = self.parameters_bottom_vav_max_flow
        self.approx_MassFlow_Bottom_Floor[self.approx_MassFlow_Bottom_Floor< 0] = 0
        self.approx_MassFlow_Bottom_Floor = pd.DataFrame(self.approx_MassFlow_Bottom_Floor.T)
        self.approx_MassFlow_Bottom_Floor.columns = ['MASS_FLOWS_BOTTOM_VAV_Approx']


        # plotting.plot_approximation(self.sim_data_MassFlow_Bottom_Floor, self.approx_MassFlow_Bottom_Floor,
        #                             self.sim_data_MassFlow_Bottom_Floor.columns[0])


        # Collect all actual VAVs for the floor
        # ============ MID FLOOR ====================================
        # >>>>>> CORE <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Core_VAV, self.sim_data_ZoneTemperature_Mid_Core,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Core,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Core,
            self.sim_data_HVAC_Availability_Mid)
        self.approx_MassFlow_Mid_Core_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Mid_Core_VAV,
                                                                                  self.sim_data_MassFlow_Mid_Core_VAV.columns[
                                                                                      0])
        self.approx_MassFlow_Mid_Core_VAV = np.insert(self.approx_MassFlow_Mid_Core_VAV, 0,
                                                         self.sim_data_MassFlow_Mid_Core_VAV.values[0])

        # >>>>>> ZONE1 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Zone1_VAV, self.sim_data_ZoneTemperature_Mid_Zone1,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Zone1,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Zone1,
            self.sim_data_HVAC_Availability_Mid)
        self.approx_MassFlow_Mid_Zone1_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Mid_Zone1,
                                                                                  self.sim_data_MassFlow_Mid_Zone1_VAV.columns[
                                                                                      0])
        self.approx_MassFlow_Mid_Zone1_VAV = np.insert(self.approx_MassFlow_Mid_Zone1_VAV, 0,
                                                         self.sim_data_MassFlow_Mid_Zone1_VAV.values[0])

        # >>>>>> ZONE2 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Zone2_VAV, self.sim_data_ZoneTemperature_Mid_Zone2,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Zone2,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Zone2,
            self.sim_data_HVAC_Availability_Mid)
        self.approx_MassFlow_Mid_Zone2_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Mid_Zone2,
                                                                                  self.sim_data_MassFlow_Mid_Zone2_VAV.columns[
                                                                                      0])
        self.approx_MassFlow_Mid_Zone2_VAV = np.insert(self.approx_MassFlow_Mid_Zone2_VAV, 0,
                                                         self.sim_data_MassFlow_Mid_Zone2_VAV.values[0])

        # >>>>>> Zone3 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Zone3_VAV, self.sim_data_ZoneTemperature_Mid_Zone3,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Zone3,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Zone3,
            self.sim_data_HVAC_Availability_Mid)
        self.approx_MassFlow_Mid_Zone3_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Mid_Zone3,
                                                                                  self.sim_data_MassFlow_Mid_Zone3_VAV.columns[
                                                                                      0])

        self.approx_MassFlow_Mid_Zone3_VAV = np.insert(self.approx_MassFlow_Mid_Zone3_VAV, 0,
                                                         self.sim_data_MassFlow_Mid_Zone3_VAV.values[0])

        # >>>>>> Zone4 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Mid_Zone4_VAV, self.sim_data_ZoneTemperature_Mid_Zone4,
            self.sim_data_ZoneTemperature_Setpoint_Mid_Zone4,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Mid_Zone4,
            self.sim_data_HVAC_Availability_Mid)
        self.approx_MassFlow_Mid_Zone4_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                  self.coefficients_MassFlow_Mid_Zone4,
                                                                                  self.sim_data_MassFlow_Mid_Zone4_VAV.columns[
                                                                                      0])
        self.approx_MassFlow_Mid_Zone4_VAV = np.insert(self.approx_MassFlow_Mid_Zone4_VAV, 0,
                                                         self.sim_data_MassFlow_Mid_Zone4_VAV.values[0])

        # MID FLOOR VAV MASS FLOWS
        self.approx_MassFlow_Mid_Floor = self.approx_MassFlow_Mid_Core_VAV \
                                            + self.approx_MassFlow_Mid_Zone1_VAV \
                                            + self.approx_MassFlow_Mid_Zone2_VAV \
                                            + self.approx_MassFlow_Mid_Zone3_VAV \
                                            + self.approx_MassFlow_Mid_Zone4_VAV

        if scenario == 2:
            self.approx_MassFlow_Mid_Floor = self.approx_MassFlow_Mid_Floor - \
                                                10*self.coefficients_MassFlow_Mid_Core_VAV['x1'] * (
                                                        24 * np.ones((1488)) - np.array(
                                                    self.sim_data_ZoneTemperature_Setpoint_Mid_Core.values.T)) \
                                                - 10*self.coefficients_MassFlow_Mid_Zone1['x1'] * (
                                                        24 * np.ones((1488)) - np.array(
                                                    self.sim_data_ZoneTemperature_Setpoint_Mid_Zone1.values.T)) \
                                                - 10*self.coefficients_MassFlow_Mid_Zone2['x1'] * (
                                                        24 * np.ones((1488)) - np.array(
                                                    self.sim_data_ZoneTemperature_Setpoint_Mid_Zone2.values.T)) \
                                                - 10*self.coefficients_MassFlow_Mid_Zone3['x1'] * (
                                                        24 * np.ones((1488)) - np.array(
                                                    self.sim_data_ZoneTemperature_Setpoint_Mid_Zone3.values.T)) \
                                                - 10*self.coefficients_MassFlow_Mid_Zone4['x1'] * (
                                                        24 * np.ones((1488)) - np.array(
                                                    self.sim_data_ZoneTemperature_Setpoint_Mid_Zone4.values.T))
        self.approx_MassFlow_Mid_Floor[
            self.approx_MassFlow_Mid_Floor > self.parameters_mid_vav_max_flow] = self.parameters_mid_vav_max_flow
        self.approx_MassFlow_Mid_Floor[self.approx_MassFlow_Mid_Floor < 0] = 0
        self.approx_MassFlow_Mid_Floor = pd.DataFrame(self.approx_MassFlow_Mid_Floor.T)
        self.approx_MassFlow_Mid_Floor.columns = ['MASS_FLOWS_Mid_VAV_Approx']

        # plotting.plot_approximation(self.sim_data_MassFlow_Mid_Floor, self.approx_MassFlow_Mid_Floor,
        #                             self.sim_data_MassFlow_Mid_Floor.columns[0])

        # ============ TOP FLOOR ====================================
        # >>>>>> CORE <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Core_VAV, self.sim_data_ZoneTemperature_Top_Core,
            self.sim_data_ZoneTemperature_Setpoint_Top_Core,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Core,
            self.sim_data_HVAC_Availability_Top)
        self.approx_MassFlow_Top_Core_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                               self.coefficients_MassFlow_Top_Core_VAV,
                                                                               self.sim_data_MassFlow_Top_Core_VAV.columns[
                                                                                   0])

        self.approx_MassFlow_Top_Core_VAV = np.insert(self.approx_MassFlow_Top_Core_VAV, 0,
                                                         self.sim_data_MassFlow_Top_Core_VAV.values[0])

        # >>>>>> ZONE1 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Zone1_VAV, self.sim_data_ZoneTemperature_Top_Zone1,
            self.sim_data_ZoneTemperature_Setpoint_Top_Zone1,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Zone1,
            self.sim_data_HVAC_Availability_Top)
        self.approx_MassFlow_Top_Zone1_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                self.coefficients_MassFlow_Top_Zone1,
                                                                                self.sim_data_MassFlow_Top_Zone1_VAV.columns[
                                                                                    0])
        self.approx_MassFlow_Top_Zone1_VAV = np.insert(self.approx_MassFlow_Top_Zone1_VAV, 0,
                                                         self.sim_data_MassFlow_Top_Zone1_VAV.values[0])

        # >>>>>> ZONE2 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Zone2_VAV, self.sim_data_ZoneTemperature_Top_Zone2,
            self.sim_data_ZoneTemperature_Setpoint_Top_Zone2,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Zone2,
            self.sim_data_HVAC_Availability_Top)
        self.approx_MassFlow_Top_Zone2_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                self.coefficients_MassFlow_Top_Zone2,
                                                                                self.sim_data_MassFlow_Top_Zone2_VAV.columns[
                                                                                    0])
        self.approx_MassFlow_Top_Zone2_VAV = np.insert(self.approx_MassFlow_Top_Zone2_VAV, 0,
                                                         self.sim_data_MassFlow_Top_Zone2_VAV.values[0])

        # >>>>>> Zone3 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Zone3_VAV, self.sim_data_ZoneTemperature_Top_Zone3,
            self.sim_data_ZoneTemperature_Setpoint_Top_Zone3,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Zone3,
            self.sim_data_HVAC_Availability_Top)
        self.approx_MassFlow_Top_Zone3_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                self.coefficients_MassFlow_Top_Zone3,
                                                                                self.sim_data_MassFlow_Top_Zone3_VAV.columns[
                                                                                    0])
        self.approx_MassFlow_Top_Zone3_VAV = np.insert(self.approx_MassFlow_Top_Zone3_VAV, 0,
                                                         self.sim_data_MassFlow_Top_Zone3_VAV.values[0])

        # >>>>>> Zone4 <<<<<<<<<<<<<<<<
        y, x1, x2, x3, x4 = process_data.process_mass_flow_data_for_regression(
            self.sim_data_MassFlow_Top_Zone4_VAV, self.sim_data_ZoneTemperature_Top_Zone4,
            self.sim_data_ZoneTemperature_Setpoint_Top_Zone4,
            self.sim_data_Temperature_Outside,
            self.sim_data_Internal_Load_Top_Zone4,
            self.sim_data_HVAC_Availability_Top)
        self.approx_MassFlow_Top_Zone4_VAV = approximate.approximate_mass_flows(x1, x2, x3, x4,
                                                                                self.coefficients_MassFlow_Top_Zone4,
                                                                                self.sim_data_MassFlow_Top_Zone4_VAV.columns[
                                                                                    0])
        self.approx_MassFlow_Top_Zone4_VAV = np.insert(self.approx_MassFlow_Top_Zone4_VAV, 0,
                                                         self.sim_data_MassFlow_Top_Zone4_VAV.values[0])

        # TOP FLOOR VAV MASS FLOWS
        self.approx_MassFlow_Top_Floor = self.approx_MassFlow_Top_Core_VAV \
                                         + self.approx_MassFlow_Top_Zone1_VAV \
                                         + self.approx_MassFlow_Top_Zone2_VAV \
                                         + self.approx_MassFlow_Top_Zone3_VAV \
                                         + self.approx_MassFlow_Top_Zone4_VAV

        if scenario == 2:
            self.approx_MassFlow_Top_Floor = self.approx_MassFlow_Top_Floor - \
                                             self.coefficients_MassFlow_Top_Core_VAV['x1'] * (
                                                     24 * np.ones((1488)) - np.array(
                                                 self.sim_data_ZoneTemperature_Setpoint_Top_Core.values.T)) \
                                             - self.coefficients_MassFlow_Top_Zone1['x1'] * (
                                                     24 * np.ones((1488)) - np.array(
                                                 self.sim_data_ZoneTemperature_Setpoint_Top_Zone1.values.T)) \
                                             - self.coefficients_MassFlow_Top_Zone2['x1'] * (
                                                     24 * np.ones((1488)) - np.array(
                                                 self.sim_data_ZoneTemperature_Setpoint_Top_Zone2.values.T)) \
                                             - self.coefficients_MassFlow_Top_Zone3['x1'] * (
                                                     24 * np.ones((1488)) - np.array(
                                                 self.sim_data_ZoneTemperature_Setpoint_Top_Zone3.values.T)) \
                                             - self.coefficients_MassFlow_Top_Zone4['x1'] * (
                                                     24 * np.ones((1488)) - np.array(
                                                 self.sim_data_ZoneTemperature_Setpoint_Top_Zone4.values.T))
        self.approx_MassFlow_Top_Floor[
            self.approx_MassFlow_Top_Floor > self.parameters_top_vav_max_flow] = self.parameters_top_vav_max_flow
        self.approx_MassFlow_Top_Floor[self.approx_MassFlow_Top_Floor < 0] = 0
        self.approx_MassFlow_Top_Floor = pd.DataFrame(self.approx_MassFlow_Top_Floor.T)
        self.approx_MassFlow_Top_Floor.columns = ['MASS_FLOWS_Top_VAV_Approx']

        # plotting.plot_approximation(self.sim_data_MassFlow_Top_Floor, self.approx_MassFlow_Top_Floor,
        #                             self.sim_data_MassFlow_Top_Floor.columns[0])

        # =============== Approximate VAV Powers =========================
        # >>>>>>>>>>> BOTTOM VAV <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_vav_floor_data_for_regression(self.sim_data_VAV_Power_Bottom, self.approx_MassFlow_Bottom_Floor)


        self.approx_VAV_Power_Bottom = pd.DataFrame(approximate.approximate_vav_power(df, self.coefficients_VAV_Power_Bottom_Floor))
        self.approx_VAV_Power_Bottom.columns = ['FAN_POWER_BOT_VAV_Approx']

        # plotting.plot_approximation(self.sim_data_VAV_Power_Bottom, self.approx_VAV_Power_Bottom,
        #                             self.sim_data_VAV_Power_Bottom.columns[0])

        # >>>>>>>>>>> MID VAV <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_vav_floor_data_for_regression(self.sim_data_VAV_Power_Mid,
                                                                   self.approx_MassFlow_Mid_Floor)


        self.approx_VAV_Power_Mid = pd.DataFrame(
            approximate.approximate_vav_power(df, self.coefficients_VAV_Power_Mid))
        self.approx_VAV_Power_Mid.columns = ['FAN_POWER_MID_VAV_Approx']

        # plotting.plot_approximation(self.sim_data_VAV_Power_Mid, self.approx_VAV_Power_Mid,
        #                             self.sim_data_VAV_Power_Mid.columns[0])

        # >>>>>>>>>>> TOP VAV <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_vav_floor_data_for_regression(self.sim_data_VAV_Power_Top,
                                                                   self.approx_MassFlow_Top_Floor)

        # self.coefficients_VAV_Power_Top = regress.get_VAV_Power_Coefficient(y, df)
        self.approx_VAV_Power_Top = pd.DataFrame(
            approximate.approximate_vav_power(df, self.coefficients_VAV_Power_Top))
        self.approx_VAV_Power_Top.columns = ['FAN_POWER_TOP_VAV_Approx']

        # plotting.plot_approximation(self.sim_data_VAV_Power_Top, self.approx_VAV_Power_Top,
        #                             self.sim_data_VAV_Power_Top.columns[0])

        # >>>>>>> Basement CAV <<<<<<<<<<<<<<<
        y, df = process_data.process_basement_power_for_regression(
            self.sim_data_CAV_Power_Basement, self.sim_data_Internal_Load_Basement,
            self.sim_data_ZoneTemperature_Basement)
        self.approx_CAV_Power_Basement = pd.DataFrame(approximate.approximate_cav_basement_coefficient(self.parameters_basement_cav_max_power, df, self.coefficients_CAV_Power_Basement))
        self.approx_CAV_Power_Basement.columns = ['FAN_POWER_BASEMENT_CAV_Approx']

        # plotting.plot_approximation(self.sim_data_CAV_Power_Basement, self.approx_CAV_Power_Basement,
        #                             self.sim_data_CAV_Power_Basement.columns[0])

        # ============ Evaporator Load =======================
        # >>>>>>>>>>>> Evaporator 1 <<<<<<<<<<<<<<<<<
        self.approx_CAV_VAV_Fan_Power = pd.DataFrame(self.approx_CAV_Power_Basement.values \
                                               + self.approx_VAV_Power_Bottom.values \
                                               + self.approx_VAV_Power_Mid.values \
                                               + self.approx_VAV_Power_Top.values)
        self.approx_CAV_VAV_Fan_Power.columns = ['Total_VAV_CAV_FAN_POWER_APPROX']

        y, df = process_data.process_evaporator_load_chiller_for_regression(
            self.sim_data_Evaporator_Load_Chiller1 , self.approx_CAV_VAV_Fan_Power,
            self.approx_Twet_bulb )
        self.approx_Evaporator_Load_Chiller1 = pd.DataFrame(
            approximate.approx_Evaporator_Load_Chiller(self.parameters_chiller_P_ref_chiller1_Watts, df, self.coefficients_Evaporator_Load_Chiller1))
        self.approx_Evaporator_Load_Chiller1.columns = ['EVAPORATOR_CHILLER1_APPROX']
        # plotting.plot_approximation(self.sim_data_Evaporator_Load_Chiller1, self.approx_Evaporator_Load_Chiller1,
        #                             self.sim_data_Evaporator_Load_Chiller1.columns[0])

        # >>>>>>>>>>>> Evaporator 2 <<<<<<<<<<<<<<<<<
        y, df = process_data.process_evaporator_load_chiller_for_regression(
            self.sim_data_Evaporator_Load_Chiller2 , self.approx_CAV_VAV_Fan_Power,
            self.approx_Twet_bulb )
        self.approx_Evaporator_Load_Chiller2 = pd.DataFrame(
            approximate.approx_Evaporator_Load_Chiller(self.parameters_chiller_P_ref_chiller1_Watts,df, self.coefficients_Evaporator_Load_Chiller2))
        self.approx_Evaporator_Load_Chiller2.columns = ['EVAPORATOR_CHILLER2_APPROX']
        # plotting.plot_approximation(self.sim_data_Evaporator_Load_Chiller2, self.approx_Evaporator_Load_Chiller2,
        #                             self.sim_data_Evaporator_Load_Chiller2.columns[0])

        # ============ Condenser Leaving Temp =======================
        # >>>>>> Condenser 1 <<<<<<<<
        y, df = process_data.process_condenser1_leaving_temp(
            self.sim_data_Condenser_Leaving_Temperature_Chiller1 , self.approx_Evaporator_Load_Chiller1 / self.approx_Evaporator_Load_Chiller1.max(axis=0),
            self.approx_Twet_bulb /self.approx_Twet_bulb.max(axis=0))
        # self.coefficients_Condenser_Leaving_Temperature_Chiller1 = regress.get_condenser_leaving_temp(y, df)
        self.approx_Condenser_Leaving_Temperature_Chiller1 = pd.DataFrame(
            approximate.approx_Condenser_Leaving_Temp(self.parameters_condenser_leaving_temperature_max, self.parameters_condenser_leaving_temperature_min, df, self.coefficients_Condenser_Leaving_Temperature_Chiller1))
        self.approx_Condenser_Leaving_Temperature_Chiller1.columns = ['CONDENSER_LEAVING_TEMP_CHILLER1']
        # plotting.plot_approximation(self.sim_data_Condenser_Leaving_Temperature_Chiller1, self.approx_Condenser_Leaving_Temperature_Chiller1,
        #                             self.sim_data_Condenser_Leaving_Temperature_Chiller1.columns[0])
        # >>>>>> Condenser 2 <<<<<<<<
        y, df = process_data.process_condenser2_leaving_temp(
                    self.sim_data_Condenser_Leaving_Temperature_Chiller2 , self.approx_Evaporator_Load_Chiller2 / self.approx_Evaporator_Load_Chiller2.max(axis=0),
                    self.approx_Twet_bulb /self.approx_Twet_bulb.max(axis=0))
        self.approx_Condenser_Leaving_Temperature_Chiller2 = pd.DataFrame(approximate.approx_Condenser_Leaving_Temp(self.parameters_condenser_leaving_temperature_max, self.parameters_condenser_leaving_temperature_min, df, self.coefficients_Condenser_Leaving_Temperature_Chiller2))
        self.approx_Condenser_Leaving_Temperature_Chiller2.columns = ['CONDENSER_LEAVING_TEMP_CHILLER2']
        # plotting.plot_approximation(self.sim_data_Condenser_Leaving_Temperature_Chiller2, self.approx_Condenser_Leaving_Temperature_Chiller2,self.sim_data_Condenser_Leaving_Temperature_Chiller2.columns[0])
        
        # ========= CHILLER POWER =====
        # >>>>>>>>>> CHILLER 1 <<<<<<<<
        self.approx_Chiller1_Power = pd.DataFrame(approximate.approx_Chiller1_Power(self))
        self.approx_Chiller1_Power.columns = ['CHILLER1_POWER']
        # plotting.plot_approximation(self.sim_data_Chiller1_Power, self.approx_Chiller1_Power,
        #                             self.sim_data_Chiller1_Power.columns[0])
        # >>>>>>>>>> CHILLER 2 <<<<<<<<
        self.approx_Chiller2_Power = pd.DataFrame(approximate.approx_Chiller2_Power(self))
        self.approx_Chiller2_Power.columns = ['CHILLER2_POWER']
        # plotting.plot_approximation(self.sim_data_Chiller2_Power, self.approx_Chiller2_Power,
        #                     self.sim_data_Chiller2_Power.columns[0])

        # ========= COOLING TOWER FAN ============
        # >>>>>>>>>>> Tower 1 <<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_cooling_tower_fan(
        self.sim_data_Fan_Power_CoolTower1 ,
        self.approx_Chiller1_Power,
        self.approx_Twet_bulb )
        self.approx_Fan_Power_CoolTower1 = pd.DataFrame(approximate.approx_cooling_Tower_Fan(self.parameters_Fan_Power_CoolTower_Max_Power, df, self.coefficients_Fan_Power_CoolTower1))
        self.approx_Fan_Power_CoolTower1.columns = ['COOLING_TOWER_FAN_1']
        # plotting.plot_approximation(self.sim_data_Fan_Power_CoolTower1,
        #                     self.approx_Fan_Power_CoolTower1,
        #                     self.sim_data_Fan_Power_CoolTower1.columns[0])
        # >>>>>>>>>>> Tower 2 <<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_cooling_tower_fan(
        self.sim_data_Fan_Power_CoolTower2 ,
        self.approx_Chiller2_Power,
        self.approx_Twet_bulb )
        self.approx_Fan_Power_CoolTower2 = pd.DataFrame(approximate.approx_cooling_Tower_Fan(self.parameters_Fan_Power_CoolTower_Max_Power, df, self.coefficients_Fan_Power_CoolTower2))
        self.approx_Fan_Power_CoolTower2.columns = ['COOLING_TOWER_FAN_2']
        # plotting.plot_approximation(self.sim_data_Fan_Power_CoolTower2,
        #                     self.approx_Fan_Power_CoolTower2,
        #                     self.sim_data_Fan_Power_CoolTower2.columns[0])

        # ========= Pump Power ============
        # >>>>>>>>>>> Primary <<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_pump_power(
        self.sim_data_Pump_Power_Primary ,
        self.approx_Chiller1_Power,
        self.approx_Twet_bulb )
        self.approx_Pump_Power_Primary = pd.DataFrame(approximate.approx_primary_pump_power(self.parameters_primary_pump_max_power, df, self.coefficients_Pump_Power_Primary))
        self.approx_Pump_Power_Primary.columns = ['PRIMARY_PUMP_POWER']
        # plotting.plot_approximation(self.sim_data_Pump_Power_Primary,
        #                     self.approx_Pump_Power_Primary,
        #                     self.sim_data_Pump_Power_Primary.columns[0])
        # >>>>>>>>>>> Secondary <<<<<<<<<<<<<<<<<<<
        y, df = process_data.process_pump_power(
        self.sim_data_Pump_Power_Secondary ,
        self.approx_Chiller1_Power,
        self.approx_Twet_bulb )
        # self.coefficients_Pump_Power_Secondary = regress.get_pump_power(y, df)
        self.approx_Pump_Power_Secondary = pd.DataFrame(approximate.approx_primary_pump_power(self.parameters_secondary_pump_max_power, df, self.coefficients_Pump_Power_Secondary))
        self.approx_Pump_Power_Secondary.columns = ['SECONDARY_PUMP_POWER']
        # plotting.plot_approximation(self.sim_data_Pump_Power_Secondary,
        #                     self.approx_Pump_Power_Secondary,
        #                     self.sim_data_Pump_Power_Secondary.columns[0])


        # ============ TOTAL APPROXIMATE_POWERS ==================================================
        self.approx_Total_Chiller_Power = pd.DataFrame(
            self.approx_Chiller1_Power.values + self.approx_Chiller2_Power.values)
        self.approx_Total_Chiller_Power.columns = ['TOTAL_CHILLERS_POWER_Approx']

        self.approx_Total_Fan_Power = pd.DataFrame(self.approx_VAV_Power_Mid.values \
                                                     + self.approx_VAV_Power_Top.values \
                                                     + self.approx_VAV_Power_Bottom.values \
                                                     + self.approx_CAV_Power_Basement.values \
                                                     + self.approx_Fan_Power_CoolTower1.values \
                                                     + self.approx_Fan_Power_CoolTower2.values)
        self.approx_Total_Fan_Power.columns = ['TOTAL_FANS_POWER_Approx']
        self.approx_Total_Pump_Power = pd.DataFrame(
            self.approx_Pump_Power_Secondary.values + self.approx_Pump_Power_Primary.values)
        self.approx_Total_Pump_Power.columns = ['TOTAL_PUMP_POWER_Approx']

        # plotting.plot_approximation(self.sim_data_Total_Pump_Power,
        #                     self.approx_Total_Pump_Power,
        #                     self.sim_data_Total_Pump_Power.columns[0])
        plotting.plot_approximation(self.sim_data_Total_Fan_Power,
                            self.approx_Total_Fan_Power,
                            self.sim_data_Total_Fan_Power.columns[0])
        # plotting.plot_approximation(self.sim_data_Total_Chiller_Power,
        #                     self.approx_Total_Chiller_Power,
        #                     self.sim_data_Total_Chiller_Power.columns[0])

        if plot_approximation == 1:  # 1 means yes
            # plotting.plot_approximation(self.sim_data_Pump_Power_Secondary,
            #                             self.approx_Pump_Power_Secondary,
            #                             self.sim_data_Pump_Power_Secondary.columns[0])
            # plotting.plot_approximation(self.sim_data_Total_Pump_Power,
            #                         self.approx_Total_Pump_Power,
            #                         self.sim_data_Total_Pump_Power.columns[0])
            # plotting.plot_approximation(self.sim_data_Total_Fan_Power,
            #                         self.approx_Total_Fan_Power,
            #                         self.sim_data_Total_Fan_Power.columns[0])
            # plotting.plot_approximation(self.sim_data_Total_Chiller_Power,
            #                         self.approx_Total_Chiller_Power,
            #                         self.sim_data_Total_Chiller_Power.columns[0])
            #
            # plotting.plot_approximation(self.sim_data_MassFlow_Bottom_Floor, self.approx_MassFlow_Bottom_Floor,self.sim_data_MassFlow_Bottom_Floor.columns[0])
            # plotting.plot_approximation(self.sim_data_MassFlow_Mid_Floor, self.approx_MassFlow_Mid_Floor,
            #                         self.sim_data_MassFlow_Mid_Floor.columns[0])
            # plotting.plot_approximation(self.sim_data_MassFlow_Top_Floor, self.approx_MassFlow_Top_Floor,
            #                         self.sim_data_MassFlow_Top_Floor.columns[0])
            #
            # plotting.plot_approximation(self.sim_data_VAV_Power_Bottom, self.approx_VAV_Power_Bottom,
            #                         self.sim_data_VAV_Power_Bottom.columns[0])
            #
            # plotting.plot_approximation(self.sim_data_VAV_Power_Mid, self.approx_VAV_Power_Mid,
            #                         self.sim_data_VAV_Power_Mid.columns[0])
            # plotting.plot_approximation(self.sim_data_VAV_Power_Top, self.approx_VAV_Power_Top,
            #                         self.sim_data_VAV_Power_Top.columns[0])
            # plotting.plot_approximation(self.sim_data_CAV_Power_Basement, self.approx_CAV_Power_Basement,
            #                         self.sim_data_CAV_Power_Basement.columns[0])
            # plotting.plot_approximation(self.sim_data_Evaporator_Load_Chiller1, self.approx_Evaporator_Load_Chiller1,
            #                         self.sim_data_Evaporator_Load_Chiller1.columns[0])
            # plotting.plot_approximation(self.sim_data_Evaporator_Load_Chiller2, self.approx_Evaporator_Load_Chiller2,
            #                         self.sim_data_Evaporator_Load_Chiller2.columns[0])
            # plotting.plot_approximation(self.sim_data_Condenser_Leaving_Temperature_Chiller1,
            #                         self.approx_Condenser_Leaving_Temperature_Chiller1,
            #                         self.sim_data_Condenser_Leaving_Temperature_Chiller1.columns[0])
            # plotting.plot_approximation(self.sim_data_Condenser_Leaving_Temperature_Chiller2,
            #                         self.approx_Condenser_Leaving_Temperature_Chiller2,
            #                         self.sim_data_Condenser_Leaving_Temperature_Chiller2.columns[0])

            plotting.plot_approximation(self.sim_data_Chiller1_Power, self.approx_Chiller1_Power,
                                    self.sim_data_Chiller1_Power.columns[0])
            # plotting.plot_approximation(self.sim_data_Chiller2_Power, self.approx_Chiller2_Power,
            #                         self.sim_data_Chiller2_Power.columns[0])
            plotting.plot_approximation(self.sim_data_Fan_Power_CoolTower1,
                                    self.approx_Fan_Power_CoolTower1,
                                    self.sim_data_Fan_Power_CoolTower1.columns[0])
            plotting.plot_approximation(self.sim_data_Fan_Power_CoolTower2,
                                    self.approx_Fan_Power_CoolTower2,
                                    self.sim_data_Fan_Power_CoolTower2.columns[0])

            # plotting.plot_approximation(self.sim_data_Pump_Power_Primary,
            #                         self.approx_Pump_Power_Primary,
            #                         self.sim_data_Pump_Power_Primary.columns[0])

if __name__ == "__main__":

    plt.close('all')
    # Time duration on which to perform approximation this can just come from E+data
    # later on when the Modelica model arrives the new data can be used to train the model
#    startTime = 97 # this is just used for training first 96 periods for E+ are just warm ups
#    plot_approximations = 1 # 1 means plot, 2 means don't

#    scenario = 2    # 1 is for training, 2 is for testing

#    if scenario == 1: # training
#        eplus_file_name = ".\data\OfficeLarge_Denver_85-basecase.csv"
#    elif scenario == 2: # testing
    eplus_file_name = ".\data\OfficeLarge_Denver_85-basecase_24to22and26.csv"
#    else:
#        print("===wrong scenario chosen===")

    # initialize the agent
#    Agent = LargeHVACAgent(eplus_file_name, startTime, scenario)
    Agent = LargeHVACAgent(eplus_file_name, 97, 2)

# get simulation data
    Agent.get_simulation_data()
    # get coefficients
    # Agent.get_coefficients(scenario) # 1 means we save coefficients
    # Agent.get_approximations(scenario, plot_approximations) # 2 means loading previously saved coefficients
    Agent.get_coefficients(1)  # 1 means we save coefficients
    Agent.get_approximations(2, 1)  # 2 means loading previously saved coefficients

# TODO: Automate procedure to configuration data through a JSON File, possibly start with some dummy json
# TODO: Create a key, topic mapping from FNCS-LargeHVAC
# TODO: Implement a simple real-time P-Q bid (similar to house HVAC):
#  1) Estimates the temperature of zones and total power at next step.
#  2) Each zone can have its basepoint and T_range, and then according to its ramp setting, the price can be found
#   which can be bid for the next interval.
#  3) Adjust the setpoint based on the basepoint and T_range and mean/std deviation price settings
#  4) Update the structure as eventually this class will go to src/tesp_support/tesp_support
# TODO: These connections can be made once the Modelica Model is integrated in TESP.
