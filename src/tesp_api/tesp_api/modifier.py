# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: glm_modifier.py

import json
import math
import os
import re
import numpy as np

from data import entities_path
from entity import assign_defaults
from model import GLModel


class GLMModifier:
    # instances of entity values
    # objects = [batteries, meters, capacitors, fuses, houses, lines, loads,
    #            secondary_transformers, solar_pvs, substation_transformers,
    #            switches, triplex_lines, triplex_loads, zip_loads, recorder]

    def __init__(self):
        self.model = GLModel()
        self.modded_model = GLModel()
        self.mod_headers = []
        self.extra_billing_meters = set()
        assign_defaults(self, 'feeder_defaults.json')
        return



    def get_objects(self, name):
        return self.model.entities[name]

    def get_object_id(self, name, object_id):
        return self.model.entities[name].entities[object_id]

    def add_objects(self, name):
        return True

    def del_objects(self, name):
        return True

    def add_objects_to(self, name):
        return True

    def del_objects_from(self, name):
        return True

    def get_path_to_substation(self):
        return True

    def mod_model(self):
        tlist = list(self.model.network.nodes.data())
        for basenode in tlist:
            print(basenode)
        return True

    def read_model(self, filepath):
        self.model.read(filepath)
        return True

    # normal objects
    def resize(self, name):
        return True

    # custom objects
    def resize_secondary_transformers(self):
        return True

    def resize_substation_transformer(self):
        return True

    def set_simulation_times(self):
        return True

    def write_model(self):
        return True

    def write_mod_model(self, filepath):
        return True
