# Copyright (C) 2018-2020 Battelle Memorial Institute
# file: gld_residential_feeder.py
"""Replaces ZIP loads with houses, and optional storage, electric vehicles,
and solar generation.

As this module populates the feeder backbone with houses and DER, it uses
the Networkx package to perform graph-based capacity analysis, upgrading
fuses, transformers and lines to serve the expected load. Transformers have
a margin of 20% to avoid overloads, while fuses have a margin of 150% to
avoid overloads. These can be changed by editing tables and variables in the
source file.

References:
    `GridAPPS-D Feeder Models <https://github.com/GRIDAPPSD/Powergrid-Models>`_

Public Functions:
    :preamble: adds tape, climate, generators, connection, and residential modules
    :generate_and_load_recs: populates residential, commercial, electric vehicle,
        and battery metadata based on user config and RECS metadata
    :buildingTypeLabel: assigns region, building type, and thermal integrity level
    :checkResidentialBuildingTable: verifies that the regional building parameter
        histograms sum to one
    :selectSetpointBins: randomly chooses a histogram row from the cooling and
        heating setpoints.
    :add_small_loads: adds loads that are too small to be a house onto a node
    :getDsoIncomeLevelTable: retrieves the DSO income level fractions for the
        given dso type and state
    :selectIncomeLevel: selects the income level with region and probability
    :getDsoThermalTable: defines the distribution of thermal integrity values by
        housing vintage and income
    :selectResidentialBuilding: writes volt-var and volt-watt settings for solar
        inverters
    :selectThermalProperties: retrieves building thermal properties for given
        building type and thermal integrity level
    :add_houses: puts houses, along with solar panels, batteries, and electric
        vehicle charges, onto a node
    :replace_commercial_loads: determines the number of commercial zones that
        loads assigned class 'C' should have
    :add_one_commercial_zone: writes a pre-configured commercial zone as a house
    :add_solar_inv_settings: writes volt-var and volt-watt settings for solar
        inverters
    :add_solar_defines: writes required define_lines for solar inverters
    :selectEVmodel: selects the EV model based on available sale distribution
        data
    :match_driving_schedule: matches schedule of vehicle from NHTS data based on
        vehicle ev_range
    :is_drive_time_valid: checks if work arrival time and home arrival time add
        up properly
    :process_nhts:data: reads and processes NHTS survey data, returning a
        dataframe
    :identify_xfmr_houses: scans each service transformer on the feeder to
        determine the number of houses it should have

"""

import math
import numpy as np
import pandas as pd
import sys

import gld_commercial_feeder as comm_FG
from tesp_support.api.helpers import gld_strict_name, random_norm_trunc, randomize_residential_skew
from tesp_support.api.modify_GLM import GLMModifier
from tesp_support.api.time_helpers import get_secs_from_hhmm, get_hhmm_from_secs, get_duration, get_dist
from tesp_support.api.time_helpers import is_hhmm_valid, subtract_hhmm_secs, add_hhmm_secs
from tesp_support.api.entity import assign_defaults

sys.path.append("../../..")
from examples.analysis.dsot.code import recs_gld_house_parameters

extra_billing_meters = set()


class Config:

    def __init__(self, glm_config=None):
        # Assign default values to those not defined in config file
        self.keys = list(assign_defaults(self, glm_config).keys())
        self.glm = GLMModifier()
        self.base = self.glm.defaults
        self.res_bldg_metadata = Residential_Build(self)
        self.comm_bldg_metadata = Commercial_Build(self)
        self.batt_metadata = Battery(self)
        self.ev_metadata = Electric_Vehicle(self)

    def preamble(self):
        # Add tape, climate, generators, connection, and residential modules
        self.glm.add_module("tape", {})
        self.glm.add_module("climate", {})
        self.glm.add_module("generators", {})
        self.glm.add_module("connection", {})
        params = {"implicit_enduses": "NONE"}
        self.glm.add_module("residential", params)

        # set for players
        if "solar_P_player" in self.keys:
            player = self.solar_P_player
            self.glm.model.add_class(player["name"], player["datatype"], player["attr"], player["static"], player["data"])

        # Set clock
        self.glm.model.set_clock(self.starttime, self.stoptime, self.timezone)

        # Set includes
        for item in self.includes:
            self.glm.model.add_include(item)

        # Add sets
        for key in self.sets:
            self.glm.model.add_set(key, self.sets[key])

        # Add defines
        for key, value in self.defines:
            self.glm.model.add_defines(key, value)

        # Add voltage dump file
        if self.base.WANT_VI_DUMP:
            self.glm.add_voltage_dump(self.base.case_name)

        # Add metrics interval and interim interval
        if self.metrics_interval > 0:
            params = {"interval": str(self.base.metrics_interval),
                      "interim": str(self.base.metrics_interim),
                      "filename": str(self.base.metrics_filename),
                      "alternate": str(self.base.metrics_alternate),
                      "extension": str(self.base.metrics_extension)
            }
            self.glm.add_object("metrics_collector_writer", "mc", params)

        # Add climate object and weather params
        params = {"interpolate": str(self.interpolate),
                  "latitude": str(self.latitude),
                  "longitude": str(self.longitude),
                  "tmyfile": str(self.tmyfile)}
                  # TODO: how to set tz_meridian parameter
                  # "tz_meridian": '{0:.2f}'.format(15 * self.time_zone_offset)}
        self.glm.add_object("climate", self.weather_name, params)

    def generate_and_load_recs(self):
        # if config['use_recs']:
        if not self.recs_exist:
            recs_gld_house_parameters.get_RECS_jsons(
                self.file_recs_income_level,
                self.file_residential_meta,
                self.out_file_residential_meta,
                self.out_file_hvac_set_point,
                self.sample,
                self.bin_size_threshold,
                self.climate_zone,
                self.wh_shift
            )

        assign_defaults(self.comm_bldg_metadata, self.file_commercial_meta)
        # We need to generate the total population of commercial buildings by type and size
        num_comm_customers = round(self.number_of_gld_homes *
                                   self.RCI_customer_count_mix["commercial"] / self.RCI_customer_count_mix["residential"])
        num_comm_bldgs = num_comm_customers / self.comm_customers_per_bldg
        self.base.comm_bldgs_pop = comm_FG.define_comm_bldg(self.comm_bldg_metadata, self.utility_type,
                                                              num_comm_bldgs)

        assign_defaults(self.res_bldg_metadata, self.out_file_residential_meta)
        cop_mat = self.res_bldg_metadata.COP_average
        years_bin = [range(1945, 1950), range(1950, 1960), range(1960, 1970), range(1970, 1980),
                     range(1980, 1990), range(1990, 2000), range(2000, 2010), range(2010, 2016),
                     range(2016, 2020)]
        years_bin = [list(years_bin[ind]) for ind in range(len(years_bin))]

        self.base.cop_lookup = []
        for _bin in range(len(years_bin)):
            temp = []
            for yr in years_bin[_bin]:
                temp.append(cop_mat[str(yr)])
            self.base.cop_lookup.append(temp)

        assign_defaults(self.batt_metadata, self.file_battery_meta)
        assign_defaults(self.ev_metadata, self.file_ev_meta)
        self.base.ev_driving_metadata = self.ev_metadata.process_nhts_data(self.file_ev_driving_meta)


