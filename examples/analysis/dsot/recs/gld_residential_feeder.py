# Copyright (C) 2018-2020 Battelle Memorial Institute
# file: feederGenerator.py
"""Replaces ZIP loads with houses, and optional storage and solar generation.

As this module populates the feeder backbone with houses and DER, it uses
As this module populates the feeder backbone with houses and DER, it uses
the Networkx package to perform graph-based capacity analysis, upgrading
fuses, transformers and lines to serve the expected load. Transformers have
a margin of 20% to avoid overloads, while fuses have a margin of 150% to
avoid overloads. These can be changed by editing tables and variables in the
source file.

There are two kinds of house populating methods implemented:

    * :Feeders with Service Transformers: This case applies to the full PNNL 
        taxonomy feeders. Do not specify the *taxchoice* argument to 
        *populate_feeder*. Each service transformer receiving houses will have a
        short service drop and a small number of houses attached.
    * :Feeders without Service Transformers: This applies to the reduced-order 
        ERCOT feeders. To invoke this mode, specify the *taxchoice* argument to 
        *populate_feeder*. Each primary load to receive houses will have a large
        service transformer, large service drop and large number of houses attached.

References:
    `GridAPPS-D Feeder Models <https://github.com/GRIDAPPSD/Powergrid-Models>`_

Public Functions:
    :populate_feeder: processes one GridLAB-D input file

TODO:
    * Verify the level zero mobile home thermal integrity properties; 
        these were copied from the MATLAB feeder generator

    * TODO - JK - Find parameters in this model and migrate them to a JSON5 file. This
                should include comments on provenance if you know it and a TODO item if
                you don't.
    * TODO - FR - Add method to read in JSON5 config
    * DONE - JK - Edit and expand docstrings and type hinting for each method in method call
                and external list in docstring
        * TODO - JK + - Tidy up and fill in missing info for docstrings
    * TODO - FR - Create definitions for new higher-level methods Trevor called out in 
                class diagram and add calls to existing methods as appropriate
                (tesp/design/feeder_generator/feeder generator class diagram).
    * DONE - JK - Apply style guide to existing code
        * TODO - JK + - review for any stylistic faux pas 
    * DONE - JK - Rename all 1, 2, or 3 letter variables to be more descriptive 
                OK - "v_an" = "voltage from phase a to neutral"
                NOT OK - "sub" = "substation"? "substitute"?
        * TODO - JK + - review flagged variables for renaming or removal
    * TODO - FR - Convert all the string formatting from ".format" to "f{}"
"""
import json
import math
import os.path
import re
import sys

import networkx as nx
import numpy as np
import pandas as pd

from tesp_support.api.helpers import gld_strict_name, random_norm_trunc
from tesp_support.api.modify_GLM import GLMModifier
from tesp_support.api.parse_helpers import parse_kva
from tesp_support.api.time_helpers import get_secs_from_hhmm, get_hhmm_from_secs, get_duration, get_dist
from tesp_support.api.time_helpers import is_hhmm_valid, subtract_hhmm_secs, add_hhmm_secs

sys.path.append('./')
import gld_commercial_feeder as comm_FG
import recs_api as recs

global c_p_frac
extra_billing_meters = set()


