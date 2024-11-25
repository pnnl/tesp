# Copyright (C) 2018-2020 Battelle Memorial Institute
# file: gld_feeder_generator.py
""" This gld_feeder_generator.py is an updated feeder generator that combines 
the functionality of both residential_feeder_glm.py and commercial_feeder_glm.py.

Replaces ZIP loads with houses, optional storage, electric vehicles, and solar
generation.

As this module populates the feeder backbone with houses and DER, it uses
the Networkx package to perform graph-based capacity analysis, upgrading
fuses, transformers and lines to serve the expected load. Transformers have
a margin of 20% to avoid overloads, while fuses have a margin of 150% to
avoid overloads. These can be changed by editing tables and variables in the
source file.

References:
    `GridAPPS-D Feeder Models <https://github.com/GRIDAPPSD/Powergrid-Models>`_

Public Functions:
    Config
    :preamble: Add required modules, objects, includes, defines, and sets 
        required to run a .glm model.
    :generate_recs: Generate RECS metadata if it does not yet exist based on 
        user config.
    :load_recs: Assign default values for residential and commercial buildings, 
        batteries, and electric vehicles, based on imported metadata for each.
    :load_position: Read in positional data from feeder, if specified in config,
        to aid plotting function of populated feeder model.

    Residential_Build
    :buildingTypeLabel: Assign formatted name of region, building type name, 
        and thermal integrity level.
    :checkResidentialBuildingTable: Verify that the regional building parameter
        histograms sum to one.
    :selectSetpointBins: Randomly choose a histogram row from the cooling and
        heating setpoints. The random number for the heating setpoint row is 
        generated internally.
    :add_small_loads: Write loads that are too small for a house, onto a node.
    :getDsoIncomeLevelTable: Retrieve the DSO income level fractions for the
        given dso type and state.
    :selectIncomeLevel: Select the income level based on region and probability.
    :getDsoThermalTable: Define the distribution of thermal integrity values 
        based on household income level, vintage, and building type.
    :selectResidentialBuilding: Retrieve the thermal integrity level by 
        building type and region.
    :selectThermalProperties: Retrieve the building thermal properties by
        building type and thermal integrity level.
    :add_houses: Add houses, along with solar panels, batteries, and electric
        vehicle charges, onto a node.
    
    Commercial_Build
    :add_one_commercial_zone: Write one pre-configured commercial zone as a 
        house and small loads such as lights, plug loads, and gas water heaters 
        as ZIPLoads.
    :define_commercial_zones: Define building parameters for commercial building
        zones and ZIP loads, then add to model as house object (commercial zone)
        or load object (ZIP load).
    :define_comm_bldg: Randomly select a set number of buildings by type and 
        size (sqft).
    :normalize_dict_prob: Ensure that the probability distribution of values in 
        a dictionary effectively sums to one.
    :rand_bin_select: Returns the element (bin) in a dictionary given a certain
        probability.
    :sub_bin_select: Returns a scalar value within a bin range based on a uniform 
        probability within that bin range.
    :find_envelope_prop: Returns the envelope value for a given type of property
        based on the age and (ASHRAE) climate zone of the building.
    
    Battery
    :add_batt: Define and add battery and inverter objects to house, under the 
        parentage of the parent_mtr.
    
    Solar
    :add_solar: Define and add solar and inverter objects to house, under the
        parentage of the parent_mtr.

    Electric_Vehicle
    :add_ev: Define and add electric vehicle charging object to the house, under
        the parentage of the house object.
    :selectEVmodel: Select the EV model based on available sale distribution
        data.
    :match_driving_schedule: Method to match the schedule of each vehicle from 
        NHTS data based on vehicle ev_range.
    :is_drive_time_valid: Check if work arrival time and home arrival time add
       up properly.
    :process_nhts_data: Read the large NHTS survey data file containing driving 
        data, process it, and return a dataframe.

    Feeder
    :feeder_gen: Read in the backbone feeder, then loop through transformer 
        instances and assign a standard size based on the downstream load. 
        Change the referenced transformer_configuration attributes. Write the
        standard transformer_configuration instance we need.
    :identify_xfmr_houses: For the full-order feeders, scan each service 
        transformer to determine the number of houses it should have.
    :identify_commercial_loads: For the full-order feeders, scan each load with
        load_class==C to determine the number of zones it should have.

"""

import logging as log
import math
import json
import os

import numpy as np
import pandas as pd

from tesp_support.api.helpers import gld_strict_name, random_norm_trunc, randomize_residential_skew
from tesp_support.api.modify_GLM import GLMModifier
from tesp_support.api.time_helpers import get_secs_from_hhmm, get_hhmm_from_secs, get_duration, get_dist
from tesp_support.api.time_helpers import is_hhmm_valid, subtract_hhmm_secs, add_hhmm_secs
from tesp_support.api.entity import assign_defaults
from tesp_support.api.recs_gld_house_parameters import get_RECS_jsons

extra_billing_meters = set()

log.basicConfig(level=log.WARNING)
log.getLogger('matplotlib.font_manager').disabled = True

class Config:
    def __init__(self, config=None):
        # Assign default values to those not defined in config file
        self.keys = list(assign_defaults(self, config).keys())
        self.glm = GLMModifier()
        self.mdl = self.glm.glm
        self.base = self.glm.defaults
        self.res_bld = Residential_Build(self)
        self.com_bld = Commercial_Build(self)
        self.sol = Solar(self)
        self.batt = Battery(self)
        self.ev = Electric_Vehicle(self)
        global rng
        rng = np.random.default_rng(self.seed)

        # Lookup vll and vln values based on taxonomy feeder
        if self.in_file_glm:
            log.warning("vll and vln not known for user-defined feeder. Using defaults.")
        for key in self.base.taxchoice:
            if key[0] == self.taxonomy[:-4]:
                self.vll = key[1]
                self.vln = key[2]

    def preamble(self) -> None:
        """ Add required modules, objects, includes, defines, and sets required
        to run a .glm model.
        Returns:
            None
        """

        # Add tape, climate, generators, connection, and residential modules
        self.glm.add_module("tape", {})
        self.glm.add_module("climate", {})
        self.glm.add_module("generators", {})
        self.glm.add_module("connection", {})
        self.glm.add_module("residential", {"implicit_enduses": "NONE"})

        # Add player files if pre-defining solar generation
        if self.use_solar_player == "True":
            player = self.solar_P_player
            self.glm.model.add_class(player["name"], player["datatype"], player["attr"], player["static"], os.path.join(self.data_path, player["data"]))

        self.glm.model.set_clock(self.starttime, self.stoptime, self.timezone)

        # Add includes
        for item in self.includes:
            self.glm.model.add_include(item)

        # Add sets
        for key in self.sets:
            self.glm.model.add_set(key, self.sets[key])

        # Add defines
        for key, value in self.defines:
            self.glm.model.add_define(key, value)

        # Add voltage dump file
        if self.base.WANT_VI_DUMP:
            self.glm.add_voltage_dump(self.base.case_name)

        # Add metrics interval and interim interval
        if self.metrics_interval > 0:
            self.mdl.metrics_collector_writer.add("mc", {
                "interval": str(self.base.metrics_interval),
                "interim": str(self.base.metrics_interim),
                "filename": str(self.base.metrics_filename),
                "alternate": str(self.base.metrics_alternate),
                "extension": str(self.base.metrics_extension) })

        # Add climate object and weather params
        self.mdl.climate.add(self.base.weather_name, {
            "interpolate": str(self.interpolate),
            "latitude": str(self.latitude),
            "longitude": str(self.longitude),
            "tmyfile": str(self.tmyfile) })

    def generate_recs(self) -> None:
        """Generate RECS metadata if it does not yet exist based on user config.
        Args:
            None
        Returns:
            None
        """

        if not self.out_file_residential_meta:
            # self.out_file_residential_meta = "RECS_residential_metadata.json"
            get_RECS_jsons(
                os.path.join(self.data_path, self.file_residential_meta),
                os.path.join(self.data_path, self.out_file_residential_meta),
                os.path.join(self.data_path, self.out_file_hvac_set_point),
                self.sample,
                self.bin_size_threshold,
                self.region,
                self.wh_shift
            )

    def load_recs(self) -> None:
        """ Assign default values for residential and commercial buildings,
        batteries, and electric vehicles, based on imported metadata for each.
        Args:
            None
        Returns:
            None
        """

        assign_defaults(self.com_bld, os.path.join(self.data_path, self.file_commercial_meta))
        # generate the total population of commercial buildings by type and size
        num_comm_customers = round(self.number_of_gld_homes *
                                   self.RCI_customer_count_mix["commercial"] /
                                   self.RCI_customer_count_mix["residential"])
        num_comm_bldgs = num_comm_customers / self.comm_customers_per_bldg
        self.base.comm_bldgs_pop = self.com_bld.define_comm_bldg(self.utility_type, num_comm_bldgs)

        assign_defaults(self.res_bld, os.path.join(self.data_path, self.out_file_residential_meta))
        self.res_bld.checkResidentialBuildingTable()
        cop_mat = self.res_bld.COP_average
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

        assign_defaults(self.batt, os.path.join(self.data_path, self.file_battery_meta))
        assign_defaults(self.ev, os.path.join(self.data_path, self.file_ev_meta))
        self.base.ev_driving_metadata = self.ev.process_nhts_data(os.path.join(self.data_path, self.file_ev_driving_meta))
    
    def load_position(self) -> dict | None:
        """ Read in positional data from feeder, if specified in config, to
        aid plotting function of populated feeder model.
        Use position files for taxonomy feeder, if no input feeder specified.
        Args:
            None
        Returns:
            dict: self.pos_data, .glm objects and their position coordinates
            dict: self.pos, an empty dictionary to assign positions to objects
                added by feeder generator
        """
        
        if not self.in_file_glm:
            self.gis_file = self.taxonomy.replace('-', '_').replace('.', '_').replace('_glm', '_pos.json')
        if self.gis_file:
            gis_path = os.path.join(self.data_path, self.gis_file)
            with open(gis_path) as gis:
                self.pos_data = json.load(gis)
                self.pos = {}
            return self.pos_data, self.pos
        else:
            pass