class Residential_Build:
    def __init__(self, config):
        self.config = config
        self.glm = config.glm

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
        return self.config.base.rgnName[rgn - 1] + ': ' + self.config.base.bldgTypeName[bldg] + ': TI Level ' + str(therm_int + 1)

    def checkResidentialBuildingTable(self):
        """Verify that the regional building parameter histograms sum to one"""
        for tbl in range(len(self.config.base.dsoThermalPct)):
            total = 0
            for row in range(len(self.config.base.dsoThermalPct[tbl])):
                for col in range(len(self.config.base.dsoThermalPct[tbl][row])):
                    total += self.config.base.dsoThermalPct[tbl][row][col]
            print(self.config.base.rgnName[tbl], 'rgnThermalPct sums to', '{:.4f}'.format(total))
        for tbl in range(len(self.config.base.bldgCoolingSetpoints)):
            total = 0
            for row in range(len(self.config.base.bldgCoolingSetpoints[tbl])):
                total += self.config.base.bldgCoolingSetpoints[tbl][row][0]
            print('bldgCoolingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
        for tbl in range(len(self.config.base.bldgHeatingSetpoints)):
            total = 0
            for row in range(len(self.config.base.bldgHeatingSetpoints[tbl])):
                total += self.config.base.bldgHeatingSetpoints[tbl][row][0]
            print('bldgHeatingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
        for bldg in range(3):
            binZeroReserve = self.config.base.bldgCoolingSetpoints[bldg][0][0]
            binZeroMargin = self.config.base.bldgHeatingSetpoints[bldg][0][0] - binZeroReserve
            if binZeroMargin < 0.0:
                binZeroMargin = 0.0
            #        print(bldg, binZeroReserve, binZeroMargin)
            for cBin in range(1, 6):
                denom = binZeroMargin
                for hBin in range(1, self.config.base.allowedHeatingBins[cBin]):
                    denom += self.config.base.bldgHeatingSetpoints[bldg][hBin][0]
                self.config.base.conditionalHeatingBinProb[bldg][cBin][0] = binZeroMargin / denom
                for hBin in range(1, self.config.base.allowedHeatingBins[cBin]):
                    self.config.base.conditionalHeatingBinProb[bldg][cBin][hBin] = \
                        self.config.base.bldgHeatingSetpoints[bldg][hBin][0] / denom
        # print('conditionalHeatingBinProb', conditionalHeatingBinProb)

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
        tbl = self.config.base.bldgCoolingSetpoints[bldg]
        for row in range(len(tbl)):
            total += tbl[row][0]
            if total >= rand:
                cBin = row
                break
        tbl = self.config.base.conditionalHeatingBinProb[bldg][cBin]
        rand_heat = np.random.uniform(0, 1)
        total = 0
        for col in range(len(tbl)):
            total += tbl[col]
            if total >= rand_heat:
                hBin = col
                break
        self.config.base.cooling_bins[bldg][cBin] -= 1
        self.config.base.heating_bins[bldg][hBin] -= 1
        return self.config.base.bldgCoolingSetpoints[bldg][cBin], self.config.base.bldgHeatingSetpoints[bldg][hBin]

    def add_small_loads(self, basenode: str, v_nom: float):
        """Write loads that are too small for a house, onto a node

        Args:
            basenode (str): GridLAB-D node name
            v_nom (float): nominal line-to-neutral voltage at basenode TODO: should this be v_ln?
        """
        kva = float(self.config.base.small_nodes[basenode][0])
        phs = self.config.base.small_nodes[basenode][1]

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
                  "configuration": self.config.base.triplex_configurations[0][0]}
        self.glm.add_object("triplex_line", tpxname, params)

        params = {"phases": phs,
                  "meter_power_consumption": "1+7j",
                  "nominal_voltage": str(v_nom),
                  "voltage_1": vstart,
                  "voltage_2": vstart}
        self.glm.add_tariff(params)
        self.glm.add_object("triplex_meter", mtrname, params)
        self.glm.add_metrics_collector(mtrname, "meter")

        params = {"parent": mtrname,
                  "phases": phs,
                  "nominal_voltage": str(v_nom),
                  "voltage_1": vstart,
                  "voltage_2": vstart,
                  "constant_power_12_real": "10.0",
                  "constant_power_12_reac": "8.0"}
        self.glm.add_object("triplex_load", loadname, params)

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
        income_mat = self.income_level[self.config.state][self.config.res_dso_type]
        # Create new dictionary only with income levels of interest
        dsoIncomePct = {}
        for key in self.config.income_level:
            dsoIncomePct[key] = income_mat[key]
        # dsoIncomePct = {"key": income_mat[key] for key in self.config.income_level}
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

    def getDsoThermalTable(self, income: int) -> float:
        """TODO: _summary_

        Args:
            income (int): Income level of household

        Raises:
            UserWarning: House vintage distribution does not sum to 1!

        Returns:
            float: DSO thermal table
        """
        vintage_mat = self.housing_vintage[self.config.state][self.config.res_dso_type][income]
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

    def selectThermalProperties(self, bldg: int, therm_int: int):
        """Retrieve the building thermal properties for a given type and
        thermal integrity level

        Args:
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            therm_int (int): 0..7 for single-family, apartment or mobile home
        """
        if bldg == 0:
            therm_prop = self.config.base.singleFamilyProperties[therm_int]
        elif bldg == 1:
            therm_prop = self.config.base.apartmentProperties[therm_int]
        else:
            therm_prop = self.config.base.mobileHomeProperties[therm_int]
        return therm_prop

    def add_houses(self, basenode: str, v_nom: float, bIgnoreThermostatSchedule=True, bWriteService=True, bTriplex=True, setpoint_offset=1.0, fg_recs_dataset=None):
        """Put houses, along with solar panels, batteries, and electric vehicle
        charges, onto a node
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
            nhouse = int(self.config.base.house_nodes[basenode][0])
        else:
            housing_type, year_made_range = fg_recs_dataset.get_house_type_vintage(self.config.base.recs_state,
                                                                                   self.config.base.recs_income_level,
                                                                                   self.config.base.recs_housing_density)
            SQFTRANGE = fg_recs_dataset.get_parameter_sample(self.config.base.recs_state,
                                                             self.config.base.recs_income_level,
                                                             self.config.base.recs_housing_density,
                                                             housing_type[0], year_made_range[0], "SQFTRANGE")
            nhouse = fg_recs_dataset.calc_building_count(self.config.base.recs_state,
                                                         self.config.base.recs_income_level,
                                                         self.config.base.recs_housing_density,
                                                         housing_type[0], year_made_range[0])

        rgn = int(self.config.base.house_nodes[basenode][1])
        lg_v_sm = float(self.config.base.house_nodes[basenode][2])
        phs = self.config.base.house_nodes[basenode][3]
        bldg = self.config.base.house_nodes[basenode][4]
        ti = self.config.base.house_nodes[basenode][5]
        inc_lev = self.config.base.house_nodes[basenode][6]
        # rgnTable = self.config.base.rgnThermalPct[rgn-1]

        if 'A' in phs:
            vstart = str(v_nom) + '+0.0j'
        elif 'B' in phs:
            vstart = format(-0.5 * v_nom, '.2f') + format(-0.866025 * v_nom, '.2f') + 'j'
        else:
            vstart = format(-0.5 * v_nom, '.2f') + '+' + format(0.866025 * v_nom, '.2f') + 'j'

        if "_Low" in basenode or "_Middle" in basenode or "_Upper" in basenode:
            basenode = basenode.replace("_Low", "")
            basenode = basenode.replace("_Middle", "")
            basenode = basenode.replace("_Upper", "")
        params = {"phases": phs,
                  "nominal_voltage": str(v_nom),
                  "voltage_1": vstart,
                  "voltage_2": vstart}
        self.glm.add_object("triplex_node", basenode, params)
        tpxname = gld_strict_name(basenode + '_tpx')
        mtrname = gld_strict_name(basenode + '_mtr')
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
            params = {"from": basenode,
                      "to": mtrname1,
                      "phases": phs,
                      "length": "30",
                      "configuration": self.config.base.name_prefix + self.config.base.triplex_configurations[0][0]}
            self.glm.add_object("triplex_line", tpxname1, params)

            params = {"phases": phs,
                      "meter_power_consumption": "1+7j",
                      "nominal_voltage": str(v_nom),
                      "voltage_1": vstart,
                      "voltage_2": vstart}
            self.glm.add_tariff(params)
            self.glm.add_object("triplex_meter", mtrname1, params)
            self.glm.add_metrics_collector(mtrname1, "meter")

            params = {"parent": mtrname1,
                      "phases": phs,
                      "nominal_voltage": str(v_nom)}
            self.glm.add_object("triplex_meter", hse_m_name, params)

        # ************* Floor area, ceiling height and stories *************************
        fa_array = {}  # distribution array for floor area min, max, mean, standard deviation
        stories = 1
        ceiling_height = 8
        vint = self.config.base.vint_type[ti]
        income = self.config.income_level[inc_lev]
        if bldg == 0:  # SF
            bldg_type = 'single_family'  # then pick single_Family_detached values for floor_area
            if (np.random.uniform(0, 1) >
                    self.num_stories[self.config.state][self.config.res_dso_type][income][bldg_type][vint]['one_story']):
                stories = 2  # all SF homes which are not single story are 2 stories
            if np.random.uniform(0, 1) <= \
                    self.high_ceilings[self.config.state][self.config.res_dso_type][income][bldg_type][vint]:
                ceiling_height = 10  # all SF homes that have high ceilings are 10 ft
            ceiling_height += np.random.randint(0, 2)
        elif bldg == 1:  # apartments
            bldg_type = 'apartments'  # then pick apartment_2_4_units for floor area
        elif bldg == 2:  # mh
            bldg_type = 'mobile_home'
        else:
            raise ValueError("Wrong building type chosen !")
        vint = self.config.base.vint_type[ti]
        # creating distribution array for floor_area
        for ind in ['min', 'max', 'mean', 'standard_deviation']:
            fa_array[ind] = self.floor_area[self.config.state][self.config.res_dso_type][income][bldg_type][ind]
        # print(i)
        # print(nhouse)
        floor_area = random_norm_trunc(fa_array)  # truncated normal distribution
        floor_area = (1 + lg_v_sm) * floor_area  # adjustment depends on whether nhouses rounded up or down
        fa_rand = np.random.uniform(0, 1)
        if floor_area > fa_array['max']:
            floor_area = fa_array['max'] - (fa_rand * 200)
        elif floor_area < fa_array['min']:
            floor_area = fa_array['min'] + (fa_rand * 100)

        # ********** residential skew and scalar for schedule files **********
        scalar1 = 324.9 / 8907 * floor_area ** 0.442
        scalar2 = 0.6 + 0.4 * np.random.uniform(0, 1)
        scalar3 = 0.6 + 0.4 * np.random.uniform(0, 1)
        resp_scalar = scalar1 * scalar2
        unresp_scalar = scalar1 * scalar3
        skew_value = self.glm.randomize_residential_skew()

        #  *************** Aspect ratio, ewf, ecf, eff, wwr ****************************
        if bldg == 0:  # SF homes
            # min, max, mean, std
            dist_array = self.aspect_ratio['single_family']
            aspect_ratio = random_norm_trunc(dist_array)
            # Exterior wall and ceiling and floor fraction
            # A normal single family house has all walls exterior, has a ceiling and a floor
            ewf = 1  # exterior wall fraction
            ecf = 1  # exterior ceiling fraction
            eff = 1  # exterior floor fraction
            # window wall ratio
            wwr = (self.window_wall_ratio['single_family']['mean'])
        elif bldg == 1:  # APT
            # min, max, mean, std
            dist_array = self.aspect_ratio['apartments']
            aspect_ratio = random_norm_trunc(dist_array)
            # window wall ratio
            wwr = (self.window_wall_ratio['apartments']['mean'])
            # Two type of apts assumed:
            #       1. small apt: 8 units with 4 units on each level: total 2 levels
            #       2. large apt: 16 units with 8 units on each level: total 2 levels
            # Let's decide if this unit belongs to a small apt (8 units) or large (16 units)
            small_apt_pct = self.housing_type[self.config.state][
                self.config.res_dso_type][income]['apartment_2_4_units']
            large_apt_pct = self.housing_type[self.config.state][
                self.config.res_dso_type][income]['apartment_5_units']
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
            wwr = (self.window_wall_ratio['mobile_home']['mean'])  # window wall ratio
            # sw_pct = self.mobile_home_single_wide[state][dso_type][income]  # single wide percentage for given vintage bin
            # next_ti = ti
            # while not sw_pct:  # if the value is null or 'None', check the next vintage bin
            #     next_ti += 1
            #     sw_pct = self.mobile_home_single_wide[vint_type[next_ti]]
            if floor_area <= 1080:  # Single wide
                aspect_ratio = random_norm_trunc(
                    self.aspect_ratio['mobile_home_single_wide'])
            else:  # double wide
                aspect_ratio = random_norm_trunc(
                    self.aspect_ratio['mobile_home_double_wide'])
            # A normal MH has all walls exterior, has a ceiling and a floor
            ewf = 1  # exterior wall fraction
            ecf = 1  # exterior ceiling fraction
            eff = 1  # exterior floor fraction

        # oversize = rgnOversizeFactor[rgn-1] * (0.8 + 0.4 * np.random.uniform(0,1))
        # data from https://collaborate.pnl.gov/projects/Transactive/Shared%20Documents/DSO+T/Setup%20Assumptions%205.3/Residential%20HVAC.xlsx
        oversize = random_norm_trunc(
            self.hvac_oversize)  # hvac_oversize factor
        wetc = random_norm_trunc(
            self.window_shading)  # window_exterior_transmission_coefficient

        tiProps = Residential_Build.selectThermalProperties(self, bldg, ti)
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
        h_COP = c_COP = np.random.choice(self.config.base.cop_lookup[ti]) * (
                0.9 + np.random.uniform(0, 1) * 0.2)  # +- 10% of mean value
        # h_COP = c_COP = tiProps[10] + np.random.uniform(0, 1) * (tiProps[9] - tiProps[10])

        params = {"parent": hse_m_name,
                  "groupid": self.config.base.bldgTypeName[bldg],
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
        heat_pump_prob = self.space_heating_type[self.config.state][
                             self.config.res_dso_type][income][bldg_type][vint]['gas_heating'] + \
                             self.space_heating_type[self.config.state][
                             self.config.res_dso_type][income][bldg_type][vint]['heat_pump']
        # Get the air conditioning percentage for homes that don't have heat pumps
        electric_cooling_percentage = \
            self.air_conditioning[self.config.state][
                self.config.res_dso_type][income][bldg_type]

        if heat_rand <= self.space_heating_type[self.config.state][self.config.res_dso_type][income][bldg_type][vint]['gas_heating']:
            house_fuel_type = 'gas'
            params["heating_system_type"] = "GAS"
            if cool_rand <= electric_cooling_percentage:
                params["cooling_system_type"] = "ELECTRIC"
            else:
                params["cooling_system_type"] = "NONE"
        elif heat_rand <= self.config.base.rgnPenGasHeat[rgn - 1] + self.config.base.rgnPenHeatPump[rgn - 1]:
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
            if cool_rand <= electric_cooling_percentage:
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
                  "heatgain_fraction": '{:.2f}'.format(self.config.base.techdata[0]),
                  "impedance_pf": '{:.2f}'.format(self.config.base.techdata[1]),
                  "current_pf": '{:.2f}'.format(self.config.base.techdata[2]),
                  "power_pf": '{:.2f}'.format(self.config.base.techdata[3]),
                  "impedance_fraction": '{:.2f}'.format(self.config.base.techdata[4]),
                  "current_fraction": '{:.2f}'.format(self.config.base.techdata[5]),
                  "power_fraction": '{:.2f}'.format(self.config.base.techdata[6])}
        self.glm.add_object("ZIPload", "responsive", params)

        params["base_power"] = 'unresponsive_loads * ' + '{:.2f}'.format(unresp_scalar)
        self.glm.add_object("ZIPload", "unresponsive", params)

        # Determine house water heating fuel type based on space heating fuel type
        wh_fuel_type = 'gas'
        properties = self.water_heating_fuel[self.config.state][self.config.res_dso_type][income][bldg_type]
        if house_fuel_type == 'gas':
            if np.random.uniform(0, 1) <= properties['sh_gas']['electric']:
                wh_fuel_type = 'electric'
        elif house_fuel_type == 'electric':
            if np.random.uniform(0, 1) <= properties['sh_electric']['electric']:
                wh_fuel_type = 'electric'
        if wh_fuel_type == 'electric':  # if the water heater fuel type is electric, install wh
            heat_element = 3.0 + 0.5 * np.random.randint(1, 6)  # numpy randint (lo, hi) returns lo..(hi-1)
            tank_set = 110 + 16 * np.random.uniform(0, 1)
            therm_dead = 1  # 4 + 4 * np.random.uniform(0, 1)
            tank_UA = 2 + 2 * np.random.uniform(0, 1)
            water_sch = np.ceil(self.config.base.waterHeaterScheduleNumber * np.random.uniform(0, 1))
            water_var = 0.95 + np.random.uniform(0, 1) * 0.1  # +/-5% variability
            wh_demand_type = 'large_'

            # new wh size implementation
            wh_data = self.water_heater_tank_size
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
            wh_skew_value = randomize_residential_skew(True)

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
            #          if np.random.uniform (0, 1) <= self.config.base.water_heater_participation:
                            # "waterheater_model": "MULTILAYER",
                            # "discrete_step_size": "60.0",
                            # "lower_tank_setpoint": '{:.1f}'.format(tank_set - 5.0),
                            # "upper_tank_setpoint": '{:.1f}'.format(tank_set + 5.0),
                            # "T_mixing_valve": '{:.1f}'.format(tank_set)
            #          else:
                            # "tank_setpoint": '{:.1f}'.format(tank_set)
            self.glm.add_object("waterheater", whname, params)
            self.glm.add_metrics_collector(whname, "waterheater")

        self.glm.add_metrics_collector(hsename, "house")

        # if PV is allowed,
        #     then only single-family houses can buy it,
        #     and only the single-family houses with PV will also consider storage
        # if PV is not allowed,
        #     then any single-family house may consider storage (if allowed)
        # apartments and mobile homes may always consider storage, but not PV
        # bConsiderStorage = True
        # Solar percentage should be defined here only from RECS data based on income level
        #solar_percentage = self.solar_pv[self.config.state][self.config.res_dso_type][income][bldg_type]
        # Calculate the solar, storage, and ev percentage based on the income level
        # Chain rule for conditional probabilities

        # P(solar and income and SF)
        p_sol_inc_sf = self.config.base.solar_percentage * self.solar_percentage[income]
        # P(SF|income)
        p_sf_g_inc = self.housing_type[self.config.state][self.config.res_dso_type][income]['single_family_detached'] + \
                     self.housing_type[self.config.state][self.config.res_dso_type][income]['single_family_attached']
        # P(income)
        il_percentage = self.income_level[self.config.state][self.config.res_dso_type][income]
        # P(solar|income and SF)
        sol_g_inc_sf = p_sol_inc_sf / (p_sf_g_inc * il_percentage)
        # P(battery and solar and SF and income)
        p_bat_sol_sf_inc = self.config.base.storage_percentage * self.battery_percentage[income]
        # P(battery|solar and SF and income)
        bat_g_sol_sf_inc = p_bat_sol_sf_inc / (sol_g_inc_sf * p_sf_g_inc * il_percentage)
        # P(ev|income)
        ev_percentage_il = (self.config.ev_percentage * self.ev_percentage[income]) / il_percentage

        if bldg == 0:  # Single-family homes
            if sol_g_inc_sf > 0.0:
                pass
                # bConsiderStorage = False
            if np.random.uniform(0, 1) <= sol_g_inc_sf:  # some single-family houses have PV
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
                pv_scaling_factor = inv_power / self.config.rooftop_pv_rating_MW
                if self.config.case_type['pv']:
                    self.config.base.solar_count += 1
                    self.config.base.solar_kw += 0.001 * inv_power
                    params = {"parent": mtrname1,
                              "phases": phs,
                              "nominal_voltage": str(v_nom)}
                    self.glm.add_object("triplex_meter", sol_m_name, params)

                    params = {"parent": sol_m_name,
                              "phases": phs,
                              "groupid": "sol_inverter",
                              "generator_status": "ONLINE",
                              "inverter_type": "FOUR_QUADRANT",
                              "inverter_efficiency": "1",
                              "rated_power": '{:.0f}'.format(inv_power),
                              "generator_mode": self.config.base.solar_inv_mode,
                              "four_quadrant_control_mode": self.config.base.solar_inv_mode}

                    if "solar_P_player" in self.config.keys:
                        params["P_Out"] = f"{self.config.solar_P_player['attr']}.value * {pv_scaling_factor}"
                        if "solar_Q_player" in self.config.keys:
                            params["Q_Out"] = f"{self.config.solar_Q_player['attr']}.value * 0.0"
                        else:
                            params["Q_Out"] = "0"
                        # Instead of solar object, write a fake V_in and I_in sufficient high so
                        # that it doesn't limit the player output
                        params["V_In"] = "10000000"
                        params["I_In"] = "10000000"

                    self.glm.add_object("inverter", sol_i_name, params)
                    self.glm.add_metrics_collector(sol_i_name, "inverter")

                    if ("solar" in self.config.keys and
                            not "solar_P_player" in self.config.keys):
                        params = {
                            "parent": sol_i_name,
                            "panel_type": 'SINGLE_CRYSTAL_SILICON',
                            # "area": '{:.2f}'.format(panel_area),
                            "rated_power":  self.config.solar["rated_power"],
                            "tilt_angle": self.config.solar["tilt_angle"],
                            "efficiency": self.config.solar["efficiency"],
                            "shading_factor": self.config.solar["shading_factor"],
                            "orientation_azimuth": self.config.solar["orientation_azimuth"],
                            "orientation": "FIXED_AXIS",
                            "SOLAR_TILT_MODEL": "SOLPOS",
                            "SOLAR_POWER_MODEL": "FLATPLATE"  }
                        self.glm.add_object("solar", solname, params)

        if np.random.uniform(0, 1) <= bat_g_sol_sf_inc:
            battery_capacity = get_dist(self.config.batt_metadata.capacity['mean'],
                                        self.config.batt_metadata.capacity['deviation_range_per']) * 1000
            max_charge_rate = get_dist(self.config.batt_metadata.rated_charging_power['mean'],
                                       self.config.batt_metadata.rated_charging_power['deviation_range_per']) * 1000
            max_discharge_rate = max_charge_rate
            inverter_efficiency = self.config.batt_metadata.inv_efficiency / 100
            charging_loss = get_dist(self.config.batt_metadata.rated_charging_loss['mean'],
                                     self.config.batt_metadata.rated_charging_loss['deviation_range_per']) / 100
            discharging_loss = charging_loss
            round_trip_efficiency = charging_loss * discharging_loss
            rated_power = max(max_charge_rate, max_discharge_rate)

            if self.config.case_type['bt']:
                self.config.base.battery_count += 1
                params = {"parent": mtrname1,
                          "phases": phs,
                          "nominal_voltage": str(v_nom)}
                self.glm.add_object("triplex_meter", bat_m_name, params)

                params = {"parent": bat_m_name,
                          "phases": phs,
                          "groupid": "batt_inverter",
                          "generator_status": "ONLINE",
                          "generator_mode": "CONSTANT_PQ",
                          "inverter_type": "FOUR_QUADRANT",
                          "four_quadrant_control_mode": self.config.base.storage_inv_mode,
                          "charge_lockout_time": 1,
                          "discharge_lockout_time": 1,
                          "rated_power": rated_power,
                          "charge_on_threshold": "2 kW",
                          "charge_off_threshold": "7 kW",
                          "discharge_on_threshold": "10 kW",
                          "discharge_off_threshold": "5 kW",
                          "max_charge_rate": max_charge_rate,
                          "max_discharge_rate": max_discharge_rate,
                          "sense_object": mtrname1,
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
                self.glm.add_metrics_collector(bat_i_name, "inverter")

        if np.random.uniform(0, 1) <= ev_percentage_il:
            # first lets select an ev model:
            #ev_name = Electric_Vehicle.selectEVmodel(self, self.config.ev_metadata['sale_probability'], np.random.uniform(0, 1))
            ev_name = Electric_Vehicle.selectEVmodel(self.config.ev_metadata.sale_probability, np.random.uniform(0, 1))
            ev_range = self.config.ev_metadata.Range_miles[ev_name]
            ev_mileage = self.config.ev_metadata.Miles_per_kWh[ev_name]
            ev_charge_eff = self.config.ev_metadata.charging_efficiency
            # check if level 1 charger is used or level 2
            if np.random.uniform(0, 1) <= self.config.ev_metadata.Level_1_usage:
                ev_max_charge = self.config.ev_metadata.Level_1_max_power_kW
                volt_conf = 'IS110'  # for level 1 charger, 110 V is good
            else:
                ev_max_charge = self.config.ev_metadata.Level_2_max_power_kW[ev_name]
                volt_conf = 'IS220'  # for level 2 charger, 220 V is must

            # now, let's map a random driving schedule with this vehicle ensuring daily miles
            # doesn't exceed the vehicle range and home duration is enough to charge the vehicle
            drive_sch = self.config.ev_metadata.match_driving_schedule(ev_range, ev_mileage, ev_max_charge)
            # ['daily_miles','home_arr_time','home_duration','work_arr_time','work_duration']

            # Should be able to turn off ev entirely using ev_percentage, definitely in debugging
            if self.config.case_type['ev']:  # evs are populated when its pvCase i.e. high renewable case
                # few sanity checks
                if drive_sch['daily_miles'] > ev_range:
                    raise UserWarning('daily travel miles for EV can not be more than range of the vehicle!')
                if (not is_hhmm_valid(drive_sch['home_arr_time']) or
                    not is_hhmm_valid(drive_sch['home_leave_time']) or
                    not is_hhmm_valid(drive_sch['work_arr_time'])):
                    raise UserWarning('invalid HHMM format of driving time!')
                if drive_sch['home_duration'] > 24 * 3600 or drive_sch['home_duration'] < 0 or \
                        drive_sch['work_duration'] > 24 * 3600 or drive_sch['work_duration'] < 0:
                    raise UserWarning('invalid home or work duration for ev!')
                if not Electric_Vehicle.is_drive_time_valid(drive_sch):
                    raise UserWarning('home and work arrival time are not consistent with durations!')

                self.config.base.ev_count += 1
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
                self.glm.add_metrics_collector(evname, "evchargerdet")
                self.glm.add_group_recorder("class=evcharger_det", "actual_charge_rate", "EV_charging_power.csv")
                self.glm.add_group_recorder("class=evcharger_det", "battery_SOC", "EV_SOC.csv")

class Commercial_Build:
    def __init__(self, config):
        self.config = config
        self.glm = config.glm

    def replace_commercial_loads(self, gld_class: str, avgBuilding: float):
        """For the full-order feeders, scan each load with load_class==C to
        determine the number of zones it should have.

        Args:
            gld_class (str): the GridLAB-D class name to scan
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

        try:
            entity = self.glm.glm.__getattribute__(gld_class)
        except:
            return
        removenames = []
        for e_name, e_object in entity.items():
            if 'load_class' in e_object:
                select_bldg = None
                if e_object['load_class'] == 'C':
                    kva = self.glm.model.accumulate_load_kva(e_object)
                    total_commercial += 1
                    total_comm_kva += kva
                    vln = float(e_object['nominal_voltage'])
                    nphs = 0
                    phases = e_object['phases']
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
                    for bldg in self.config.base.comm_bldgs_pop:
                        if 0 >= (self.config.base.comm_bldgs_pop[bldg][1] - target_sqft) > sqft_error:
                            select_bldg = bldg
                            sqft_error = self.config.base.comm_bldgs_pop[bldg][1] - target_sqft
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
                    comm_type = self.config.base.comm_bldgs_pop[select_bldg][0]
                    comm_size = self.config.base.comm_bldgs_pop[select_bldg][1]
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

                        del (self.config.base.comm_bldgs_pop[select_bldg])
                    else:
                        if nzones > 0:
                            print('Commercial building could not be found for ', '{:.2f}'.format(kva), ' KVA load')
                        comm_name = 'streetlights'
                        comm_type = 'ZIPLOAD'
                        comm_size = 0
                        total_zipload += 1
                    mtr = gld_strict_name(e_object['parent'])
                    extra_billing_meters.add(mtr)
                    self.config.base.comm_loads[e_name] = [mtr, comm_type, comm_size, kva, nphs, phases, vln, total_commercial, comm_name]
                    removenames.append(e_name)
        for e_name in removenames:
            self.glm.del_object(gld_class, e_name)
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
        for bldg in self.config.base.comm_bldgs_pop:
            remain_comm_kva += self.config.base.comm_bldgs_pop[bldg][1] * sqft_kva_ratio
        print('{} commercial buildings, approximately {} kVA still to be assigned.'.
              format(len(self.config.base.comm_bldgs_pop), int(remain_comm_kva)))

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
                  "base_power": '{:s}_exterior*{:.2f}'.format(bldg['base_schedule'], bldg['adj_ext'])}
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
                      "impedance_fraction": '{:.2f}'.format(bldg['c_z_frac']),
                      "current_fraction": '{:.2f}'.format(bldg['c_i_frac']),
                      "power_pf": '{:.2f}'.format(bldg['c_p_pf']),
                      "current_pf": '{:.2f}'.format(bldg['c_i_pf']),
                      "impedance_pf": '{:.2f}'.format(bldg['c_z_pf']),
                      "base_power": '{:.2f}'.format(bldg['adj_refrig'])}
            self.glm.add_object("ZIPload", "large refrigeration", params)

        self.glm.add_metrics_collector(name, "house")

    def add_commercial_loads(self, rgn: int, key: str):
        """Put commercial building zones and ZIP loads into the model

        Args:
            rgn (int): region 1..5 where the building is located
            key (str): GridLAB-D load name that is being replaced
        """
        mtr = self.config.base.comm_loads[key][0]
        comm_type = self.config.base.comm_loads[key][1]
        nz = int(self.config.base.comm_loads[key][2])
        kva = float(self.config.base.comm_loads[key][3])
        nphs = int(self.config.base.comm_loads[key][4])
        phases = self.config.base.comm_loads[key][5]
        vln = float(self.config.base.comm_loads[key][6])
        loadnum = int(self.config.base.comm_loads[key][7])

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
                'oversize': self.config.base.over_sizing_factor[rgn - 1],
                'glazing_layers': 'TWO',
                'glass_type': 'GLASS',
                'glazing_treatment': 'LOW_S',
                'window_frame': 'NONE',
                'c_z_frac': self.config.base.c_z_frac,
                'c_i_frac': self.config.base.c_i_frac,
                'c_p_frac': 1.0 - self.config.base.c_z_frac - self.config.base.c_i_frac,
                'c_z_pf': self.config.base.c_z_pf,
                'c_i_pf': self.config.base.c_i_pf,
                'c_p_pf': self.config.base.c_p_pf}

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
                        bldg['COP_A'] = self.config.base.cooling_COP * (0.8 + 0.4 * np.random.random())

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
                    bldg['COP_A'] = self.config.base.cooling_COP * (0.8 + 0.4 * np.random.random())

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
                bldg['COP_A'] = self.config.base.cooling_COP * (0.8 + 0.4 * np.random.random())
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
            params = {"parent": '{:s}'.format(mtr),
                      "groupid": "STREETLIGHTS",
                      "nominal_voltage": '{:2f}'.format(vln),
                      "phases": '{:s}'.format(phases)}
            for phs in ['A', 'B', 'C']:
                if phs in phases:
                    params["impedance_fraction_" + phs] = '{:f}'.format(self.config.base.c_z_frac)
                    params["current_fraction_" + phs] = '{:f}'.format(self.config.base.c_i_frac)
                    params["power_fraction_" + phs] = '{:f}'.format(bldg['c_p_frac'])
                    params["impedance_pf_" + phs] = '{:f}'.format(self.config.base.c_z_pf)
                    params["current_pf_" + phs] = '{:f}'.format(self.config.base.c_i_pf)
                    params["power_pf_" + phs] = '{:f}'.format(self.config.base.c_p_pf)
                    params["base_power_" + phs] = '{:.2f}'.format(self.config.base.light_scalar_comm * phsva)
            self.glm.add_object("load", name, params)
        else:
            name = '{:s}'.format(key)
            params = {"parent": '{:s}'.format(mtr),
                      "groupid": '{:s}'.format(comm_type),
                      "nominal_voltage": '{:2f}'.format(vln),
                      "phases": '{:s}'.format(phases)}
            self.glm.add_object("load", name, params)