class Feeder:


    def __init__(self, taxonomy_choice):

        self.glm = GLMModifier()
        self.taxonomy = self.glm.defaults.taxchoice[taxonomy_choice]
        self.g, success = self.glm.model.readBackboneModel(self.taxonomy[0] + '.glm')
        if not success:
            raise 'File not found or file not supported, exiting!'
        self.base = self.glm.defaults

    # EV population functions
    def process_nhts_data(self, data_file: str) -> pd.DataFrame:
        """Read the large nhts survey data file containing driving data, process
        it and return a dataframe

        Args:
            data_file (str): path of the file

        Returns:
            pd.DataFrame: dataframe containing start_time, end_time, travel_day 
            (weekday/weekend) and daily miles driven
        """
        # Read data from NHTS survey
        df_data = pd.read_csv(data_file, index_col=[0, 1])
        # filter based on trip leaving only from home and not from work or other places
        # take the earliest time leaving from home of a particular vehicle
        df_data_leave = df_data[df_data['WHYFROM'] == 1].groupby(level=['HOUSEID', 'VEHID']).min()[
            ['STRTTIME', 'TRAVDAY']]
        # filter based on trip arriving only at home and not at work or other places
        # take the latest time arriving at home of a particular vehicle
        df_data_arrive = df_data[df_data['WHYTO'] == 1].groupby(level=['HOUSEID', 'VEHID']).max()[
            ['ENDTIME', 'TRAVDAY']]
        # take the sum of trip miles by a particular vehicle in a day
        df_data_miles = df_data.groupby(level=['HOUSEID', 'VEHID']).sum()['TRPMILES']
        # limit daily miles to maximum possible range of EV from the ev model data as EVs cant travel more
        # than the range in a day if we don't consider the highway charging
        max_ev_range = max(self.base.ev_metadata['Range (miles)'].values())
        df_data_miles = df_data_miles[df_data_miles < max_ev_range]
        df_data_miles = df_data_miles[df_data_miles > 0]

        # combine all 4 parameters: starttime, endtime, total_miles, travel_day.
        # Ignore vehicle ids that don't have both leaving and arrival time at home
        temp = df_data_leave.merge(df_data_arrive['ENDTIME'], left_index=True, right_index=True)
        df_fin = temp.merge(df_data_miles, left_index=True, right_index=True)
        return df_fin

    def selectEVmodel(self, evTable: dict, prob: float) -> str:
        """Selects the building and vintage type

        Args:
            evTable (dict): models probability list
            prob (float): probability

        Raises:
            UserWarning: EV model sale distribution does not sum to 1!

        Returns:
            str: name
        """    

        total = 0
        for name, pr in evTable.items():
            total += pr
            if total >= prob:
                return name
        raise UserWarning('EV model sale distribution does not sum to 1!')

    def match_driving_schedule(self, ev_range: float, ev_mileage: float, ev_max_charge: float) -> dict:
        """Method to match the schedule of each vehicle from NHTS data based on 
        vehicle ev_range. 
        - Checks to make sure daily travel miles are less than 
        ev_range-margin. Allows a reserve SoC to be specified.
        - Checka if home_duration is enough to charge for daily_miles driven + 
        margin
        - Since during v1g or v2g mode, we only allow charging start at the 
        start of the next hour after vehicle, come home and charging must end at
        the full hour just before vehicle leaves home, the actual chargeable 
        hours duration may be smaller than the car home duration by maximum 2 
        hours.

        Args:
            ev_range (float): _description_
            ev_mileage (float): _description_
            ev_max_charge (float): _description_

        Raises:
            UserWarning: _description_

        Returns:
            dict: driving_sch containing {daily_miles, home_arr_time, 
            home_leave_time, home_duration, work_arr_time, work_duration}
        """

        while True:
            mile_ind = np.random.randint(0, len(self.base.ev_driving_metadata['TRPMILES']))
            daily_miles = self.base.ev_driving_metadata['TRPMILES'].iloc[mile_ind]
            if ev_range * 0.0 < daily_miles < ev_range * (1 - self.base.ev_reserved_soc / 100):
                break
        daily_miles = max(daily_miles, ev_range * 0.2)
        home_leave_time = self.base.ev_driving_metadata['STRTTIME'].iloc[mile_ind]
        home_arr_time = self.base.ev_driving_metadata['ENDTIME'].iloc[mile_ind]
        home_duration = get_duration(home_arr_time, home_leave_time)

        margin_miles = daily_miles * 0.10  # 10% extra miles
        charge_hour_need = (daily_miles + margin_miles) / (ev_max_charge * ev_mileage)  # hours

        min_home_need = charge_hour_need + 2
        if min_home_need >= 23:
            raise UserWarning('A particular EV can not be charged fully even within 23 hours!')
        if home_duration < min_home_need * 3600:  # if home duration is less than required minimum
            home_duration = min_home_need * 3600
        if home_duration > 23 * 3600:
            home_duration = 23 * 3600 - 1  # -1 to ensure work duration is not 0 with 1 hour commute time
        # update home arrival time
        home_arr_time = subtract_hhmm_secs(home_leave_time, home_duration)

        # estimate work duration and arrival time
        commute_duration = min(3600, 24 * 3600 - home_duration)  # in secs, maximum 1 hour: 30 minutes for work-home and
        # 30 minutes for home-work. If remaining time is less than an hour,
        # make that commute time, but it should not occur as maximum home duration is always less than 23 hours
        work_duration = max(24 * 3600 - (home_duration + commute_duration), 1)  # remaining time at work
        # minimum work duration is 1 second to avoid 0 that may give error in GridLABD sometimes
        work_arr_secs = get_secs_from_hhmm(home_leave_time) + int(commute_duration / 2)
        if work_arr_secs > 24 * 3600:  # if midnight crossing
            work_arr_secs = work_arr_secs - 24 * 3600
        work_arr_time = get_hhmm_from_secs(work_arr_secs)

        driving_sch = {'daily_miles': daily_miles,
                       'home_arr_time': int(home_arr_time),
                       'home_leave_time': int(home_leave_time),
                       'home_duration': home_duration,
                       'work_arr_time': int(work_arr_time),
                       'work_duration': work_duration
                       }
        return driving_sch

    def is_drive_time_valid(self, drive_sch: dict) -> bool:
        """Checks if work arrival time and home arrival time adds up properly

        Args:
            drive_sch (dict): Contains {daily_miles, home_arr_time, 
            home_leave_time, home_duration, work_arr_time, work_duration}

        Returns:
            bool: true or false
        """
        home_leave_time = add_hhmm_secs(drive_sch['home_arr_time'], drive_sch['home_duration'])
        commute_secs = min(3600, 24 * 3600 - drive_sch['home_duration'])
        work_arr_time = add_hhmm_secs(home_leave_time, commute_secs / 2)
        work_duration = 24 * 3600 - drive_sch['home_duration'] - commute_secs
        if (work_arr_time != drive_sch['work_arr_time'] or
                round(work_duration / 60) != round(drive_sch['work_duration'] / 60)):
            return False
        return True

    def add_node_house_configs(self, xfkva: float, xfkvll: float, xfkvln: float, phs: str, want_inverter=False):
        """Writes transformers, inverter settings for GridLAB-D houses at a 
        primary load point.

        An aggregated single-phase triplex or three-phase quadriplex line 
        configuration is also written, based on estimating enough parallel 1/0 
        AA to supply xfkva load. This function should only be called once for 
        each combination of xfkva and phs to use, and it should be called before
        write_node_houses.

        Args:
            xfkva (float): the total transformer size to serve expected load;
                make this big enough to avoid overloads
            xfkvll (float): line-to-line voltage [kV] on the primary. The 
                secondary voltage will be 208 three-phase
            xfkvln (float): line-to-neutral voltage [kV] on the primary. The 
                secondary voltage will be 120/240 for split secondary
            phs (str): either 'ABC' for three-phase, or concatenation of 'A',
                'B', and/or 'C' with 'S' for single-phase to triplex
            want_inverter (boolean): True to write the IEEE 1547-2018 smarter 
                inverter function setpoints
        """
        if want_inverter:
            # print ('#define INVERTER_MODE=CONSTANT_PF', file=fp)
            # print ('//#define INVERTER_MODE=VOLT_VAR', file=fp)
            # print ('//#define INVERTER_MODE=VOLT_WATT', file=fp)
            # print ('// default IEEE 1547-2018 settings for Category B', file=fp)
            self.glm.model.define_lines.append("#define INV_V2=0.98")
            self.glm.model.define_lines.append("#define INV_V2=0.98")
            self.glm.model.define_lines.append("#define INV_V3=1.02")
            self.glm.model.define_lines.append("#define INV_V4=1.08")
            self.glm.model.define_lines.append("#define INV_Q1=0.44")
            self.glm.model.define_lines.append("#define INV_Q2=0.00")
            self.glm.model.define_lines.append("#define INV_Q3=0.00")
            self.glm.model.define_lines.append("#define INV_Q4=-0.44")
            self.glm.model.define_lines.append("#define INV_VIN=200.0")
            self.glm.model.define_lines.append("#define INV_IIN=32.5")
            self.glm.model.define_lines.append("#define INV_VVLOCKOUT=300.0")
            self.glm.model.define_lines.append("#define INV_VW_V1=1.05 // 1.05833")
            self.glm.model.define_lines.append("#define INV_VW_V2=1.10")
            self.glm.model.define_lines.append("#define INV_VW_P1=1.0")
            self.glm.model.define_lines.append("#define INV_VW_P2=0.0")
        if 'S' in phs:
            for secphs in phs.rstrip('S'):
                xfkey = 'XF{:s}_{:d}'.format(secphs, int(xfkva))
                self.add_xfmr_config(xfkey, secphs + 'S', kvat=xfkva, vnom=None, vsec=120.0,
                                     install_type='PADMOUNT', vprimll=None, vprimln=1000.0 * xfkvln)
                self.add_kersting_triplex(xfkva)
        else:
            xfkey = 'XF3_{:d}'.format(int(xfkva))
            self.add_xfmr_config(xfkey, phs, kvat=xfkva, vnom=None, vsec=208.0, install_type='PADMOUNT',
                                 vprimll=1000.0 * xfkvll, vprimln=None)
            self.add_kersting_quadriplex(xfkva)

    def add_kersting_quadriplex(self, kva: float):
        """Writes a quadriplex_line_configuration based on 1/0 AA example from 
        Kersting's book

        The conductor capacity is 202 amps, so the number of triplex in parallel 
        will be kva/sqrt(3)/0.208/202

        Args:
            kva (float): 
        """
        params = dict()
        params["key"] = 'quad_cfg_{:d}'.format(int(kva))
        params["amps"] = kva / math.sqrt(3.0) / 0.208
        params["npar"] = math.ceil(params["amps"] / 202.0)
        params["apar"] = 202.0 * params["npar"]
        params["scale"] = 5280.0 / 100.0 / params["npar"]  # for impedance per mile of parallel circuits
        params["r11"] = 0.0268 * params["scale"]
        params["x11"] = 0.0160 * params["scale"]
        params["r12"] = 0.0080 * params["scale"]
        params["x12"] = 0.0103 * params["scale"]
        params["r13"] = 0.0085 * params["scale"]
        params["x13"] = 0.0095 * params["scale"]
        params["r22"] = 0.0258 * params["scale"]
        params["x22"] = 0.0176 * params["scale"]
        self.glm.add_object("line_configuration", params["key"], params)

    def add_kersting_triplex(self, kva: float):
        """Writes a triplex_line_configuration based on 1/0 AA example from 
        Kersting's book

        The conductor capacity is 202 amps, so the number of triplex in parallel 
        will be kva/0.12/202

        Args:
            kva (float): 
        """
        params = dict()
        params["key"] = 'tpx_cfg_{:d}'.format(int(kva))
        params["amps"] = kva / 0.12
        params["npar"] = math.ceil(params["amps"] / 202.0)
        params["apar"] = 202.0 * params["npar"]
        params["scale"] = 5280.0 / 100.0 / params["npar"]  # for impedance per mile of parallel circuits
        params["r11"] = 0.0271 * params["scale"]
        params["x11"] = 0.0146 * params["scale"]
        params["r12"] = 0.0087 * params["scale"]
        params["x12"] = 0.0081 * params["scale"]
        self.glm.add_object("triplex_line_configuration", params["key"], params)

    def accumulate_load_kva(self, data: dict) -> float:
        """Add up the total kva in a load-bearing object instance

        Considers constant_power_A/B/C/1/2/12 and power_1/2/12 attributes

        Args:
            data (dict): dictionary of data for a selected GridLAB-D instance

        Returns:
            kva (float): total kva in a load-bearing object instance
        """
        kva = 0.0
        if 'constant_power_A' in data:
            kva += parse_kva(data['constant_power_A'])
        if 'constant_power_B' in data:
            kva += parse_kva(data['constant_power_B'])
        if 'constant_power_C' in data:
            kva += parse_kva(data['constant_power_C'])
        if 'constant_power_1' in data:
            kva += parse_kva(data['constant_power_1'])
        if 'constant_power_2' in data:
            kva += parse_kva(data['constant_power_2'])
        if 'constant_power_12' in data:
            kva += parse_kva(data['constant_power_12'])
        if 'power_1' in data:
            kva += parse_kva(data['power_1'])
        if 'power_2' in data:
            kva += parse_kva(data['power_2'])
        if 'power_12' in data:
            kva += parse_kva(data['power_12'])
        return kva

    def log_model(self, model: dict, h: dict):
        """Prints the whole parsed model for debugging

        Args:
            model (dict): parsed GridLAB-D model
            h (dict): object ID hash
        """
        for t in model:
            print(t + ':')
            for o in model[t]:
                print('\t' + o + ':')
                for p in model[t][o]:
                    if ':' in model[t][o][p]:
                        print('\t\t' + p + '\t-->\t' + h[model[t][o][p]])
                    else:
                        print('\t\t' + p + '\t-->\t' + model[t][o][p])

    def selectResidentialBuilding(self, rgnTable: list, prob: float) -> list:
        """Writes volt-var and volt-watt settings for solar inverters

        Args:
            rgnTable (list): 
            prob (float):
        """
        row = 0
        total = 0
        for row in range(len(rgnTable)):
            for col in range(len(rgnTable[row])):
                total += rgnTable[row][col]
                if total >= prob:
                    return row, col
        row = len(rgnTable) - 1
        col = len(rgnTable[row]) - 1
        return row, col

    def getDsoIncomeLevelTable(self):
        """Retrieves the DSO Income Level
        Fraction of income level in a given dso type and state:
        Index 0 is the income level:
            0 = Low
            1 = Middle (No longer using Moderate)
            2 = Upper

        Raises:
            UserWarning: Income level distribution does not sum to 1!

        Returns:
            list: dsoIncomePct
        """
        income_mat = self.base.res_bldg_metadata['income_level'][self.base.state][self.base.dso_type]
        dsoIncomePct = {"key": income_mat[key] for key in self.base.income_level}  # Create new dictionary only with income levels of interest
        dsoIncomePct = list(dsoIncomePct.values())
        dsoIncomePct = [round(i / sum(dsoIncomePct), 4) for i in dsoIncomePct]  # Normalize so array adds up to 1
        # now check if the sum of all values is 1
        total = 0
        for row in range(len(dsoIncomePct)):
            total += dsoIncomePct[row]
        if total > 1.01 or total < 0.99:
             raise UserWarning('Income level distribution does not sum to 1!')
        return dsoIncomePct

    def selectIncomeLevel(self, incTable: list, prob: float) -> int:
        """Selects the income level with region and probability

        Args:
            incTable (): income table
            prob (float): probability

        Returns:

        """
        total = 0
        for row in range(len(incTable)):
            total += incTable[row]
            if total >= prob:
                return row
        row = len(incTable) - 1
        return row

    def buildingTypeLabel(self, rgn: int, bldg: int, therm_int: int):
        """Formatted name of region, building type name and thermal integrity level

        Args:
            rgn (int): region number 1..5
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            therm_int (int): thermal integrity level, 0..6 for single-family, 
            only 0..2 valid for apartment or mobile home
        
        Returns:
            list: table containing region, building type, and thermal integrity
        """
        return self.base.rgnName[rgn - 1] + ': ' + self.base.bldgTypeName[bldg] + ': TI Level ' + str(therm_int + 1)

    def checkResidentialBuildingTable(self):
        """Verify that the regional building parameter histograms sum to one"""

        for tbl in range(len(self.base.dsoThermalPct)):
            total = 0
            for row in range(len(self.base.dsoThermalPct[tbl])):
                for col in range(len(self.base.dsoThermalPct[tbl][row])):
                    total += self.base.dsoThermalPct[tbl][row][col]
            print(self.base.rgnName[tbl], 'rgnThermalPct sums to', '{:.4f}'.format(total))
        for tbl in range(len(self.base.bldgCoolingSetpoints)):
            total = 0
            for row in range(len(self.base.bldgCoolingSetpoints[tbl])):
                total += self.base.bldgCoolingSetpoints[tbl][row][0]
            print('bldgCoolingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
        for tbl in range(len(self.base.bldgHeatingSetpoints)):
            total = 0
            for row in range(len(self.base.bldgHeatingSetpoints[tbl])):
                total += self.base.bldgHeatingSetpoints[tbl][row][0]
            print('bldgHeatingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
        for bldg in range(3):
            binZeroReserve = self.base.bldgCoolingSetpoints[bldg][0][0]
            binZeroMargin = self.base.bldgHeatingSetpoints[bldg][0][0] - binZeroReserve
            if binZeroMargin < 0.0:
                binZeroMargin = 0.0
            #        print(bldg, binZeroReserve, binZeroMargin)
            for cBin in range(1, 6):
                denom = binZeroMargin
                for hBin in range(1, self.base.allowedHeatingBins[cBin]):
                    denom += self.base.bldgHeatingSetpoints[bldg][hBin][0]
                self.base.conditionalHeatingBinProb[bldg][cBin][0] = binZeroMargin / denom
                for hBin in range(1, self.base.allowedHeatingBins[cBin]):
                    self.base.conditionalHeatingBinProb[bldg][cBin][hBin] = \
                        self.base.bldgHeatingSetpoints[bldg][hBin][0] / denom
        # print('conditionalHeatingBinProb', conditionalHeatingBinProb)

    def selectThermalProperties(self, bldg: int, therm_int: int):
        """Retrieve the building thermal properties for a given type and 
        thermal integrity level

        Args:
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            therm_int (int): 0..7 for single-family, apartment or mobile home
        """
        if bldg == 0:
            therm_prop = self.base.singleFamilyProperties[therm_int]
        elif bldg == 1:
            therm_prop = self.base.apartmentProperties[therm_int]
        else:
            therm_prop = self.base.mobileHomeProperties[therm_int]
        return therm_prop

    def selectSetpointBins(self, bldg: int, rand: float):
        """Randomly choose a histogram row from the cooling and heating setpoints.
        The random number for the heating setpoint row is generated internally.

        Args:
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            rand (float): random number [0..1] for the cooling setpoint row
        
        Returns:
            int: cooling and heating setpoints
        """
        cBin = hBin = 0
        total = 0
        tbl = self.base.bldgCoolingSetpoints[bldg]
        for row in range(len(tbl)):
            total += tbl[row][0]
            if total >= rand:
                cBin = row
                break
        tbl = self.base.conditionalHeatingBinProb[bldg][cBin]
        rand_heat = np.random.uniform(0, 1)
        total = 0
        for col in range(len(tbl)):
            total += tbl[col]
            if total >= rand_heat:
                hBin = col
                break
        self.base.cooling_bins[bldg][cBin] -= 1
        self.base.heating_bins[bldg][hBin] -= 1
        return self.base.bldgCoolingSetpoints[bldg][cBin], self.base.bldgHeatingSetpoints[bldg][hBin]

    def initialize_config_dict(self, fgconfig: str):
        """TODO:_summary_

        Args:
            fgconfig (str): path and name of the file that is to be used as the 
                configuration json for loading ConfigDict dictionary
        """
        global ConfigDict
        global c_p_frac
        if fgconfig is not None:
            ConfigDict = {}
            with open(fgconfig, 'r') as fgfile:
                confile = fgfile.read()
                ConfigDict = json.loads(confile)
                fgfile.close()
            tval2 = ConfigDict['feedergenerator']['constants']
            ConfigDict = tval2
            cval1 = ConfigDict['c_z_frac']['value']
            cval2 = ConfigDict['c_i_frac']['value']
            # c_p_frac = 1.0 - ConfigDict['c_z_frac'] - ConfigDict['c_i_frac']
            c_p_frac = 1.0 - cval1 - cval2
    #       fgfile.close()

    def add_solar_inv_settings(self, params: dict):
        """ Writes volt-var and volt-watt settings for solar inverters

        Args:
            params (dict): solar inverter parameters. Contains:
                {four_quadrant_control_mode, V1, Q1, V2, Q2, V3, Q3, V4, Q4, 
                V_In, I_In, volt_var_control_lockout, VW_V1, VW_V2, VW_P1, VW_P2}
        """
        # print ('    four_quadrant_control_mode ${' + name_prefix + 'INVERTER_MODE};', file=op)
        params["four_quadrant_control_mode"] = self.base.name_prefix + 'INVERTER_MODE'
        params["V_base"] = '${INV_VBASE}'
        params["V1"] = '${INV_V1}'
        params["Q1"] = '${INV_Q1}'
        params["V2"] = '${INV_V2}'
        params["Q2"] = '${INV_Q2}'
        params["V3"] = '${INV_V3}'
        params["Q3"] = '${INV_Q3}'
        params["V4"] = '${INV_V4}'
        params["Q4"] = '${INV_Q4}'
        params["V_In"] = '${INV_VIN}'
        params["I_In"] = '${INV_IIN}'
        params["volt_var_control_lockout"] = '${INV_VVLOCKOUT}'
        params["VW_V1"] = '${INV_VW_V1}'
        params["VW_V2"] = '${INV_VW_V2}'
        params["VW_P1"] = '${INV_VW_P1}'
        params["VW_P2"] = '${INV_VW_P2}'

    def getDsoThermalTable(self, income: int) -> float:
        """TODO: _summary_

        Args:
            income (int): Income level of household

        Raises:
            UserWarning: House vintage distribution does not sum to 1!

        Returns:
            float: DSO thermal table
        """
        vintage_mat = self.base.res_bldg_metadata['housing_vintage'][self.base.state][
            self.base.dso_type][income]
        df = pd.DataFrame(vintage_mat)
        # df = df.transpose()
        dsoThermalPct = np.zeros(shape=(3, 9))  # initialize array
        dsoThermalPct[0] = (df['single_family_detached'] + df['single_family_attached']).values
        dsoThermalPct[1] = (df['apartment_2_4_units'] + df['apartment_5_units']).values
        dsoThermalPct[2] = (df['mobile_home']).values
        dsoThermalPct = dsoThermalPct.tolist()
        # now check if the sum of all values is 1
        total = 0
        for row in range(len(dsoThermalPct)):
            for col in range(len(dsoThermalPct[row])):
                total += dsoThermalPct[row][col]
        if total > 1.01 or total < 0.99:
            raise UserWarning('House vintage distribution does not sum to 1!')
        # print(rgnName, 'dsoThermalPct sums to', '{:.4f}'.format(total))
        return dsoThermalPct
        # print(dsoThermalPct)

    def obj(self, parent: str, model: dict, line: str, itr: iter, oidh: dict, octr: int) -> {str, int}:
        """Store an object in the model structure

        Args:
            parent (str): name of parent object (used for nested object defs)
            model (dict): dictionary model structure
            line (str): glm line containing the object definition
            itr (iter): iterator over the list of lines
            oidh (dict): hash of object id's to object names
            octr (int): object counter

        Returns:
            str, int: the current line and updated octr
        """
        octr += 1
        # Identify the object type
        m = re.search('object ([^:{\s]+)[:{\s]', line, re.IGNORECASE)
        type = m.group(1)
        # If the object has an id number, store it
        n = re.search('object ([^:]+:[^{\s]+)', line, re.IGNORECASE)
        if n:
            oid = n.group(1)
        line = next(itr)
        # Collect parameters
        oend = 0
        oname = None
        params = {}
        if parent is not None:
            params['parent'] = parent
        while not oend:
            m = re.match('\s*(\S+) ([^;{]+)[;{]', line)
            if m:
                # found a parameter
                param = m.group(1)
                val = m.group(2)
                intobj = 0
                if param == 'name':
                    oname = self.base.name_prefix + val
                elif param == 'object':
                    # found a nested object
                    intobj += 1
                    if oname is None:
                        print('ERROR: nested object defined before parent name')
                        quit()
                    line, octr = self.obj(oname, model, line, itr, oidh, octr)
                elif re.match('object', val):
                    # found an inline object
                    intobj += 1
                    line, octr = self.obj(None, model, line, itr, oidh, octr)
                    params[param] = 'ID_' + str(octr)
                else:
                    params[param] = val
            if re.search('}', line):
                if intobj:
                    intobj -= 1
                    line = next(itr)
                else:
                    oend = 1
            else:
                line = next(itr)
        # If undefined, use a default name
        if oname is None:
            oname = self.base.name_prefix + 'ID_' + str(octr)
        oidh[oname] = oname
        # Hash an object identifier to the object name
        if n:
            oidh[oid] = oname
        # Add the object to the model
        if type not in model:
            # New object type
            model[type] = {}
        model[type][oname] = {}
        for param in params:
            model[type][oname][param] = params[param]
        return line, octr

    def add_link_class(self, model: dict, h: dict, t: str, seg_loads: dict, want_metrics=False):
        """Write a GridLAB-D link (i.e., edge) class

        Args:
            model (dict): the parsed GridLAB-D model
            h (dict): the object ID hash
            t (str): the GridLAB-D class
            seg_loads (dict) : a dictionary of downstream loads for each link
            want_metrics (bool): true or false

        """
        if t in model:
            for o in model[t]:
                params = dict()
                if o in seg_loads:
                    # print('// downstream', '{:.2f}'.format(seg_loads[o][0]), 'kva on', seg_loads[o][1])
                    for p in model[t][o]:
                        if ':' in model[t][o][p]:
                            params[p] = h[model[t][o][p]]
                        else:
                            if p == "from" or p == "to" or p == "parent":
                                params[p] = gld_strict_name(model[t][o][p])
                            else:
                                params[p] = model[t][o][p]
                            self.glm.add_object(t, o, params)

                    if want_metrics:
                        self.glm.add_collector(o, t)

    def add_local_triplex_configurations(self):
        """Adds local triplex configurations"""
        params = dict()
        for row in self.base.triplex_conductors:
            name = self.base.name_prefix + row[0]
            params["resistance"] = row[1]
            params["geometric_mean_radius"] = row[2]
            rating_str = str(row[2])
            params["rating.summer.continuous"] = rating_str
            params["rating.summer.emergency"] = rating_str
            params["rating.winter.continuous"] = rating_str
            params["rating.winter.emergency"] = rating_str
            self.glm.add_object("triplex_line_conductor", name, params)
        for row in self.base.triplex_configurations:
            params = dict()
            name = self.base.name_prefix + row[0]
            params["conductor_1"] = self.base.name_prefix + row[0]
            params["conductor_2"] = self.base.name_prefix + row[1]
            params["conductor_N"] = self.base.name_prefix + row[2]
            params["insulation_thickness"] = str(row[3])
            params["diameter"] = str(row[4])
            self.glm.add_object("triplex_line_configuration", name, params)

    def add_ercot_houses(self, model: dict, h: dict, v_ln: float, v_sec: float):
        """For the reduced-order ERCOT feeders, add houses and a large service 
        transformer to the load points
        TODO: not all variables are used in this function

        Args:
            model (dict): the parsed GridLAB-D model
            h (dict): the object ID hash
            v_ln (float): the primary line-to-neutral voltage
            v_sec (float): the secondary line-to-neutral voltage
        """
        for key in self.base.house_nodes:
            #        bus = key[:-2]
            bus = self.base.house_nodes[key][6]
            phs = self.base.house_nodes[key][3]
            nh = self.base.house_nodes[key][0]
            xfkva = self.glm.find_1phase_xfmr_kva(6.0 * nh)
            if xfkva > 100.0:
                npar = int(xfkva / 100.0 + 0.5)
                xfkva = 100.0
            elif xfkva <= 0.0:
                xfkva = 100.0
                npar = int(0.06 * nh + 0.5)
            else:
                npar = 1
            # add the service transformer==>TN==>TPX==>TM for all houses
            kvat = npar * xfkva
            row = self.glm.find_1phase_xfmr(xfkva)
            params = {}
            name = key + '_xfconfig'
            params["power_rating"] = format(kvat, '.2f')
            if 'A' in phs:
                params["powerA_rating"] = format(kvat, '.2f')
            elif 'B' in phs:
                params["powerB_rating"] = format(kvat, '.2f')
            elif 'C' in phs:
                params["powerC_rating"] = format(kvat, '.2f')
            params["install_type"] = "PADMOUNT"
            params["connect_type"] = "SINGLE_PHASE_CENTER_TAPPED"
            params["primary_voltage"] = str(v_ln)
            params["secondary_voltage"] = format(v_sec, '.1f')
            params["resistance"] = format(row[1] * 0.5, '.5f')
            params["resistance1"] = format(row[1], '.5f')
            params["resistance2"] = format(row[1], '.5f')
            params["reactance"] = format(row[2] * 0.8, '.5f')
            params["reactance1"] = format(row[2] * 0.4, '.5f')
            params["reactance2"] = format(row[2] * 0.4, '.5f')
            params["shunt_resistance"] = format(1.0 / row[3], '.2f')
            params["shunt_reactance"] = format(1.0 / row[4], '.2f')
            self.glm.add_object("transformer_configuration", name, params)

            name = key + '_xf'
            params = {"phases": phs + 'S',
                      "from": bus,
                      "to": key + '_tn',
                      "configuration": key + '_xfconfig'}
            self.glm.add_object("transformer", name, params)

            name = key + '_tpxconfig'
            zs = format(self.base.tpxR11 / nh, '.5f') + '+' + format(self.base.tpxX11 / nh, '.5f') + 'j;'
            zm = format(self.base.tpxR12 / nh, '.5f') + '+' + format(self.base.tpxX12 / nh, '.5f') + 'j;'
            amps = format(self.base.tpxAMP * nh, '.1f') + ';'
            params = {"z11": zs,
                      "z22": zs,
                      "z12": zm,
                      "rating.summer.continuous": amps}
            self.glm.add_object("triplex_line_configuration", name, params)

            name = key + '_tpx'
            params = {"phases": phs + 'S',
                      "from": key + '_tn',
                      "to": key + '_mtr',
                      "length": 50,
                      "configuration": key + '_tpxconfig'}
            self.glm.add_object("triplex_line", name, params)

            if 'A' in phs:
                vstart = str(v_sec) + '+0.0j;'
            elif 'B' in phs:
                vstart = format(-0.5 * v_sec, '.2f') + format(-0.866025 * v_sec, '.2f') + 'j;'
            else:
                vstart = format(-0.5 * v_sec, '.2f') + '+' + format(0.866025 * v_sec, '.2f') + 'j;'

            t_name = key + '_tn'
            params = {"phases": phs + 'S',
                      "voltage_1": vstart,
                      "voltage_2": vstart,
                      "voltage_N": 0,
                      "nominal_voltage": format(v_sec, '.1f')}
            self.glm.add_object("triplex_node", t_name, params)

            t_name = key + '_mtr'
            params = {"phases": phs + 'S',
                      "voltage_1": vstart,
                      "voltage_2": vstart,
                      "voltage_N": 0,
                      "nominal_voltage": format(v_sec, '.1f')}
            self.glm.add_tariff(params)
            self.glm.add_object("triplex_meter", t_name, params)
            self.glm.add_collector(t_name, "meter")

    def connect_ercot_commercial(self):
        """For the reduced-order ERCOT feeders, add a billing meter to the 
        commercial load points, except small ZIPLOADs
        """
        meters_added = set()
        for key in self.base.comm_loads:
            mtr = self.base.comm_loads[key][0]
            comm_type = self.base.comm_loads[key][1]
            if comm_type == 'ZIPLOAD':
                continue
            phases = self.base.comm_loads[key][5]
            vln = float(self.base.comm_loads[key][6])
            idx = mtr.rfind('_')
            parent = mtr[:idx]
            if mtr not in meters_added:
                meters_added.add(mtr)
                params = {"parent": parent,
                          "phases": phases,
                          "nominal_voltage": format(vln, '.1f')}
                self.glm.add_tariff(params)
                self.glm.add_object("meter", mtr, params)
                self.glm.add_collector(mtr, "meter")

    def add_ercot_small_loads(self, basenode: str, v_nom:float):
        """For the reduced-order ERCOT feeders, write loads that are too small 
        for houses

        Args:
          basenode (str): the GridLAB-D node name
          v_nom (float): the primary line-to-neutral voltage
        """
        kva = float(self.base.small_nodes[basenode][0])
        phs = self.base.small_nodes[basenode][1]
        parent = self.base.small_nodes[basenode][2]
        cls = self.base.small_nodes[basenode][3]
        if 'A' in phs:
            voltage = "voltage_A"
            v_voltage = str(v_nom) + '+0.0j;'
            power = 'constant_power_A_real'
            v_power = format(1000.0 * kva, '.2f')
        elif 'B' in phs:
            voltage = "voltage_B"
            v_voltage = format(-0.5 * v_nom, '.2f') + format(-0.866025 * v_nom, '.2f') + 'j'
            power = 'constant_power_B_real'
            v_power = format(1000.0 * kva, '.2f')
        else:
            voltage = "voltage_C"
            v_voltage = format(-0.5 * v_nom, '.2f') + '+' + format(0.866025 * v_nom, '.2f') + 'j'
            power = 'constant_power_C_real'
            v_power = format(1000.0 * kva, '.2f')

        params = {"parent": parent,
                  "phases": phs,
                  "nominal_voltage": str(v_nom),
                  "load_class": cls,
                  voltage: v_voltage,
                  power: v_power}
        self.glm.add_object("load", basenode, params)

    def identify_ercot_houses(self, model: dict, h: dict, t: str, avgHouse: float, rgn: int):
        """For the reduced-order ERCOT feeders, scan each primary load to 
        determine the number of houses it should have. Looks at the primary 
        loads, not the service transformers.
        TODO: not all variables are used in function

        Args:
            model (dict): the parsed GridLAB-D model
            h (dict): the object ID hash
            t (str): the GridLAB-D class name to scan
            avgHouse (float): the average house load in kva
            rgn (int): the region number, 1..5
        """
        print('Average ERCOT House {}, region number {}'.format(avgHouse, rgn))
        total_houses = {'A': 0, 'B': 0, 'C': 0}
        total_small = {'A': 0, 'B': 0, 'C': 0}
        total_small_kva = {'A': 0, 'B': 0, 'C': 0}
        total_sf = 0
        total_apt = 0
        total_mh = 0
        if t in model:
            for o in model[t]:
                name = o
                node = o
                parent = model[t][o]['parent']
                for phs in ['A', 'B', 'C']:
                    tok = 'constant_power_' + phs
                    key = node + '_' + phs
                    if tok in model[t][o]:
                        kva = parse_kva(model[t][o][tok])
                        nh = 0
                        cls = 'U'
                        # don't populate houses onto A, C, I or U load_class nodes
                        if 'load_class' in model[t][o]:
                            cls = model[t][o]['load_class']
                            if cls == 'R':
                                if (kva > 1.0):
                                    nh = int((kva / avgHouse) + 0.5)
                                    total_houses[phs] += nh
                        if nh > 0:
                            lg_v_sm = kva / avgHouse - nh  # >0 if we rounded down the number of houses
                            bldg, ti = self.selectResidentialBuilding(self.base.rgnThermalPct[rgn - 1],
                                                                      np.random.uniform(0, 1))
                            if bldg == 0:
                                total_sf += nh
                            elif bldg == 1:
                                total_apt += nh
                            else:
                                total_mh += nh
                            # parent is the primary node, only for ERCOT
                            self.base.house_nodes[key] = [nh, rgn, lg_v_sm, phs, bldg, ti, parent]
                        elif kva > 0.1:
                            total_small[phs] += 1
                            total_small_kva[phs] += kva
                            # parent is the primary node, only for ERCOT
                            self.base.small_nodes[key] = [kva, phs, parent, cls]

        for phs in ['A', 'B', 'C']:
            print('phase {}: {} Houses and {} Small Loads totaling {:.2f} kVA'.
                  format(phs, total_houses[phs], total_small[phs], total_small_kva[phs]))
        print('{} primary house nodes, [SF, APT, MH] = {}, {}, {}'.
              format(len(self.base.house_nodes), total_sf, total_apt, total_mh))
        for i in range(6):
            self.base.heating_bins[0][i] = round(total_sf * self.base.bldgHeatingSetpoints[0][i][0] + 0.5)
            self.base.heating_bins[1][i] = round(total_apt * self.base.bldgHeatingSetpoints[1][i][0] + 0.5)
            self.base.heating_bins[2][i] = round(total_mh * self.base.bldgHeatingSetpoints[2][i][0] + 0.5)
            self.base.cooling_bins[0][i] = round(total_sf * self.base.bldgCoolingSetpoints[0][i][0] + 0.5)
            self.base.cooling_bins[1][i] = round(total_apt * self.base.bldgCoolingSetpoints[1][i][0] + 0.5)
            self.base.cooling_bins[2][i] = round(total_mh * self.base.bldgCoolingSetpoints[2][i][0] + 0.5)

    def replace_commercial_loads(self, model: dict, h: dict, t: str, avgBuilding: float):
        """For the full-order feeders, scan each load with load_class==C to 
        determine the number of zones it should have.
        TODO: not all variables are used in this function

        Args:
            model (dict): the parsed GridLAB-D model
            h (dict): the object ID hash
            t (str): the GridLAB-D class name to scan
            avgBuilding (float): the average building in kva
        """
        print('Average Commercial Building', avgBuilding)
        total_commercial = 0
        total_comm_kva = 0
        total_zipload = 0
        total_office = 0
        total_warehouse_storage = 0
        total_big_box = 0
        total_strip_mall = 0
        total_education = 0
        total_food_service = 0
        total_food_sales = 0
        total_lodging = 0
        total_healthcare_inpatient = 0
        total_low_occupancy = 0
        sqft_kva_ratio = 0.005  # Average com building design load is 5 W/sq ft.

        if t in model:
            for o in list(model[t].keys()):
                if 'load_class' in model[t][o]:
                    select_bldg = None
                    if model[t][o]['load_class'] == 'C':
                        kva = self.accumulate_load_kva(model[t][o])
                        total_commercial += 1
                        total_comm_kva += kva
                        vln = float(model[t][o]['nominal_voltage'])
                        nphs = 0
                        phases = model[t][o]['phases']
                        if 'A' in phases:
                            nphs += 1
                        if 'B' in phases:
                            nphs += 1
                        if 'C' in phases:
                            nphs += 1
                        nzones = int((kva / avgBuilding) + 0.5)
                        target_sqft = kva / sqft_kva_ratio
                        sqft_error = -target_sqft
                        # TODO: Need a way to place all remaining buildings if this is the last/fourth feeder.
                        # TODO: Need a way to place link for j-modelica buildings on fourth feeder of Urban DSOs
                        # TODO: Need to work out what to do if we run out of commercial buildings before we get to the fourth feeder.
                        for bldg in self.base.comm_bldgs_pop:
                            if 0 >= (self.base.comm_bldgs_pop[bldg][1] - target_sqft) > sqft_error:
                                select_bldg = bldg
                                sqft_error = self.base.comm_bldgs_pop[bldg][1] - target_sqft
                        # if nzones > 14 and nphs == 3:
                        #   comm_type = 'OFFICE'
                        #   total_office += 1
                        # elif nzones > 5 and nphs > 1:
                        #   comm_type = 'BIGBOX'
                        #   total_bigbox += 1
                        # elif nzones > 0:
                        #   comm_type = 'STRIPMALL'
                        #   total_stripmall += 1
                    if select_bldg is not None:
                        comm_name = select_bldg
                        comm_type = self.base.comm_bldgs_pop[select_bldg][0]
                        comm_size = self.base.comm_bldgs_pop[select_bldg][1]
                        if comm_type == 'office':
                            total_office += 1
                        elif comm_type == 'warehouse_storage':
                            total_warehouse_storage += 1
                        elif comm_type == 'big_box':
                            total_big_box += 1
                        elif comm_type == 'strip_mall':
                            total_strip_mall += 1
                        elif comm_type == 'education':
                            total_education += 1
                        elif comm_type == 'food_service':
                            total_food_service += 1
                        elif comm_type == 'food_sales':
                            total_food_sales += 1
                        elif comm_type == 'lodging':
                            total_lodging += 1
                        elif comm_type == 'healthcare_inpatient':
                            total_healthcare_inpatient += 1
                        elif comm_type == 'low_occupancy':
                            total_low_occupancy += 1

                            # code = 'total_' + comm_type + ' += 1'
                            # exec(code)
                            # my_exec(code)
                            # eval(compile(code, '<string>', 'exec'))

                            del (self.base.comm_bldgs_pop[select_bldg])
                        else:
                            if nzones > 0:
                                print('Commercial building could not be found for ', '{:.2f}'.format(kva), ' KVA load')
                            comm_name = 'streetlights'
                            comm_type = 'ZIPLOAD'
                            comm_size = 0
                            total_zipload += 1
                        mtr = gld_strict_name(model[t][o]['parent'])
                        extra_billing_meters.add(mtr)
                        self.base.comm_loads[o] = [mtr, comm_type, comm_size, kva, nphs, phases, vln,
                                                   total_commercial, comm_name]
                        del model[t][o]
        # Print commercial info
        print('Found {} commercial loads totaling {:.2f} kVA'.
              format(total_commercial, total_comm_kva))
        print('  ', total_office, 'med/small offices,')
        print('  ', total_warehouse_storage, 'warehouses,')
        print('  ', total_big_box, 'big box retail,')
        print('  ', total_strip_mall, 'strip malls,')
        print('  ', total_education, 'education,')
        print('  ', total_food_service, 'food service,')
        print('  ', total_food_sales, 'food sales,')
        print('  ', total_lodging, 'lodging,')
        print('  ', total_healthcare_inpatient, 'healthcare,')
        print('  ', total_low_occupancy, 'low occupancy,')
        print('  ', total_zipload, 'ZIP loads')
        remain_comm_kva = 0
        for bldg in self.base.comm_bldgs_pop:
            remain_comm_kva += self.base.comm_bldgs_pop[bldg][1] * sqft_kva_ratio
        print('{} commercial buildings, approximately {} kVA still to be assigned.'.
              format(len(self.base.comm_bldgs_pop), int(remain_comm_kva)))

    def identify_xfmr_houses(self, model: dict, h: dict, t: str, seg_loads: dict, avgHouse: float, rgn: int):
        """For the full-order feeders, scan each service transformer to 
        determine the number of houses it should have
        TODO: not all variables are used in this function
        Args:
            model (dict): the parsed GridLAB-D model
            h (dict): the object ID hash
            t (str): the GridLAB-D class name to scan
            seg_loads (dict): dictionary of downstream load (kva) served by each GridLAB-D link
            avgHouse (float): the average house load in kva
            rgn (int): the region number, 1..5
        """
        print('Average House', avgHouse)
        total_houses = 0
        total_sf = 0
        total_apt = 0
        total_mh = 0
        total_small = 0
        total_small_kva = 0
        if t in model:
            for o in model[t]:
                if o in seg_loads:
                    tkva = seg_loads[o][0]
                    phs = seg_loads[o][1]
                    if 'S' in phs:
                        nhouse = int((tkva / avgHouse) + 0.5)  # round to nearest int
                        name = o
                        node = gld_strict_name(model[t][o]['to'])
                        if nhouse <= 0:
                            total_small += 1
                            total_small_kva += tkva
                            self.base.small_nodes[node] = [tkva, phs]
                        else:
                            total_houses += nhouse
                            lg_v_sm = tkva / avgHouse - nhouse  # >0 if we rounded down the number of houses
                            # let's get the income level for the dso_type and state
                            dsoIncomePct = self.getDsoIncomeLevelTable()
                            inc_lev = self.selectIncomeLevel(dsoIncomePct, np.random.uniform(0, 1))
                            # let's get the vintage table for dso_type, state, and income level
                            dsoThermalPct = self.getDsoThermalTable(self.base.income_level[inc_lev])
                            bldg, ti = self.selectResidentialBuilding(dsoThermalPct, np.random.uniform(0, 1))
                            if bldg == 0:
                                total_sf += nhouse
                            elif bldg == 1:
                                total_apt += nhouse
                            else:
                                total_mh += nhouse
                            self.base.house_nodes[node] = [nhouse, rgn, lg_v_sm, phs, bldg, ti, inc_lev]
        print('{} small loads totaling {:.2f} kVA'.
              format(total_small, total_small_kva))
        print('{} houses on {} transformers, [SF, APT, MH] = [{}, {}, {}]'.
              format(total_houses, len(self.base.house_nodes), total_sf, total_apt, total_mh))
        for i in range(6):
            self.base.heating_bins[0][i] = round(total_sf * self.base.bldgHeatingSetpoints[0][i][0] + 0.5)
            self.base.heating_bins[1][i] = round(total_apt * self.base.bldgHeatingSetpoints[1][i][0] + 0.5)
            self.base.heating_bins[2][i] = round(total_mh * self.base.bldgHeatingSetpoints[2][i][0] + 0.5)
            self.base.cooling_bins[0][i] = round(total_sf * self.base.bldgCoolingSetpoints[0][i][0] + 0.5)
            self.base.cooling_bins[1][i] = round(total_apt * self.base.bldgCoolingSetpoints[1][i][0] + 0.5)
            self.base.cooling_bins[2][i] = round(total_mh * self.base.bldgCoolingSetpoints[2][i][0] + 0.5)

    def add_small_loads(self, basenode: str, v_nom: float):
        """Write loads that are too small for a house, onto a node

        Args:
            basenode (str): GridLAB-D node name
            v_nom (float): nominal line-to-neutral voltage at basenode TODO: should this be v_ln?
        """
        kva = float(self.base.small_nodes[basenode][0])
        phs = self.base.small_nodes[basenode][1]

        if 'A' in phs:
            vstart = str(v_nom) + '+0.0j'
        elif 'B' in phs:
            vstart = format(-0.5 * v_nom, '.2f') + format(-0.866025 * v_nom, '.2f') + 'j'
        else:
            vstart = format(-0.5 * v_nom, '.2f') + '+' + format(0.866025 * v_nom, '.2f') + 'j'

        tpxname = basenode + '_tpx_1'
        mtrname = basenode + '_mtr_1'
        loadname = basenode + '_load_1'
        params = {"phases": phs,
                  "nominal_voltage": str(v_nom),
                  "voltage_1": vstart,
                  "voltage_2": vstart}
        self.glm.add_object("triplex_node", basenode, params)

        params = {"from": basenode,
                  "to": mtrname,
                  "phases": phs,
                  "length": "30",
                  "configuration": self.base.triplex_configurations[0][0]}
        self.glm.add_object("triplex_line", tpxname, params)

        params = {"phases": phs,
                  "meter_power_consumption": "1+7j",
                  "nominal_voltage": str(v_nom),
                  "voltage_1": vstart,
                  "voltage_2": vstart}
        self.glm.add_tariff(params)
        self.glm.add_object("triplex_meter", mtrname, params)
        self.glm.add_collector(mtrname, "meter")

        params = {"parent": mtrname,
                  "phases": phs,
                  "nominal_voltage": str(v_nom),
                  "voltage_1": vstart,
                  "voltage_2": vstart,
                  "constant_power_12_real": "10.0",
                  "constant_power_12_reac": "8.0"}
        self.glm.add_object("triplex_load", loadname, params)

    def add_one_commercial_zone(self, bldg: dict):
        """Write one pre-configured commercial zone as a house

        Args:
            bldg (dict): dictionary of GridLAB-D house and zipload attributes
        """
        name = bldg['zonename']
        params = {"parent": bldg['parent'],
                  "groupid": bldg['groupid'],
                  "motor_model": "BASIC",
                  "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
                  "floor_area": '{:.0f}'.format(bldg['floor_area']),
                  "design_internal_gains": '{:.0f}'.format(bldg['int_gains'] * bldg['floor_area'] * 3.413),
                  "number_of_doors": '{:.0f}'.format(bldg['no_of_doors']),
                  "aspect_ratio": '{:.2f}'.format(bldg['aspect_ratio']),
                  "total_thermal_mass_per_floor_area": '{:1.2f}'.format(bldg['thermal_mass_per_floor_area']),
                  "interior_surface_heat_transfer_coeff": '{:1.2f}'.format(bldg['surface_heat_trans_coeff']),
                  "interior_exterior_wall_ratio": '{:.2f}'.format(bldg['interior_exterior_wall_ratio']),
                  "exterior_floor_fraction": '{:.3f}'.format(bldg['exterior_floor_fraction']),
                  "exterior_ceiling_fraction": '{:.3f}'.format(bldg['exterior_ceiling_fraction']),
                  "Rwall": str(bldg['Rwall']),
                  "Rroof": str(bldg['Rroof']),
                  "Rfloor": str(bldg['Rfloor']),
                  "Rdoors": str(bldg['Rdoors']),
                  "exterior_wall_fraction": '{:.2f}'.format(bldg['exterior_wall_fraction']),
                  "glazing_layers": '{:s}'.format(bldg['glazing_layers']),
                  "glass_type": '{:s}'.format(bldg['glass_type']),
                  "glazing_treatment": '{:s}'.format(bldg['glazing_treatment']),
                  "window_frame": '{:s}'.format(bldg['window_frame']),
                  "airchange_per_hour": '{:.2f}'.format(bldg['airchange_per_hour']),
                  "window_wall_ratio": '{:0.3f}'.format(bldg['window_wall_ratio']),
                  "heating_system_type": '{:s}'.format(bldg['heat_type']),
                  "auxiliary_system_type": '{:s}'.format(bldg['aux_type']),
                  "fan_type": '{:s}'.format(bldg['fan_type']),
                  "cooling_system_type": '{:s}'.format(bldg['cool_type']),
                  "air_temperature": '{:.2f}'.format(bldg['init_temp']),
                  "mass_temperature": '{:.2f}'.format(bldg['init_temp']),
                  "over_sizing_factor": '{:.1f}'.format(bldg['os_rand']),
                  "cooling_COP": '{:2.2f}'.format(bldg['COP_A']),
                  "cooling_setpoint": '80.0',
                  "heating_setpoint": '60.0'}
        self.glm.add_object("house", name, params)

        params = {"parent": name,
                  "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
                  "heatgain_fraction": "0.8",
                  "power_fraction": '{:.2f}'.format(bldg['c_p_frac']),
                  "impedance_fraction": 'impedance_fraction {:.2f}'.format(bldg['c_z_frac']),
                  "current_fraction": '{:.2f}'.format(bldg['c_i_frac']),
                  "power_pf": '{:.2f}'.format(bldg['c_p_pf']),
                  "current_pf": '{:.2f}'.format(bldg['c_i_pf']),
                  "impedance_pf": '{:.2f}'.format(bldg['c_z_pf']),
                  "base_power": '{:.2f}'.format(bldg['base_schedule'], bldg['adj_lights'])}
        self.glm.add_object("ZIPload", "lights", params)

        params = {"parent": name,
                  "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
                  "heatgain_fraction": "0.9",
                  "power_fraction": '{:.2f}'.format(bldg['c_p_frac']),
                  "impedance_fraction": '{:.2f}'.format(bldg['c_z_frac']),
                  "current_fraction": '{:.2f}'.format(bldg['c_i_frac']),
                  "power_pf": '{:.2f}'.format(bldg['c_p_pf']),
                  "current_pf": '{:.2f}'.format(bldg['c_i_pf']),
                  "impedance_pf": '{:.2f}'.format(bldg['c_z_pf']),
                  "base_power": '{:.2f}'.format(bldg['base_schedule'], bldg['adj_plugs'])}
        self.glm.add_object("ZIPload", "plug loads", params)

        params = {"parent": name,
                  "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
                  "heatgain_fraction": "1.0",
                  "power_fraction": "0",
                  "impedance_fraction": "0",
                  "current_fraction": "0",
                  "power_pf": "1",
                  "base_power": '{:.2f}'.format(bldg['base_schedule'], bldg['adj_gas'])}
        self.glm.add_object("ZIPload", "gas waterheater", params)

        params = {"parent": name,
                  "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
                  "heatgain_fraction": "0.0",
                  "power_fraction": '{:.2f}'.format(bldg['c_p_frac']),
                  "impedance_fraction": '{:.2f}'.format(bldg['c_z_frac']),
                  "current_fraction": '{:.2f}'.format(bldg['c_i_frac']),
                  "power_pf": '{:.2f}'.format(bldg['c_p_pf']),
                  "current_pf": '{:.2f}'.format(bldg['c_i_pf']),
                  "impedance_pf": '{:.2f}'.format(bldg['c_z_pf']),
                  "base_power": '{:s}_exterior*{:.2f};'.format(bldg['base_schedule'], bldg['adj_ext'])}
        self.glm.add_object("ZIPload", "exterior lights", params)

        params = {"parent": name,
                  "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
                  "heatgain_fraction": "1.0",
                  "power_fraction": "0",
                  "impedance_fraction": "0",
                  "current_fraction": "0",
                  "power_pf": "1",
                  "base_power": '{:s}_occupancy*{:.2f}'.format(bldg['base_schedule'], bldg['adj_occ'])}
        self.glm.add_object("ZIPload", "occupancy", params)

        if bldg['adj_refrig'] != 0:
            # TODO: set to 0.01 to avoid a divide by zero issue in the agent code.
            #  Should be set to zero after that is fixed.
            params = {"heatgain_fraction": "0.01",
                      "power_fraction": '{:.2f}'.format(bldg['c_p_frac']),
                      "impedance_fraction": '{:.2f};'.format(bldg['c_z_frac']),
                      "current_fraction": '{:.2f};'.format(bldg['c_i_frac']),
                      "power_pf": '{:.2f};'.format(bldg['c_p_pf']),
                      "current_pf": '{:.2f};'.format(bldg['c_i_pf']),
                      "impedance_pf": '{:.2f};'.format(bldg['c_z_pf']),
                      "base_power": '{:.2f};'.format(bldg['adj_refrig'])}
            self.glm.add_object("ZIPload", "large refrigeration", params)

        self.glm.add_collector(name, "house")

    def add_commercial_loads(self, rgn: int, key: str):
        """Put commercial building zones and ZIP loads into the model

        Args:
            rgn (int): region 1..5 where the building is located
            key (str): GridLAB-D load name that is being replaced
        """
        mtr = self.base.comm_loads[key][0]
        comm_type = self.base.comm_loads[key][1]
        nz = int(self.base.comm_loads[key][2])
        kva = float(self.base.comm_loads[key][3])
        nphs = int(self.base.comm_loads[key][4])
        phases = self.base.comm_loads[key][5]
        vln = float(self.base.comm_loads[key][6])
        loadnum = int(self.base.comm_loads[key][7])

        print('load', key, 'mtr', mtr, 'type', comm_type, 'nz', nz, 'kVA', '{:.3f}'.format(kva),
              'nphs', nphs, 'phases', phases, 'vln', '{:.3f}'.format(vln))

        bldg = {'parent': key,
                'mtr': mtr,
                'groupid': comm_type + '_' + str(loadnum),
                'fan_type': 'ONE_SPEED',
                'heat_type': 'GAS',
                'cool_type': 'ELECTRIC',
                'aux_type': 'NONE',
                'no_of_stories': 1,
                'surface_heat_trans_coeff': 0.59,
                'oversize': self.base.over_sizing_factor[rgn - 1],
                'glazing_layers': 'TWO',
                'glass_type': 'GLASS',
                'glazing_treatment': 'LOW_S',
                'window_frame': 'NONE',
                'c_z_frac': self.base.c_z_frac,
                'c_i_frac': self.base.c_i_frac,
                'c_p_frac': 1.0 - self.base.c_z_frac - self.base.c_i_frac,
                'c_z_pf': self.base.c_z_pf,
                'c_i_pf': self.base.c_i_pf,
                'c_p_pf': self.base.c_p_pf}

        if comm_type == 'OFFICE':
            bldg['ceiling_height'] = 13.0
            bldg['airchange_per_hour'] = 0.69
            bldg['Rroof'] = 19.0
            bldg['Rwall'] = 18.3
            bldg['Rfloor'] = 46.0
            bldg['Rdoors'] = 3.0
            bldg['int_gains'] = 3.24  # W/sf
            bldg['thermal_mass_per_floor_area'] = 1  # TODO
            bldg['exterior_ceiling_fraction'] = 1  # TODO
            bldg['base_schedule'] = 'office'
            num_offices = int(round(nz / 15))  # each with 3 floors of 5 zones
            for jjj in range(num_offices):
                floor_area_choose = 40000. * (0.5 * np.random.random() + 0.5)
                for floor in range(1, 4):
                    bldg['skew_value'] = self.glm.randomize_commercial_skew()
                    total_depth = math.sqrt(floor_area_choose / (3. * 1.5))
                    total_width = 1.5 * total_depth
                    if floor == 3:
                        bldg['exterior_ceiling_fraction'] = 1
                    else:
                        bldg['exterior_ceiling_fraction'] = 0
                    for zone in range(1, 6):
                        if zone == 5:
                            bldg['window_wall_ratio'] = 0  # this was not in the CCSI version
                            bldg['exterior_wall_fraction'] = 0
                            w = total_depth - 30.
                            d = total_width - 30.
                        else:
                            bldg['window_wall_ratio'] = 0.33
                            d = 15.
                            if zone == 1 or zone == 3:
                                w = total_width - 15.
                            else:
                                w = total_depth - 15.
                            bldg['exterior_wall_fraction'] = w / (2. * (w + d))

                        floor_area = w * d
                        bldg['floor_area'] = floor_area
                        bldg['aspect_ratio'] = w / d

                        if floor > 1:
                            bldg['exterior_floor_fraction'] = 0
                        else:
                            bldg['exterior_floor_fraction'] = w / (2. * (w + d)) / (
                                        floor_area / (floor_area_choose / 3.))

                        bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * np.random.random())
                        bldg['interior_exterior_wall_ratio'] = floor_area / (bldg['ceiling_height'] * 2. * (w + d)) - 1. \
                                                               + bldg['window_wall_ratio'] * bldg[
                                                                   'exterior_wall_fraction']

                        # will round to zero, presumably the exterior doors are treated like windows
                        bldg['no_of_doors'] = 0.1
                        bldg['init_temp'] = 68. + 4. * np.random.random()
                        bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
                        bldg['COP_A'] = self.base.cooling_COP * (0.8 + 0.4 * np.random.random())

                        # randomize 10# then convert W/sf -> kW
                        bldg['adj_lights'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
                        bldg['adj_plugs'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
                        bldg['adj_gas'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
                        bldg['adj_ext'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
                        bldg['adj_occ'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.

                        bldg['zonename'] = gld_strict_name(
                            key + '_bldg_' + str(jjj + 1) + '_floor_' + str(floor) + '_zone_' + str(zone))
                        self.add_one_commercial_zone(bldg)

        elif comm_type == 'BIGBOX':
            bldg['ceiling_height'] = 14.
            bldg['airchange_per_hour'] = 1.5
            bldg['Rroof'] = 19.
            bldg['Rwall'] = 18.3
            bldg['Rfloor'] = 46.
            bldg['Rdoors'] = 3.
            bldg['int_gains'] = 3.6  # W/sf
            bldg['thermal_mass_per_floor_area'] = 1  # TODO
            bldg['exterior_ceiling_fraction'] = 1  # TODO
            bldg['base_schedule'] = 'bigbox'

            num_bigboxes = int(round(nz / 6.))
            for jjj in range(num_bigboxes):
                bldg['skew_value'] = self.glm.randomize_commercial_skew()
                floor_area_choose = 20000. * (0.5 + 1. * np.random.random())
                floor_area = floor_area_choose / 6.
                bldg['floor_area'] = floor_area
                bldg['thermal_mass_per_floor_area'] = 3.9 * (0.8 + 0.4 * np.random.random())  # +/- 20#
                bldg['exterior_ceiling_fraction'] = 1.
                bldg['aspect_ratio'] = 1.28301275561855
                total_depth = math.sqrt(floor_area_choose / bldg['aspect_ratio'])
                total_width = bldg['aspect_ratio'] * total_depth
                d = total_width / 3.
                w = total_depth / 2.

                for zone in range(1, 7):
                    if zone == 2 or zone == 5:
                        bldg['exterior_wall_fraction'] = d / (2. * (d + w))
                        bldg['exterior_floor_fraction'] = (0. + d) / (2. * (total_width + total_depth)) / (
                                floor_area / floor_area_choose)
                    else:
                        bldg['exterior_wall_fraction'] = 0.5
                        bldg['exterior_floor_fraction'] = (w + d) / (2. * (total_width + total_depth)) / (
                                floor_area / floor_area_choose)
                    if zone == 2:
                        bldg['window_wall_ratio'] = 0.76
                    else:
                        bldg['window_wall_ratio'] = 0.

                    if zone < 4:
                        bldg['no_of_doors'] = 0.1  # this will round to 0
                    elif zone == 5:
                        bldg['no_of_doors'] = 24.
                    else:
                        bldg['no_of_doors'] = 1.

                    bldg['interior_exterior_wall_ratio'] = (floor_area + bldg['no_of_doors'] * 20.) \
                                                           / (bldg['ceiling_height'] * 2. * (w + d)) - 1. + bldg[
                                                               'window_wall_ratio'] * bldg['exterior_wall_fraction']
                    bldg['init_temp'] = 68. + 4. * np.random.random()
                    bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
                    bldg['COP_A'] = self.base.cooling_COP * (0.8 + 0.4 * np.random.random())

                    bldg['adj_lights'] = 1.2 * (
                            0.9 + 0.1 * np.random.random()) * floor_area / 1000.  # randomize 10# then convert W/sf -> kW
                    bldg['adj_plugs'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
                    bldg['adj_gas'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
                    bldg['adj_ext'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
                    bldg['adj_occ'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.

                    bldg['zonename'] = gld_strict_name(key + '_bldg_' + str(jjj + 1) + '_zone_' + str(zone))
                    self.add_one_commercial_zone(bldg)

        elif comm_type == 'STRIPMALL':
            bldg['ceiling_height'] = 12  # T)D)
            bldg['airchange_per_hour'] = 1.76
            bldg['Rroof'] = 19.0
            bldg['Rwall'] = 18.3
            bldg['Rfloor'] = 40.0
            bldg['Rdoors'] = 3.0
            bldg['int_gains'] = 3.6  # W/sf
            bldg['exterior_ceiling_fraction'] = 1.
            bldg['base_schedule'] = 'stripmall'
            midzone = int(math.floor(nz / 2.0) + 1.)
            for zone in range(1, nz + 1):
                bldg['skew_value'] = self.glm.randomize_commercial_skew()
                floor_area_choose = 2400.0 * (0.7 + 0.6 * np.random.random())
                bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * np.random.random())
                bldg['no_of_doors'] = 1
                if zone == 1 or zone == midzone:
                    floor_area = floor_area_choose
                    bldg['aspect_ratio'] = 1.5
                    bldg['window_wall_ratio'] = 0.05
                    bldg['exterior_wall_fraction'] = 0.4
                    bldg['exterior_floor_fraction'] = 0.8
                    bldg['interior_exterior_wall_ratio'] = -0.05
                else:
                    floor_area = floor_area_choose / 2.0
                    bldg['aspect_ratio'] = 3.0
                    bldg['window_wall_ratio'] = 0.03
                    if zone == nz:
                        bldg['exterior_wall_fraction'] = 0.63
                        bldg['exterior_floor_fraction'] = 2.0
                    else:
                        bldg['exterior_wall_fraction'] = 0.25
                        bldg['exterior_floor_fraction'] = 0.8
                    bldg['interior_exterior_wall_ratio'] = -0.40

                bldg['floor_area'] = floor_area
                bldg['init_temp'] = 68.0 + 4.0 * np.random.random()
                bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
                bldg['COP_A'] = self.base.cooling_COP * (0.8 + 0.4 * np.random.random())
                bldg['adj_lights'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.0
                bldg['adj_plugs'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.0
                bldg['adj_gas'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.0
                bldg['adj_ext'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.0
                bldg['adj_occ'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.0
                bldg['zonename'] = gld_strict_name(key + '_zone_' + str(zone))
                self.add_one_commercial_zone(bldg)

        if comm_type == 'ZIPLOAD':
            phsva = 1000.0 * kva / nphs
            name = '{:s}'.format(key + '_streetlights')
            params = {"parent": '{:s};'.format(mtr),
                      "groupid": "STREETLIGHTS",
                      "nominal_voltage": '{:2f}'.format(vln),
                      "phases": '{:s}'.format(phases)}
            for phs in ['A', 'B', 'C']:
                if phs in phases:
                    params["impedance_fraction_" + phs] = '{:f};'.format(self.base.c_z_frac)
                    params["current_fraction_" + phs] = '{:f}'.format(self.base.c_i_frac)
                    params["power_fraction_" + phs] = '{:f}'.format(bldg['c_p_frac'])
                    params["impedance_pf_" + phs] = '{:f}'.format(self.base.c_z_pf)
                    params["current_pf_" + phs] = '{:f}'.format(self.base.c_i_pf)
                    params["power_pf_" + phs] = '{:f}'.format(self.base.c_p_pf)
                    params["base_power_" + phs] = '{:.2f}'.format(self.base.light_scalar_comm * phsva)
            self.glm.add_object("load", name, params)
        else:
            name = '{:s}'.format(key)
            params = {"parent": '{:s};'.format(mtr),
                      "groupid": '{:s}'.format(comm_type),
                      "nominal_voltage": '{:2f}'.format(vln),
                      "phases": '{:s}'.format(phases)}
            self.glm.add_object("load", name, params)

    def add_houses(self, basenode: str, v_nom: float, bIgnoreThermostatSchedule=True, bWriteService=True, bTriplex=True, setpoint_offset=1.0, fg_recs_dataset=None):
        """Put houses, along with solar panels and batteries, onto a node
        TODO: not all variables are used in this function
        
        Args: TODO
            basenode (str): GridLAB-D node name
            v_nom (float): nominal line-to-neutral voltage at basenode
            bIgnoreThermostatSchedule (bool, optional): _description_. Defaults to True.
            bWriteService (bool, optional): _description_. Defaults to True.
            bTriplex (bool, optional): _description_. Defaults to True.
            setpoint_offset (float, optional): _description_. Defaults to 1.0.
            fg_recs_dataset (_type_, optional): _description_. Defaults to None.

        Raises:
            ValueError: _description_
            UserWarning: _description_
            UserWarning: _description_
            UserWarning: _description_
            UserWarning: _description_
        """

        if fg_recs_dataset is None:
            nhouse = int(self.base.house_nodes[basenode][0])
        else:
            housing_type, year_made_range = fg_recs_dataset.get_house_type_vintage(self.base.recs_state,
                                                                                   self.base.recs_income_level,
                                                                                   self.base.recs_housing_density)
            SQFTRANGE = fg_recs_dataset.get_parameter_sample(self.base.recs_state,
                                                             self.base.recs_income_level,
                                                             self.base.recs_housing_density,
                                                             housing_type[0], year_made_range[0], "SQFTRANGE")
            nhouse = fg_recs_dataset.calc_building_count(self.base.recs_state,
                                                         self.base.recs_income_level,
                                                         self.base.recs_housing_density,
                                                         housing_type[0], year_made_range[0])

        rgn = int(self.base.house_nodes[basenode][1])
        lg_v_sm = float(self.base.house_nodes[basenode][2])
        phs = self.base.house_nodes[basenode][3]
        bldg = self.base.house_nodes[basenode][4]
        ti = self.base.house_nodes[basenode][5]
        inc_lev = self.base.house_nodes[basenode][6]
        # rgnTable = self.base.rgnThermalPct[rgn-1]

        if 'A' in phs:
            vstart = str(v_nom) + '+0.0j'
        elif 'B' in phs:
            vstart = format(-0.5 * v_nom, '.2f') + format(-0.866025 * v_nom, '.2f') + 'j'
        else:
            vstart = format(-0.5 * v_nom, '.2f') + '+' + format(0.866025 * v_nom, '.2f') + 'j'

        tpxname = gld_strict_name(basenode + '_tpx')
        mtrname = gld_strict_name(basenode + '_mtr')
        if self.base.forERCOT == "True":
            phs = phs + 'S'
        else:
            params = {"phases": phs,
                      "nominal_voltage": str(v_nom),
                      "voltage_1": vstart,
                      "voltage_2": vstart}
            self.glm.add_object("triplex_node", basenode, params)
        for i in range(nhouse):
            tpxname1 = tpxname + '_' + str(i + 1)
            mtrname1 = mtrname + '_' + str(i + 1)
            hsename = gld_strict_name(basenode + '_hse_' + str(i + 1))
            hse_m_name = gld_strict_name(basenode + '_mhse_' + str(i + 1))
            whname = gld_strict_name(basenode + '_wh_' + str(i + 1))
            solname = gld_strict_name(basenode + '_sol_' + str(i + 1))
            batname = gld_strict_name(basenode + '_bat_' + str(i + 1))
            evname = gld_strict_name(basenode + '_ev_' + str(i + 1))
            sol_i_name = gld_strict_name(basenode + '_isol_' + str(i + 1))
            bat_i_name = gld_strict_name(basenode + '_ibat_' + str(i + 1))
            sol_m_name = gld_strict_name(basenode + '_msol_' + str(i + 1))
            bat_m_name = gld_strict_name(basenode + '_mbat_' + str(i + 1))
            if self.base.forERCOT:
                params = {"parent": mtrname,
                          "phases": phs,
                          "meter_power_consumption": "1+7j",
                          "nominal_voltage": str(v_nom),
                          "voltage_1": vstart,
                          "voltage_2": vstart}
                self.glm.add_tariff(params)
                self.glm.add_object("triplex_meter", mtrname1, params)
                self.glm.add_collector(mtrname, "meter")

                params = {"parent": mtrname,
                          "phases": phs,
                          "nominal_voltage": str(v_nom)}
                self.glm.add_object("triplex_meter", hse_m_name, params)
            else:
                params = {"from": basenode,
                          "to": mtrname1,
                          "phases": phs,
                          "length": "30",
                          "configuration": self.base.name_prefix + self.base.triplex_configurations[0][0]}
                self.glm.add_object("triplex_line", tpxname, params)

                params = {"phases": phs,
                          "meter_power_consumption": "1+7j",
                          "nominal_voltage": str(v_nom),
                          "voltage_1": vstart,
                          "voltage_2": vstart}
                self.glm.add_tariff(params)
                self.glm.add_object("triplex_meter", mtrname1, params)
                self.glm.add_collector(mtrname, "meter")

                params = {"parent": mtrname1,
                          "phases": phs,
                          "nominal_voltage": str(v_nom)}
                self.glm.add_object("triplex_meter", hse_m_name, params)

        # ************* Floor area, ceiling height and stories *************************
        fa_array = {}  # distribution array for floor area min, max, mean, standard deviation
        stories = 1
        ceiling_height = 8
        vint = self.base.vint_type[ti]
        income = self.base.income_level[inc_lev]

        if bldg == 0:  # SF
            fa_bldg = 'single_family_detached'  # then pick single_Family_detached values for floor_area
            if (np.random.uniform(0, 1) >
                    self.base.res_bldg_metadata['num_stories'][self.base.state][self.base.dso_type][income][fa_bldg][vint]['one_story']):
                stories = 2  # all SF homes which are not single story are 2 stories
            if np.random.uniform(0, 1) <= \
                    self.base.res_bldg_metadata['high_ceilings'][self.base.state][self.base.dso_type][income][fa_bldg][vint]:
                ceiling_height = 10  # all SF homes that have high ceilings are 10 ft
            ceiling_height += np.random.randint(0, 2)
        elif bldg == 1:  # apartments
            fa_bldg = 'apartment_2_4_units'  # then pick apartment_2_4_units for floor area
        elif bldg == 2:  # mh
            fa_bldg = 'mobile_home'
        else:
            raise ValueError("Wrong building type chosen !")

        vint = self.base.vint_type[ti]
        # creating distribution array for floor_area
        for ind in ['min', 'max', 'mean', 'standard_deviation']:
            fa_array[ind] = self.base.res_bldg_metadata['floor_area'][self.base.state][self.base.dso_type][income][fa_bldg][ind]
            # next_ti = ti
            # while not fa_array[ind]:  # if value is null/None, check the next vintage bin
            #     next_ti += 1
            #     fa_array[ind] = res_bldg_metadata['floor_area'][ind][fa_bldg][vint_type[next_ti]]
        # print(i)
        # print(nhouse)
        floor_area = random_norm_trunc(fa_array)  # truncated normal distribution
        floor_area = (1 + lg_v_sm) * floor_area  # adjustment depends on whether nhouses rounded up or down
        fa_rand = np.random.uniform(0, 1)
        if floor_area > 6000:  # TODO: do we need this condition ? it was originally 4000
            floor_area = 5800 + fa_rand * 200
        elif floor_area < 300:
            floor_area = 300 + fa_rand * 100
        floor_area = (1 + lg_v_sm) * floor_area  # adjustment depends on whether nhouses rounded up or down

        fa_rand = np.random.uniform(0, 1)
        if floor_area > 6000:  # TODO: do we need this condition ? it was originally 4000
            floor_area = 5800 + fa_rand * 200
        elif floor_area < 300:
            floor_area = 300 + fa_rand * 100

        scalar1 = 324.9 / 8907 * floor_area ** 0.442
        scalar2 = 0.6 + 0.4 * np.random.uniform(0, 1)
        scalar3 = 0.6 + 0.4 * np.random.uniform(0, 1)
        resp_scalar = scalar1 * scalar2
        unresp_scalar = scalar1 * scalar3

        skew_value = self.glm.randomize_residential_skew()

        #  *************** Aspect ratio, ewf, ecf, eff, wwr ****************************
        if bldg == 0:  # SF homes
            # min, max, mean, std
            dist_array = self.base.res_bldg_metadata['aspect_ratio']['single_family']
            aspect_ratio = random_norm_trunc(dist_array)
            # Exterior wall and ceiling and floor fraction
            # A normal single family house has all walls exterior, has a ceiling and a floor
            ewf = 1  # exterior wall fraction
            ecf = 1  # exterior ceiling fraction
            eff = 1  # exterior floor fraction
            # window wall ratio
            wwr = (self.base.res_bldg_metadata['window_wall_ratio']['single_family']['mean'])
        elif bldg == 1:  # APT
            # min, max, mean, std
            dist_array = self.base.res_bldg_metadata['aspect_ratio']['apartments']
            aspect_ratio = random_norm_trunc(dist_array)
            # window wall ratio
            wwr = (self.base.res_bldg_metadata['window_wall_ratio']['apartments']['mean'])
            # Two type of apts assumed:
            #       1. small apt: 8 units with 4 units on each level: total 2 levels
            #       2. large apt: 16 units with 8 units on each level: total 2 levels
            # Let's decide if this unit belongs to a small apt (8 units) or large (16 units)
            small_apt_pct = self.base.res_bldg_metadata['housing_type'][self.base.state][
                self.base.dso_type][income]['apartment_2_4_units']
            large_apt_pct = self.base.res_bldg_metadata['housing_type'][self.base.state][
                self.base.dso_type][income]['apartment_5_units']
            if np.random.uniform(0, 1) < small_apt_pct / (small_apt_pct + large_apt_pct):
                # 2-level small apt (8 units)
                # in these apt, all 4 upper units are identical and all 4 lower units are identical
                # So, only two types of units: upper and lower (50% chances of each)
                # all units have 50% walls exterior
                ewf = 0.5
                # for 50% units: has floor but no ceiling
                if np.random.uniform(0, 1) < 0.5:
                    ecf = 0
                    eff = 1
                else:  # for other 50% units: has ceiling but not floor
                    ecf = 1
                    eff = 0
            else:
                # double-loaded (2-level) 16 units apts
                # In these apts, there are 4 type of units: 4 corner bottom floor, 4 corner upper,
                # 4 middle upper and 4 middle lower floor units. Each unit type has 25% chances
                if np.random.uniform(0, 1) < 0.25:  # 4: corner bottom floor units
                    ewf = 0.5
                    ecf = 0
                    eff = 1
                elif np.random.uniform(0, 1) < 0.5:  # 4: corner upper floor units
                    ewf = 0.5
                    ecf = 1
                    eff = 0
                elif np.random.uniform(0, 1) < 0.75:  # 4: middle bottom floor units
                    ewf = aspect_ratio / (1 + aspect_ratio) / 2
                    ecf = 0
                    eff = 1
                else:  # np.random.uniform(0, 1) < 1  # 4: middle upper floor units
                    ewf = aspect_ratio / (1 + aspect_ratio) / 2
                    ecf = 1
                    eff = 0
        else:  # bldg == 2  # Mobile Homes
            # select between single and double wide
            wwr = (self.base.res_bldg_metadata['window_wall_ratio']['mobile_home']['mean'])  # window wall ratio
            # sw_pct = res_bldg_metadata['mobile_home_single_wide'][state][dso_type][income]  # single wide percentage for given vintage bin
            # next_ti = ti
            # while not sw_pct:  # if the value is null or 'None', check the next vintage bin
            #     next_ti += 1
            #     sw_pct = res_bldg_metadata['mobile_home_single_wide'][vint_type[next_ti]]
            if floor_area <= 1080:  # Single wide
                aspect_ratio = random_norm_trunc(
                    self.base.res_bldg_metadata['aspect_ratio']['mobile_home_single_wide'])
            else:  # double wide
                aspect_ratio = random_norm_trunc(
                    self.base.res_bldg_metadata['aspect_ratio']['mobile_home_double_wide'])
            # A normal MH has all walls exterior, has a ceiling and a floor
            ewf = 1  # exterior wall fraction
            ecf = 1  # exterior ceiling fraction
            eff = 1  # exterior floor fraction

        # oversize = rgnOversizeFactor[rgn-1] * (0.8 + 0.4 * np.random.uniform(0,1))
        # data from https://collaborate.pnl.gov/projects/Transactive/Shared%20Documents/DSO+T/Setup%20Assumptions%205.3/Residential%20HVAC.xlsx
        oversize = random_norm_trunc(
            self.base.res_bldg_metadata['hvac_oversize'])  # hvac_oversize factor
        wetc = random_norm_trunc(
            self.base.res_bldg_metadata['window_shading'])  # window_exterior_transmission_coefficient

        tiProps = self.selectThermalProperties(bldg, ti)
        # Rceiling(roof), Rwall, Rfloor, WindowLayers, WindowGlass,Glazing,WindowFrame,Rdoor,AirInfil,COPhi,COPlo
        Rroof = tiProps[0] * (0.8 + 0.4 * np.random.uniform(0, 1))
        Rwall = tiProps[1] * (0.8 + 0.4 * np.random.uniform(0, 1))
        Rfloor = tiProps[2] * (0.8 + 0.4 * np.random.uniform(0, 1))
        glazing_layers = int(tiProps[3])
        glass_type = int(tiProps[4])
        glazing_treatment = int(tiProps[5])
        window_frame = int(tiProps[6])
        Rdoor = tiProps[7] * (0.8 + 0.4 * np.random.uniform(0, 1))
        airchange = tiProps[8] * (0.8 + 0.4 * np.random.uniform(0, 1))
        init_temp = 68 + 4 * np.random.uniform(0, 1)
        mass_floor = 2.5 + 1.5 * np.random.uniform(0, 1)
        mass_solar_gain_frac = 0.5
        mass_int_gain_frac = 0.5
        # ***********COP*********************************
        # pick any one year value randomly from the bin in cop_lookup
        h_COP = c_COP = np.random.choice(self.base.cop_lookup[ti]) * (
                0.9 + np.random.uniform(0, 1) * 0.2)  # +- 10% of mean value
        # h_COP = c_COP = tiProps[10] + np.random.uniform(0, 1) * (tiProps[9] - tiProps[10])

        params = {"parent": hse_m_name,
                  "groupid": self.base.bldgTypeName[bldg],
                  "schedule_skew": '{:.0f}'.format(skew_value),
                  "floor_area": '{:.0f}'.format(floor_area),
                  "number_of_stories": str(stories),
                  "ceiling_height": str(ceiling_height),
                  "over_sizing_factor": '{:.1f}'.format(oversize),
                  "Rroof": '{:.2f}'.format(Rroof),
                  "Rwall": '{:.2f}'.format(Rwall),
                  "Rfloor": '{:.2f}'.format(Rfloor),
                  "glazing_layers": str(glazing_layers),
                  "glass_type": str(glass_type),
                  "glazing_treatment": str(glazing_treatment),
                  "window_frame": str(window_frame),
                  "Rdoors": '{:.2f}'.format(Rdoor),
                  "airchange_per_hour": '{:.2f}'.format(airchange),
                  "cooling_COP": '{:.1f}'.format(c_COP),
                  "air_temperature": '{:.2f}'.format(init_temp),
                  "mass_temperature": '{:.2f}'.format(init_temp),
                  "total_thermal_mass_per_floor_area": '{:.3f}'.format(mass_floor),
                  "mass_solar_gain_fraction": '{}'.format(mass_solar_gain_frac),
                  "mass_internal_gain_fraction": '{}'.format(mass_int_gain_frac),
                  "aspect_ratio": '{:.2f}'.format(aspect_ratio),
                  "exterior_wall_fraction": '{:.2f}'.format(ewf),
                  "exterior_floor_fraction": '{:.2f}'.format(eff),
                  "exterior_ceiling_fraction": '{:.2f}'.format(ecf),
                  "window_exterior_transmission_coefficient": '{:.2f}'.format(wetc),
                  "window_wall_ratio": '{:.2f}'.format(wwr),
                  "breaker_amps": "1000", "hvac_breaker_rating": "1000"}
        heat_rand = np.random.uniform(0, 1)
        cool_rand = np.random.uniform(0, 1)
        house_fuel_type = 'electric'
        heat_pump_prob = self.base.res_bldg_metadata['space_heating_type'][self.base.state][
                             self.base.dso_type][income][fa_bldg][vint]['gas_heating'] + \
                             self.base.res_bldg_metadata['space_heating_type'][self.base.state][
                             self.base.dso_type][income][fa_bldg][vint]['heat_pump']
        # Get the air conditioning percentage for homes that don't have heat pumps
        electric_cooling_percentage = \
            self.base.res_bldg_metadata['air_conditioning'][self.base.state][
                self.base.dso_type][income][fa_bldg]

        if heat_rand <= self.base.res_bldg_metadata['space_heating_type'][self.base.state][self.base.dso_type][income][fa_bldg][vint]['gas_heating']:
            house_fuel_type = 'gas'
            params["heating_system_type"] = "GAS"
            if cool_rand <= electric_cooling_percentage:
                params["cooling_system_type"] = "ELECTRIC"
            else:
                params["cooling_system_type"] = "NONE"
        elif heat_rand <= self.base.rgnPenGasHeat[rgn - 1] + self.base.rgnPenHeatPump[rgn - 1]:
            params["heating_system_type"] = "HEAT_PUMP"
            params["heating_COP"] = '{:.1f}'.format(h_COP)
            params["cooling_system_type"] = "ELECTRIC"
            params["auxiliary_strategy"] = "DEADBAND"
            params["auxiliary_system_type"] = "ELECTRIC"
            params["motor_model"] = "BASIC"
            params["motor_efficiency"] = "AVERAGE"
        # TODO: check with Rob if following large home condition is needed or not:
        # elif floor_area * ceiling_height > 12000.0:  # electric heat not allowed on large homes
        #     params["heating_system_type"] =  "GAS"
        #     if cool_rand <= electric_cooling_percentage:
        #         params["cooling_system_type"] = "ELECTRIC"
        #     else:
        #         params["cooling_system_type"] = "NONE"
        else:
            params["heating_system_type"] = "RESISTANCE"
            if cool_rand <= self.base.electric_cooling_percentage:
                params["cooling_system_type"] = "ELECTRIC"
                params["motor_model"] = "BASIC"
                params["motor_efficiency"] = "GOOD"
            else:
                params["cooling_system_type"] = "NONE"

        # default heating and cooling setpoints are 70 and 75 degrees in GridLAB-D
        # we need more separation to assure no overlaps during transactive simulations
        params["cooling_setpoint"] = "80.0"
        params["heating_setpoint"] = "60.0"
        self.glm.add_object("house", hsename, params)

        # heatgain fraction, Zpf, Ipf, Ppf, Z, I, P
        params = {"parent": hsename,
                  "schedule_skew": '{:.0f}'.format(skew_value),
                  "base_power": 'responsive_loads * ' + '{:.2f}'.format(resp_scalar),
                  "heatgain_fraction": '{:.2f}'.format(self.base.techdata[0]),
                  "impedance_pf": '{:.2f}'.format(self.base.techdata[1]),
                  "current_pf": '{:.2f}'.format(self.base.techdata[2]),
                  "power_pf": '{:.2f}'.format(self.base.techdata[3]),
                  "impedance_fraction": '{:.2f}'.format(self.base.techdata[4]),
                  "current_fraction": '{:.2f}'.format(self.base.techdata[5]),
                  "power_fraction": '{:.2f}'.format(self.base.techdata[6])}
        self.glm.add_object("ZIPload", "responsive", params)

        params["base_power"] = 'unresponsive_loads * ' + '{:.2f}'.format(unresp_scalar)
        self.glm.add_object("ZIPload", "unresponsive", params)

        # if np.random.uniform (0, 1) <= self.base.water_heater_percentage:
        # Determine if house has matching heating types for space and water
        if np.random.uniform(0, 1) <= \
                self.base.res_bldg_metadata['water_heating_type'][self.base.state][
                    self.base.dso_type][income][fa_bldg][vint]:
            wh_fuel_type = house_fuel_type
        elif house_fuel_type == 'gas':
            wh_fuel_type = 'electric'
        elif house_fuel_type == 'electric':
            wh_fuel_type = 'gas'

        if wh_fuel_type == 'electric':  # if the water heater fuel type is electric, install wh
            heat_element = 3.0 + 0.5 * np.random.randint(1, 6)  # numpy randint (lo, hi) returns lo..(hi-1)
            tank_set = 110 + 16 * np.random.uniform(0, 1)
            therm_dead = 4 + 4 * np.random.uniform(0, 1)
            tank_UA = 2 + 2 * np.random.uniform(0, 1)
            water_sch = np.ceil(self.base.waterHeaterScheduleNumber * np.random.uniform(0, 1))
            water_var = 0.95 + np.random.uniform(0, 1) * 0.1  # +/-5% variability
            wh_demand_type = 'large_'

            # sizeIncr = np.random.randint (0,3)  # MATLAB randi(imax) returns 1..imax
            # sizeProb = np.random.uniform (0, 1);
            # if sizeProb <= self.base.rgnWHSize[rgn-1][0]:
            #    wh_size = 20 + sizeIncr * 5
            #    wh_demand_type = 'small_'
            # elif sizeProb <= (self.base.rgnWHSize[rgn-1][0] + self.base.rgnWHSize[rgn-1][1]):
            #    wh_size = 30 + sizeIncr * 10
            #    if floor_area < 2000.0:
            #        wh_demand_type = 'small_'
            # else:
            #    if floor_area < 2000.0:
            #       wh_size = 30 + sizeIncr * 10
            #   else:
            #       wh_size = 50 + sizeIncr * 10
            # new wh size implementation
            wh_data = self.base.res_bldg_metadata['water_heater_tank_size']
            if floor_area <= wh_data['floor_area']['1_2_people']['floor_area_max']:
                size_array = range(wh_data['tank_size']['1_2_people']['min'],
                                   wh_data['tank_size']['1_2_people']['max'] + 1, 5)
                wh_demand_type = 'small_'
            elif floor_area <= wh_data['floor_area']['2_3_people']['floor_area_max']:
                size_array = range(wh_data['tank_size']['2_3_people']['min'],
                                   wh_data['tank_size']['2_3_people']['max'] + 1, 5)
                wh_demand_type = 'small_'
            elif floor_area <= wh_data['floor_area']['3_4_people']['floor_area_max']:
                size_array = range(wh_data['tank_size']['3_4_people']['min'],
                                   wh_data['tank_size']['3_4_people']['max'] + 1, 10)
            else:
                size_array = range(wh_data['tank_size']['5_plus_people']['min'],
                                   wh_data['tank_size']['5_plus_people']['max'] + 1, 10)
            wh_size = np.random.choice(size_array)
            wh_demand_str = wh_demand_type + '{:.0f}'.format(water_sch) + '*' + '{:.2f}'.format(water_var)
            wh_skew_value = 3 * self.base.residential_skew_std * np.random.randn()
            if wh_skew_value < -6 * self.base.residential_skew_max:
                wh_skew_value = -6 * self.base.residential_skew_max
            elif wh_skew_value > 6 * self.base.residential_skew_max:
                wh_skew_value = 6 * self.base.residential_skew_max

            params = {"parent": hsename,
                      "schedule_skew": '{:.0f}'.format(wh_skew_value),
                      "heating_element_capacity": '{:.1f}'.format(heat_element),
                      "thermostat_deadband": '{:.1f}'.format(therm_dead),
                      "location": "INSIDE",
                      "tank_diameter": "1.5",
                      "tank_UA": '{:.1f}'.format(tank_UA),
                      "water_demand": wh_demand_str,
                      "tank_volume": '{:.0f}'.format(wh_size),
                      "waterheater_model": "MULTILAYER",
                      "discrete_step_size": "60.0",
                      "lower_tank_setpoint": '{:.1f}'.format(tank_set - 5.0),
                      "upper_tank_setpoint": '{:.1f}'.format(tank_set + 5.0),
                      "T_mixing_valve": '{:.1f}'.format(tank_set)}
            # All wh are multilayer now
            #          if np.random.uniform (0, 1) <= self.base.water_heater_participation:
                            # "waterheater_model": "MULTILAYER",
                            # "discrete_step_size": "60.0",
                            # "lower_tank_setpoint": '{:.1f}'.format(tank_set - 5.0),
                            # "upper_tank_setpoint": '{:.1f}'.format(tank_set + 5.0),
                            # "T_mixing_valve": '{:.1f}'.format(tank_set)
            #          else:
                            # "tank_setpoint": '{:.1f}'.format(tank_set)
            self.glm.add_object("waterheater", whname, params)
            self.glm.add_collector(whname, "waterheater")

        self.glm.add_collector(hsename, "house")

        # if PV is allowed,
        #     then only single-family houses can buy it,
        #     and only the single-family houses with PV will also consider storage
        # if PV is not allowed,
        #     then any single-family house may consider storage (if allowed)
        # apartments and mobile homes may always consider storage, but not PV
        # bConsiderStorage = True
        # Solar percentage should be defined here only from RECS data based on income level
        # solar_percentage = res_bldg_metadata['solar_pv'][state][dso_type][income][fa_bldg]
        # Calculate the solar, storage, and ev percentage based on the income level
        il_percentage = self.base.res_bldg_metadata['income_level'][self.base.state][self.base.dso_type][income]

        if fg_recs_dataset is not None:
            solar_percentage_il = fg_recs_dataset.calc_solar_percentage(self.base.recs_state,
                                                                        self.base.recs_income_level,
                                                                        self.base.recs_housing_density)
        else:
            solar_percentage_il = (self.base.solar_percentage *
                                   self.base.res_bldg_metadata['solar_percentage'][income]) / il_percentage

        storage_percentage_il = (self.base.storage_percentage *
                                 self.base.res_bldg_metadata['battery_percentage'][income]) / il_percentage
        ev_percentage_il = (self.base.ev_percentage * self.base.res_bldg_metadata['ev_percentage'][
            income]) / il_percentage
        if bldg == 0:  # Single-family homes
            if solar_percentage_il > 0.0:
                pass
                # bConsiderStorage = False
            if np.random.uniform(0, 1) <= solar_percentage_il:  # some single-family houses have PV
                # bConsiderStorage = True
                # This is legacy code method to find solar rating
                # panel_area = 0.1 * floor_area
                # if panel_area < 162:
                #     panel_area = 162
                # elif panel_area > 270:
                #     panel_area = 270
                # inverter_undersizing = 1.0
                # array_efficiency = 0.2
                # rated_insolation = 1000.0
                # inv_power = inverter_undersizing * (panel_area / 10.7642) * rated_insolation * array_efficiency
                # this results in solar ranging from 3 to 5 kW
                # new method directly proportional to sq. ft.
                # typical PV panel is 350 Watts and avg home has 5kW installed.
                # If we assume 2500 sq. ft as avg area of a single family house, we can say:
                # one 350 W panel for every 175 sq. ft.
                num_panel = np.floor(floor_area / 175)
                inverter_undersizing = 1.0
                inv_power = num_panel * 350 * inverter_undersizing
                pv_scaling_factor = inv_power / self.base.rooftop_pv_rating_MW
                if self.base.case_type['pv']:
                    self.base.solar_count += 1
                    self.base.solar_kw += 0.001 * inv_power
                    params = {"parent": mtrname,
                              "phases": phs,
                              "nominal_voltage": str(vnom)}
                    self.glm.add_object("triplex_meter", sol_m_name, params)

                    params = {"parent": sol_m_name,
                              "phases": phs,
                              "groupid": "sol_inverter",
                              "generator_status": "ONLINE",
                              "inverter_type": "FOUR_QUADRANT",
                              "inverter_efficiency": "1",
                              "rated_power": '{:.0f}'.format(inv_power),
                              "generator_mode": self.base.solar_inv_mode,
                              "four_quadrant_control_mode": self.base.solar_inv_mode,
                              "P_Out": 'P_out_inj.value * {}'.format(pv_scaling_factor)}
                    if 'no_file' not in self.base.solar_Q_player:
                        params["Q_Out"] = "Q_out_inj.value * 0.0"
                    else:
                        params["Q_Out"] = "0"
                    # write_solar_inv_settings(op)  # don't want volt/var control
                    # No need of solar object
                    # print('    object solar {', file=op)
                    # print('      name', solname + ';', file=op)
                    # print('      panel_type SINGLE_CRYSTAL_SILICON;', file=op)
                    # print('      efficiency', '{:.2f}'.format(array_efficiency) + ';', file=op)
                    # print('      area', '{:.2f}'.format(panel_area) + ';', file=op)
                    # print('    };', file=op)
                    # Instead of solar object, write a fake V_in and I_in sufficient high so
                    # that it doesn't limit the player output
                    params["V_In"] = "10000000"
                    params["I_In"] = "10000000"
                    self.glm.add_object("inverter", sol_i_name, params)
                    self.glm.add_collector(sol_i_name, "inverter")

        if np.random.uniform(0, 1) <= storage_percentage_il:
            battery_capacity = get_dist(self.base.batt_metadata['capacity(kWh)']['mean'],
                                        self.base.batt_metadata['capacity(kWh)'][
                                            'deviation_range_per']) * 1000
            max_charge_rate = get_dist(self.base.batt_metadata['rated_charging_power(kW)']['mean'],
                                       self.base.batt_metadata['rated_charging_power(kW)'][
                                           'deviation_range_per']) * 1000
            max_discharge_rate = max_charge_rate
            inverter_efficiency = self.base.batt_metadata['inv_efficiency(per)'] / 100
            charging_loss = get_dist(self.base.batt_metadata['rated_charging_loss(per)']['mean'],
                                     self.base.batt_metadata['rated_charging_loss(per)'][
                                         'deviation_range_per']) / 100
            discharging_loss = charging_loss
            round_trip_efficiency = charging_loss * discharging_loss
            rated_power = max(max_charge_rate, max_discharge_rate)

            if self.base.case_type['bt']:
                self.base.battery_count += 1
                params = {"parent": mtrname,
                          "phases": phs,
                          "nominal_voltage": str(vnom)}
                self.glm.add_object("triplex_meter", bat_m_name, params)

                params = {"parent": bat_m_name,
                          "phases": phs,
                          "groupid": "batt_inverter",
                          "generator_status": "ONLINE",
                          "generator_mode": "CONSTANT_PQ",
                          "inverter_type": "FOUR_QUADRANT",
                          "four_quadrant_control_mode": self.base.storage_inv_mode,
                          "charge_lockout_time": 1,
                          "discharge_lockout_time": 1,
                          "rated_power": rated_power,
                          "max_charge_rate": max_charge_rate,
                          "max_discharge_rate": max_discharge_rate,
                          "sense_object": mtrname,
                          "inverter_efficiency": inverter_efficiency,
                          "power_factor": 1.0}
                self.glm.add_object("inverter", bat_i_name, params)

                params = {"parent": bat_i_name,
                          "use_internal_battery_model": "true",
                          "nominal_voltage": 480,
                          "battery_capacity": battery_capacity,
                          "round_trip_efficiency": round_trip_efficiency,
                          "state_of_charge": 0.50}
                self.glm.add_object("battery", batname, params)
                self.glm.add_collector(batname, "inverter")

        if np.random.uniform(0, 1) <= ev_percentage_il:
            # first lets select an ev model:
            ev_name = self.selectEVmodel(self.base.ev_metadata['sale_probability'], np.random.uniform(0, 1))
            ev_range = self.base.ev_metadata['Range (miles)'][ev_name]
            ev_mileage = self.base.ev_metadata['Miles per kWh'][ev_name]
            ev_charge_eff = self.base.ev_metadata['charging efficiency']
            # check if level 1 charger is used or level 2
            if np.random.uniform(0, 1) <= self.base.ev_metadata['Level_1_usage']:
                ev_max_charge = self.base.ev_metadata['Level_1 max power (kW)']
                volt_conf = 'IS110'  # for level 1 charger, 110 V is good
            else:
                ev_max_charge = self.base.ev_metadata['Level_2 max power (kW)'][ev_name]
                volt_conf = 'IS220'  # for level 2 charger, 220 V is must

            # now, let's map a random driving schedule with this vehicle ensuring daily miles
            # doesn't exceed the vehicle range and home duration is enough to charge the vehicle
            drive_sch = self.match_driving_schedule(ev_range, ev_mileage, ev_max_charge)
            # ['daily_miles','home_arr_time','home_duration','work_arr_time','work_duration']

            # Should be able to turn off ev entirely using ev_percentage, definitely in debugging
            if self.base.case_type['pv']:  # evs are populated when its pvCase i.e. high renewable case
                # few sanity checks
                if drive_sch['daily_miles'] > ev_range:
                    raise UserWarning('daily travel miles for EV can not be more than range of the vehicle!')
                if not is_hhmm_valid(drive_sch['home_arr_time']) or not is_hhmm_valid(
                        drive_sch['home_leave_time']) or not is_hhmm_valid(drive_sch['work_arr_time']):
                    raise UserWarning('invalid HHMM format of driving time!')
                if drive_sch['home_duration'] > 24 * 3600 or drive_sch['home_duration'] < 0 or \
                        drive_sch['work_duration'] > 24 * 3600 or drive_sch['work_duration'] < 0:
                    raise UserWarning('invalid home or work duration for ev!')
                if not self.is_drive_time_valid(drive_sch):
                    raise UserWarning('home and work arrival time are not consistent with durations!')

                self.base.ev_count += 1
                params = {"parent": hsename,
                          "configuration": volt_conf,
                          "breaker_amps": 1000,
                          "battery_SOC": 100.0,
                          "travel_distance": drive_sch['daily_miles'],
                          "arrival_at_work": drive_sch['work_arr_time'],
                          "duration_at_work": drive_sch['work_duration'],
                          "arrival_at_home": drive_sch['home_arr_time'],
                          "duration_at_home": '{}; // (secs)'.format(drive_sch['home_duration']),
                          "work_charging_available": "FALSE",
                          "maximum_charge_rate": ev_max_charge * 1000,
                          "mileage_efficiency": ev_mileage,
                          "mileage_classification": ev_range,
                          "charging_efficiency": ev_charge_eff}
                self.glm.add_object("evcharger_det", evname, params)
                self.glm.add_collector(evname, "house")

    def add_substation(self, name: str, phs: str, v_nom: float, v_ll: float):
        """Write the substation swing node, transformer, metrics collector and 
        fncs_msg object
        TODO: not all variables are used in this function

        Args:
            name (str): node name of the primary (not transmission) substation bus
            phs (str): primary phasing in the substation
            v_nom (float): not used
            v_ll (float): feeder primary line-to-line voltage
        """
        # if this feeder will be combined with others, need USE_FNCS to appear first as a marker for the substation
        if len(self.base.case_name) > 0:
            if self.base.message_broker == "fncs_msg":
                def_params = dict()
                t_name = "gld" + self.base.substation_name
                def_params["parent"] = "network_node"
                def_params["configure"] = self.base.case_name + '_gridlabd.txt'
                def_params["option"] = "transport:hostname localhost, port " + str(self.base.port)
                def_params["aggregate_subscriptions"] = "true"
                def_params["aggregate_publications"] = "true"
                self.glm.add_object("fncs_msg", t_name, def_params)
            if self.base.message_broker == "helics_msg":
                def_params = dict()
                t_name = "gld" + self.base.substation_name
                def_params["configure"] = self.base.case_name + '.json'
                self.glm.add_object("helics_msg", t_name, def_params)

        name = 'substation_xfmr_config'
        params = {"connect_type": 'WYE_WYE',
                  "install_type": 'PADMOUNT',
                  "primary_voltage": '{:.2f}'.format(self.base.transmissionVoltage),
                  "secondary_voltage": '{:.2f}'.format(v_ll),
                  "power_rating": '{:.2f}'.format(self.base.transmissionXfmrMVAbase * 1000.0),
                  "resistance": '{:.2f}'.format(0.01 * self.base.transmissionXfmrRpct),
                  "reactance": '{:.2f}'.format(0.01 * self.base.transmissionXfmrXpct),
                  "shunt_resistance": '{:.2f}'.format(100.0 / self.base.transmissionXfmrNLLpct),
                  "shunt_reactance": '{:.2f}'.format(100.0 / self.base.transmissionXfmrImagpct)}
        self.glm.add_object("transformer_configuration", name, params)

        name = "substation_transformer"
        params = {"from": "network_node",
                  "to": name, "phases": phs,
                  "configuration": "substation_xfmr_config"}
        self.glm.add_object("transformer", name, params)

        vsrcln = self.base.transmissionVoltage / math.sqrt(3.0)
        name = "network_node"
        params = {"groupid": self.base.base_feeder_name,
                  "bustype": 'SWING',
                  "nominal_voltage": '{:.2f}'.format(vsrcln),
                  "positive_sequence_voltage": '{:.2f}'.format(vsrcln),
                  "base_power": '{:.2f}'.format(self.base.transmissionXfmrMVAbase * 1000000.0),
                  "power_convergence_value": "100.0",
                  "phases": phs}
        self.glm.add_object("substation", name, params)
        self.glm.add_collector(name, "meter")
        self.glm.add_recorder(name, "distribution_power_A", "sub_power.csv")

    def add_voltage_class(self, model: dict, h: dict, t: str, v_prim: float, v_ll: float, secmtrnode: dict):
        """Write GridLAB-D instances that have a primary nominal voltage, i.e., 
        node, meter and load.
        
        If triplex load, node or meter, the nominal voltage is 120. If the name 
        or parent attribute is found in secmtrnode, we look up the nominal 
        voltage there. Otherwise, the nominal voltage is vprim 
        secmtrnode[mtr_node] = [kva_total, phases, vnom]. The transformer 
        phasing was not changed, and the transformers were up-sized to the 
        largest phase kva. Therefore, it should not be necessary to look up
        kva_total, but phases might have changed N==>S. If the phasing did 
        change N==>S, we have to prepend triplex_ to the class, write power_1 
        and voltage_1. When writing commercial buildings, if load_class is 
        present and == C, skip the instance.

        Args:
            model (dict): a parsed GridLAB-D model
            h (dict): the object ID hash
            t (str): the GridLAB-D class name to write
            v_prim (float): the primary nominal line-to-neutral voltage TODO: Should this be v_ln?
            v_ll (float): the primary nominal line-to-line voltage
            secmtrnode (dict): key to [transfomer kva, phasing, nominal voltage] by secondary node name
        """
        if t in model:
            for o in model[t]:
                #            if 'load_class' in model[t][o]:
                #                if model[t][o]['load_class'] == 'C':
                #                    continue
                name = o  # model[t][o]['name']
                phs = model[t][o]['phases']
                vnom = v_prim
                if 'bustype' in model[t][o]:
                    if model[t][o]['bustype'] == 'SWING':
                        self.add_substation(name, phs, vnom, v_ll)
                parent = ''
                prefix = ''
                if str.find(phs, 'S') >= 0:
                    bHadS = True
                else:
                    bHadS = False
                if str.find(name, '_tn_') >= 0 or str.find(name, '_tm_') >= 0:
                    vnom = 120.0
                if name in secmtrnode:
                    vnom = secmtrnode[name][2]
                    phs = secmtrnode[name][1]
                if 'parent' in model[t][o]:
                    parent = model[t][o]['parent']
                    if parent in secmtrnode:
                        vnom = secmtrnode[parent][2]
                        phs = secmtrnode[parent][1]
                if str.find(phs, 'S') >= 0:
                    bHaveS = True
                else:
                    bHaveS = False
                if bHaveS == True and bHadS == False:
                    prefix = 'triplex_'
                params = {}
                if len(parent) > 0:
                    params["parent"] = parent
                name = name
                if 'groupid' in model[t][o]:
                    params["groupid"] = model[t][o]['groupid']
                if 'bustype' in model[t][o]:  # already moved the SWING bus behind substation transformer
                    if model[t][o]['bustype'] != 'SWING':
                        params["bustype"] = model[t][o]['bustype']
                params["phases"] = phs
                params["nominal_voltage"] = str(vnom)
                if 'load_class' in model[t][o]:
                    params["load_class"] = model[t][o]['load_class']
                if 'constant_power_A' in model[t][o]:
                    if bHaveS:
                        params["power_1"] = model[t][o]['constant_power_A']
                    else:
                        params["constant_power_A"] = model[t][o]['constant_power_A']
                if 'constant_power_B' in model[t][o]:
                    if bHaveS:
                        params["power_1"] = model[t][o]['constant_power_B']
                    else:
                        params["constant_power_B"] = model[t][o]['constant_power_B']
                if 'constant_power_C' in model[t][o]:
                    if bHaveS:
                        params["power_1"] = model[t][o]['constant_power_C']
                    else:
                        params["constant_power_C"] = model[t][o]['constant_power_C']
                if 'power_1' in model[t][o]:
                    params["power_1"] = model[t][o]['power_1']
                if 'power_2' in model[t][o]:
                    params["power_2"] = model[t][o]['power_2']
                if 'power_12' in model[t][o]:
                    params["power_12"] = model[t][o]['power_12']
                vstarta = str(vnom) + '+0.0j'
                vstartb = format(-0.5 * vnom, '.2f') + format(-0.866025 * vnom, '.2f') + 'j'
                vstartc = format(-0.5 * vnom, '.2f') + '+' + format(0.866025 * vnom, '.2f') + 'j'
                if 'voltage_A' in model[t][o]:
                    if bHaveS:
                        params["voltage_1"] = vstarta
                        params["voltage_2"] = vstarta
                    else:
                        params["voltage_A"] = vstarta
                if 'voltage_B' in model[t][o]:
                    if bHaveS:
                        params["voltage_1"] = vstartb
                        params["voltage_2"] = vstartb
                    else:
                        params["voltage_B"] = vstartb
                if 'voltage_C' in model[t][o]:
                    if bHaveS:
                        params["voltage_1"] = vstartc
                        params["voltage_2"] = vstartc
                    else:
                        params["voltage_C"] = vstartc
                if 'power_1' in model[t][o]:
                    params["power_1"] = model[t][o]['power_1']
                if 'power_2' in model[t][o]:
                    params["power_2"] = model[t][o]['power_2']
                if 'voltage_1' in model[t][o]:
                    if str.find(phs, 'A') >= 0:
                        params["voltage_1"] = vstarta
                        params["voltage_2"] = vstarta
                    if str.find(phs, 'B') >= 0:
                        params["voltage_1"] = vstartb
                        params["voltage_2"] = vstartb
                    if str.find(phs, 'C') >= 0:
                        params["voltage_1"] = vstartc
                        params["voltage_2"] = vstartc
                if name in extra_billing_meters:
                    self.glm.add_tariff(params)
                    self.glm.add_collector(name, prefix + t)
                self.glm.add_object(prefix + t, name, params)

    def add_config_class(self, model: dict, h: dict, t: str):
        """Write a GridLAB-D configuration (i.e., not a link or node) class

        Args:
            model (dict): the parsed GridLAB-D model
            h (dict): the object ID hash
            t (str): the GridLAB-D class
        """
        if t in model:
            for o in model[t]:
                params = dict()
                for p in model[t][o]:
                    if ':' in str(model[t][o][p]):
                        params[p] = h[model[t][o][p]]
                    else:
                        params[p] = model[t][o][p]
                self.glm.add_object(t, o, params)

    def add_xfmr_config(self, key: str, phs: str, kvat: float, v_nom: float, v_sec: float, install_type: str, vprimll: float, vprimln: float):
        """Write a transformer_configuration
        TODO: not all variables are used in this function

        Args:
            key (str): name of the configuration
            phs (str): primary phasing
            kvat (float): transformer rating in kVA TODO: why kvat? Should this be kva or xfkva?
            v_nom (float): primary voltage rating, not used any longer (see 
                vprimll and vprimln)
            v_sec (float): secondary voltage rating, should be line-to-neutral 
                for single-phase or line-to-line for three-phase
            install_type (str): should be VAULT, PADMOUNT or POLETOP
            vprimll (float): primary line-to-line voltage, used for three-phase  TODO: should this be v_ll?
            vprimln (float): primary line-to-neutral voltage, used for 
                single-phase transformers TODO: should this be v_ln?
        """
        params = dict()
        name = self.base.name_prefix + key
        params["power_rating"] = format(kvat, '.2f')
        kvaphase = kvat
        if 'XF2' in key:
            kvaphase /= 2.0
        if 'XF3' in key:
            kvaphase /= 3.0
        if 'A' in phs:
            params["powerA_rating"] = format(kvaphase, '.2f')
        else:
            params["powerA_rating"] = "0.0"
        if 'B' in phs:
            params["powerB_rating"] = format(kvaphase, '.2f')
        else:
            params["powerB_rating"] = "0.0"
        if 'C' in phs:
            params["powerC_rating"] = format(kvaphase, '.2f')
        else:
            params["powerC_rating"] = "0.0"
        params["install_type"] = install_type
        if 'S' in phs:
            row = self.glm.find_1phase_xfmr(kvat)
            params["connect_type"] = "SINGLE_PHASE_CENTER_TAPPED"
            params["primary_voltage"] = str(vprimln)
            params["secondary_voltage"] = format(v_sec, '.1f')
            params["resistance"] = format(row[1] * 0.5, '.5f')
            params["resistance1"] = format(row[1], '.5f')
            params["resistance2"] = format(row[1], '.5f')
            params["reactance"] = format(row[2] * 0.8, '.5f')
            params["reactance1"] = format(row[2] * 0.4, '.5f')
            params["reactance2"] = format(row[2] * 0.4, '.5f')
            params["shunt_resistance"] = format(1.0 / row[3], '.2f')
            params["shunt_reactance"] = format(1.0 / row[4], '.2f')
        else:
            row = self.glm.find_3phase_xfmr(kvat)
            params["connect_type"] = "WYE_WYE"
            params["primary_voltage"] = str(vprimll)
            params["secondary_voltage"] = format(v_sec, '.1f')
            params["resistance"] = format(row[1], '.5f')
            params["reactance"] = format(row[2], '.5f')
            params["shunt_resistance"] = format(1.0 / row[3], '.2f')
            params["shunt_reactance"] = format(1.0 / row[4], '.2f')
        self.glm.add_object("transformer_configuration", name, params)

    def process_taxonomy(self):
        """Parse and re-populate one backbone feeder, usually but not necessarily
        one of the PNNL taxonomy feeders

        This function:
            * reads and parses the backbone model from *rootname.glm*
            * replaces loads with houses and DER
            * upgrades transformers and fuses as needed, based on a radial graph analysis
            * writes the repopulated feeder to *outname.glm*

        Attributes:
            outname (str): the output feeder model name
            rootname (str): the input (usually taxonomy) feeder model name
            vll (float): the feeder primary line-to-line voltage
            vln (float): the feeder primary line-to-neutral voltage
            avghouse (float): the average house load in kVA
            avgcommercial (float): the average commercial load in kVA, not used
        """

        outname = ""
        rootname = self.taxonomy[0]
        vll = self.taxonomy[1]
        vln = self.taxonomy[2]
        avghouse = self.taxonomy[3]
        avgcommercial = self.taxonomy[4]

        self.base.solar_count = 0
        self.base.solar_kw = 0
        self.base.battery_count = 0
        self.base.ev_count = 0

        if self.base.use_recs_data == "true":
            fg_recs_dataset = recs.recs_data_set(self.base.recs_data_file)

        self.base.base_feeder_name = gld_strict_name(rootname)
        rgn = self.glm.model.get_region(rootname)
        print('using', self.base.solar_percentage, 'solar and', self.base.storage_percentage,
              'storage penetration')
        # if self.base.electric_cooling_percentage <= 0.0:
        #     self.base.electric_cooling_percentage = self.base.rgnPenElecCool[rgn - 1]
        #     print('using regional default', self.base.electric_cooling_percentage,
        #           'air conditioning penetration')
        # else:
        #     print('using', self.base.electric_cooling_percentage,
        #           'air conditioning penetration from JSON config')
        # if self.base.water_heater_percentage <= 0.0:
        #     self.base.water_heater_percentage = self.base.rgnPenElecWH[rgn - 1]
        #     print('using regional default', self.base.water_heater_percentage, 'water heater penetration')
        # else:
        #     print('using', self.base.water_heater_percentage, 'water heater penetration from JSON config')

        self.glm.model.module_entities['clock'].starttime.value = self.base.starttime
        self.glm.model.module_entities['clock'].stoptime.value = self.base.endtime
        self.glm.model.module_entities['clock'].timezone.value = self.base.timezone

        swing_node = ''
        G = self.glm.model.draw_network()
        for n1, data in G.nodes(data=True):
            if 'nclass' in data:
                if 'bustype' in data['ndata']:
                    if data['ndata']['bustype'] == 'SWING':
                        swing_node = n1

        sub_graphs = nx.connected_components(G)
        seg_loads = {}  # [name][kva, phases]
        total_kva = 0.0
        for n1, data in G.nodes(data=True):
            if 'ndata' in data:
                kva = self.accumulate_load_kva(data['ndata'])
                # need to account for large-building loads added through transformer connections
                if n1 == self.base.Eplus_Bus:
                    kva += self.base.Eplus_kVA
                if kva > 0:
                    total_kva += kva
                    nodes = nx.shortest_path(G, n1, swing_node)
                    edges = zip(nodes[0:], nodes[1:])
                    for u, v in edges:
                        eclass = G[u][v]['eclass']
                        if self.glm.model.is_edge_class(eclass):
                            ename = G[u][v]['ename']
                            if ename not in seg_loads:
                                seg_loads[ename] = [0.0, '']
                            seg_loads[ename][0] += kva
                            seg_loads[ename][1] = self.glm.union_of_phases(seg_loads[ename][1], data['ndata']['phases'])

        print('  swing node', swing_node, 'with', len(list(sub_graphs)), 'subgraphs and',
              '{:.2f}'.format(total_kva), 'total kva')

        # preparatory items for TESP
        self.glm.add_module("climate", {})
        self.glm.add_module("generators", {})
        self.glm.add_module("connection", {})
        params = {"implicit_enduses": "NONE"}
        self.glm.add_module("residential", params)

        self.glm.model.include_lines.append('#include "${TESPDIR}/data/schedules/appliance_schedules.glm"')
        self.glm.model.include_lines.append('#include "${TESPDIR}/data/schedules/water_and_setpoint_schedule_v5.glm"')
        self.glm.model.include_lines.append('#include "${TESPDIR}/data/schedules/commercial_schedules.glm"')

        self.glm.model.set_lines.append('#set minimum_timestep=' + str(self.base.timestep))
        self.glm.model.set_lines.append('#set relax_naming_rules=1')
        self.glm.model.set_lines.append('#set warn=0')

        if self.base.metrics_interval > 0:
            params = {"interval": str(self.base.metrics_interval),
                      "interim": "43200"}
            if self.base.forERCOT == "True":
                params["filename"] = outname + '_metrics.json'
            else:
                params["filename"] = '${METRICS_FILE}'
            self.glm.add_object("metrics_collector_writer", "mc", params)

        name = "localWeather"
        params = {"name": str(self.base.weather_name),
                   "interpolate": "QUADRATIC",
                   "latitude": str(self.base.latitude),
                   "longitude": str(self.base.longitude),
                   "tz_meridian": '{0:.2f};'.format(15 * self.base.time_zone_offset)}
        self.glm.add_object("climate", name, params)

        if self.base.solar_percentage > 0.0:
            # Waiting for the add comment method to be added to the modify class
            #    default IEEE 1547-2018 settings for Category B'
            #    solar inverter mode on this feeder
            self.glm.model.define_lines.append(
                '#define ' + self.base.name_prefix + 'INVERTER_MODE=' + self.base.solar_inv_mode)
            self.glm.model.define_lines.append('#define INV_VBASE=240.0')
            self.glm.model.define_lines.append('#define INV_V1=0.92')
            self.glm.model.define_lines.append('#define INV_V2=0.98')
            self.glm.model.define_lines.append('#define INV_V3=1.02')
            self.glm.model.define_lines.append('#define INV_V4=1.08')
            self.glm.model.define_lines.append('#define INV_Q1=0.44')
            self.glm.model.define_lines.append('#define INV_Q2=0.00')
            self.glm.model.define_lines.append('#define INV_Q3=0.00')
            self.glm.model.define_lines.append('#define INV_Q4=-0.44')
            self.glm.model.define_lines.append('#define INV_VIN=200.0')
            self.glm.model.define_lines.append('#define INV_IIN=32.5')
            self.glm.model.define_lines.append('#define INV_VVLOCKOUT=300.0')
            self.glm.model.define_lines.append('#define INV_VW_V1=1.05 // 1.05833')
            self.glm.model.define_lines.append('#define INV_VW_V2=1.10')
            self.glm.model.define_lines.append('#define INV_VW_P1=1.0')
            self.glm.model.define_lines.append('#define INV_VW_P2=0.0')
        # write the optional volt_dump and curr_dump for validation

        if self.base.WANT_VI_DUMP == "True":
            params = {"parent": name,
                      "filename": 'Voltage_Dump_' + outname + '.csv',
                      "mode": 'polar'}
            self.glm.add_object("voltdump", name, params)
            params = {"parent": name,
                      "filename": 'Current_Dump_' + outname + '.csv',
                      "mode": 'polar'}
            self.glm.add_object("currdump", name, params)

        # NEW STRATEGY - loop through transformer instances and assign a standard size based on the downstream load
        #              - change the referenced transformer_configuration attributes
        #              - write the standard transformer_configuration instances we actually need
        model = self.glm.model.model
        h = self.glm.model.hash  # OID hash
        xfused = {}  # ID, phases, total kva, vnom (LN), vsec, poletop/padmount
        secnode = {}  # Node, st, phases, vnom
        t = 'transformer'
        if t not in model:
            model[t] = {}
        for o in model[t]:
            seg_kva = seg_loads[o][0]
            seg_phs = seg_loads[o][1]
            nphs = 0
            if 'A' in seg_phs:
                nphs += 1
            if 'B' in seg_phs:
                nphs += 1
            if 'C' in seg_phs:
                nphs += 1
            if nphs > 1:
                kvat = self.glm.find_3phase_xfmr_kva(seg_kva)
            else:
                kvat = self.glm.find_1phase_xfmr_kva(seg_kva)
            if 'S' in seg_phs:
                vnom = 120.0
                vsec = 120.0
            else:
                if 'N' not in seg_phs:
                    seg_phs += 'N'
                if kvat > self.base.max208kva:
                    vsec = 480.0
                    vnom = 277.0
                else:
                    vsec = 208.0
                    vnom = 120.0

            secnode[gld_strict_name(model[t][o]['to'])] = [kvat, seg_phs, vnom]

            old_key = h[model[t][o]['configuration']]
            install_type = model['transformer_configuration'][old_key]['install_type']

            raw_key = 'XF' + str(nphs) + '_' + install_type + '_' + seg_phs + '_' + str(kvat)
            key = raw_key.replace('.', 'p')

            model[t][o]['configuration'] = self.base.name_prefix + key
            model[t][o]['phases'] = seg_phs
            if key not in xfused:
                xfused[key] = [seg_phs, kvat, vnom, vsec, install_type]

        for key in xfused:
            self.add_xfmr_config(key, xfused[key][0], xfused[key][1], xfused[key][2], xfused[key][3],
                                 xfused[key][4], vll, vln)

        t = 'capacitor'
        if t in model:
            for o in model[t]:
                model[t][o]['nominal_voltage'] = str(int(vln))
                model[t][o]['cap_nominal_voltage'] = str(int(vln))

        t = 'fuse'
        if t not in model:
            model[t] = {}
        for o in model[t]:
            if o in seg_loads:
                seg_kva = seg_loads[o][0]
                seg_phs = seg_loads[o][1]
                nphs = 0
                if 'A' in seg_phs:
                    nphs += 1
                if 'B' in seg_phs:
                    nphs += 1
                if 'C' in seg_phs:
                    nphs += 1
                if nphs == 3:
                    amps = 1000.0 * seg_kva / math.sqrt(3.0) / vll
                elif nphs == 2:
                    amps = 1000.0 * seg_kva / 2.0 / vln
                else:
                    amps = 1000.0 * seg_kva / vln
                model[t][o]['current_limit'] = str(self.glm.find_fuse_limit(amps))

        self.add_local_triplex_configurations()
        self.add_config_class(model, h, 'regulator_configuration')
        self.add_config_class(model, h, 'overhead_line_conductor')
        self.add_config_class(model, h, 'line_spacing')
        self.add_config_class(model, h, 'line_configuration')
        self.add_config_class(model, h, 'triplex_line_conductor')
        self.add_config_class(model, h, 'triplex_line_configuration')
        self.add_config_class(model, h, 'underground_line_conductor')

        self.add_link_class(model, h, 'fuse', seg_loads)
        self.add_link_class(model, h, 'switch', seg_loads)
        self.add_link_class(model, h, 'recloser', seg_loads)
        self.add_link_class(model, h, 'sectionalizer', seg_loads)

        self.add_link_class(model, h, 'overhead_line', seg_loads)
        self.add_link_class(model, h, 'underground_line', seg_loads)
        self.add_link_class(model, h, 'series_reactor', seg_loads)

        self.add_link_class(model, h, 'regulator', seg_loads, want_metrics=True)
        self.add_link_class(model, h, 'transformer', seg_loads)
        self.add_link_class(model, h, 'capacitor', seg_loads, want_metrics=True)

        if self.base.forERCOT == "True":
            self.replace_commercial_loads(model, h, 'load', 0.001 * avgcommercial)
            #            connect_ercot_commercial (op)
            self.identify_ercot_houses(model, h, 'load', 0.001 * avghouse, rgn)

            # connect_ercot_houses(model, h, op, vln, 120.0)
            self.add_ercot_houses(model, h, vln, 120.0)

            for key in self.base.house_nodes:
                self.add_houses(key, 120.0)
            for key in self.base.small_nodes:
                self.add_ercot_small_loads(key, vln)
            for key in self.base.comm_loads:
                self.add_commercial_loads(rgn, key)
        else:
            self.replace_commercial_loads(model, h, 'load', 0.001 * avgcommercial)
            self.identify_xfmr_houses(model, h, 'transformer', seg_loads, 0.001 * avghouse, rgn)
            for key in self.base.house_nodes:
                self.add_houses(key, 120.0)
            for key in self.base.small_nodes:
                self.add_small_loads(key, 120.0)
            for key in self.base.comm_loads:
                # add_commercial_loads(rgn, key)
                bldg_definition = comm_FG.define_comm_loads(self, self.base.comm_loads[key][1],
                                                            self.base.comm_loads[key][2],
                                                            "Suburban",
                                                            # self.base.dso_type,
                                                            self.base.ashrae_zone,
                                                            self.base.comm_bldg_metadata)
                comm_FG.add_comm_zones(self.glm, bldg_definition,
                                       self.base.comm_loads, key,
                                       self.base.batt_metadata, self.base.storage_percentage,
                                       self.base.ev_metadata, self.base.ev_percentage,
                                       self.base.solar_percentage, self.base.pv_rating_MW,
                                       self.base.solar_Q_player,
                                       self.base.case_type)

        self.add_voltage_class(model, h, 'node', vln, vll, secnode)
        self.add_voltage_class(model, h, 'meter', vln, vll, secnode)
        if self.base.forERCOT == "False":
            self.add_voltage_class(model, h, 'load', vln, vll, secnode)
        if len(self.base.Eplus_Bus) > 0 and self.base.Eplus_Volts > 0.0 and \
                self.base.Eplus_kVA > 0.0:
            # Waiting for the add comment method to be added to the modify class
            #            print('////////// EnergyPlus large-building load ///////////////', file=op)
            row = self.glm.find_3phase_xfmr(self.base.Eplus_kVA)
            actual_kva = row[0]
            watts_per_phase = 1000.0 * actual_kva / 3.0
            Eplus_vln = self.base.Eplus_Volts / math.sqrt(3.0)
            vstarta = format(Eplus_vln, '.2f') + '+0.0j'
            vstartb = format(-0.5 * Eplus_vln, '.2f') + format(-0.866025 * Eplus_vln, '.2f') + 'j'
            vstartc = format(-0.5 * Eplus_vln, '.2f') + '+' + format(0.866025 * Eplus_vln, '.2f') + 'j'

            name = self.base.name_prefix + 'Eplus_transformer_configuration'
            params = {"connect_type": "WYE_WYE",
                      "install_type": "PADMOUNT",
                      "power_rating": str(actual_kva),
                      "primary_voltage": str(vll),
                      "secondary_voltage": format(self.base.Eplus_Volts, '.1f'),
                      "resistance": format(row[1], '.5f'),
                      "reactance": format(row[2], '.5f'),
                      "shunt_resistance": format(1.0 / row[3], '.2f'),
                      "shunt_reactance": format(1.0 / row[4], '.2f')}
            self.glm.add_object("transformer_configuration", name, params)

            name = self.base.name_prefix + 'Eplus_transformer'
            params = {"phases": "ABCN",
                      "from": self.base.name_prefix + self.base.Eplus_Bus,
                      "to": self.base.name_prefix + 'Eplus_meter',
                      "configuration": self.base.name_prefix + 'Eplus_transformer_configuration'}
            self.glm.add_object("transformer", name, params)

            t_name = self.base.name_prefix + 'Eplus_meter'
            params = {"phases": "ABCN",
                      "meter_power_consumption": "1+15j",
                      "nominal_voltage": '{:.4f}'.format(Eplus_vln),
                      "voltage_A": vstarta,
                      "voltage_B": vstartb,
                      "voltage_C": vstartc}
            self.glm.add_tariff(params)
            self.glm.add_object("meter", t_name, params)
            self.glm.add_collector(t_name, "meter")

            name = self.base.name_prefix + 'Eplus_load;'
            params = {"parent": self.base.name_prefix + 'Eplus_meter',
                      "phases": "ABCN",
                      "nominal_voltage": '{:.4f}'.format(Eplus_vln),
                      "voltage_A": vstarta,
                      "voltage_B": vstartb,
                      "voltage_C": vstartc,
                      "constant_power_A": '{:.1f}'.format(watts_per_phase),
                      "constant_power_B": '{:.1f}'.format(watts_per_phase),
                      "constant_power_C": '{:.1f}'.format(watts_per_phase)}
            self.glm.add_object("load", name, params)

        print('cooling bins unused', self.base.cooling_bins)
        print('heating bins unused', self.base.heating_bins)
        print(self.base.solar_count, 'pv totaling', '{:.1f}'.format(self.base.solar_kw),
              'kw with', self.base.battery_count, 'batteries')

    def add_node_houses(self, node: str, region: int, xfkva: float, phs: str, nh=None, loadkw=None, house_avg_kw=None, secondary_ft=None,
                        storage_fraction=0.0, solar_fraction=0.0, electric_cooling_fraction=0.5,
                        node_metrics_interval=None, random_seed=False):
        """Writes GridLAB-D houses to a primary load point.

        One aggregate service transformer is included, plus an optional aggregate
        secondary service drop. Each house has a separate meter or triplex_meter,
        each with a common parent, either a node or triplex_node on either the
        transformer secondary, or the end of the service drop. The houses may be
        written per phase, i.e., unbalanced load, or as a balanced three-phase 
        load. The houses should be #included into a master GridLAB-D file. Before
        using this function, call write_node_house_configs once, and only once, 
        for each combination xfkva/phs that will be used.

        Args:
            node (str): the GridLAB-D primary node name
            region (int): the taxonomy region for housing population, 1..6
            xfkva (float): the total transformer size to serve expected load; 
                make this big enough to avoid overloads
            phs (str): 'ABC' for three-phase balanced distribution, 'AS', 'BS', 
                or 'CS' for single-phase triplex
            nh (int): directly specify the number of houses; an alternative to 
                loadkw and house_avg_kw
            loadkw (float): total load kW that the houses will represent; with 
                house_avg_kw, an alternative to nh
            house_avg_kw (float): average house load in kW; with loadkw, an 
                alternative to nh
            secondary_ft (float): if not None, the length of adequately sized 
                secondary circuit from transformer to the meters
            electric_cooling_fraction (float): fraction of houses to have air 
                conditioners
            solar_fraction (float): fraction of houses to have rooftop solar 
                panels
            storage_fraction (float): fraction of houses with solar panels that 
                also have residential storage systems
            node_metrics_interval (int): if not None, the metrics collection 
                interval in seconds for houses, meters, solar and storage at 
                this node
            random_seed (boolean): if True, reseed each function call. Default 
                value False provides repeatability of output.
        """
        self.base.house_nodes = {}
        if not random_seed:
            np.random.seed(0)
        bTriplex = False
        if 'S' in phs:
            bTriplex = True
        self.base.storage_percentage = storage_fraction
        self.base.solar_percentage = solar_fraction
        self.base.electric_cooling_percentage = electric_cooling_fraction
        lg_v_sm = 0.0
        vnom = 120.0
        if node_metrics_interval is not None:
            self.base.metrics_interval = node_metrics_interval
        else:
            self.base.metrics_interval = 0
        if nh is not None:
            nhouse = nh
        else:
            nhouse = int((loadkw / house_avg_kw) + 0.5)
            if nhouse > 0:
                lg_v_sm = loadkw / house_avg_kw - nhouse  # >0 if we rounded down the number of houses
        bldg, ti = self.selectResidentialBuilding(self.base.rgnThermalPct[region - 1],
                                                  np.random.uniform(0, 1))  # TODO - these will all be identical!
        if nhouse > 0:
            # write the transformer and one billing meter at the house, with optional secondary circuit
            if bTriplex:
                xfkey = 'XF{:s}_{:d}'.format(phs[0], int(xfkva))
                linekey = 'tpx_cfg_{:d}'.format(int(xfkva))
                meter_class = 'triplex_meter'
                line_class = 'triplex_line'
            else:
                xfkey = 'XF3_{:d}'.format(int(xfkva))
                linekey = 'quad_cfg_{:d}'.format(int(xfkva))
                meter_class = 'meter'
                line_class = 'overhead_line'
            if secondary_ft is None:
                xfmr_meter = '{:s}_mtr'.format(node)  # same as the house meter
            else:
                xfmr_meter = '{:s}_xfmtr'.format(node)  # needs its own secondary meter
            if (self.base.solar_percentage > 0.0) or (self.base.storage_percentage > 0.0):
                if bTriplex:
                    # waiting for the add comment method to be added to the modifier class
                    # print('// inverter base voltage for volt-var functions, on triplex circuit', file=fp)
                    self.glm.model.define_lines.append("#define INV_VBASE=240.0")
                else:
                    # waiting for the add comment method to be added to the modifier class
                    # print('// inverter base voltage for volt-var functions, on 208-V three-phase circuit', file=fp)
                    self.glm.model.define_lines.append("#define INV_VBASE=208.0")

            name = '{:s}_xfmr'.format(node)
            params = {"phases": '{:s};'.format(phs),
                      "from": '{:s}'.format(node),
                      "to": '{:s}'.format(xfmr_meter),
                      "configuration": '{:s}'.format(xfkey)}
            self.glm.add_object("transformer", name, params)

            if secondary_ft is not None:
                name = '{:s}_mtr;'.format(node)
                params = {"phases": '{:s}'.format(phs),
                          "nominal_voltage": '{:.2f};'.format(vnom)}
                self.glm.add_object('{:s} {{'.format(meter_class), name, params)

                name = '{:s}_secondary;'.format(node)
                params = {"phases": '{:s};'.format(phs),
                          "from": '{:s};'.format(xfmr_meter),
                          "to": '{:s}_mtr'.format(node),
                          "length": '{:.1f};'.format(secondary_ft),
                          "configuration": '{:s}'.format(linekey)}
                self.glm.add_object('{:s} {{'.format(line_class), name, params)
            name = '{:s}_mtr;'.format(node)
            params = {"phases": '{:s};'.format(phs),
                      "nominal_voltage": '{:.2f}'.format(vnom)}
            self.glm.add_tariff(params)
            self.glm.add_object('{:s} {{'.format(meter_class), name, params)

            if self.base.metrics_interval > 0:
                params = {"parent": name,
                          "interval": str(self.base.metrics_interval)}
                self.glm.add_object('{:s} {{'.format(meter_class), name, params)

            # write all the houses on that meter
            self.base.house_nodes[node] = [nhouse, region, lg_v_sm, phs, bldg, ti]
            self.add_houses(node, vnom, bIgnoreThermostatSchedule=False, bWriteService=False, bTriplex=bTriplex,
                            setpoint_offset=1.0)
        else:
            print('// Zero houses at {:s} phases {:s}'.format(node, phs))
            # waiting for the add comment methods to be added to modifier class
            # print('// Zero houses at {:s} phases {:s}'.format(node, phs), file=fp)

# def selectRECSBuildingTypeVintage(rcs_dataset, state, income_lvl, pop_density):
#     type_df, vint_df = rcs_dataset.get_house_type_vintage("Washington","Low","U" )
#     tdt, tdv = rcs_dataset.sample_type_vintage(type_df, vint_df)
#     return tdt, tdv


def _test1():
    """ Parse and re-populate one backbone feeder, usually but not necessarily 
    one of the PNNL taxonomy feeders
    """
    feeder = Feeder(4)
    # loading default agent data
    data_Path = "../data/"
    # loading general metadata
    with open(os.path.join(data_Path, "8-hi-metadata-lean.json"), 'r', encoding='utf-8') as json_file:
        feeder.base.dso_config = json.load(json_file)
    # loading residential metadata
    with open(os.path.join(data_Path, "RECS_residential_metadata.json"), 'r', encoding='utf-8') as json_file:
        feeder.base.res_bldg_metadata = json.load(json_file)
    # loading commercial building metadata
    with open(os.path.join(data_Path, "DSOT_commercial_metadata.json"), 'r', encoding='utf-8') as json_file:
        feeder.base.comm_bldg_metadata = json.load(json_file)
    # loading battery metadata
    with open(os.path.join(data_Path, "DSOT_battery_metadata.json"), 'r', encoding='utf-8') as json_file:
        feeder.base.batt_metadata = json.load(json_file)
    # loading ev model metadata
    with open(os.path.join(data_Path, "DSOT_ev_model_metadata.json"), 'r', encoding='utf-8') as json_file:
        feeder.base.ev_metadata = json.load(json_file)

    # We need to generate the total population of commercial buildings by type and size
    dso_val = feeder.base.dso_config["DSO_2"]
    feeder.base.ashrae_zone = dso_val['ashrae_zone']
    feeder.base.pv_rating_MW = dso_val['rooftop_pv_rating_MW']
    num_res_customers = dso_val['number_of_gld_homes']
    num_comm_customers = round(num_res_customers * dso_val['RCI customer count mix']['commercial'] /
                               dso_val['RCI customer count mix']['residential'])
    num_comm_bldgs = num_comm_customers / dso_val['comm_customers_per_bldg']
    feeder.base.comm_bldgs_pop = comm_FG.define_comm_bldg(feeder.base.comm_bldg_metadata, dso_val['utility_type'], num_comm_bldgs)

    feeder.base.driving_data_file = "DSOT_ev_driving_metadata.csv"
    feeder.base.ev_driving_metadata = feeder.process_nhts_data(os.path.join(data_Path + feeder.base.driving_data_file))

    feeder.base.solar_path = "../../../data/solar_data/solar_pv_power_profiles/"
    feeder.base.solar_P_player = "5_minute_dist_power.csv"
    feeder.base.solar_Q_player = "no_file"
    feeder.base.state = "TX"
    feeder.base.dso_type = "No_DSO_Type"   # Suburban, Urban, Rural, No_DSO_Type
    # feeder.base.dso_type = "Suburban"
    feeder.base.income_level = ["Low", "Middle", "Upper"]
    feeder.base.electric_cooling_percentage = 90
    feeder.base.rooftop_pv_rating_MW = 1677.84

    cop_mat = feeder.base.res_bldg_metadata['COP_average']
    years_bin = [range(1945, 1950), range(1950, 1960), range(1960, 1970), range(1970, 1980),
                 range(1980, 1990), range(1990, 2000), range(2000, 2010), range(2010, 2016), range(2016, 2021)]
    years_bin = [list(years_bin[ind]) for ind in range(len(years_bin))]
    feeder.base.cop_lookup = []
    for _bin in range(len(years_bin)):
        temp = []
        for yr in years_bin[_bin]:
            temp.append(cop_mat[str(yr)])
        feeder.base.cop_lookup.append(temp)

    feeder.process_taxonomy()
    feeder.glm.write_model("test.glm")

    # Test read, write, plot
    gm = GLMModifier()
    g, success = gm.read_model("test.glm")
    if success:
        gm.write_model("test2.glm")
        # gm.model.plot_model()


if __name__ == "__main__":
    _test1()