class Residential_Build:
    def __init__(self, config):
        self.config = config
        self.glm = config.glm
        self.mdl = config.glm.glm

    def buildingTypeLabel(self, rgn: int, bldg: int, therm_int: int) -> list:
        """Assign formatted name of region, building type name, and thermal
        integrity level.

        Args:
            rgn (int): region number 1..5
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            therm_int (int): thermal integrity level, 0..6 for single-family, 
                only 0..2 valid for apartment or mobile home
        Returns:
            list: table containing region, building type, and thermal integrity
        """

        return self.config.base.rgnName[rgn - 1] + ': ' + self.config.base.bldgTypeName[bldg] + ': TI Level ' + str(therm_int + 1)

    def checkResidentialBuildingTable(self) -> None:
        """Verify that the regional building parameter histograms sum to one.
        Args:
            None
        Returns:
            None
        """

        for tbl in range(len(self.config.base.bldgCoolingSetpoints)):
            total = 0
            for row in range(len(self.config.base.bldgCoolingSetpoints[tbl])):
                total += self.config.base.bldgCoolingSetpoints[tbl][row][0]
            log.info('bldgCoolingSetpoints %s histograms sum to %.4f', tbl, total)
        for tbl in range(len(self.config.base.bldgHeatingSetpoints)):
            total = 0
            for row in range(len(self.config.base.bldgHeatingSetpoints[tbl])):
                total += self.config.base.bldgHeatingSetpoints[tbl][row][0]
            log.info('bldgHeatingSetpoints %s histograms sum to %.4f', tbl, total)
        for bldg in range(3):
            binZeroReserve = self.config.base.bldgCoolingSetpoints[bldg][0][0]
            binZeroMargin = self.config.base.bldgHeatingSetpoints[bldg][0][0] - binZeroReserve
            if binZeroMargin < 0.0:
                binZeroMargin = 0.0
            log.info('bldg %s, binZeroReserve %s, binZeroMargin %s', bldg, binZeroReserve, binZeroMargin)
            for cBin in range(1, 6):
                denom = binZeroMargin
                for hBin in range(1, self.config.base.allowedHeatingBins[cBin]):
                    denom += self.config.base.bldgHeatingSetpoints[bldg][hBin][0]
                self.config.base.conditionalHeatingBinProb[bldg][cBin][0] = binZeroMargin / denom
                for hBin in range(1, self.config.base.allowedHeatingBins[cBin]):
                    self.config.base.conditionalHeatingBinProb[bldg][cBin][hBin] = \
                        self.config.base.bldgHeatingSetpoints[bldg][hBin][0] / denom

    def selectSetpointBins(self, bldg: int, rand: float) -> int:
        """Randomly choose a histogram row from the cooling and heating setpoints.
        The random number for the heating setpoint row is generated internally.

        Args:
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            rand (float): random number [0..1) for the cooling setpoint row
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
        rand_heat = rng.random()
        total = 0
        for col in range(len(tbl)):
            total += tbl[col]
            if total >= rand_heat:
                hBin = col
                break
        return self.config.base.bldgCoolingSetpoints[bldg][cBin], self.config.base.bldgHeatingSetpoints[bldg][hBin]

    def add_small_loads(self, basenode: str, v_nom: float) -> None:
        """Write loads that are too small for a house, onto a node.

        Args:
            basenode (str): GridLAB-D node name
            v_nom (float): nominal line-to-neutral voltage at basenode
        Returns:
            None
        """

        phs = self.config.base.small_nodes[basenode][1]
        if 'A' in phs:
            vstart = str(v_nom) + '+0.0j'
        elif 'B' in phs:
            vstart = format(-0.5 * v_nom, '.2f') + format(-0.866025 * v_nom, '.2f') + 'j'
        else:
            vstart = format(-0.5 * v_nom, '.2f') + '+' + format(0.866025 * v_nom, '.2f') + 'j'

        tpxname = basenode + '_tpx_sm'
        mtrname = basenode + '_mtr_sm'
        loadname = basenode + '_load_sm'
        self.mdl.triplex_node.add(basenode, {
            "phases": phs,
            "nominal_voltage": str(v_nom),
            "voltage_1": vstart,
            "voltage_2": vstart })

        self.mdl.triplex_line.add(tpxname, {
            "from": basenode,
            "to": mtrname,
            "phases": phs,
            "length": "30",
            "configuration": self.config.base.triplex_configurations[0][0] })

        params = {"phases": phs,
                  "meter_power_consumption": "1+7j",
                  "nominal_voltage": str(v_nom),
                  "voltage_1": vstart,
                  "voltage_2": vstart}
        self.glm.add_tariff(params)
        self.mdl.triplex_meter.add(mtrname, params)
        self.glm.add_metrics_collector(mtrname, "meter")

        self.mdl.triplex_load.add(loadname, {
            "parent": mtrname,
            "phases": phs,
            "nominal_voltage": str(v_nom),
            "voltage_1": vstart,
            "voltage_2": vstart,
            "constant_power_12_real": "10.0",
            "constant_power_12_reac": "8.0" })
        if self.config.gis_file:
            self.config.pos[mtrname] = self.config.pos_data[basenode]

    def getDsoIncomeLevelTable(self) -> list:
        """Retrieve the DSO Income Level Fraction of income level in a given 
        dso type and state.
        
        Index 0 is the income level:
            0 = Low
            1 = Middle (No longer using Moderate)
            2 = Upper
        Args:
            None
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
        dsoIncomePct = list(dsoIncomePct.values())
        # Normalize so array adds up to 1
        dsoIncomePct = [round(i / sum(dsoIncomePct), 4) for i in dsoIncomePct]  
        # Check if the sum of all values is 1
        total = 0
        for row in range(len(dsoIncomePct)):
            total += dsoIncomePct[row]
        if total > 1.01 or total < 0.99:
             raise UserWarning('Income level distribution does not sum to 1!')
        return dsoIncomePct

    def selectIncomeLevel(self, incTable: list, prob: float) -> int:
        """Select the income level based on region and probability.

        Args:
            incTable (): income table
            prob (float): probability
        Returns:
            int: row
        """

        total = 0
        for row in range(len(incTable)):
            total += incTable[row]
            if total >= prob:
                return row
        row = len(incTable) - 1
        return row

    def getDsoThermalTable(self, income: int) -> float:
        """ Define the distribution of thermal integrity values based on 
        household income level, vintage, and building type.

        Args:
            income (int): Income level of household
        Raises:
            UserWarning: House vintage distribution does not sum to 1!
        Returns:
            float: DSO thermal table
        """

        vintage_mat = self.housing_vintage[self.config.state][self.config.res_dso_type][income]
        df = pd.DataFrame(vintage_mat)
        # Initialize array
        dsoThermalPct = np.zeros(shape=(3, 9)) 
        dsoThermalPct[0] = (df['single_family_detached'] + df['single_family_attached']).values
        dsoThermalPct[1] = (df['apartment_2_4_units'] + df['apartment_5_units']).values
        dsoThermalPct[2] = (df['mobile_home']).values
        dsoThermalPct = dsoThermalPct.tolist()
        # Check if the sum of all values is 1
        total = 0
        for row in range(len(dsoThermalPct)):
            for col in range(len(dsoThermalPct[row])):
                total += dsoThermalPct[row][col]
        if total > 1.01 or total < 0.99:
            raise UserWarning('House vintage distribution does not sum to 1!')
        #log.info('dsoThermalPct sums to %.4f', total)
        return dsoThermalPct

    def selectResidentialBuilding(self, rgnTable: list, prob: float) -> list:
        """Retrieve the thermal integrity level by building type and region.

        Args:
            rgnTable (list): thermal integrity by region
            prob (float): probability 
        Returns:
            int: row
            int: col
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

    def selectThermalProperties(self, bldg: int, therm_int: int) -> list:
        """Retrieve the building thermal properties by building type and
        thermal integrity level.

        Args:
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            therm_int (int): 0..7 for single-family, apartment or mobile home
        Returns:
            list: therm_prop
        """

        if bldg == 0:
            therm_prop = self.config.base.singleFamilyProperties[therm_int]
        elif bldg == 1:
            therm_prop = self.config.base.apartmentProperties[therm_int]
        else:
            therm_prop = self.config.base.mobileHomeProperties[therm_int]
        return therm_prop

    def add_houses(self, basenode: str, v_nom: float) -> None:
        """Add houses, along with solar panels, batteries, and electric vehicle
        chargers, onto a node.
        
        Args:
            basenode (str): GridLAB-D node name
            v_nom (float): nominal line-to-neutral voltage at basenode
        Raises:
            ValueError: if bldg_type does not exist, raise: Wrong building type 
                chosen!
            UserWarning: if daily drive miles exceeds range of EV, raise: daily 
                travel miles for EV cannot be more than range of the vehicle!
            UserWarning: if home arrival time, leave time, and work arrival 
                times are incorrectly formatted, raise: invalid HHMM format of 
                driving time!
            UserWarning: if home or work durations exceed all hours of the day 
                or are negative, raise: invalid home or work duration for ev!
            UserWarning: if drive times are not valid, raise: home and work 
                arrival time are not consistent with durations!
        Returns:
            None
        """

        self.nhouse = int(self.config.base.house_nodes[basenode][0])
        lg_v_sm = float(self.config.base.house_nodes[basenode][2])
        phs = self.config.base.house_nodes[basenode][3]
        bldg = self.config.base.house_nodes[basenode][4]
        ti = self.config.base.house_nodes[basenode][5]
        inc_lev = self.config.base.house_nodes[basenode][6]

        # Add triplex meters for nodes and houses, string lines between
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
        self.mdl.triplex_node.add(basenode, {
            "phases": phs,
            "nominal_voltage": str(v_nom),
            "voltage_1": vstart,
            "voltage_2": vstart })
        tpxname = f'{basenode}_tpx'
        mtrname = f'{tpxname}_mtr'
        for i in range(self.nhouse):
            idx = i + 1
            tpxname1 = f'{tpxname}_{idx}'
            mtrname1 = f'{mtrname}_{idx}'
            hsename = f'{basenode}_hs_{idx}'
            hse_m_name = f'{basenode}_hsmtr_{idx}'
            whname = f'{basenode}_wh_{idx}'
            sol_i_name = f'{basenode}_solinv_{idx}'
            bat_i_name = f'{basenode}_batinv_{idx}'
            sol_m_name = f'{basenode}_solmtr_{idx}'
            sol_name = f'{basenode}_sol_{idx}'
            bat_m_name = f'{basenode}_batmtr_{idx}'
            bat_name = f'{basenode}_bat_{idx}'
            # Add position data to house and meter objects, if available
            if self.config.gis_file:
                self.config.pos[mtrname1] = self.config.pos_data[basenode]
                self.config.pos[hsename] = self.config.pos_data[basenode]
                self.config.pos[hse_m_name] = self.config.pos_data[basenode]
                self.config.pos[bat_m_name] = self.config.pos_data[basenode]
                self.config.pos[sol_m_name] = self.config.pos_data[basenode]
            self.mdl.triplex_line.add(tpxname1, {"from": basenode,
                      "to": mtrname1,
                      "phases": phs,
                      "length": "30",
                      "configuration": self.config.base.name_prefix + self.config.base.triplex_configurations[0][0] })

            params = {"phases": phs,
                      "meter_power_consumption": "1+7j",
                      "nominal_voltage": str(v_nom),
                      "voltage_1": vstart,
                      "voltage_2": vstart}
            self.glm.add_tariff(params)
            self.mdl.triplex_meter.add(mtrname1, params)
            self.glm.add_metrics_collector(mtrname1, "meter")

            self.mdl.triplex_meter.add(hse_m_name, {
                "parent": mtrname1,
                "phases": phs,
                "nominal_voltage": str(v_nom) })

            # Assign floor area, ceiling height, and stories of houses
            fa_array = {}  # distribution array for floor area min, max, mean, standard deviation
            stories = 1
            ceiling_height = 8
            vint = self.config.base.vint_type[ti]
            income = self.config.income_level[inc_lev]
            if bldg == 0:  # SF
                bldg_type = 'single_family'  # pick single_family_detached values for floor_area
                if (rng.random() >
                        self.num_stories[self.config.state][self.config.res_dso_type][income][bldg_type][vint]['one_story']):
                    stories = 2  # all SF homes which are not single story are 2 stories
                if rng.random() <= \
                        self.high_ceilings[self.config.state][self.config.res_dso_type][income][bldg_type][vint]:
                    ceiling_height = 10  # all SF homes that have high ceilings are 10 ft
                ceiling_height += rng.integers(0, 2)
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
            floor_area = random_norm_trunc(fa_array)  # truncated normal distribution
            floor_area = (1 + lg_v_sm) * floor_area  # adjustment depends on whether nhouses rounded up or down
            fa_rand = rng.random()
            if floor_area > fa_array['max']:
                floor_area = fa_array['max'] - (fa_rand * 200)
            elif floor_area < fa_array['min']:
                floor_area = fa_array['min'] + (fa_rand * 100)

            # Define residential skew and scalar for schedule files
            scalar1 = 324.9 / 8907 * floor_area ** 0.442
            scalar2 = 0.6 + 0.4 * rng.random()
            scalar3 = 0.6 + 0.4 * rng.random()
            resp_scalar = scalar1 * scalar2
            unresp_scalar = scalar1 * scalar3
            skew_value = self.glm.randomize_residential_skew()

            # Define aspect ratio, ewf, ecf, eff, wwr
            if bldg == 0:  # SF homes
                # min, max, mean, std
                dist_array = self.aspect_ratio['single_family']
                aspect_ratio = random_norm_trunc(dist_array)
                # Exterior wall and ceiling and floor fraction
                # single family detatched house has all exterior walls, ceiling, and floor
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
                # Two type of apts assumed, total 2 levels each:
                #       1. small apt: 8 units with 4 units on each level
                #       2. large apt: 16 units with 8 units on each level
                # Assign percentage of units to small apt (8 units) or large (16 units)
                small_apt_pct = self.housing_type[self.config.state][
                    self.config.res_dso_type][income]['apartment_2_4_units']
                large_apt_pct = self.housing_type[self.config.state][
                    self.config.res_dso_type][income]['apartment_5_units']
                if rng.random() < small_apt_pct / (small_apt_pct + large_apt_pct):
                    # 2-level small apt (8 units):
                    # All 4 upper units are identical and all 4 lower units are identical
                    # So, only two types of units: upper and lower (50% chances of each)
                    # all units have 50% walls exterior
                    ewf = 0.5
                    # for 50% units: has exterior floor but not ceiling
                    if rng.random() < 0.5:
                        ecf = 0
                        eff = 1
                    else:  # for other 50% units: has exterior ceiling but not floor
                        ecf = 1
                        eff = 0
                else:
                    # 2-level large 16 units apts:
                    # There are 4 type of units: 4 corner bottom floor, 4 corner upper,
                    # 4 middle upper and 4 middle lower floor units. Each unit type has 25% chance
                    if rng.random() < 0.25:  # 4 corner bottom floor units
                        ewf = 0.5
                        ecf = 0
                        eff = 1
                    elif rng.random() < 0.5:  # 4 corner upper floor units
                        ewf = 0.5
                        ecf = 1
                        eff = 0
                    elif rng.random() < 0.75:  # 4 middle bottom floor units
                        ewf = aspect_ratio / (1 + aspect_ratio) / 2
                        ecf = 0
                        eff = 1
                    else:  # rng.random() < 1  # 4 middle upper floor units
                        ewf = aspect_ratio / (1 + aspect_ratio) / 2
                        ecf = 1
                        eff = 0
            else:  # bldg == 2, Mobile Homes
                # select between single and double wide
                wwr = (self.window_wall_ratio['mobile_home']['mean'])  # window wall ratio
                if floor_area <= 1080:  # Single wide
                    aspect_ratio = random_norm_trunc(
                        self.aspect_ratio['mobile_home_single_wide'])
                else:  # double wide
                    aspect_ratio = random_norm_trunc(
                        self.aspect_ratio['mobile_home_double_wide'])
                # A detatched MH has all walls exterior, has a ceiling and a floor
                ewf = 1  # exterior wall fraction
                ecf = 1  # exterior ceiling fraction
                eff = 1  # exterior floor fraction

            oversize = random_norm_trunc(
                self.hvac_oversize)  # hvac_oversize factor
            wetc = random_norm_trunc(
                self.window_shading)  # window_exterior_transmission_coefficient

            tiProps = Residential_Build.selectThermalProperties(self, bldg, ti)
            # Rceiling(roof), Rwall, Rfloor, WindowLayers, WindowGlass, Glazing,
            # WindowFrame, Rdoor, AirInfil, COPhi, COPlo
            Rroof = tiProps[0] * (0.8 + 0.4 * rng.random())
            Rwall = tiProps[1] * (0.8 + 0.4 * rng.random())
            Rfloor = tiProps[2] * (0.8 + 0.4 * rng.random())
            glazing_layers = int(tiProps[3])
            glass_type = int(tiProps[4])
            glazing_treatment = int(tiProps[5])
            window_frame = int(tiProps[6])
            Rdoor = tiProps[7] * (0.8 + 0.4 * rng.random())
            airchange = tiProps[8] * (0.8 + 0.4 * rng.random())
            init_temp = 68 + 4 * rng.random()
            mass_floor = 2.5 + 1.5 * rng.random()
            mass_solar_gain_frac = 0.5
            mass_int_gain_frac = 0.5

            # COP: pick any one year value randomly from the bin in cop_lookup
            h_COP = c_COP = rng.choice(self.config.base.cop_lookup[ti]) * (0.9 + rng.random() * 0.2)
            # +- 10% of mean value

            # Set housing parameters
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
            heat_rand = rng.random()
            cool_rand = rng.random()
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
            elif heat_rand <= heat_pump_prob:
                params["heating_system_type"] = "HEAT_PUMP"
                params["heating_COP"] = '{:.1f}'.format(h_COP)
                params["cooling_system_type"] = "ELECTRIC"
                params["auxiliary_strategy"] = "DEADBAND"
                params["auxiliary_system_type"] = "ELECTRIC"
                params["motor_model"] = "BASIC"
                params["motor_efficiency"] = "AVERAGE"
            # Optional: Restrict large homes from using electric heating
            # elif floor_area * ceiling_height > 12000.0:
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

            # Randomly choose cooling and heating setpoints within bins
            cooling_bin, heating_bin = self.selectSetpointBins(bldg, rng.random())
            # Adjust separation to account for deadband
            cooling_set = cooling_bin[3] + rng.random() * (cooling_bin[2] - cooling_bin[3])
            heating_set = heating_bin[3] + rng.random() * (heating_bin[2] - heating_bin[3])
            params["cooling_setpoint"] = np.round(cooling_set)
            params["heating_setpoint"] = np.round(heating_set)
            # For transactive case, override defaults for larger separation to
            # assure no overlaps during transactive simulations
            # params["cooling_setpoint"] = "80.0"
            # params["heating_setpoint"] = "60.0"
            self.mdl.house.add(hsename, params)

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
            self.mdl.ZIPload.add("responsive", params)

            params["base_power"] = 'unresponsive_loads * ' + '{:.2f}'.format(unresp_scalar)
            self.mdl.ZIPload.add("unresponsive", params)

            # Determine house water heating fuel type based on space heating fuel type
            wh_fuel_type = 'gas'
            properties = self.water_heating_fuel[self.config.state][self.config.res_dso_type][income][bldg_type]
            if house_fuel_type == 'gas':
                # percentage of homes with gas space heating but electric water heaters
                if rng.random() <= properties['sh_gas']['electric']:
                    wh_fuel_type = 'electric'
            elif house_fuel_type == 'electric':
                # percentage of homes with both electric space and water heating
                if rng.random() <= properties['sh_electric']['electric']:
                    wh_fuel_type = 'electric'
            if wh_fuel_type == 'electric':  # if the water heater fuel type is electric, install wh
                heat_element = 3.0 + 0.5 * rng.integers(1, 6)  # numpy integers (lo, hi) returns lo..(hi-1)
                tank_set = 110 + 16 * rng.random()
                therm_dead = 1  # 4 + 4 * rng.random()
                tank_UA = 2 + 2 * rng.random()
                water_sch = np.ceil(self.config.base.waterHeaterScheduleNumber * rng.random())
                water_var = 0.95 + rng.random() * 0.1  # +/-5% variability
                wh_demand_type = 'large_'

                # Water heater sizing
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
                wh_size = rng.choice(size_array)
                wh_demand_str = wh_demand_type + '{:.0f}'.format(water_sch) + '*' + '{:.2f}'.format(water_var)
                wh_skew_value = randomize_residential_skew(True)

                if self.config.water_heater_model == "MULTILAYER":
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
                else: # Traditional single-node model
                    params = {"parent": hsename,
                            "schedule_skew": '{:.0f}'.format(wh_skew_value),
                            "heating_element_capacity": '{:.1f}'.format(heat_element),
                            "thermostat_deadband": '{:.1f}'.format(therm_dead),
                            "location": "INSIDE",
                            "tank_diameter": "1.5",
                            "tank_UA": '{:.1f}'.format(tank_UA),
                            "water_demand": wh_demand_str,
                            "tank_volume": '{:.0f}'.format(wh_size),
                            "waterheater_model": "TWONODE",
                            "tank_setpoint": '{:.1f}'.format(tank_set - 5.0)}
                self.mdl.waterheater.add(whname, params)

            self.glm.add_metrics_collector(hsename, "house")

            # ------------------------------------------------------------------
            # Add solar, storage, and EVs
            # Calculates the probability of solar, battery and ev by building 
            #   type and income based on 2020 RECS data distributions.
            # Note that the 2020 RECS data does not capture battery distributions.
            #   We therefore assume batteries follow the same housing and income
            #   trends as solar, but allow the user to specify a different
            #   deployment level in the config.
            #-------------------------------------------------------------------
            if self.config.use_recs == "True":
                if bldg == 0:
                    prob_solar = self.config.solar_deployment * (self.solar_pv[self.config.state][self.config.res_dso_type]
                                                                [income]["single_family_detached"] +
                                                                self.solar_pv[self.config.state][self.config.res_dso_type]
                                                                [income]["single_family_attached"])
                    prob_batt = self.config.battery_deployment * (self.solar_pv[self.config.state][self.config.res_dso_type]
                                                                [income]["single_family_detached"] +
                                                                self.solar_pv[self.config.state][self.config.res_dso_type]
                                                                [income]["single_family_attached"])
                    prob_ev = self.config.ev_deployment * (self.ev[self.config.state][self.config.res_dso_type][income]
                                                            ["single_family_detached"] + self.ev[self.config.state]
                                                            [self.config.res_dso_type][income]["single_family_attached"])
                elif bldg == 1:
                    prob_solar = self.config.solar_deployment * (self.solar_pv[self.config.state][self.config.res_dso_type]
                                                                [income]["apartment_2_4_units"] +
                                                                self.solar_pv[self.config.state][self.config.res_dso_type]
                                                                [income]["apartment_5_units"])
                    prob_batt = self.config.battery_deployment * (self.solar_pv[self.config.state][self.config.res_dso_type]
                                                                [income]["apartment_2_4_units"] +
                                                                self.solar_pv[self.config.state][self.config.res_dso_type]
                                                                [income]["apartment_5_units"])
                    prob_ev = self.config.ev_deployment * (self.ev[self.config.state][self.config.res_dso_type][income]
                                                            ["apartment_2_4_units"] + self.ev[self.config.state]
                                                            [self.config.res_dso_type][income]["apartment_5_units"])
                else:
                    prob_solar = self.config.solar_deployment * self.solar_pv[self.config.state][self.config.res_dso_type][income]["mobile_home"]
                    prob_batt = self.config.battery_deployment * self.solar_pv[self.config.state][self.config.res_dso_type][income]["mobile_home"]
                    prob_ev = self.config.ev_deployment * self.ev[self.config.state][self.config.res_dso_type][income]["mobile_home"]

            # This is a special case, implemented for the Rates Analysis work
            else:
                prob_sf = self.housing_type[self.config.state][self.config.res_dso_type][income]['single_family_attached'] + \
                        self.housing_type[self.config.state][self.config.res_dso_type][income]['single_family_attached']

                prob_inc = self.income_level[self.config.state][self.config.res_dso_type][income]

                prob_solar = (self.config.base.solar_percentage * self.solar_percentage[income])/(prob_sf * prob_inc)

                prob_batt = (self.config.base.storage_percentage * self.battery_percentage[income])/(self.config.base.solar_percentage * self.solar_percentage[income])

                prob_ev = (self.config.base.ev_percentage * self.ev_percentage[income])/prob_inc

            # add solar, ev, and battery based on RECS data or user-input
            self.config.sol.add_solar(prob_solar, mtrname1, sol_m_name, sol_name, sol_i_name, phs, v_nom, floor_area)

            self.config.batt.add_batt(prob_batt, mtrname1, bat_m_name, bat_name, bat_i_name, phs, v_nom)

            self.config.ev.add_ev(prob_ev, hsename)

class Commercial_Build:
    def __init__(self, config):
        self.config = config
        self.glm = config.glm
        self.mdl = config.glm.glm

    def add_one_commercial_zone(self, bldg: dict, key: str) -> None:
        """Write one pre-configured commercial zone as a house and small loads
        such as lights, plug loads, and gas water heaters as ZIPLoads.

        Args:
            bldg (dict): dictionary of GridLAB-D house and zipload attributes
            key (str): location name for object
        Returns:
            None
        """

        name = bldg['zonename']
        self.mdl.house.add(name, {
            "parent": bldg['parent'],
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
            "heating_setpoint": '60.0' })

        self.mdl.ZIPload.add("lights", {
            "parent": name,
            "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
            "heatgain_fraction": "0.8",
            "power_fraction": '{:.2f}'.format(bldg['c_p_frac']),
            "impedance_fraction": '{:.2f}'.format(bldg['c_z_frac']),
            "current_fraction": '{:.2f}'.format(bldg['c_i_frac']),
            "power_pf": '{:.2f}'.format(bldg['c_p_pf']),
            "current_pf": '{:.2f}'.format(bldg['c_i_pf']),
            "impedance_pf": '{:.2f}'.format(bldg['c_z_pf']),
            "base_power":  '{:s}_lights*{:.2f}'.format(bldg['base_schedule'], bldg['adj_lights']) })

        self.mdl.ZIPload.add("plug_loads", {
            "parent": name,
            "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
            "heatgain_fraction": "0.9",
            "power_fraction": '{:.2f}'.format(bldg['c_p_frac']),
            "impedance_fraction": '{:.2f}'.format(bldg['c_z_frac']),
            "current_fraction": '{:.2f}'.format(bldg['c_i_frac']),
            "power_pf": '{:.2f}'.format(bldg['c_p_pf']),
            "current_pf": '{:.2f}'.format(bldg['c_i_pf']),
            "impedance_pf": '{:.2f}'.format(bldg['c_z_pf']),
            "base_power":  '{:s}_plugs*{:.2f}'.format(bldg['base_schedule'], bldg['adj_plugs']) })

        self.mdl.ZIPload.add("gas_waterheater", {
            "parent": name,
            "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
            "heatgain_fraction": "1.0",
            "power_fraction": "0",
            "impedance_fraction": "0",
            "current_fraction": "0",
            "power_pf": "1",
            "base_power": '{:s}_gas*{:.2f}'.format(bldg['base_schedule'], bldg['adj_gas']) })

        self.mdl.ZIPload.add("exterior_lights", {
            "parent": name,
            "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
            "heatgain_fraction": "0.0",
            "power_fraction": '{:.2f}'.format(bldg['c_p_frac']),
            "impedance_fraction": '{:.2f}'.format(bldg['c_z_frac']),
            "current_fraction": '{:.2f}'.format(bldg['c_i_frac']),
            "power_pf": '{:.2f}'.format(bldg['c_p_pf']),
            "current_pf": '{:.2f}'.format(bldg['c_i_pf']),
            "impedance_pf": '{:.2f}'.format(bldg['c_z_pf']),
            "base_power": '{:s}_exterior*{:.2f}'.format(bldg['base_schedule'], bldg['adj_ext']) })

        self.mdl.ZIPload.add("occupancy", {
            "parent": name,
            "schedule_skew": '{:.0f}'.format(bldg['skew_value']),
            "heatgain_fraction": "1.0",
            "power_fraction": "0",
            "impedance_fraction": "0",
            "current_fraction": "0",
            "power_pf": "1",
            "base_power": '{:s}_occupancy*{:.2f}'.format(bldg['base_schedule'], bldg['adj_occ']) })

        self.glm.add_metrics_collector(name, "house")
        # Add position data to commercial building, if available
        if self.config.gis_file:
            self.config.pos[name] = self.config.pos_data[key]


    def define_commercial_zones(self, rgn: int, key: str, kva: float) -> None:
        """Define building parameters for commercial building zones and ZIP 
        loads, then add to model as house object (commercial_zone) or load 
        object (ZIP load).

        Args:
            rgn (int): region 1..5 where the building is located
            key (str): GridLAB-D load name that is being replaced
            kva (flaot): total commercial building load, in kVA
        Returns:
            None
        """

        mtr = self.config.base.comm_loads[key][0]
        comm_type = self.config.base.comm_loads[key][1]
        nphs = int(self.config.base.comm_loads[key][4])
        phases = self.config.base.comm_loads[key][5]
        vln = float(self.config.base.comm_loads[key][6])
        loadnum = int(self.config.base.comm_loads[key][7])
        log.info('load: %s, mtr: %s, type: %s, kVA: %.4f, nphs: %s, phases: %s, vln: %.3f', key, mtr, comm_type, kva, nphs, phases, vln)

        bldg = {'parent': mtr,
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
                'c_p_pf': self.config.base.c_p_pf
                }
        
        if comm_type == 'ZIPload':
            phsva = 1000.0 * kva / nphs
            name = '{:s}'.format(key + '_streetlights')
            params = {"parent": '{:s}'.format(mtr),
                      "groupid": "STREETLIGHTS",
                      "nominal_voltage": '{:2f}'.format(vln)}
            for phs in ['A', 'B', 'C']:
                if phs in phases:
                    params["impedance_fraction_" + phs] = '{:f}'.format(self.config.base.c_z_frac)
                    params["current_fraction_" + phs] = '{:f}'.format(self.config.base.c_i_frac)
                    params["power_fraction_" + phs] = '{:f}'.format(bldg['c_p_frac'])
                    params["impedance_pf_" + phs] = '{:f}'.format(self.config.base.c_z_pf)
                    params["current_pf_" + phs] = '{:f}'.format(self.config.base.c_i_pf)
                    params["power_pf_" + phs] = '{:f}'.format(self.config.base.c_p_pf)
                    params["base_power_" + phs] = '{:.2f}'.format(self.config.base.light_scalar_comm * phsva)
            self.mdl.load.add(name, params)
            # Add position data to commercial ZIPload, if available
            if self.config.gis_file:
                self.config.pos[name] = self.config.pos_data[key]

        else:
            bld_specs = self.building_model_specifics[comm_type] 
            # Randomly determine the age (year of construction) of the building
            bldg['floor_area'] = bldg_area
            bldg['aspect_ratio'] = bld_specs["aspect_ratio"] * rng.normal(1, 0.01)
            bldg['window_wall_ratio'] = bld_specs["window-wall_ratio"] * rng.normal(1, 0.2)
            wall_area = (bld_specs['ceiling_height'] * 2 * math.sqrt(bldg['floor_area'] / bldg['no_of_stories'] / 
                                                                    bldg['aspect_ratio']) * (bldg['aspect_ratio'] + 1))
            ratio = wall_area * (1 - bldg['window_wall_ratio']) / bldg['floor_area']
            age = Commercial_Build.normalize_dict_prob('vintage', bld_specs['vintage'])
            age_bin = Commercial_Build.rand_bin_select(age, rng.random())
            bldg['age'] = Commercial_Build.sub_bin_select(age_bin, 'vintage', rng.random())
            bldg['thermal_mass_per_floor_area'] = (0.9 * rng.normal(self.general['interior_mass']['mean'], 0.2) + 0.5 
                                                * ratio * self.general['wall_thermal_mass'][str(bldg['age'])])

            if comm_type == 'office':
                bldg['ceiling_height'] = 13.0
                bldg['airchange_per_hour'] = 0.69
                bldg['Rroof'] = 19.0
                bldg['Rwall'] = 18.3
                bldg['Rfloor'] = 46.0
                bldg['Rdoors'] = 3.0
                bldg['int_gains'] = 3.24  # W/sf
                bldg['base_schedule'] = 'office'
                floor_area_choose = 40000. * (0.5 * rng.random() + 0.5)
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

                        bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * rng.random())
                        bldg['interior_exterior_wall_ratio'] = floor_area / (bldg['ceiling_height'] * 2. * (w + d)) - 1. \
                                                                + bldg['window_wall_ratio'] * bldg[
                                                                    'exterior_wall_fraction']

                        # Round to zero, presumably the exterior doors are treated like windows
                        bldg['no_of_doors'] = 0.1
                        bldg['init_temp'] = 68. + 4. * rng.random()
                        bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * rng.random())
                        bldg['COP_A'] = self.config.base.cooling_COP * (0.8 + 0.4 * rng.random())

                        # Randomize 10# then convert W/sf -> kW
                        bldg['adj_lights'] = (0.9 + 0.1 * rng.random()) * floor_area / 1000.
                        bldg['adj_plugs'] = (0.9 + 0.2 * rng.random()) * floor_area / 1000.
                        bldg['adj_gas'] = (0.9 + 0.2 * rng.random()) * floor_area / 1000.
                        bldg['adj_ext'] = (0.9 + 0.1 * rng.random()) * floor_area / 1000.
                        bldg['adj_occ'] = (0.9 + 0.1 * rng.random()) * floor_area / 1000.

                        bldg['zonename'] = gld_strict_name(f'{key}_floor_{floor}_zone_{zone}_{comm_type}')
                        Commercial_Build.add_one_commercial_zone(self, bldg, key)

            elif comm_type == 'big_box':
                bldg['ceiling_height'] = 14.
                bldg['airchange_per_hour'] = 1.5
                bldg['Rroof'] = 19.
                bldg['Rwall'] = 18.3
                bldg['Rfloor'] = 46.
                bldg['Rdoors'] = 3.
                bldg['int_gains'] = 3.6  # W/sf
                bldg['base_schedule'] = 'bigbox'
                bldg['skew_value'] = self.glm.randomize_commercial_skew()
                floor_area_choose = 20000. * (0.5 + 1. * rng.random())
                floor_area = floor_area_choose / 6.
                bldg['floor_area'] = floor_area
                bldg['thermal_mass_per_floor_area'] = 3.9 * (0.8 + 0.4 * rng.random())  # +/- 20#
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
                    bldg['init_temp'] = 68. + 4. * rng.random()
                    bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * rng.random())
                    bldg['COP_A'] = self.config.base.cooling_COP * (0.8 + 0.4 * rng.random())

                    bldg['adj_lights'] = 1.2 * (
                            0.9 + 0.1 * rng.random()) * floor_area / 1000.  # Randomize 10# then convert W/sf -> kW
                    bldg['adj_plugs'] = (0.9 + 0.2 * rng.random()) * floor_area / 1000.
                    bldg['adj_gas'] = (0.9 + 0.2 * rng.random()) * floor_area / 1000.
                    bldg['adj_ext'] = (0.9 + 0.1 * rng.random()) * floor_area / 1000.
                    bldg['adj_occ'] = (0.9 + 0.1 * rng.random()) * floor_area / 1000.

                    bldg['zonename'] = gld_strict_name(f'{key}_zone_{zone}_{comm_type}')
                    Commercial_Build.add_one_commercial_zone(self, bldg, key)

            elif comm_type == 'strip_mall':
                bldg['ceiling_height'] = 17
                bldg['airchange_per_hour'] = 1.76
                bldg['Rroof'] = 19.0
                bldg['Rwall'] = 18.3
                bldg['Rfloor'] = 40.0
                bldg['Rdoors'] = 3.0
                bldg['int_gains'] = 3.6  # W/sf
                bldg['exterior_ceiling_fraction'] = 1.
                bldg['base_schedule'] = 'stripmall'
                midzone = int(math.floor(self.total_strip_mall / 2.0) + 1.)
                for zone in range(1, self.total_strip_mall + 1):
                    bldg['skew_value'] = self.glm.randomize_commercial_skew()
                    floor_area_choose = 2400.0 * (0.7 + 0.6 * rng.random())
                    bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * rng.random())
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
                        if zone == self.total_strip_mall:
                            bldg['exterior_wall_fraction'] = 0.63
                            bldg['exterior_floor_fraction'] = 2.0
                        else:
                            bldg['exterior_wall_fraction'] = 0.25
                            bldg['exterior_floor_fraction'] = 0.8
                        bldg['interior_exterior_wall_ratio'] = -0.40
                    bldg['floor_area'] = floor_area
                    bldg['init_temp'] = 68.0 + 4.0 * rng.random()
                    bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * rng.random())
                    bldg['COP_A'] = self.config.base.cooling_COP * (0.8 + 0.4 * rng.random())
                    bldg['adj_lights'] = (0.8 + 0.4 * rng.random()) * floor_area / 1000.0
                    bldg['adj_plugs'] = (0.8 + 0.4 * rng.random()) * floor_area / 1000.0
                    bldg['adj_gas'] = (0.8 + 0.4 * rng.random()) * floor_area / 1000.0
                    bldg['adj_ext'] = (0.8 + 0.4 * rng.random()) * floor_area / 1000.0
                    bldg['adj_occ'] = (0.8 + 0.4 * rng.random()) * floor_area / 1000.0
                    bldg['zonename'] = gld_strict_name(f'{key}_zone_{zone}_{comm_type}')
                    Commercial_Build.add_one_commercial_zone(self, bldg, key)

            else: # For all other building types
                bldg['skew_value'] = self.glm.randomize_commercial_skew()
                bldg['adj_lights'] = (bld_specs['internal_heat_gains']['lighting'] * (0.9 + 0.1 * rng.random()) 
                                    * bldg_area / 1000.0)
                bldg['adj_plugs'] = bld_specs['internal_heat_gains']['MEL'] * (0.9 + 0.2 * rng.random()) * bldg_area / 1000.
                occ_load = 73  # Assumes 73 watts / occupant from Caney Fork study
                bldg['adj_occ'] = (bld_specs['internal_heat_gains']['occupancy'] * occ_load * (0.9 + 0.1 * rng.random()) 
                                * bldg_area / 1000.0)
                bldg['adj_gas'] = 0
                bldg['adj_ext'] = 0 # Plug and light parameters capture all of CBECS loads.
                bldg['int_gains'] = bldg['adj_lights'] + bldg['adj_plugs'] + bldg['adj_occ'] + bldg['adj_gas']
                bldg['interior_exterior_wall_ratio'] = 1
                bldg['exterior_floor_fraction'] = 1
                bldg['exterior_ceiling_fraction'] = 1
                bldg['exterior_wall_fraction'] = 1
                bldg['roof_type'] = Commercial_Build.rand_bin_select(bld_specs['roof_construction_insulation'], rng.random())
                bldg['wall_type'] = Commercial_Build.rand_bin_select(bld_specs['wall_construction'], rng.random())
                bldg['Rroof'] = 1 / Commercial_Build.find_envelope_prop(bldg['roof_type'], bldg['age'],
                                                                        self.general['thermal_integrity'],
                                                                        self.config.climate) * 1.3 * rng.normal(1, 0.1)
                bldg['Rwall'] = 1 / Commercial_Build.find_envelope_prop(bldg['wall_type'], bldg['age'],
                                                                        self.general['thermal_integrity'],
                                                                        self.config.climate) * 1.3 * rng.normal(1, 0.1)
                bldg['Rfloor'] = 22. # Value from previous study
                bldg['Rdoors'] = 3. # Value from previous study
                bldg['no_of_doors'] = 3 # Value from previous study
                bldg['airchange_per_hour'] = bld_specs['ventilation_requirements']['air_change_per_hour']
                bldg['init_temp'] = 68. + 4. * rng.random()
                bldg['os_rand'] = rng.normal(self.general['HVAC']['oversizing_factor']['mean'],
                                             self.general['HVAC']['oversizing_factor']['std_dev'])
                bldg['COP_A'] = self.general['HVAC']['COP'][str(bldg['age'])] * rng.normal(1, 0.05)
                if comm_type == 'lodging':
                    bldg['base_schedule'] = 'alwaysocc'
                elif comm_type in ['warehouse_storage', 'education']:
                    bldg['base_schedule'] = 'office'
                elif comm_type in ['food_service', 'food_sales']:
                    bldg['base_schedule'] = 'retail'
                elif comm_type == 'low_occupancy':
                    bldg['base_schedule'] = 'lowocc'
                bldg['zonename'] = gld_strict_name(f'{key}_{comm_type}')
                Commercial_Build.add_one_commercial_zone(self, bldg, key)

    def define_comm_bldg(self, dso_type: str, num_bldgs: float) -> list:
        """Randomly selects a set number of buildings by type and size (sqft).

        Args:
            dso_type (str): 'Urban', 'Suburban', or 'Rural'
            num_bldgs (float): scalar value of number of buildings to be selected
        Returns:
            bldgs (list): buildings
        """

        global bldg_area
        bldgs = {}
        bldg_types = Commercial_Build.normalize_dict_prob(dso_type, self.general['building_type'][dso_type])
        i = 0
        while i < num_bldgs:
            bldg_type = Commercial_Build.rand_bin_select(bldg_types, rng.random())
            area = Commercial_Build.normalize_dict_prob(bldg_type, self.building_model_specifics[bldg_type]['total_area'])
            bldg_area_bin = Commercial_Build.rand_bin_select(area, rng.random())
            bldg_area = Commercial_Build.sub_bin_select(bldg_area_bin, 'total_area', rng.random())
            bldgs['bldg_' + str(i + 1)] = [bldg_type, bldg_area]
            i += 1
        return bldgs
    
    @staticmethod
    def normalize_dict_prob(name: str, diction: dict) -> dict:
        """ Ensure that the probability distribution of values in a dictionary 
            effectively sums to one.

        Args:
            name (str): name of dictionary to normalize
            diction (dict): dictionary of elements and associated non-cumulative 
                probabilities
        Returns:
            dict: normalized dictionary of elements and associated with
                non-cumulative probabilities
        """

        sum1 = 0
        sum2 = 0
        for i in diction:
            sum1 += diction[i]
        for y in diction:
            diction[y] = diction[y] / sum1
        for z in diction:
            sum2 += diction[z]
        if sum1 != sum2:
            log.debug("WARNING %s dictionary normalize to 1, values are > %s", name, diction)
        return diction

    @staticmethod
    def rand_bin_select(diction: dict, probability: float) -> str | None:
        """ Returns the element (bin) in a dictionary given a certain
          probability.

        Args:
            diction: dictionary of elements and associated non-cumulative 
                probabilities
            probability: scalar value between 0 and 1
        Returns:
            str: element
        """

        total = 0

        for element in diction:
            total += diction[element]
            if total >= probability:
                return element
        return None

    @staticmethod
    def sub_bin_select(bin_range: str, bin_type: str, prob: float) -> int:
        """ Returns a scalar value within a bin type based on a uniform
            probability within that bin range.

        Args:
            bin_range (str): name of bin range
            bin_type (str): building parameter describing set of bins
            prob (float): scalar value between 0 and 1
        Returns:
            int: val, scalar value within bin range
        """

        bins = {}
        if bin_type == 'vintage':
            bins = {'pre_1960': [1945, 1959],
                    '1960-1979': [1960, 1979],
                    '1980-1999': [1980, 1999],
                    '2000-2009': [2000, 2009],
                    '2010-2015': [2010, 2015]}
        elif bin_type == 'total_area':
            bins = {'1-5': [1000, 5000],
                    '5-10': [5001, 10000],
                    '10-25': [10001, 25000],
                    '25-50': [25001, 50000],
                    '50_more': [50001, 55000]}
        elif bin_type == 'occupancy':
            bins = {'0': [0, 0],
                    '1-39': [1, 39.99],
                    '40-48': [40, 48.99],
                    '49-60': [49, 60.99],
                    '61-84': [61, 84.99],
                    '85-167': [85, 167.99],
                    '168': [168, 168]}
        val = bins[bin_range][0] + prob * (bins[bin_range][1] - bins[bin_range][0])
        if bin_type in ['vintage']:
            val = int(val)
        return val

    @staticmethod
    def find_envelope_prop(prop: str, age: int, env_data: dict, climate: str) -> float:
        """ Returns the envelope value for a given type of property based on the
            age and (ASHRAE) climate zone of the building.

        Args:
            prop (str): envelope material property of interest (e.g. 
                'wood-framed' or 'u-windows')
            age (int): age of the building in question (typically between 1945 
                and present).
            env_data (dict): Dictionary of envelope property data
            climate (str): ASHRAE climate zone of building (e.g. '2A')
        Returns:
            float: val, property value - typically a U-value.
        """

        val = None
        # Find age bin for properties
        if age < 1960:
            age_bin = '1960'
        elif age < 1980:
            age_bin = '1960-1979'
        elif age < 2000:
            age_bin = '1980-1999'
        elif age < 2010:
            age_bin = '2000-2009'
        elif age < 2016:
            age_bin = '2010-2015'
        else:
            age_bin = '2015'

        if prop in ['insulation_above_deck', 'insulation_in_attic_and_other']:
            if age_bin in ['1960', '1960-1979', '1980-1999', '2000-2009']:
                val = env_data[climate]['u_roof_all_types'][age_bin]
            else:
                val = env_data[climate]['u_roof_all_types'][age_bin][prop]

        if prop in ['steel_framed', 'mass_wall', 'metal_building', 'wood_framed']:
            if age_bin in ['1960', '1960-1979', '1980-1999']:
                val = env_data[climate]['u_walls_above_grade'][age_bin]
            else:
                val = env_data[climate]['u_walls_above_grade'][age_bin][prop]

        if prop == 'u_windows':
            val = env_data[climate]['u_windows'][age_bin]

        if prop == 'window_SHGC':
            val = env_data[climate]['window_SHGC'][age_bin]
        return val

class Battery:
    def __init__(self, config):
        self.config = config
        self.glm = config.glm
        self.mdl = config.glm.glm
        self.battery_count = 0
        self.battery_capacity_count = 0
    
    def add_batt(self, bat_prob: float, parent_mtr: str, bat_mtr: str, bat_name: str, inv_name: str, phs: float, v_nom: float) -> None:
        """Define and add battery and inverter objects to house, under the 
        parentage of the parent_mtr.

        Args:
            bat_prob (float): probability distribution of houses with batteries
            parent_mtr (str): name of parent meter
            bat_mtr (str): name of battery meter
            bat_name (str): name of the battery object
            inv_name (str): name of the inverter object
            phs (float): phase of parent triplex meter 
            v_nom (float): nominal line-to-neutral voltage at basenode
        Returns:
            None
        """

        if rng.random() <= bat_prob:
            battery_capacity = get_dist(self.config.batt.capacity['mean'],
                                        self.config.batt.capacity['deviation_range_per']) * 1000
            max_charge_rate = get_dist(self.config.batt.rated_charging_power['mean'],
                                       self.config.batt.rated_charging_power['deviation_range_per']) * 1000
            max_discharge_rate = max_charge_rate
            inverter_efficiency = self.config.batt.inv_efficiency / 100
            charging_loss = get_dist(self.config.batt.rated_charging_loss['mean'],
                                     self.config.batt.rated_charging_loss['deviation_range_per']) / 100
            discharging_loss = charging_loss
            round_trip_efficiency = charging_loss * discharging_loss
            rated_power = max(max_charge_rate, max_discharge_rate)

            self.battery_count += 1
            self.battery_capacity_count += battery_capacity
            self.mdl.triplex_meter.add(bat_mtr, {
                "parent": parent_mtr,
                "phases": phs,
                "nominal_voltage": str(v_nom) })

            self.mdl.inverter.add(inv_name, {
                "parent": bat_mtr,
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
                "sense_object": bat_mtr,
                "inverter_efficiency": inverter_efficiency,
                "power_factor": 1.0 })

            self.mdl.battery.add(bat_name, {
                "parent": inv_name,
                "use_internal_battery_model": "true",
                "nominal_voltage": 480,
                "battery_capacity": battery_capacity,
                "round_trip_efficiency": round_trip_efficiency,
                "state_of_charge": 0.50 })
            self.glm.add_metrics_collector(inv_name, "inverter")

class Solar:
    def __init__(self, config):
        self.config = config
        self.glm = config.glm
        self.mdl = config.glm.glm
        self.solar_count = 0
        self.solar_kw = 0
  
    def add_solar(self, solar_prob: float,  parent_mtr: str, solar_mtr: str, solar_name: str, inv_name: str, phs: float, v_nom: float, floor_area: float) -> None:
        """ Define and add solar and inverter to house under the parentage of
        parent_mtr.
        
        Find solar capacity directly proportional to sq. ft. of house.
        Typical PV panel is 350-450 Watts and avg home has 5kW installed.
        We assume 2500 sq. ft as avg area of a single family house, and one
        350 W panel for every 175 sq. ft.
        
        Args:
            solar_prob (float): probability distribution of houses with solar 
            parent_mtr (str): name of parent meter
            solar_mtr (str): name of solar meter
            solar_name (str): name of solar object
            inv_name (str): name of inverter object
            phs (float): phase of parent triplex meter
            v_nom (float): nominal line-to-neutral voltage at basenode
            floor_area (float): area of house in sqft
        Returns:
            None
        """

        if rng.random() <= solar_prob: 
            num_panel = np.floor(floor_area / 175)
            inverter_undersizing = 1.0
            inv_power = num_panel * 350 * inverter_undersizing
            
            self.solar_count += 1
            self.solar_kw += 0.001 * inv_power
            self.mdl.triplex_meter.add(solar_mtr, {"parent": parent_mtr,
                        "phases": phs,
                        "nominal_voltage": str(v_nom) })

            params = {"parent": solar_mtr,
                        "phases": phs,
                        "groupid": "sol_inverter",
                        "generator_status": "ONLINE",
                        "inverter_type": "FOUR_QUADRANT",
                        "inverter_efficiency": "1",
                        "rated_power": '{:.0f}'.format(inv_power),
                        "generator_mode": self.config.base.solar_inv_mode,
                        "four_quadrant_control_mode": self.config.base.solar_inv_mode}

            if self.config.use_solar_player == "True": 
                pv_scaling_factor = inv_power / self.config.rooftop_pv_rating_MW
                params["P_Out"] = f"{self.config.solar_P_player['attr']}.value * {pv_scaling_factor}"
                params["Q_Out"] = f"{self.config.solar_Q_player['attr']}.value * 0.0"
            else:
                params["Q_Out"] = "0"
                # Instead of solar object, write a fake V_in and I_in 
                # sufficiently high so that it doesn't limit the player output
                params["V_In"] = "10000000"
                params["I_In"] = "10000000"

            self.mdl.inverter.add(inv_name, params)
            self.glm.add_metrics_collector(inv_name, "inverter")

            if self.config.use_solar_player == "False":
                self.mdl.solar.add(solar_name, {
                    "parent": inv_name,
                    "panel_type": self.config.solar["panel_type"],
                    # "area": '{:.2f}'.format(panel_area),
                    "rated_power":  self.config.solar["rated_power"],
                    "tilt_angle": self.config.solar["tilt_angle"],
                    "efficiency": self.config.solar["efficiency"],
                    "shading_factor": self.config.solar["shading_factor"],
                    "orientation_azimuth": self.config.solar["orientation_azimuth"],
                    "orientation": self.config.solar["orientation"],
                    "SOLAR_TILT_MODEL": self.config.solar["SOLAR_TILT_MODEL"],
                    "SOLAR_POWER_MODEL": self.config.solar["SOLAR_POWER_MODEL"] })

class Electric_Vehicle:
    def __init__(self, config):
        self.config = config
        self.glm = config.glm
        self.ev_count = 0

    def add_ev(self, ev_prob: float, house_name: str) -> None:
        """Define and add electric vehicle charging object to the house, under
        the parentage of the house object.

        Args:
            ev_prob (float): probability distribution of houses with EVs 
            house_name (str): name of house object
        Raises:
            UserWarning: Raises "daily travel miles for EV cannot be more than 
                range of the vehicle!" if daily drive miles exceeds EV range.
            UserWarning: Raises "invalid HHMM format of driving time!" if home
                arrival, leave, or work arrival times are of invalid format.
            UserWarning: Raises: "invalid home or work duration for ev!" if home
                or work duration exceeds hours of day.
            UserWarning: Raises: "home and work arrival time are not consistent
                with durations!" if EV drive time is not valid.
        Returns:
            None
        """

        # Select an ev model:
        ev_name = Electric_Vehicle.selectEVmodel(self.config.ev.sale_probability, rng.random())
        ev_range = self.config.ev.Range_miles[ev_name]
        ev_mileage = self.config.ev.Miles_per_kWh[ev_name]
        ev_charge_eff = self.config.ev.charging_efficiency
        # Check if level 1 charger is used or level 2
        if rng.random() <= self.config.ev.Level_1_usage:
            ev_max_charge = self.config.ev.Level_1_max_power_kW
            volt_conf = 'IS110'  # for level 1 charger, 110 V is good
        else:
            ev_max_charge = self.config.ev.Level_2_max_power_kW[ev_name]
            volt_conf = 'IS220'  # for level 2 charger, must be 220 V
        # Map a random driving schedule with this vehicle ensuring daily miles
        # doesn't exceed the vehicle range and home duration is enough to charge the vehicle
        drive_sch = self.config.ev.match_driving_schedule(ev_range, ev_mileage, ev_max_charge)
        if drive_sch['daily_miles'] > ev_range:
            raise UserWarning('daily travel miles for EV cannot be more than range of the vehicle!')
        if (not is_hhmm_valid(drive_sch['home_arr_time']) or
            not is_hhmm_valid(drive_sch['home_leave_time']) or
            not is_hhmm_valid(drive_sch['work_arr_time'])):
            raise UserWarning('invalid HHMM format of driving time!')
        if drive_sch['home_duration'] > 24 * 3600 or drive_sch['home_duration'] < 0 or \
                drive_sch['work_duration'] > 24 * 3600 or drive_sch['work_duration'] < 0:
            raise UserWarning('invalid home or work duration for ev!')
        if not Electric_Vehicle.is_drive_time_valid(drive_sch):
            raise UserWarning('home and work arrival time are not consistent with durations!')

        if rng.random() <= ev_prob:
            self.ev_count += 1
            params = {"parent": house_name,
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
            ev_name = ev_name.replace(" ","_")
            self.glm.add_object("evcharger_det", f'{ev_name}_{self.ev_count}', params)
            self.glm.add_collector("class=evcharger_det", "sum(actual_charge_rate)", "EV_charging_total.csv")
            self.glm.add_group_recorder("class=evcharger_det", "actual_charge_rate", "EV_charging_power.csv")
            self.glm.add_group_recorder("class=evcharger_det", "battery_SOC", "EV_SOC.csv")

    @staticmethod
    def selectEVmodel(evTable: dict, prob: float) -> str:
        """Select the EV model based on available sale distribution data.

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
        - Checks if home_duration is enough to charge for daily_miles driven +
            margin
        - During v1g or v2g mode, we only allow charging to start at the top
            of the hour following the vehicle arriving home. Charging must 
            end at the full hour just before vehicle leaves home. The actual 
            chargeable hours duration may be smaller than the car home duration 
            by maximum 2 hours.
        - Maximum commute_duration: 1 hour 30 minutes for work-home and 
            30 minutes for home-work. If remaining time is less than an hour, 
            make that commute time, but it should not occur as maximum home 
            duration is always less than 23 hours
        Args:
            ev_range (float): range of EV, in miles
            ev_mileage (float): daily drive miles
            ev_max_charge (float): max charge level of the vehicle
        Raises:
            UserWarning: if the required charge time exceeds 23 hours, raise: 
                'A particular EV can not be charged fully even within 23 hours!'
        Returns:
            dict: driving_sch containing {daily_miles, home_arr_time,
            home_leave_time, home_duration, work_arr_time, work_duration}
        """

        while True:
            mile_ind = rng.integers(0, len(self.config.base.ev_driving_metadata['TRPMILES']))
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
        # Update home arrival time
        home_arr_time = subtract_hhmm_secs(home_leave_time, home_duration)

        # Estimate work duration and arrival time, in secs
        commute_duration = min(3600, 24 * 3600 - home_duration)
         
        # Estimate remaining time at work
        work_duration = max(24 * 3600 - (home_duration + commute_duration), 1)  
        # minimum work duration is 1 sec to avoid 0 that may give error in GridLABD
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
        """Check if work arrival time and home arrival time add up properly.

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
        """Read the large NHTS survey data file containing driving data, process
            it, and return a dataframe.

        Args:
            data_file (str): path of the file
        Returns:
            dataframe: df_fin, containing start_time, end_time, travel_day
                (weekday/weekend) and daily miles driven
        """

        # Read data from NHTS survey
        df_data = pd.read_csv(data_file, index_col=[0, 1])
        # Filter based on trip leaving only from home and not from work or other
        # places. Take the earliest time leaving home of a particular vehicle.
        df_data_leave = df_data[df_data['WHYFROM'] == 1].groupby(level=['HOUSEID', 'VEHID']).min()[
            ['STRTTIME', 'TRAVDAY']]
        # Filter based on trip arriving only at home and not at work or other
        # places. Take the latest time arriving at home of a particular vehicle.
        df_data_arrive = df_data[df_data['WHYTO'] == 1].groupby(level=['HOUSEID', 'VEHID']).max()[
            ['ENDTIME', 'TRAVDAY']]
        # Take the sum of trip miles by a particular vehicle in a day
        df_data_miles = df_data.groupby(level=['HOUSEID', 'VEHID']).sum()['TRPMILES']
        # Limit daily miles to maximum possible range of EV from the EV model 
        # data, as EVs can't travel more than their range in a day if we don't
        # consider highway charging.
        max_ev_range = max(self.Range_miles.values())
        df_data_miles = df_data_miles[df_data_miles < max_ev_range]
        df_data_miles = df_data_miles[df_data_miles > 0]

        # Combine all 4 parameters: starttime, endtime, total_miles, travel_day.
        # Ignore vehicle IDs that don't have both leaving and arrival time at home
        temp = df_data_leave.merge(df_data_arrive['ENDTIME'], left_index=True, right_index=True)
        df_fin = temp.merge(df_data_miles, left_index=True, right_index=True)
        return df_fin