class Battery:
    def __init__(self, config):
        self.config = config

class Solar:

    def __init__(self, config):
        self.config = config
        self.glm = config.glm

    def add_solar_inv_settings(self, params: dict):
        """ Writes volt-var and volt-watt settings for solar inverters

        Args:
            params (dict): solar inverter parameters. Contains:
                {four_quadrant_control_mode, V1, Q1, V2, Q2, V3, Q3, V4, Q4,
                V_In, I_In, volt_var_control_lockout, VW_V1, VW_V2, VW_P1, VW_P2}
        """
        params["four_quadrant_control_mode"] = self.config.base.name_prefix + 'INVERTER_MODE'
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

    def add_solar_defines(self):

        if self.config.base.solar_percentage > 0.0:
            # Waiting for the add comment method to be added to the modify class
            #    default IEEE 1547-2018 settings for Category B'
            #    solar inverter mode on this feeder
            self.glm.model.define_lines.append(
                '#define ' + self.config.base.name_prefix + 'INVERTER_MODE=' + self.config.base.solar_inv_mode)
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

class Electric_Vehicle:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def selectEVmodel(evTable: dict, prob: float) -> str:
        """Selects the EV model based on available sale distribution data

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
            mile_ind = np.random.randint(0, len(self.config.base.ev_driving_metadata['TRPMILES']))
            daily_miles = self.config.base.ev_driving_metadata['TRPMILES'].iloc[mile_ind]
            if ev_range * 0.0 < daily_miles < ev_range * (1 - self.config.ev_reserved_soc / 100):
                break
        daily_miles = max(daily_miles, ev_range * 0.2)
        home_leave_time = self.config.base.ev_driving_metadata['STRTTIME'].iloc[mile_ind]
        home_arr_time = self.config.base.ev_driving_metadata['ENDTIME'].iloc[mile_ind]
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

    @staticmethod
    def is_drive_time_valid(drive_sch: dict) -> bool:
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
        max_ev_range = max(self.Range_miles.values())
        df_data_miles = df_data_miles[df_data_miles < max_ev_range]
        df_data_miles = df_data_miles[df_data_miles > 0]

        # combine all 4 parameters: starttime, endtime, total_miles, travel_day.
        # Ignore vehicle ids that don't have both leaving and arrival time at home
        temp = df_data_leave.merge(df_data_arrive['ENDTIME'], left_index=True, right_index=True)
        df_fin = temp.merge(df_data_miles, left_index=True, right_index=True)
        return df_fin

class Feeder:

    def __init__(self, config: Config):
        self.config = config
        self.glm = config.glm
        config.generate_and_load_recs()

        # Read in backbone feeder to populate
        if config.use_feeder:
            glm, success = self.glm.model.readBackboneModel(config.taxonomy)
            if not success:
                exit()
        else:
            self.glm.read_model(config.in_file_glm)

        config.preamble()

        # NEW STRATEGY - loop through transformer instances and assign a
        # standard size based on the downstream load
        #   - change the referenced transformer_configuration attributes
        #   - write the standard transformer_configuration instances we actually need
        seg_loads = self.glm.model.identify_seg_loads()

        # Power and region to requirements for commercial and residential load
        # The taxchoice array are for feeder taxonomy signature glm file
        # and are size accordingly with file name, the transformer configuration,
        # setting current_limit for fuse, setting cap_nominal_voltage
        # and current_limit for capacitor

        # taxchoice array [taxonomy, vll, vln, avg_house, avg_commercial, region]
        # and are configure in the config file with above names.

        xfused = {}  # ID, phases, total kva, vnom (LN), vsec, poletop/padmount
        secnode = {}  # Node, st, phases, vnom

        for e_name, e_object in self.glm.glm.transformer.items():
            # "identify_seg_loads" does not account for parallel paths in the
            # model. This test allows us to skip paths that have not been
            # had load accumulated with them, including parallel paths.
            # Also skipping population for transformers with secondary more than 500 V
            e_config = e_object['configuration']
            sec_v = float(self.glm.glm.transformer_configuration[e_config]['secondary_voltage'])
            if e_name not in seg_loads or sec_v > 500:
                print(f"WARNING: {e_name} not in the seg loads")
                continue
            seg_kva = seg_loads[e_name][0]
            seg_phs = seg_loads[e_name][1]

            nphs = 0
            if 'A' in seg_phs:
                nphs += 1
            if 'B' in seg_phs:
                nphs += 1
            if 'C' in seg_phs:
                nphs += 1
            if nphs > 1:
                kvat = self.glm.find_3phase_xfmr_w_margin(seg_kva)
            else:
                kvat = self.glm.find_1phase_xfmr_w_margin(seg_kva)
            if 'S' in seg_phs:
                vnom = 120.0
                vsec = 120.0
            else:
                if 'N' not in seg_phs:
                    seg_phs += 'N'
                if kvat > config.base.max208kva:
                    vsec = 480.0
                    vnom = 277.0
                else:
                    vsec = 208.0
                    vnom = 120.0

            secnode[gld_strict_name(e_object['to'])] = [kvat, seg_phs, vnom]

            old_key = self.glm.model.hash[e_object['configuration']]
            install_type = self.glm.glm.transformer_configuration[old_key]['install_type']

            raw_key = 'XF' + str(nphs) + '_' + install_type + '_' + seg_phs + '_' + str(kvat)
            key = raw_key.replace('.', 'p')

            e_object['configuration'] = config.base.name_prefix + key
            e_object['phases'] = seg_phs
            if key not in xfused:
                xfused[key] = [seg_phs, kvat, vnom, vsec, install_type]

        for key in xfused:
            self.glm.add_xfmr_config(key, xfused[key][0], xfused[key][1], xfused[key][2], xfused[key][3],
                                 xfused[key][4], config.vll, config.vln)

        for e_name, e_object in self.glm.glm.capacitor.items():
            e_object['nominal_voltage'] = str(int(config.vln))
            e_object['cap_nominal_voltage'] = str(int(config.vln))

        for e_name, e_object in self.glm.glm.fuse.items():
            if e_name in seg_loads:
                seg_kva = seg_loads[e_name][0]
                seg_phs = seg_loads[e_name][1]

                nphs = 0
                if 'A' in seg_phs:
                    nphs += 1
                if 'B' in seg_phs:
                    nphs += 1
                if 'C' in seg_phs:
                    nphs += 1
                if nphs == 3:
                    amps = 1000.0 * seg_kva / math.sqrt(3.0) / config.vll
                elif nphs == 2:
                    amps = 1000.0 * seg_kva / 2.0 / config.vln
                else:
                    amps = 1000.0 * seg_kva / config.vln
                e_object['current_limit'] = str(self.glm.find_fuse_limit_w_margin(amps))

        self.glm.add_local_triplex_configurations()

        configurations = ['regulator_configuration', 'overhead_line_conductor', 'line_spacing', 'line_configuration',
                          'triplex_line_conductor', 'triplex_line_configuration', 'underground_line_conductor']
        for configure in configurations:
            self.glm.add_config_class(configure)

        links = ['fuse', 'switch', 'recloser', 'sectionalizer',
                 'overhead_line', 'underground_line', 'series_reactor',
                 'regulator', 'transformer', 'capacitor']
        for link in links:
            metrics = False
            if link in ['regulator', 'capacitor']:
                metrics = True
            self.glm.add_link_class(link, seg_loads, want_metrics=metrics)

        # Identify commercial and residential loads
        config.comm_bldg_metadata.replace_commercial_loads('load', 0.001 * config.avg_commercial)
        self.identify_xfmr_houses('transformer', seg_loads, 0.001 * config.avg_house, config.region)

        # Build the grid for commercial and residential loads
        for key in config.base.house_nodes:
            config.res_bldg_metadata.add_houses(key, 120.0)
        for key in config.base.small_nodes:
            config.res_bldg_metadata.add_small_loads(key, 120.0)
        for key in config.base.comm_loads:
            # add_commercial_loads(rgn, key)
            bldg_definition = comm_FG.define_comm_loads(self.glm,
                config.base.comm_loads[key][1],
                config.base.comm_loads[key][2],
                config.utility_type,
                config.ashrae_zone,
                config.comm_bldg_metadata)
            comm_FG.add_comm_zones(self, bldg_definition, key)

#        self.glm.add_voltage_class('node', self.g_config.vln, self.g_config.vll, secnode)
#        self.glm.add_voltage_class('meter', self.g_config.vln, self.g_config.vll, secnode)
#        self.glm.add_voltage_class('load', self.g_config.vln, self.g_config.vll, secnode)

        print(f"cooling bins unused {config.base.cooling_bins}")
        print(f"heating bins unused {config.base.heating_bins}")
        print(f"{config.base.solar_count} pv totaling "
              f"{config.base.solar_kw:.1f} kw with "
              f"{config.base.battery_count} batteries")
        self.glm.write_model(config.out_file_glm)

        # To plot the model using the networkx package:
        #print("\nPlotting image of model; this will take a minute.")
        #self.glm.model.plot_model()

    def identify_xfmr_houses(self, gld_class: str, seg_loads: dict, avgHouse: float, rgn: int):
        """For the full-order feeders, scan each service transformer to
        determine the number of houses it should have
        Args:
            gld_class (str): the GridLAB-D class name to scan
            seg_loads (dict): dictionary of downstream load (kva) served by each GridLAB-D link
            avgHouse (float): the average house load in kva
            rgn (int): the region number, 1..5
        """
        print(f"Average House {avgHouse} kVA")
        total_houses = 0
        total_sf = 0
        total_apt = 0
        total_mh = 0
        total_small = 0
        total_small_kva = 0
        dsoIncomePct = self.config.res_bldg_metadata.getDsoIncomeLevelTable()
        try:
            entity = self.glm.glm.__getattribute__(gld_class)
        except:
            return
        for e_name, e_object in entity.items():
            if e_name in seg_loads:
                tkva = seg_loads[e_name][0]
                phs = seg_loads[e_name][1]
                if 'S' in phs:
                    nhouse = int((tkva / avgHouse) + 0.5)  # round to nearest int
                    node = gld_strict_name(e_object['to'])
                    if nhouse <= 0:
                        total_small += 1
                        total_small_kva += tkva
                        self.config.base.small_nodes[node] = [tkva, phs]
                    else:
                        total_houses += nhouse
                        lg_v_sm = tkva / avgHouse - nhouse  # >0 if we rounded down the number of houses
                        # let's get the income level for the dso_type and state
                        inc_lev = self.config.res_bldg_metadata.selectIncomeLevel(dsoIncomePct, np.random.uniform(0, 1))
                        # let's get the vintage table for dso_type, state, and income level
                        dsoThermalPct = self.config.res_bldg_metadata.getDsoThermalTable(self.config.income_level[inc_lev])
                        bldg, ti = self.config.res_bldg_metadata.selectResidentialBuilding(dsoThermalPct, np.random.uniform(0, 1))
                        if bldg == 0:
                            total_sf += nhouse
                        elif bldg == 1:
                            total_apt += nhouse
                        else:
                            total_mh += nhouse
                        self.config.base.house_nodes[node] = [nhouse, rgn, lg_v_sm, phs, bldg, ti, inc_lev]
        print(f"{total_small} small loads totaling {total_small_kva:.2f} kVA")
        print(f"{total_houses} houses on {len(self.config.base.house_nodes)} transformers, "
              f"[SF, APT, MH] = [{total_sf}, {total_apt}, {total_mh}]")
        for i in range(6):
            self.config.base.heating_bins[0][i] = round(total_sf * self.config.base.bldgHeatingSetpoints[0][i][0] + 0.5)
            self.config.base.heating_bins[1][i] = round(total_apt * self.config.base.bldgHeatingSetpoints[1][i][0] + 0.5)
            self.config.base.heating_bins[2][i] = round(total_mh * self.config.base.bldgHeatingSetpoints[2][i][0] + 0.5)
            self.config.base.cooling_bins[0][i] = round(total_sf * self.config.base.bldgCoolingSetpoints[0][i][0] + 0.5)
            self.config.base.cooling_bins[1][i] = round(total_apt * self.config.base.bldgCoolingSetpoints[1][i][0] + 0.5)
            self.config.base.cooling_bins[2][i] = round(total_mh * self.config.base.bldgCoolingSetpoints[2][i][0] + 0.5)


def _test1():
    config = Config("./feeder_config.json5")
    feeder = Feeder(config)



if __name__ == "__main__":
    _test1()