#************************************************************************************************************
    def create_kersting_quadriplex(self, kva):
        kerst_quad_dict = dict()
        kerst_quad_dict["key"] = 'quad_cfg_{:d}'.format(int(kva))
        kerst_quad_dict["amps"] = kva / math.sqrt(3.0) / 0.208
        kerst_quad_dict["npar"] = math.ceil(kerst_quad_dict["amps"] / 202.0)
        kerst_quad_dict["apar"] = 202.0 * kerst_quad_dict["npar"]
        kerst_quad_dict["scale"] = 5280.0 / 100.0 / kerst_quad_dict["npar"]# for impedance per mile of parallel circuits
        kerst_quad_dict["r11"] = 0.0268 * kerst_quad_dict["scale"]
        kerst_quad_dict["x11"] = 0.0160 * kerst_quad_dict["scale"]
        kerst_quad_dict["r12"] = 0.0160 * kerst_quad_dict["scale"]
        kerst_quad_dict["x12"] = 0.0103 * kerst_quad_dict["scale"]
        kerst_quad_dict["r13"] = 0.0085 * kerst_quad_dict["scale"]
        kerst_quad_dict["x13"] = 0.0095 * kerst_quad_dict["scale"]
        kerst_quad_dict["r22"] = 0.0258 * kerst_quad_dict["scale"]
        kerst_quad_dict["x22"] = 0.0176 * kerst_quad_dict["scale"]
        return kerst_quad_dict

    # ************************************************************************************************************

    # Helper functions
    def write_node_house_configs (self, xfkva, xfkvll, xfkvln, phs, want_inverter=False):
        #      """Writes transformers, inverter settings for GridLAB-D houses at a primary load point.

        # An aggregated single-phase triplex or three-phase quadriplex line configuration is also
        # written, based on estimating enough parallel 1/0 AA to supply xfkva load.
        # This function should only be called once for each combination of xfkva and phs to use,
        # and it should be called before write_node_houses.

        # Args:
        #    xfkva (float): the total transformer size to serve expected load; make this big enough to avoid overloads
        #    xfkvll (float): line-to-line voltage [kV] on the primary. The secondary voltage will be 208 three-phase
        #    xfkvln (float): line-to-neutral voltage [kV] on the primary. The secondary voltage will be 120/240 for split secondary
        #    phs (str): either 'ABC' for three-phase, or concatenation of 'A', 'B', and/or 'C' with 'S' for single-phase to triplex
        #    want_inverter (boolean): True to write the IEEE 1547-2018 smarter inverter function setpoints
        # """
        if want_inverter:
            self.mod_headers.append('#define INVERTER_MODE=CONSTANT_PF')
            self.mod_headers.append('//#define INVERTER_MODE=VOLT_VAR')
            self.mod_headers.append('//#define INVERTER_MODE=VOLT_WATT')
            self.mod_headers.append('// default IEEE 1547-2018 settings for Category B')
            self.mod_headers.append('#define INV_V1=0.92')
            self.mod_headers.append('#define INV_V2=0.98')
            self.mod_headers.append('#define INV_V3=1.02')
            self.mod_headers.append('#define INV_V4=1.08')
            self.mod_headers.append('#define INV_Q1=0.44')
            self.mod_headers.append('#define INV_Q2=0.00')
            self.mod_headers.append('#define INV_Q3=0.00')
            self.mod_headers.append('#define INV_Q4=-0.44')
            self.mod_headers.append('#define INV_VIN=200.0')
            self.mod_headers.append('#define INV_IIN=32.5')
            self.mod_headers.append('#define INV_VVLOCKOUT=300.0')
            self.mod_headers.append('define INV_VW_V1=1.05 // 1.05833')
            self.mod_headers.append('#define INV_VW_V2=1.10')
            self.mod_headers.append('#define INV_VW_P1=1.0')
            self.mod_headers.append('#define INV_VW_P2=0.0')
            if 'S' in phs:
                for secphs in phs.rstrip('S'):
                    xfkey = 'XF{:s}_{:d}'.format(secphs, int(xfkva))
                    self.create_xfmr_config(xfkey, secphs + 'S', kvat=xfkva, vnom=None, vsec=120.0, install_type='PADMOUNT', vprimll=None, vprimln=1000.0*xfkvln)
                self.create_kersting_triplex(xfkva)
            else:
                xfkey = 'XF3_{:d}'.format(int(xfkva))
                self.create_xfmr_config(xfkey, phs, kvat=xfkva, vnom=None, vsec=208.0, install_type='PADMOUNT', vprimll=1000.0*xfkvll, vprimln=None)
                self.create_kersting_quadriplex(xfkva)

    # ************************************************************************************************************

    def create_kersting_triplex(self, kva):
        """Writes a triplex_line_configuration based on 1/0 AA example from Kersting's book

        The conductor capacity is 202 amps, so the number of triplex in parallel will be kva/0.12/202
        """
        kerst_trip_dict = dict()
        kerst_trip_dict["key"] = 'tpx_cfg_{:d}'.format(int(kva))
        kerst_trip_dict["amps"] = kva / 0.12
        kerst_trip_dict["npar"] = math.ceil(kerst_trip_dict["amps"] / 202.0)
        kerst_trip_dict["apar"] = 202.0 * kerst_trip_dict["npar"]
        kerst_trip_dict["scale"] = 5280.0 / 100.0 / kerst_trip_dict["npar"]  # for impedance per mile of parallel circuits
        kerst_trip_dict["r11"] = 0.0271 * kerst_trip_dict["scale"]
        kerst_trip_dict["x11"] = 0.0146 * kerst_trip_dict["scale"]
        kerst_trip_dict["r12"] = 0.0087 * kerst_trip_dict["scale"]
        kerst_trip_dict["x12"] = 0.0081 * kerst_trip_dict["scale"]
        return kerst_trip_dict

    # ************************************************************************************************************

    def create_kersting_quadriplex (self, kva):
        """Writes a quadriplex_line_configuration based on 1/0 AA example from Kersting's book

        The conductor capacity is 202 amps, so the number of triplex in parallel will be kva/sqrt(3)/0.208/202
        """
        key = 'quad_cfg_{:d}'.format (int(kva))
        amps = kva / math.sqrt(3.0) / 0.208
        npar = math.ceil (amps / 202.0)
        apar = 202.0 * npar
        scale = 5280.0 / 100.0 / npar  # for impedance per mile of parallel circuits
        r11 = 0.0268 * scale
        x11 = 0.0160 * scale
        r12 = 0.0080 * scale
        x12 = 0.0103 * scale
        r13 = 0.0085 * scale
        x13 = 0.0095 * scale
        r22 = 0.0258 * scale
        x22 = 0.0176 * scale
        self.mod_headers.append('object line_configuration {{ // {:d} 1/0 AA in parallel')
        self.mod_headers.append('  name {:s};'.format(key))
        self.mod_headers.append('  z11 {:.4f}+{:.4f}j;'.format(r11, x11))
        self.mod_headers.append('  z12 {:.4f}+{:.4f}j;'.format(r12, x12))
        self.mod_headers.append('  z13 {:.4f}+{:.4f}j;'.format(r13, x13))
        self.mod_headers.append('  z21 {:.4f}+{:.4f}j;'.format(r12, x12))
        self.mod_headers.append('  z22 {:.4f}+{:.4f}j;'.format(r22, x22))
        self.mod_headers.append('  z23 {:.4f}+{:.4f}j;'.format(r12, x12))
        self.mod_headers.append('  z31 {:.4f}+{:.4f}j;'.format(r13, x13))
        self.mod_headers.append('  z32 {:.4f}+{:.4f}j;'.format(r12, x12))
        self.mod_headers.append('  z33 {:.4f}+{:.4f}j;'.format(r11, x11))
        self.mod_headers.append('  rating.summer.continuous {:.1f};'.format(apar))
        self.mod_headers.append('  rating.summer.emergency {:.1f};'.format(apar))
        self.mod_headers.append('  rating.winter.continuous {:.1f};'.format(apar))
        self.mod_headers.append('  rating.winter.emergency {:.1f};'.format(apar))
        self.mod_headers.append('}')

    # ************************************************************************************************************

    def create_xfmr_config(self, key, phs, kvat, vnom, vsec, install_type, vprimll, vprimln):
        """Write a transformer_configuration

        Args:
            key (str): name of the configuration
            phs (str): primary phasing
            kvat (float): transformer rating in kVA
            vnom (float): primary voltage rating, not used any longer (see vprimll and vprimln)
            vsec (float): secondary voltage rating, should be line-to-neutral for single-phase or line-to-line for three-phase
            install_type (str): should be VAULT, PADMOUNT or POLETOP
            vprimll (float): primary line-to-line voltage, used for three-phase transformers
            vprimln (float): primary line-to-neutral voltage, used for single-phase transformers
        """
        xfmr_config_dict = dict()
        xfmr_config_dict["name"] = self.name_prefix + key + ";"
        # print('  power_rating ' + format(kvat, '.2f') + ';', file=op)
        xfmr_config_dict['power_rating'] = format(kvat, '.2f') + ';'
        kvaphase = kvat
        if 'XF2' in key:
            kvaphase /= 2.0
        if 'XF3' in key:
            kvaphase /= 3.0
        if 'A' in phs:
            xfmr_config_dict['powerA_rating'] = format(kvaphase, '.2f')
        else:
            xfmr_config_dict['powerA_rating'] = '0.0'
        if 'B' in phs:
            xfmr_config_dict['powerB_rating'] = format(kvaphase, '.2f')
        else:
            xfmr_config_dict['powerB_rating'] = '0.0'
        if 'C' in phs:
            xfmr_config_dict['powerC_rating'] = format(kvaphase, '.2f')
        else:
            xfmr_config_dict['powerC_rating'] = '0.0'
        xfmr_config_dict['powerC_rating'] = install_type
        if 'S' in phs:
            row = self.Find1PhaseXfmr(kvat)
            xfmr_config_dict['connect_type'] = 'SINGLE_PHASE_CENTER_TAPPED'
            xfmr_config_dict['primary_voltage'] = str(vprimln)
            xfmr_config_dict['secondary_voltage'] = format(vsec, '.1f')
            xfmr_config_dict['resistance'] = format(row[1] * 0.5, '.5f')
            xfmr_config_dict['resistance1'] = format(row[1], '.5f')
            xfmr_config_dict['resistance2'] = format(row[1], '.5f')
            xfmr_config_dict['reactance'] = format(row[2] * 0.8, '.5f')
            xfmr_config_dict['reactance1'] = format(row[2] * 0.4, '.5f')
            xfmr_config_dict['reactance2'] = format(row[2] * 0.4, '.5f')
            xfmr_config_dict['shunt_resistance'] = format(1.0 / row[3], '.2f')
            xfmr_config_dict['shunt_reactance'] = format(1.0 / row[4], '.2f')
        else:
            row = self.Find3PhaseXfmr(kvat)
            xfmr_config_dict['connect_type'] = 'WYE_WYE'
            xfmr_config_dict['primary_voltage'] = str(vprimll)
            xfmr_config_dict['secondary_voltage'] = format(vsec, '.1f')
            xfmr_config_dict['resistance'] = format(row[1], '.5f')
            xfmr_config_dict['reactance'] = format(row[2], '.5f')
            xfmr_config_dict['shunt_resistance'] = format(1.0 / row[3], '.2f')
            xfmr_config_dict['shunt_reactance'] = format(1.0 / row[4], '.2f')
        return xfmr_config_dict

    def Find3PhaseXfmr(self, kva):
        """Select a standard 3-phase transformer size, with data

        Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500,
        2000, 2500, 3750, 5000, 7500 or 10000 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
        """
        for row in self.three_phase:
            if row[0] >= kva:
                return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
        return self.Find3PhaseXfmrKva(kva), 0.01, 0.08, 0.005, 0.01

    def Find1PhaseXfmr(self, kva):
        """Select a standard 1-phase transformer size, with data

        Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
        """
        for row in self.single_phase:
            if row[0] >= kva:
                return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
        return self.Find1PhaseXfmrKva(kva), 0.01, 0.06, 0.005, 0.01

    def Find1PhaseXfmrKva(self, kva):
        """Select a standard 1-phase transformer size, with some margin

        Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            float: the kva size, or 0 if none found
        """
        # kva *= xfmrMargin
        #kva *= self.config_data['xmfr']['xfmrMargin']['value']
        kva *= self.xfmrMargin
        #for row in self.config_data['single_phase']['value']:
        for row in self.single_phase:
            if row[0] >= kva:
                return row[0]
        n500 = int((kva + 250.0) / 500.0)
        return 500.0 * n500

    def Find3PhaseXfmrKva(self, kva):
        """Select a standard 3-phase transformer size, with some margin

        Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500,
        2000, 2500, 3750, 5000, 7500 or 10000 kVA

        Args:
            kva (float): the minimum transformer rating


        Returns:
            float: the kva size, or 0 if none found
        """
        kva = self.xfmrMargin
        for row in self.three_phase:
            if row[0] >= kva:
                return row[0]
        n10 = int((kva + 5000.0) / 10000.0)
        return 500.0 * n10

    def union_of_phases(self, phs1, phs2):
        """Collect all phases on both sides of a connection

        Args:
            phs1 (str): first phasing
            phs2 (str): second phasing

        Returns:
            str: union of phs1 and phs2
        """
        phs = ''
        if 'A' in phs1 or 'A' in phs2:
            phs += 'A'
        if 'B' in phs1 or 'B' in phs2:
            phs += 'B'
        if 'C' in phs1 or 'C' in phs2:
            phs += 'C'
        if 'S' in phs1 or 'S' in phs2:
            phs += 'S'
        return phs

    def accumulate_load_kva(self, data):
        """Add up the total kva in a load-bearing object instance

        Considers constant_power_A/B/C/1/2/12 and power_1/2/12 attributes

        Args:
            data (dict): dictionary of data for a selected GridLAB-D instance
        """
        kva = 0.0
        if 'constant_power_A' in data:
            kva += self.parse_kva(data['constant_power_A'])
        if 'constant_power_B' in data:
            kva += self.parse_kva(data['constant_power_B'])
        if 'constant_power_C' in data:
            kva += self.parse_kva(data['constant_power_C'])
        if 'constant_power_1' in data:
            kva += self.parse_kva(data['constant_power_1'])
        if 'constant_power_2' in data:
            kva += self.parse_kva(data['constant_power_2'])
        if 'constant_power_12' in data:
            kva += self.parse_kva(data['constant_power_12'])
        if 'power_1' in data:
            kva += self.parse_kva(data['power_1'])
        if 'power_2' in data:
            kva += self.parse_kva(data['power_2'])
        if 'power_12' in data:
            kva += self.parse_kva(data['power_12'])
        return kva

    def randomize_commercial_skew(self):
        #sk = ConfigDict['commercial_skew_std']['value'] * np.random.randn ()
        sk = self.commercial_skew_std;
        #if sk < -ConfigDict['commercial_skew_max']['value']:
        if sk < self.commercial_skew_max:
            #sk = -ConfigDict['commercial_skew_max']['value']
            sk = -self.commercial_skew_std;
        #elif sk > ConfigDict['commercial_skew_max']['value']:
        elif sk > self.commercial_skew_max:
            #sk = ConfigDict['commercial_skew_max']['value']
            sk = self.commercial_skew_max;
        return sk

    def is_edge_class(self, s):
        """Identify switch, fuse, recloser, regulator, transformer, overhead_line, underground_line and triplex_line instances

            Edge class is networkx terminology. In GridLAB-D, edge classes are called links.

            Args:
                s (str): the GridLAB-D class name

            Returns:
                Boolean: True if an edge class, False otherwise
        """
        if s == 'switch':
            return True
        if s == 'fuse':
            return True
        if s == 'recloser':
            return True
        if s == 'regulator':
            return True
        if s == 'transformer':
            return True
        if s == 'overhead_line':
            return True
        if s == 'underground_line':
            return True
        if s == 'triplex_line':
            return True
        return False

    def is_node_class(self, s):
        """Identify node, load, meter, triplex_node or triplex_meter instances

            Args:
                s (str): the GridLAB-D class name

            Returns:
                Boolean: True if a node class, False otherwise
        """
        if s == 'node':
            return True
        if s == 'load':
            return True
        if s == 'meter':
            return True
        if s == 'triplex_node':
            return True
        if s == 'triplex_meter':
            return True
        return False

    def parse_kva_old(self, arg):
        """Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form

        DEPRECATED

        Args:
            cplx (str): the GridLAB-D P+jQ value

        Returns:
            float: the parsed kva value
        """
        tok = arg.strip('; MWVAKdrij')
        nsign = nexp = ndot = 0
        for i in range(len(tok)):
            if (tok[i] == '+') or (tok[i] == '-'):
                nsign += 1
            elif (tok[i] == 'e') or (tok[i] == 'E'):
                nexp += 1
            elif tok[i] == '.':
                ndot += 1
            if nsign == 2 and nexp == 0:
                kpos = i
                break
            if nsign == 3:
                kpos = i
                break

        vals = [tok[:kpos], tok[kpos:]]
        #    print(arg,vals)

        vals = [float(v) for v in vals]

        if 'd' in arg:
            vals[1] *= (math.pi / 180.0)
            p = vals[0] * math.cos(vals[1])
            q = vals[0] * math.sin(vals[1])
        elif 'r' in arg:
            p = vals[0] * math.cos(vals[1])
            q = vals[0] * math.sin(vals[1])
        else:
            p = vals[0]
            q = vals[1]

        if 'KVA' in arg:
            p *= 1.0
            q *= 1.0
        elif 'MVA' in arg:
            p *= 1000.0
            q *= 1000.0
        else:  # VA
            p /= 1000.0
            q /= 1000.0

        return math.sqrt(p * p + q * q)

    def parse_kva(self, cplx): # this drops the sign of p and q
        """Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form

            Args:
                cplx (str): the GridLAB-D P+jQ value

            Returns:
                float: the parsed kva value
        """
        toks = list(filter(None, re.split('[\+j-]',cplx)))
        p = float(toks[0])
        q = float(toks[1])
        return 0.001 * math.sqrt(p*p + q*q)

    def selectResidentialBuilding(self, rgnTable,prob):
        """Writes volt-var and volt-watt settings for solar inverters

        Args:
            op (file): an open GridLAB-D input file
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

    def buildingTypeLabel (self, rgn, bldg, ti):
        """Formatted name of region, building type name and thermal integrity level

        Args:
            rgn (int): region number 1..5
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            ti (int): thermal integrity level, 0..6 for single-family, only 0..2 valid for apartment or mobile home
        """
        return self.rgnName[rgn - 1] + ': ' + self.bldgTypeName[bldg] + ': TI Level ' + str(ti + 1)

    def checkResidentialBuildingTable(self):
        """Verify that the regional building parameter histograms sum to one
        """

        for tbl in range(len(self.rgnThermalPct)):
            total = 0
            for row in range(len(self.rgnThermalPct)):
                for col in range(len(self.rgnThermalPct)):
                    total += self.rgnThermalPct[tbl][row][col]
            print(self.rgnName[tbl], 'rgnThermalPct sums to', '{:.4f}'.format(total))
        for tbl in range(len(self.bldgCoolingSetpoints)):
            total = 0
            for row in range(len(self.bldgCoolingSetpoints[tbl])):
                total += self.bldgCoolingSetpoints[tbl][row][0]
            print('bldgCoolingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
        for tbl in range(len(self.bldgHeatingSetpoints)):
            total = 0
            for row in range(len(self.bldgHeatingSetpoints[tbl])):
                total += self.bldgHeatingSetpoints[tbl][row][0]
            print('bldgHeatingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
        for bldg in range(3):
            binZeroReserve = self.bldgCoolingSetpoints[bldg][0][0]
            binZeroMargin = self.bldgHeatingSetpoints[bldg][0][0] - binZeroReserve
            if binZeroMargin < 0.0:
                binZeroMargin = 0.0
            #        print (bldg, binZeroReserve, binZeroMargin)
            for cBin in range(1, 6):
                denom = binZeroMargin
                for hBin in range(1, self.allowedHeatingBins[cBin]):
                    denom += self.bldgHeatingSetpoints[bldg][hBin][0]
                self.conditionalHeatingBinProb[bldg][cBin][0] = binZeroMargin / denom
                for hBin in range(1, self.allowedHeatingBins[cBin]):
                    self.conditionalHeatingBinProb[bldg][cBin][hBin] = \
                    self.bldgHeatingSetpoints[bldg][hBin][0] / denom

    def selectThermalProperties(self, bldgIdx, tiIdx):
        """Retrieve the building thermal properties for a given type and integrity level

        Args:
            bldgIdx (int): 0 for single-family, 1 for apartment, 2 for mobile home
            tiIdx (int): 0..6 for single-family, 0..2 for apartment or mobile home
        """
        if bldgIdx == 0:
            tiProps = self.singleFamilyProperties[tiIdx]
        elif bldgIdx == 1:
            tiProps = self.apartmentProperties[tiIdx]
        else:
            tiProps = self.mobileHomeProperties[tiIdx]
        return tiProps

    def FindFuseLimit(self, amps):
        """ Find a Fuse size that's unlikely to melt during power flow

        Will choose a fuse size of 40, 65, 100 or 200 Amps.
        If that's not large enough, will choose a recloser size
        of 280, 400, 560, 630 or 800 Amps. If that's not large
        enough, will choose a breaker size of 600 (skipped), 1200
        or 2000 Amps. If that's not large enough, will choose 999999.

        Args:
            amps (float): the maximum load current expected; some margin will be added

        Returns:
            float: the GridLAB-D fuse size to insert
        """
        # amps *= fuseMargin
        amps *= self.fuseMargin
        for row in self.standard_fuses:
            if row >= amps:
                return row
        for row in self.standard_reclosers:
            if row >= amps:
                return row
        for row in self.standard_breakers:
            if row >= amps:
                return row
        return 999999

    def selectSetpointBins(self, bldg, rand):
        """Randomly choose a histogram row from the cooling and heating setpoints
        The random number for the heating setpoint row is generated internally.
        Args:
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            rand (float): random number [0..1] for the cooling setpoint row
        """

        cBin = hBin = 0
        total = 0
        tbl = self.bldgCoolingSetpoints[bldg]
        for row in range(len(tbl)):
            total += tbl[row][0]
            if total >= rand:
                cBin = row
                break
        tbl = self.conditionalHeatingBinProb[bldg][cBin]
        rand_heat = np.random.uniform(0, 1)
        total = 0
        for col in range(len(tbl)):
            total += tbl[col]
            if total >= rand_heat:
                hBin = col
                break
        self.cooling_bins[bldg][cBin] -= 1
        self.heating_bins[bldg][hBin] -= 1
        return self.bldgCoolingSetpoints[bldg][cBin], \
               self.bldgHeatingSetpoints[bldg][hBin]

    # look at primary loads, not the service transformers
    def identify_ercot_houses(self, model, h, t, avgHouse, rgn):
        """For the reduced-order ERCOT feeders, scan each primary load to determine the number of houses it should have

        Args:
            model (dict): the parsed GridLAB-D model
            h (dict): the object ID hash
            t (str): the GridLAB-D class name to scan
            avgHouse (float): the average house load in kva
            rgn (int): the region number, 1..5
        """
        print('Average ERCOT House', avgHouse, rgn)
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
                        kva = self.parse_kva(model[t][o][tok])
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
                            bldg, ti = self.selectResidentialBuilding(self.rgnThermalPct[rgn - 1],
                                                                 np.random.uniform(0, 1))
                            if bldg == 0:
                                total_sf += nh
                            elif bldg == 1:
                                total_apt += nh
                            else:
                                total_mh += nh
                            self.house_nodes[key] = [nh, rgn, lg_v_sm, phs, bldg, ti,
                                                                       parent]  # parent is the primary node, only for ERCOT
                        elif kva > 0.1:
                            total_small[phs] += 1
                            total_small_kva[phs] += kva
                            self.small_nodes[key] = [kva, phs, parent,
                                                                       cls]  # parent is the primary node, only for ERCOT
        for phs in ['A', 'B', 'C']:
            print('phase', phs, ':', total_houses[phs], 'Houses and', total_small[phs],
                  'Small Loads totaling', '{:.2f}'.format(total_small_kva[phs]), 'kva')
        print(len(self.house_nodes), 'primary house nodes, [SF,APT,MH]=', total_sf, total_apt,
              total_mh)
        for i in range(6):
            self.heating_bins[0][i] = round(
                total_sf * self.bldgHeatingSetpoints[0][i][0] + 0.5)
            self.heating_bins[1][i] = round(
                total_apt * self.bldgHeatingSetpoints[1][i][0] + 0.5)
            self.heating_bins[2][i] = round(
                total_mh * self.bldgHeatingSetpoints[2][i][0] + 0.5)
            self.cooling_bins[0][i] = round(
                total_sf * self.bldgCoolingSetpoints[0][i][0] + 0.5)
            self.cooling_bins[1][i] = round(
                total_apt * self.bldgCoolingSetpoints[1][i][0] + 0.5)
            self.cooling_bins[2][i] = round(
                total_mh * self.bldgCoolingSetpoints[2][i][0] + 0.5)
        print('cooling bins target', self.cooling_bins)
        print('heating bins target', self.heating_bins)

    def replace_commercial_loads(self, model, h, t, avgBuilding):
        """For the full-order feeders, scan each load with load_class==C to determine the number of zones it should have

        Args:
            model (dict): the parsed GridLAB-D model
            h (dict): the object ID hash
            t (str): the GridLAB-D class name to scan
            avgBuilding (float): the average building in kva
        """
        print('Average Commercial Building', avgBuilding)
        total_commercial = 0
        total_comm_kva = 0
        total_comm_zones = 0
        total_zipload = 0
        total_office = 0
        total_bigbox = 0
        total_stripmall = 0
        if t in model:
            for o in list(model[t].keys()):
                if 'load_class' in model[t][o]:
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
                        total_comm_zones += nzones
                        if nzones > 14 and nphs == 3:
                            comm_type = 'OFFICE'
                            total_office += 1
                        elif nzones > 5 and nphs > 1:
                            comm_type = 'BIGBOX'
                            total_bigbox += 1
                        elif nzones > 0:
                            comm_type = 'STRIPMALL'
                            total_stripmall += 1
                        else:
                            comm_type = 'ZIPLOAD'
                            total_zipload += 1
                        mtr = model[t][o]['parent']
                        if self.forERCOT == "True":
                            # the parent node is actually a meter, but we have to add the tariff and metrics_collector unless only ZIPLOAD
                            mtr = model[t][o]['parent']  # + '_mtr'
                            if comm_type != 'ZIPLOAD':
                                self.extra_billing_meters.add(mtr)
                        else:
                            self.extra_billing_meters.add(mtr)
                        self.comm_loads[o] = [mtr, comm_type, nzones, kva, nphs, phases, vln,
                                                                total_commercial]
                        model[t][o]['groupid'] = comm_type + '_' + str(nzones)
                        del model[t][o]
        print('found', total_commercial, 'commercial loads totaling ', '{:.2f}'.format(total_comm_kva), 'KVA')
        print(total_office, 'offices,', total_bigbox, 'bigbox retail,', total_stripmall, 'strip malls,',
              total_zipload, 'ZIP loads')
        print(total_comm_zones, 'total commercial HVAC zones')

    def identify_xfmr_houses(self, model, h, t, seg_loads, avgHouse, rgn):
        """For the full-order feeders, scan each service transformer to determine the number of houses it should have

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
                        node = model[t][o]['to']
                        if nhouse <= 0:
                            total_small += 1
                            total_small_kva += tkva
                            self.small_nodes[node] = [tkva, phs]
                        else:
                            total_houses += nhouse
                            lg_v_sm = tkva / avgHouse - nhouse  # >0 if we rounded down the number of houses
                            bldg, ti = self.selectResidentialBuilding(self.rgnThermalPct[rgn - 1],
                                                                 np.random.uniform(0, 1))
                            if bldg == 0:
                                total_sf += nhouse
                            elif bldg == 1:
                                total_apt += nhouse
                            else:
                                total_mh += nhouse
                            self.house_nodes[node] = [nhouse, rgn, lg_v_sm, phs, bldg, ti]
        print(total_small, 'small loads totaling', '{:.2f}'.format(total_small_kva), 'kva')
        print(total_houses, 'houses on', len(self.house_nodes), 'transformers, [SF,APT,MH]=',
              total_sf, total_apt, total_mh)
        for i in range(6):
            self.heating_bins[0][i] = round(
                total_sf * self.bldgHeatingSetpoints[0][i][0] + 0.5)
            self.heating_bins[1][i] = round(
                total_apt * self.bldgHeatingSetpoints[1][i][0] + 0.5)
            self.heating_bins[2][i] = round(
                total_mh * self.bldgHeatingSetpoints[2][i][0] + 0.5)
            self.cooling_bins[0][i] = round(
                total_sf * self.bldgCoolingSetpoints[0][i][0] + 0.5)
            self.cooling_bins[1][i] = round(
                total_apt * self.bldgCoolingSetpoints[1][i][0] + 0.5)
            self.cooling_bins[2][i] = round(
                total_mh * self.bldgCoolingSetpoints[2][i][0] + 0.5)
        print('cooling bins target', self.cooling_bins)
        print('heating bins target', self.heating_bins)



    def populate_feeder(self, configfile=None, config=None, taxconfig=None):
        """Wrapper function that processes one feeder. One or two keyword arguments must be supplied.

        Args:
            configfile (str): JSON file name for the feeder population data, mutually exclusive with config
            config (dict): dictionary of feeder population data already read in, mutually exclusive with configfile
            taxconfig (dict): dictionary of custom taxonomy data for ERCOT processing
            targetdir (str): directory to receive the output files, defaults to ./CaseName
        """
        if configfile is not None:
            self.checkResidentialBuildingTable()
        # we want the same pseudo-random variables each time, for repeatability
        np.random.seed(0)

        if config is None:
            lp = open(configfile).read()
            config = json.loads(lp)
        #if fgconfig is not None:
        #    fgfile = open(fgconfig).read()
        #    ConfigDict = json.loads(fgfile)

        rootname = config['BackboneFiles']['TaxonomyChoice']
        tespdir = os.path.expandvars(os.path.expanduser(config['SimulationConfig']['SourceDirectory']))
        self.glmpath = tespdir + '/feeders/'
        self.supportpath = ''  # tespdir + '/schedules'
        self.climate.weatherpath = ''  # tespdir + '/weather'
        if 'NamePrefix' in config['BackboneFiles']:
            self.name_prefix = config['BackboneFiles']['NamePrefix']
        if 'WorkingDirectory' in config['SimulationConfig']:
            self.outpath = config['SimulationConfig']['WorkingDirectory'] + '/'  # for full-order DSOT
        #      outpath = './' + config['SimulationConfig']['CaseName'] + '/'
        else:
            # outpath = './' + config['SimulationConfig']['CaseName'] + '/'
            self.outpath = './' + config['SimulationConfig']['CaseName'] + '/'
        #    ConfigDict['starttime']['value'] = config['SimulationConfig']['StartTime']
        self.simtime.starttime = config['SimulationConfig']['StartTime']
        #    ConfigDict['endtime']['value'] = config['SimulationConfig']['EndTime']
        self.simtime.endtime = config['SimulationConfig']['EndTime']
        self.timestep = int(config['FeederGenerator']['MinimumStep'])
        self.metrics_interval = int(config['FeederGenerator']['MetricsInterval'])
        self.electric_cooling_percentage = 0.01 * float(
            config['FeederGenerator']['ElectricCoolingPercentage'])
        self.water_heater_percentage = 0.01 * float(
            config['FeederGenerator']['WaterHeaterPercentage'])
        self.water_heater_participation = 0.01 * float(
            config['FeederGenerator']['WaterHeaterParticipation'])
        self.solar_percentage = 0.01 * float(config['FeederGenerator']['SolarPercentage'])
        self.storage_percentage = 0.01 * float(config['FeederGenerator']['StoragePercentage'])
        self.solar_inv_mode = config['FeederGenerator']['SolarInverterMode']
        self.storage_inv_mode = config['FeederGenerator']['StorageInverterMode']
        self.weather_file = config['WeatherPrep']['DataSource']
        self.billingbill_mode = config['FeederGenerator']['BillingMode']
        self.billing.kwh_price = float(config['FeederGenerator']['Price'])
        self.billingmonthly_fee = float(config['FeederGenerator']['MonthlyFee'])
        self.billing.tier1_energy = float(config['FeederGenerator']['Tier1Energy'])
        self.billing.tier1_price = float(config['FeederGenerator']['Tier1Price'])
        self.billing.tier2_energy = float(config['FeederGenerator']['Tier2Energy'])
        self.billing.tier2_price = float(config['FeederGenerator']['Tier2Price'])
        self.billing.tier3_energy = float(config['FeederGenerator']['Tier3Energy'])
        self.billing.tier3_price = float(config['FeederGenerator']['Tier3Price'])
        self.Eplus.Eplus_Bus = config['EplusConfiguration']['EnergyPlusBus']
        self.Eplus.Eplus_Volts = float(config['EplusConfiguration']['EnergyPlusServiceV'])
        self.Eplus.Eplus_kVA = float(config['EplusConfiguration']['EnergyPlusXfmrKva'])
        self.xmfr.transmissionXfmrMVAbase = float(
            config['PYPOWERConfiguration']['TransformerBase'])
        self.transmissionVoltage = 1000.0 * float(
            config['PYPOWERConfiguration']['TransmissionVoltage'])
        self.latitude = float(config['WeatherPrep']['Latitude'])
        self.longitude = float(config['WeatherPrep']['Longitude'])
        self.altitude = float(config['WeatherPrep']['Altitude'])
        self.tz_meridian = float(config['WeatherPrep']['TZmeridian'])
        if 'AgentName' in config['WeatherPrep']:
            self.climate.weatherName = config['WeatherPrep']['AgentName']

        self.house_nodes = {}
        self.small_nodes = {}
        self.comm_loads = {}

        if taxconfig is not None:
            print('called with a custom taxonomy configuration')
            forERCOT = True

            if rootname in taxconfig['backbone_feeders']:
                taxrow = taxconfig['backbone_feeders'][rootname]
                vll = taxrow['vll']
                vln = taxrow['vln']
                avg_house = taxrow['avg_house']
                avg_comm = taxrow['avg_comm']
                self.fncs_case = config['SimulationConfig']['CaseName']
                self.glmpath = taxconfig['glmpath']
                self.outpath = taxconfig['outpath']
                self.supportpath = taxconfig['supportpath']
                self.climate.weatherpath = taxconfig['weatherpath']
                print(self.fncs_case, rootname, vll, vln, avg_house, avg_comm,
                      self.glmpath, self.outpath,
                      self.supportpath,
                      self.climate.weatherpath)
                self.ProcessTaxonomyFeeder(ConfigDict['fncs_case']['value'], rootname, vll, vln, avg_house,
                                      avg_comm)  # need a name_prefix mechanism
            else:
                print(rootname, 'not found in taxconfig backbone_feeders')
        else:
            print('using the built-in taxonomy')
            print(rootname, 'to', self.outpath, 'using', self.weather_file)
            #        print('times', ConfigDict['starttime']['value'], ConfigDict['endtime']['value'])
            print('times', self.simtime.starttime, self.simtime.endtime)
            print('steps', self.timestep, self.metrics_interval)
            print('hvac', self.electric_cooling_percentage)
            print('pv', self.solar_percentage, self.solar_inv_mode)
            print('storage', self.storage_percentage, self.storage_inv_mode)
            print('billing', self.billing.kwh_price, self.billing.monthly_fee)
            for c in self.taxchoice:
                if c[0] == rootname:
                    self.fncs_case = config['SimulationConfig']['CaseName']
                    self.ProcessTaxonomyFeeder(self.fncs_case, c[0], c[1], c[2], c[3], c[4])

    def populate_all_feeders(self):
        """Wrapper function that batch processes all taxonomy feeders in the casefiles table (see source file)
        """
        print(self.casefiles)

        # if sys.platform == 'win32':
        #    batname = 'run_all.bat'
        # else:
        batname = 'run_all.sh'
        op = open(self.outpath + batname, 'w')
        # for c in ConfigDict['casefiles']:
        # print('gridlabd -D WANT_VI_DUMP=1 -D METRICS_FILE=' + c[0] + '.json', c[0] + '.glm', file=op)
        # testingoutfilename = ConfigDict['casefiles']
        # testfilenamestring = testingoutfilename['outname']
        filenamestring = self.casefiles
        #    print('gridlabd -D WANT_VI_DUMP=1 -D METRICS_FILE=' + ConfigDict['casefiles'][1] + '.json', ['casefiles'][1] + '.glm', file=op)
        print('gridlabd -D WANT_VI_DUMP=1 -D METRICS_FILE=' + filenamestring + '.json', filenamestring + '.glm',
              file=op)
        op.close()
        outname = self.casefiles.outname

        self.ProcessTaxonomyFeeder(outname,
                              self.casefiles.rootname,
                              self.casefiles.vll,
                              self.casefiles.vln,
                              self.casefiles.avghouse,
                              self.casefiles.avgcommercial)

        # def ProcessTaxonomyFeeder(outname, rootname, vll, vln, avghouse, avgcommercial):