class Feeder:
    def __init__(self, config: Config):
        self.config = config
        self.glm = config.glm
        self.mdl = config.glm.glm
        
        # Generate RECS metadata, if it does not exist
        self.config.generate_recs()
        # Assign defaults based on RECS data
        self.config.load_recs()
        # Load position data, if available
        self.config.load_position()
        # Populate the feeder
        self.feeder_gen()
        # Configure the .glm
        self.config.preamble()

        # Identify and add residential loads
        self.identify_xfmr_houses('transformer', self.seg_loads, 0.001 * self.config.avg_house, self.config.region)
        for key in self.config.base.house_nodes:
            self.config.res_bld.add_houses(key, 120.0)
        for key in self.config.base.small_nodes:
            self.config.res_bld.add_small_loads(key, 120.0)

        # Identify and add commercial loads
        self.identify_commercial_loads('load', 0.001 * self.config.avg_commercial)
        for key in self.config.base.comm_loads:
            self.config.com_bld.define_commercial_zones(config.region, key, self.config.com_bld.total_comm_kva)
        #self.glm.add_voltage_class('node', self.config.vln, self.config.vll, self.secnode)
        #self.glm.add_voltage_class('meter',config.vln, self.config.vll, self.secnode)
        #self.glm.add_voltage_class('load', self.config.vln, self.config.vll, self.secnode)

        print('DER added:'
              f" {self.config.sol.solar_count} PV with combined capacity of "
              f"{self.config.sol.solar_kw:.1f} kW; "
              f"{self.config.batt.battery_count} batteries with combined capacity of "
              f"{self.config.batt.battery_capacity_count/1000:.1f} kWh; and "
              f"{self.config.ev.ev_count} EV chargers")
        
        # Write the popoulated glm model to the output file
        self.glm.write_model(os.path.join(config.data_path, config.out_file_glm))

        # Plot the model using the networkx package:
        if self.config.gis_file:
            print("\nUsing location data to plot image of model; this should just take a sec.")
            # Merge house and meter position assignments with rest of GIS data
            self.config.pos |= self.config.pos_data
            self.glm.model.plot_model(self.config.pos)
        else:
            print("\nPlotting image of model; this may take several minutes.")
            self.glm.model.plot_model()

    def feeder_gen(self) -> None:
        """ Read in the backbone feeder, then loop through transformer 
        instances and assign a standard size based on the downstream load. 
        Change the referenced transformer_configuration attributes. Write the
        standard transformer_configuration instances we need.

        The tax choice array are for feeder taxonomy signature glm file and are
        sized accordingly with file name, the transformer configuration, setting
        current_limit for fuse, setting cap_nominal_voltage and current_limit
        for capacitor.

        Args:
            None            
        Returns:
            None
        """

        # Read in backbone feeder to populate. User-defined or taxonomy feeder.
        if not self.config.in_file_glm:
            i_glm, success = self.glm.model.readBackboneModel(self.config.taxonomy)
            print('User feeder not defined, using taxonomy feeder', self.config.taxonomy)
            self.config.gis_file = self.config.taxonomy.replace('-', '_').replace('.', '_').replace('_glm', '_pos.json')
            if not success:
                exit()
        else:
            i_glm, success = self.glm.read_model(os.path.join(self.config.data_path, self.config.in_file_glm))
            if not success:
                exit()

        # To plot an upopulated version of the base feeder:        
        #self.glm.model.plot_model()

        xfused = {}  # ID, phases, total kva, vnom (LN), vsec, poletop/padmount
        self.secnode = {}  # Node, st, phases, vnom
        self.seg_loads = self.glm.model.identify_seg_loads()

        for e_name, e_object in i_glm.transformer.items():
            # "identify_seg_loads" does not account for parallel paths in the
            # model. This test allows us to skip paths that have not had load
            # accumulated with them, including parallel paths. Also skipping
            # population for transformers with secondary voltage more than 500 V.
            e_config = e_object['configuration']
            sec_v = float(i_glm.transformer_configuration[e_config]['secondary_voltage'])

            if e_name not in self.seg_loads or sec_v > 500:
                log.warning(f"WARNING: %s not in the seg loads", e_name)
                continue
            seg_kva = self.seg_loads[e_name][0]
            seg_phs = self.seg_loads[e_name][1]

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
                if kvat > self.config.base.max208kva:
                    vsec = 480.0
                    vnom = 277.0
                else:
                    vsec = 208.0
                    vnom = 120.0

            self.secnode[gld_strict_name(e_object['to'])] = [kvat, seg_phs, vnom]

            old_key = self.glm.model.hash[e_object['configuration']]
            install_type = i_glm.transformer_configuration[old_key]['install_type']

            raw_key = 'XF' + str(nphs) + '_' + install_type + '_' + seg_phs + '_' + str(kvat)
            key = raw_key.replace('.', 'p')

            e_object['configuration'] = self.config.base.name_prefix + key
            e_object['phases'] = seg_phs
            if key not in xfused:
                xfused[key] = [seg_phs, kvat, vnom, vsec, install_type]
        
        for key in xfused:
            self.glm.add_xfmr_config(key, xfused[key][0], xfused[key][1], xfused[key][2], xfused[key][3],
                                xfused[key][4], self.config.vll, self.config.vln)

        for e_name, e_object in i_glm.capacitor.items():
            e_object['nominal_voltage'] = str(int(self.config.vln))
            e_object['cap_nominal_voltage'] = str(int(self.config.vln))

        for e_name, e_object in i_glm.fuse.items():
            if e_name in self.seg_loads:
                seg_kva = self.seg_loads[e_name][0]
                seg_phs = self.seg_loads[e_name][1]

                nphs = 0
                if 'A' in seg_phs:
                    nphs += 1
                if 'B' in seg_phs:
                    nphs += 1
                if 'C' in seg_phs:
                    nphs += 1
                if nphs == 3:
                    amps = 1000.0 * seg_kva / math.sqrt(3.0) / self.config.vll
                elif nphs == 2:
                    amps = 1000.0 * seg_kva / 2.0 / self.config.vln
                else:
                    amps = 1000.0 * seg_kva / self.config.vln
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
            self.glm.add_link_class(link, self.seg_loads, want_metrics=metrics)
        return self.secnode, self.seg_loads

    def identify_xfmr_houses(self, gld_class: str, seg_loads: dict, avgHouse: float, rgn: int) -> None:
        """For the full-order feeders, scan each service transformer to
        determine the number of houses it should have.
        Args:
            gld_class (str): the GridLAB-D class name to scan
            seg_loads (dict): dictionary of downstream load (kva) served by each
               GridLAB-D link
            avgHouse (float): the average house load in kva
            rgn (int): the region number, 1..5
        Returns:
            None
        """

        print(f"Average House size: {avgHouse} kVA")
        print('Results in a populated feeder with:')
        total_houses = 0
        total_sf = 0
        total_apt = 0
        total_mh = 0
        total_small = 0
        total_small_kva = 0
        dsoIncomePct = self.config.res_bld.getDsoIncomeLevelTable()
        try:
            entity = self.mdl.__getattribute__(gld_class)
        except:
            return
        for e_name, e_object in entity.items():
            if e_name in seg_loads:
                tkva = seg_loads[e_name][0]
                phs = seg_loads[e_name][1]
                if 'S' in phs:
                    self.config.res_bld.nhouse = int((tkva / avgHouse) + 0.5)  # round to nearest int
                    node = gld_strict_name(e_object['to'])
                    if self.config.res_bld.nhouse <= 0:
                        total_small += 1
                        total_small_kva += tkva
                        self.config.base.small_nodes[node] = [tkva, phs]
                    else:
                        total_houses += 1
                        lg_v_sm = tkva / avgHouse - self.config.res_bld.nhouse  
                        # > 0 if we rounded down the number of houses
                        # Get the income level for the dso_type and state
                        inc_lev = self.config.res_bld.selectIncomeLevel(dsoIncomePct, rng.random())
                        # Get the vintage table for dso_type, state, and income level
                        dsoThermalPct = self.config.res_bld.getDsoThermalTable(self.config.income_level[inc_lev])
                        bldg, ti = self.config.res_bld.selectResidentialBuilding(dsoThermalPct, rng.random())
                        if bldg == 0:
                            total_sf += 1
                        elif bldg == 1:
                            total_apt += 1
                        else:
                            total_mh += 1
                        self.config.base.house_nodes[node] = [self.config.res_bld.nhouse, rgn, lg_v_sm, phs, bldg, ti, inc_lev]
        print(f"    {total_small} small loads totaling {total_small_kva:.2f} kVA")
        print(f"    {total_houses} houses added to {len(self.config.base.house_nodes)} transformers")
        print(f"    {total_sf} single family homes, {total_apt} apartments, and {total_mh} mobile homes")
    
    def identify_commercial_loads(self, gld_class: str, avgBuilding: float) -> None:
        """For the full-order feeders, scan each load with load_class==C to
        determine the number of zones it should have.

        Args:
            gld_class (str): the GridLAB-D class name to scan
            avgBuilding (float): the average building size in kva
        Returns:
            None
        """
        
        print('Average Commercial Building size:', avgBuilding, 'kVA')
        print('Results in a populated feeder with:')
        total_commercial = 0
        self.config.com_bld.total_comm_kva = 0
        total_zipload = 0
        total_office = 0
        total_warehouse_storage = 0
        total_big_box = 0
        self.config.com_bld.total_strip_mall = 0
        total_education = 0
        total_food_service = 0
        total_food_sales = 0
        total_lodging = 0
        total_healthcare_inpatient = 0
        total_low_occupancy = 0
        sqft_kva_ratio = 0.005  # Average com building design load is 5 W/sq ft.

        try:
            entity = self.mdl.__getattribute__(gld_class)
        except:
            return
        removenames = []
        for e_name, e_object in entity.items():
            if 'load_class' not in e_object:
                log.warning("load_class not defined! Cannot add commercial loads")
                return None
            else:
                select_bldg = None
                if e_object['load_class'] != 'C':
                    continue
                elif e_object['load_class'] == 'C':
                    kva = self.glm.model.accumulate_load_kva(e_object)
                    total_commercial += 1
                    self.config.com_bld.total_comm_kva += kva
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
                    remain_comm_kva = 0
                    for bldg in self.config.base.comm_bldgs_pop:
                        if 0 >= (self.config.base.comm_bldgs_pop[bldg][1] - target_sqft) > sqft_error:
                            select_bldg = bldg
                            sqft_error = self.config.base.comm_bldgs_pop[bldg][1] - target_sqft
                        remain_comm_kva += self.config.base.comm_bldgs_pop[bldg][1] * sqft_kva_ratio
           
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
                        self.config.com_bld.total_strip_mall += 1
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
                    del (self.config.base.comm_bldgs_pop[select_bldg])
                else:
                    if nzones > 0:
                        log.warning('Commercial building could not be found for %.2f KVA load', kva)
                    comm_name = 'streetlights'
                    comm_type = 'ZIPload'
                    comm_size = 0
                    total_zipload += 1
                mtr = gld_strict_name(e_object['parent'])
                extra_billing_meters.add(mtr)
                self.config.base.comm_loads[e_name] = [mtr, comm_type, comm_size, kva, nphs, phases, vln, total_commercial, comm_name]
                removenames.append(e_name)
        for e_name in removenames:
            self.glm.del_object(gld_class, e_name)
        
        if e_object['load_class'] != 'C':
            return None
        
        # Print commercial info
        print('    {} commercial loads identified, {} buildings added, approximately {} kVA still to be assigned.'.
              format(len(self.config.base.comm_bldgs_pop), total_commercial, int(remain_comm_kva)))
        print('     ', total_office, 'med/small offices with 3 floors, 5 zones each:', total_office*5*3, 'total office zones' )
        print('     ', total_warehouse_storage, 'warehouses,')
        print('     ', total_big_box, 'big box retail with 6 zones each:', total_big_box*6, 'total big box zones')
        print('     ', self.config.com_bld.total_strip_mall, 'strip malls,')
        print('     ', total_education, 'education,')
        print('     ', total_food_service, 'food service,')
        print('     ', total_food_sales, 'food sales,')
        print('     ', total_lodging, 'lodging,')
        print('     ', total_healthcare_inpatient, 'healthcare,')
        print('     ', total_low_occupancy, 'low occupancy,')
        print('     ', total_zipload, 'streetlights')
        log.info('The {} commercial loads and {} streetlights (ZIPloads) totaling {:.2f} kVA added to this feeder'.
                 format(total_commercial, total_zipload, self.config.com_bld.total_comm_kva))

def _test1():
    data_path = os.path.expandvars('$TESPDIR/examples/capabilities/feeder-generator/')
    config_file = 'feeder_config.json5'
    config = Config(os.path.join(data_path, config_file))
    config.data_path = data_path
    feeder = Feeder(config)

if __name__ == "__main__":
    _test1()