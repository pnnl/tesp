# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: glm_modifier.py

import json
import math
import os
import re
import numpy as np

import tesp_support.helpers
from store import entities_path
from entity import assign_defaults
from entity import Entity
from model import GLModel


class GLMModifier:
    # instances of entity values
    # objects = [batteries, meters, capacitors, fuses, houses, lines, loads,
    #            secondary_transformers, solar_pvs, substation_transformers,
    #            switches, triplex_lines, triplex_loads, zip_loads, recorder]

    def __init__(self):
        self.model = GLModel()
        self.mod_headers = []
        assign_defaults(self, entities_path + 'feeder_defaults.json')
        return

    def get_object(self, gld_type):
        return self.model.entities[gld_type]

    def get_object_name(self, gld_type, name):
        return self.get_object(gld_type).instance[name]
        
    def get_object_names(self, gld_type):
        return list(self.get_object(gld_type).instance.keys())

    def add_object(self, gld_type, name, params):
        return self.get_object(gld_type).set_instance(name, params)

    def del_object(self, gld_type, name):
        self.get_object(gld_type).del_instance(name)
        for obj in self.model.entities:
            myObj = self.model.entities[obj]
            myArr = []
            if myObj.find_item('parent'):
                for myName in myObj.instance:
                    instance = myObj.instance[myName]
                    if 'parent' in instance.keys():
                        if instance['parent'] == name:
                            myArr.append(myName)
            for myName in myArr:
                myObj.del_instance(myName)

    def add_object_attr(self, gld_type, name, item_name, item_value):
        return self.get_object(gld_type).set_item(name, item_name, item_value)

    def del_object_attr(self, gld_type, name, item_name):
        self.get_object(gld_type).del_item(name, item_name)

    def mod_model(self):
        tlist = list(self.model.network.nodes.data())
        for basenode in tlist:
            print(basenode)
        return True

    def read_model(self, filepath):
        self.model.read(filepath)
        return True

    def write_model(self, filepath):
        # op = open(filepath, "w", encoding='utf-8')
        # glm_out = self.model.instancesToGLM()
        # print(glm_out, op)
        # #print(self.model.instancesToGLM(), op)
        # op.close()
        self.model.write(filepath)
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
    def buildingTypeLabel (self, rgn, bldg, ti):
        """Formatted name of region, building type name and thermal integrity level

        Args:
            rgn (int): region number 1..5
            bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
            ti (int): thermal integrity level, 0..6 for single-family, only 0..2 valid for apartment or mobile home
        """
        return self.rgnName[rgn - 1] + ': ' + self.bldgTypeName[bldg] + ': TI Level ' + str(ti + 1)

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
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
    # ************************************************************************************************************
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

    # ************************************************************************************************************
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
        return total_commercial, total_office, total_bigbox, total_stripmall, total_zipload, total_comm_zones

    # ************************************************************************************************************
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

    # ************************************************************************************************************

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

    # ************************************************************************************************************
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

    # ************************************************************************************************************
    def connect_ercot_houses(self, model, h, op, vln, vsec):
        """For the reduced-order ERCOT feeders, add houses and a large service transformer to the load points

        Args:
            model (dict): the parsed GridLAB-D model
            h (dict): the object ID hash
            op (file): an open GridLAB-D input file
            vln (float): the primary line-to-neutral voltage
            vsec (float): the secondary line-to-neutral voltage
        """
        for key in self.house_nodes:
            #        bus = key[:-2]
            bus = self.house_nodes[key][6]
            phs = self.house_nodes[key][3]
            nh = self.house_nodes[key][0]
            xfkva = self.Find1PhaseXfmrKva(6.0 * nh)
            if xfkva > 100.0:
                npar = int(xfkva / 100.0 + 0.5)
                xfkva = 100.0
            elif xfkva <= 0.0:
                xfkva = 100.0
                npar = int(0.06 * nh + 0.5)
            else:
                npar = 1
            #        print (key, bus, phs, nh, xfkva, npar)
            # write the service transformer==>TN==>TPX==>TM for all houses
            kvat = npar * xfkva
            row = self.Find1PhaseXfmr(xfkva)
            tempEntity = Entity(key + '_xfconfig', self.model.objects['transformer_configuration'])
            tempEntity.name = key + '_xfconfig'
            tempEntity.power_rating = format(kvat, '.2f')
            if 'A' in phs:
                tempEntity.powerA_rating = format(kvat, '.2f')
            elif 'B' in phs:
                tempEntity.powerB_rating = format(kvat, '.2f')
            elif 'C' in phs:
                tempEntity.powerC_rating = format(kvat, '.2f')
            tempEntity.install_type = 'PADMOUNT'
            tempEntity.connect_type = 'SINGLE_PHASE_CENTER_TAPPED'
            tempEntity.primary_voltage = str(vln) + ';'
            tempEntity.secondary_voltage = format(vsec, '.1f')
            tempEntity.resistance = format(row[1] * 0.5, '.5f')
            tempEntity.resistance1 = format(row[1], '.5f')
            tempEntity.resistance2 = format(row[1], '.5f')
            tempEntity.reactance = format(row[2] * 0.8, '.5f')
            tempEntity.reactance1 = format(row[2] * 0.4, '.5f')
            tempEntity.reactance2 = format(row[2] * 0.4, '.5f')
            tempEntity.shunt_resistance = format(1.0 / row[3], '.2f')
            tempEntity.shunt_reactance = format(1.0 / row[4], '.2f')
            self.entities[tempEntity.name] = tempEntity

            tempEntity = Entity(key + '_xf', self.objects['transformer'])
            tempEntity.name = key + '_xf'
            tempEntity.phases = phs + 'S'
            #tempEntity.from = bus
            tempEntity.to = key + '_tn'
            tempEntity.configuration = key + '_xfconfig'
            self.entities[tempEntity.name] = tempEntity

            tempEntity = Entity(key + '_tpxconfig', self.objects['triplex_line_configuration'])
            tempEntity.name = key + '_tpxconfig'
            zs = format(self.tpxR11 / nh, '.5f') + '+' + format(self.tpxX11 / nh, '.5f') + 'j;'
            zm = format(self.tpxR12 / nh, '.5f') + '+' + format(self.tpxX12 / nh, '.5f') + 'j;'
            amps = format(self.tpxAMP * nh, '.1f') + ';'
            tempEntity.z11 = zs
            tempEntity.z22 = zs
            tempEntity.z12 = zm
            tempEntity.z21 = zm
            tempEntity.rating.summer.continuous = amps
            self.entities[tempEntity.name] = tempEntity

            tempEntity = Entity(key + '_tpx', self.objects['triplex_line'])
            tempEntity.name = key + '_tpx'
            tempEntity.phases = phs + 'S'
            #tempEntity.from = key + '_tn'
            tempEntity.to = key + '_mtr'
            tempEntity.length = '50'
            tempEntity.configuration = key + '_tpxconfig'
            self.entities[tempEntity.name] = tempEntity

            if 'A' in phs:
                vstart = str(vsec) + '+0.0j'
            elif 'B' in phs:
                vstart = format(-0.5 * vsec, '.2f') + format(-0.866025 * vsec, '.2f') + 'j'
            else:
                vstart = format(-0.5 * vsec, '.2f') + '+' + format(0.866025 * vsec, '.2f') + 'j'

            tempEntity = Entity(key + '_tn', self.objects['triplex_node'])
            tempEntity.name = key + '_tn'
            tempEntity.phases = phs + 'S'
            tempEntity.voltage_1 = vstart
            tempEntity.voltage_2 = vstart
            tempEntity.voltage_N = '0'
            tempEntity.nominal_voltage = format(vsec, '.1f')
            self.entities[tempEntity.name] = tempEntity

            tempEntity = Entity(key + '_mtr', self.objects['triplex_meter'])
            tempEntity.name = key + '_mtr'
            tempEntity.phases = phs + 'S'
            tempEntity.voltage_1 = vstart
            tempEntity.voltage_2 = vstart
            tempEntity.voltage_N = '0'
            tempEntity.nominal_voltage = format(vsec, '.1f')
            self.entities[tempEntity.name] = tempEntity
#            write_tariff(op)
#           if self.metrics_interval > 0:
#                print('  object metrics_collector {', file=op)
#                print('    interval', str(self.metrics_interval) + ';', file=op)
#                print('  };', file=op)
#           print('}', file=op)

    # ************************************************************************************************************
    def write_local_triplex_configurations(self):
        """Write a 4/0 AA triplex configuration

        Args:
          op (file): an open GridLAB-D input file
        """
        for row in ConfigDict['triplex_conductors']:
            tempEntity = Entity(self.name_prefix + row, self.objects['triplex_line_conductor'])
            tempEntity.name = self.name_prefix + row
            tempEntity.resistance = str(self.triplex_conductors[row][0])
            tempEntity.geometric_mean_radius = str(self.triplex_conductors[row][1])
            rating_str = str(self.triplex_conductors[row][2])
            tempEntity.rating.summer.continuous = rating_str
            tempEntity.rating.summer.emergency = rating_str
            tempEntity.rating.winter.continuous = rating_str
            tempEntity.rating.winter.emergency = rating_str
            self.entities[tempEntity.name] = tempEntity

        for row in self.triplex_configurations:
            tempEntity = Entity(self.name_prefix + row, self.objects['triplex_line_configuration'])
            tempEntity.name = self.name_prefix + row
            tempEntity.conductor_1 = self.name_prefix + self.triplex_configurations[row]['conductors'][0]
            tempEntity.conductor_2 = self.name_prefix + self.triplex_configurations[row]['conductors'][1]
            tempEntity.conductor_N = self.name_prefix + self.triplex_configurations[row]['conductors'][2]
            tempEntity.insulation_thickness = str(self.triplex_configurations[row]['insulation'])
            tempEntity.diameter = str(self.triplex_configurations[row]['diameter'])
            self.entities[tempEntity.name] = tempEntity
#************************************************************************************************************

        # def generate_triplex_line(self, tpxname, basenode, mtrname, phs)
        #     triplex_line_entity = Entity(tpxname, self.objects['triplex_line'])
        #     setattr(triplex_line_entity, 'name', tpxname)
        #     setattr(triplex_line_entity, 'from', basenode)
        #     setattr(triplex_line_entity, 'to', mtrname)
        #     setattr(triplex_line_entity, 'phases', phs)
        #     setattr(triplex_line_entity, 'length', 30)
        #     setattr(triplex_line_entity, 'configuration',self.name_prefix + list(self.triplex_configurations.keys())[0])
        #     return triplex_line_entity


#************************************************************************************************************
    def another_house_guy(self):
        params = []
        get_

def write_houses(self, basenode, vnom, bIgnoreThermostatSchedule=True, bWriteService=True, bTriplex=True, setpoint_offset=1.0):
    """Put houses, along with solar panels and batteries, onto a node

    Args:
        basenode (str): GridLAB-D node name
        op (file): open file to write to
        vnom (float): nominal line-to-neutral voltage at basenode
    """
#    global ConfigDict

    meter_class = 'triplex_meter'
    node_class = 'triplex_node'
    if bTriplex == False:
        meter_class = 'meter'
        node_class = 'node'

    nhouse = int(self.house_nodes[basenode][0])
    rgn = int(self.house_nodes[basenode][1])
    lg_v_sm = float(self.house_nodes[basenode][2])
    phs = self.house_nodes[basenode][3]
    bldg = self.house_nodes[basenode][4]
    ti = self.house_nodes[basenode][5]
    rgnTable = self.rgnThermalPct[rgn-1]

    if 'A' in phs:
        vstart = str(vnom) + '+0.0j'
    elif 'B' in phs:
        vstart = format(-0.5*vnom,'.2f') + format(-0.866025*vnom,'.2f') + 'j'
    else:
        vstart = format(-0.5*vnom,'.2f') + '+' + format(0.866025*vnom,'.2f') + 'j'

    if self.forERCOT == "True":
        phs = phs + 'S'
        tpxname = helpers.gld_strict_name (basenode + '_tpx')
        mtrname = helpers.gld_strict_name (basenode + '_mtr')
    elif bWriteService == True:
#        print ('object {:s} {{'.format (node_class), file=op)
        tempEntity = Entity(self.basenode, self.objects[format(node_class)])
#        print ('  name', basenode + ';', file=op)
        tempEntity.name = basenode
#        print ('  phases', phs + ';', file=op)
        tempEntity.phases = phs
#        print ('  nominal_voltage ' + str(vnom) + ';', file=op)
        tempEntity.nominal_voltage = str(vnom)
#        print ('  voltage_1 ' + vstart + ';', file=op)  # TODO: different attributes for regular node
        tempEntity.voltage_1 = vstart
#        print ('  voltage_2 ' + vstart + ';', file=op)
        tempEntity.voltage_2 = vstart
#        print ('}', file=op)
        self.entities[tempEntity.name] = tempEntity
    else:
        mtrname = helpers.gld_strict_name (basenode + '_mtr')
    for i in range(nhouse):
        if (self.forERCOT == "False") and (bWriteService == True):
            tpxname = helpers.gld_strict_name (basenode + '_tpx_' + str(i+1))
            mtrname = helpers.gld_strict_name (basenode + '_mtr_' + str(i+1))
            tempEntity = self.generate_Triplex_Line(tpxname, basenode, mtrname, phs)
            self.entities[tempEntity.name] = tempEntity

            #tempEntity = Entity(tpxname, self.objects['triplex_line'])
            #tempEntity.name = tpxname
            #tempEntity.from = basenode
            #tempEntity.to = mtrname
            #tempEntity.phases = phs
            #tempEntity.length = 30
            #tempEntity.configuration = self.name_prefix + list(self.triplex_configurations.keys())[0]




#            print ('object triplex_meter {', file=op)
            tempEntity = Entity(mtrname, self.objects['triplex_meter'])
#            print ('  name', mtrname + ';', file=op)
            tempEntity.name = mtrname
#            print ('  phases', phs + ';', file=op)
            tempEntity.phases = phs
#            print ('  meter_power_consumption 1+7j;', file=op)
            tempEntity.meter_power_consumption = '1+7j'
#            write_tariff (op)
#            print ('  nominal_voltage ' + str(vnom) + ';', file=op)
            tempEntity.nominal_voltage = str(vnom)
#            print ('  voltage_1 ' + vstart + ';', file=op)
            tempEntity.voltage_1 = vstart
#            print ('  voltage_2 ' + vstart + ';', file=op)
            tempEntity.voltage_2 = vstart


# how to handle this as an entity
            if self.metrics_interval > 0:
                print ('  object metrics_collector {', file=op)
                print ('    interval', str(ConfigDict['metrics_interval']['value']) + ';', file=op)
                print ('  };', file=op)

#            print ('}', file=op)
            self.entities[tempEntity.name] = tempEntity

        hsename = helpers.gld_strict_name (basenode + '_hse_' + str(i+1))
        whname = helpers.gld_strict_name (basenode + '_wh_' + str(i+1))
        solname = helpers.gld_strict_name (basenode + '_sol_' + str(i+1))
        batname = helpers.gld_strict_name (basenode + '_bat_' + str(i+1))
        sol_i_name = helpers.gld_strict_name (basenode + '_isol_' + str(i+1))
        bat_i_name = helpers.gld_strict_name (basenode + '_ibat_' + str(i+1))
        sol_m_name = helpers.gld_strict_name (basenode + '_msol_' + str(i+1))
        bat_m_name = helpers.gld_strict_name (basenode + '_mbat_' + str(i+1))
        if self.forERCOT == "True":
          hse_m_name = mtrname
        else:
          hse_m_name = helpers.gld_strict_name (basenode + '_mhse_' + str(i+1))
#          print ('object {:s} {{'.format (meter_class), file=op)
          tempEntity = Entity(hse_m_name, self.objects['{:s} {{'.format (meter_class)])
#          print ('  name', hse_m_name + ';', file=op)
          tempEntity.name = hse_m_name
#          print ('  parent', mtrname + ';', file=op)
          tempEntity.parent = mtrname
#          print ('  phases', phs + ';', file=op)
          tempEntity.phases = phs
#          print ('  nominal_voltage ' + str(vnom) + ';', file=op)
          tempEntity.nominal_voltage = str(vnom)
#          print ('}', file=op)
        self.entities[tempEntity.name] = tempEntity

        fa_base = self.rgnFloorArea[rgn-1][bldg]
        fa_rand = np.random.uniform (0, 1)
        stories = 1
        ceiling_height = 8
        if bldg == 0: # SF homes
            floor_area = fa_base + 0.5 * fa_base * fa_rand * (ti - 3) / 3;
            if np.random.uniform (0, 1) > self.rgnOneStory[rgn-1]:
                stories = 2
            ceiling_height += np.random.randint (0, 2)
        else: # apartment or MH
            floor_area = fa_base + 0.5 * fa_base * (0.5 - fa_rand) # +/- 50%
        floor_area = (1 + lg_v_sm) * floor_area # adjustment depends on whether nhouses rounded up or down
        if floor_area > 4000:
            floor_area = 3800 + fa_rand*200;
        elif floor_area < 300:
            floor_area = 300 + fa_rand*100;

        scalar1 = 324.9/8907 * floor_area**0.442
        scalar2 = 0.8 + 0.4 * np.random.uniform(0,1)
        scalar3 = 0.8 + 0.4 * np.random.uniform(0,1)
        resp_scalar = scalar1 * scalar2
        unresp_scalar = scalar1 * scalar3

        skew_value = self.residential_skew_std * np.random.randn ()
        if skew_value < -self.residential_skew_max:
            skew_value = -self.residential_skew_max
        elif skew_value > self.residential_skew_max:
            skew_value = self.residential_skew_max

        oversize = self.rgnOversizeFactor[rgn-1] * (0.8 + 0.4 * np.random.uniform(0,1))
        tiProps = self.selectThermalProperties (bldg, ti)
        # Rceiling(roof), Rwall, Rfloor, WindowLayers, WindowGlass,Glazing,WindowFrame,Rdoor,AirInfil,COPhi,COPlo
        Rroof = tiProps[0] * (0.8 + 0.4 * np.random.uniform(0,1))
        Rwall = tiProps[1] * (0.8 + 0.4 * np.random.uniform(0,1))
        Rfloor = tiProps[2] * (0.8 + 0.4 * np.random.uniform(0,1))
        glazing_layers = int(tiProps[3])
        glass_type = int(tiProps[4])
        glazing_treatment = int(tiProps[5])
        window_frame = int(tiProps[6])
        Rdoor = tiProps[7] * (0.8 + 0.4 * np.random.uniform(0,1))
        airchange = tiProps[8] * (0.8 + 0.4 * np.random.uniform(0,1))
        init_temp = 68 + 4 * np.random.uniform(0,1)
        mass_floor = 2.5 + 1.5 * np.random.uniform(0,1)
        h_COP = c_COP = tiProps[10] + np.random.uniform(0,1) * (tiProps[9] - tiProps[10])

#        print ('object house {', file=op)
        tempEntity = Entity(hsename, self.objects['house'])
#        print ('  name', hsename + ';', file=op)
        tempEntity.name = hsename
#        print ('  parent', hse_m_name + ';', file=op)
        tempEntity.parent = hse_m_name
#        print ('  groupid', ConfigDict['bldgTypeName']['value'][bldg] + ';', file=op)
        tempEntity.groupid = self.bldgTypeName[bldg]
#        print ('  // thermal_integrity_level', ConfigDict['thermal_integrity_level']['value'][ti] + ';', file=op)
        tempEntity.thermal_integrity_level = self.thermal_integrity_level[ti]
#        print ('  schedule_skew', '{:.0f}'.format(skew_value) + ';', file=op)
        tempEntity.schedule_skew = '{:.0f}'.format(skew_value)
#        print ('  floor_area', '{:.0f}'.format(floor_area) + ';', file=op)
        tempEntity.floor_area ='{:.0f}'.format(floor_area)
#        print ('  number_of_stories', str(stories) + ';', file=op)
        tempEntity.number_of_stories = str(stories)
#        print ('  ceiling_height', str(ceiling_height) + ';', file=op)
        tempEntity.ceiling_height = str(ceiling_height)
#        print ('  over_sizing_factor', '{:.1f}'.format(oversize) + ';', file=op)
        tempEntity.over_sizing_factor = '{:.1f}'.format(oversize)
#        print ('  Rroof', '{:.2f}'.format(Rroof) + ';', file=op)
        tempEntity.Rroof = '{:.2f}'.format(Rroof)
#        print ('  Rwall', '{:.2f}'.format(Rwall) + ';', file=op)
        tempEntity.Rwall = '{:.2f}'.format(Rwall)
#        print ('  Rfloor', '{:.2f}'.format(Rfloor) + ';', file=op)
        tempEntity.Rfloor = '{:.2f}'.format(Rfloor)
#        print ('  glazing_layers', str (glazing_layers) + ';', file=op)
        tempEntity.glazing_layers = str (glazing_layers)
#        print ('  glass_type', str (glass_type) + ';', file=op)
        tempEntity.glass_type = str (glass_type)
#        print ('  glazing_treatment', str (glazing_treatment) + ';', file=op)
        tempEntity.glazing_treatment = str (glazing_treatment)
#        print ('  window_frame', str (window_frame) + ';', file=op)
        tempEntity.window_frame = str (window_frame)
#        print ('  Rdoors', '{:.2f}'.format(Rdoor) + ';', file=op)
        tempEntity.Rdoors = '{:.2f}'.format(Rdoor)
#        print ('  airchange_per_hour', '{:.2f}'.format(airchange) + ';', file=op)
        tempEntity.airchange_per_hour = '{:.2f}'.format(airchange)
#        print ('  cooling_COP', '{:.1f}'.format(c_COP) + ';', file=op)
        tempEntity.cooling_COP = '{:.1f}'.format(c_COP)
#        print ('  air_temperature', '{:.2f}'.format(init_temp) + ';', file=op)
        tempEntity.air_temperature = '{:.2f}'.format(init_temp)
#        print ('  mass_temperature', '{:.2f}'.format(init_temp) + ';', file=op)
        tempEntity.mass_temperature = '{:.2f}'.format(init_temp)
#        print ('  total_thermal_mass_per_floor_area', '{:.3f}'.format(mass_floor) + ';', file=op)
        tempEntity.total_thermal_mass_per_floor_area = '{:.3f}'.format(mass_floor)
#        print ('  breaker_amps 1000;', file=op)
        tempEntity.breaker_amps = 1000
#        print ('  hvac_breaker_rating 1000;', file=op)
        tempEntity.hvac_breaker_rating = 1000
        heat_rand = np.random.uniform(0,1)
        cool_rand = np.random.uniform(0,1)
        if heat_rand <= self.rgnPenGasHeat[rgn-1]:
#            print ('  heating_system_type GAS;', file=op)
            tempEntity.heating_system_type = 'GAS'
            if cool_rand <= self.electric_cooling_percentage:
#                print ('  cooling_system_type ELECTRIC;', file=op)
                tempEntity.cooling_system_type = 'ELECTRIC'
            else:
#                print ('  cooling_system_type NONE;', file=op)
                tempEntity.cooling_system_type = 'NONE'
        elif heat_rand <= self.rgnPenGasHeat[rgn-1] + self.rgnPenHeatPump[rgn-1]:
#            print ('  heating_system_type HEAT_PUMP;', file=op);
            tempEntity.heating_system_type = 'HEAT_PUMP'
#            print ('  heating_COP', '{:.1f}'.format(h_COP) + ';', file=op);
            tempEntity.heating_COP = '{:.1f}'.format(h_COP)
#            print ('  cooling_system_type ELECTRIC;', file=op);
            tempEntity.cooling_system_type = 'ELECTRIC'
#            print ('  auxiliary_strategy DEADBAND;', file=op);
            tempEntity.auxiliary_strategy = 'DEADBAND'
#            print ('  auxiliary_system_type ELECTRIC;', file=op);
            tempEntity.auxiliary_system_type = 'ELECTRIC'
#            print ('  motor_model BASIC;', file=op);
            tempEntity.motor_model = 'BASIC'
#            print ('  motor_efficiency AVERAGE;', file=op);
            tempEntity.motor_efficiency = 'AVERAGE'
        elif floor_area * ceiling_height > 12000.0: # electric heat not allowed on large homes
#            print ('  heating_system_type GAS;', file=op)
            tempEntity.heating_system_type = 'GAS'
            if cool_rand <= self.electric_cooling_percentage:
#                print ('  cooling_system_type ELECTRIC;', file=op)
                tempEntity.cooling_system_type = 'ELECTRIC'
            else:
#                print ('  cooling_system_type NONE;', file=op)
                tempEntity.cooling_system_type = 'NONE'
        else:
#            print ('  heating_system_type RESISTANCE;', file=op)
            tempEntity.heating_system_type = 'RESISTANCE'
            if cool_rand <= self.electric_cooling_percentage:
#                print ('  cooling_system_type ELECTRIC;', file=op)
                tempEntity.cooling_system_type = 'ELECTRIC'
#                print ('  motor_model BASIC;', file=op);
                tempEntity.motor_model = 'BASIC'
#                print ('  motor_efficiency GOOD;', file=op);
                tempEntity.motor_efficiency = 'GOOD'
            else:
#                print ('  cooling_system_type NONE;', file=op)
                tempEntity.cooling_system_type = 'NONE'

        cooling_sch = np.ceil(self.coolingScheduleNumber * np.random.uniform (0, 1))
        heating_sch = np.ceil(self.heatingScheduleNumber * np.random.uniform (0, 1))
        # [Bin Prob, NightTimeAvgDiff, HighBinSetting, LowBinSetting]
        cooling_bin, heating_bin = self.selectSetpointBins (bldg, np.random.uniform (0,1))
        # randomly choose setpoints within bins, and then widen the separation to account for deadband
        cooling_set = cooling_bin[3] + np.random.uniform(0,1) * (cooling_bin[2] - cooling_bin[3]) + setpoint_offset
        heating_set = heating_bin[3] + np.random.uniform(0,1) * (heating_bin[2] - heating_bin[3]) - setpoint_offset
        cooling_diff = 2.0 * cooling_bin[1] * np.random.uniform(0,1)
        heating_diff = 2.0 * heating_bin[1] * np.random.uniform(0,1)
        cooling_scale = np.random.uniform(0.95, 1.05)
        heating_scale = np.random.uniform(0.95, 1.05)
        cooling_str = 'cooling{:.0f}*{:.4f}+{:.2f}'.format(cooling_sch, cooling_scale, cooling_diff)
        heating_str = 'heating{:.0f}*{:.4f}+{:.2f}'.format(heating_sch, heating_scale, heating_diff)
        # default heating and cooling setpoints are 70 and 75 degrees in GridLAB-D
        # we need more separation to assure no overlaps during transactive simulations
        if bIgnoreThermostatSchedule == True:
#          print ('  cooling_setpoint 80.0; // ', cooling_str + ';', file=op)
          tempEntity.cooling_setpoint = 80.0
#          print ('  heating_setpoint 60.0; // ', heating_str + ';', file=op)
          tempEntity.heating_setpoint = 60.0
        else:
#          print ('  cooling_setpoint {:s};'.format (cooling_str), file=op)
          tempEntity.cooling_setpoint = '{:s};'.format (cooling_str)
#          print ('  heating_setpoint {:s};'.format (heating_str), file=op)
          tempEntity.heating_setpoint = '{:s};'.format (heating_str)

        # heatgain fraction, Zpf, Ipf, Ppf, Z, I, P


# These ZIPload objects do not have names
        print ('  object ZIPload { // responsive', file=op)
        print ('    schedule_skew', '{:.0f}'.format(skew_value) + ';', file=op)
        print ('    base_power', 'responsive_loads*' + '{:.2f}'.format(resp_scalar) + ';', file=op)
        print ('    heatgain_fraction', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['heatgain_fraction']['value']) + ';', file=op)
        print ('    impedance_pf', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['impedance_pf']['value']) + ';', file=op)
        print ('    current_pf', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['current_pf']['value']) + ';', file=op)
        print ('    power_pf', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['power_pf']['value']) + ';', file=op)
        print ('    impedance_fraction', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['impedance_fraction']['value']) + ';', file=op)
        print ('    current_fraction', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['current_fraction']['value']) + ';', file=op)
        print ('    power_fraction', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['power_fraction']['value']) + ';', file=op)
        print ('  };', file=op)
        print ('  object ZIPload { // unresponsive', file=op)
        print ('    schedule_skew', '{:.0f}'.format(skew_value) + ';', file=op)
        print ('    base_power', 'unresponsive_loads*' + '{:.2f}'.format(unresp_scalar) + ';', file=op)
        print ('    heatgain_fraction', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['heatgain_fraction']['value']) + ';', file=op)
        print ('    impedance_pf', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['impedance_pf']['value']) + ';', file=op)
        print ('    current_pf', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['current_pf']['value']) + ';', file=op)
        print ('    power_pf', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['power_pf']['value']) + ';', file=op)
        print ('    impedance_fraction', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['impedance_fraction']['value']) + ';', file=op)
        print ('    current_fraction', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['current_fraction']['value']) + ';', file=op)
        print ('    power_fraction', '{:.2f}'.format(ConfigDict['ZIPload_parameters'][0]['power_fraction']['value']) + ';', file=op)
        print ('  };', file=op)



        if np.random.uniform (0, 1) <= self.water_heater_percentage:
          heat_element = 3.0 + 0.5 * np.random.randint (1,6);
          tank_set = 110 + 16 * np.random.uniform (0, 1);
          therm_dead = 4 + 4 * np.random.uniform (0, 1);
          tank_UA = 2 + 2 * np.random.uniform (0, 1);
          water_sch = np.ceil(self.waterHeaterScheduleNumber * np.random.uniform (0, 1))
          water_var = 0.95 + np.random.uniform (0, 1) * 0.1 # +/-5% variability
          wh_demand_type = 'large_'
          sizeIncr = np.random.randint (0,3)  # MATLAB randi(imax) returns 1..imax
          sizeProb = np.random.uniform (0, 1);
          if sizeProb <= self.rgnWHSize[rgn-1][0]:
              wh_size = 20 + sizeIncr * 5
              wh_demand_type = 'small_'
          elif sizeProb <= (self.rgnWHSize[rgn-1][0] + self.rgnWHSize[rgn-1][1]):
              wh_size = 30 + sizeIncr * 10
              if floor_area < 2000.0:
                  wh_demand_type = 'small_'
          else:
              if floor_area < 2000.0:
                  wh_size = 30 + sizeIncr * 10
              else:
                  wh_size = 50 + sizeIncr * 10
          wh_demand_str = wh_demand_type + '{:.0f}'.format(water_sch) + '*' + '{:.2f}'.format(water_var)
          wh_skew_value = 3 * self.residential_skew_std * np.random.randn ()
          if wh_skew_value < -6 * self.residential_skew_max:
              wh_skew_value = -6 * self.residential_skew_max
          elif wh_skew_value > 6 * self.residential_skew_max:
              wh_skew_value = 6 * self.residential_skew_max
#          print ('  object waterheater {', file=op)
          tempEntity2 = Entity(whname, self.objects['waterheater'])
          #print ('    name', whname + ';', file=op)
          tempEntity2.name = whname
          #print ('    schedule_skew','{:.0f}'.format(wh_skew_value) + ';', file=op)
          tempEntity2.schedule_skew = '{:.0f}'.format(wh_skew_value)
          #print ('    heating_element_capacity','{:.1f}'.format(heat_element), 'kW;', file=op)
          tempEntity2.heating_element_capacity = '{:.1f}'.format(heat_element), 'kW'
          #print ('    thermostat_deadband','{:.1f}'.format(therm_dead) + ';', file=op)
          tempEntity2.thermostat_deadband = '{:.1f}'.format(therm_dead)
          #print ('    location INSIDE;', file=op)
          tempEntity2.location = 'INSIDE'
          #print ('    tank_diameter 1.5;', file=op)
          tempEntity2.tank_diameter = 1.5
          #print ('    tank_UA','{:.1f}'.format(tank_UA) + ';', file=op)
          tempEntity2.tank_UA = '{:.1f}'.format(tank_UA)
          #          print ('    water_demand', wh_demand_str + ';', file=op)
          tempEntity2.water_demand = wh_demand_str
          #          print ('    tank_volume','{:.0f}'.format(wh_size) + ';', file=op)
          tempEntity2.tank_volume = '{:.0f}'.format(wh_size)
          if np.random.uniform (0, 1) <= self.water_heater_participation:
#              print ('    waterheater_model MULTILAYER;', file=op)
              tempEntity2.waterheater_model = 'MULTILAYER'
#              print ('    discrete_step_size 60.0;', file=op)
              tempEntity2.discrete_step_size = 60.0
#              print ('    lower_tank_setpoint','{:.1f}'.format(tank_set - 5.0) + ';', file=op)
              tempEntity2.lower_tank_setpoint = '{:.1f}'.format(tank_set - 5.0)
#              print ('    upper_tank_setpoint','{:.1f}'.format(tank_set + 5.0) + ';', file=op)
              tempEntity2.upper_tank_setpoint = '{:.1f}'.format(tank_set + 5.0)
#              print ('    T_mixing_valve','{:.1f}'.format(tank_set) + ';', file=op)
              tempEntity2.T_mixing_valve = '{:.1f}'.format(tank_set)
          else:
#              print ('    tank_setpoint','{:.1f}'.format(tank_set) + ';', file=op)
              tempEntity2.tank_setpoint = '{:.1f}'.format(tank_set)

# How are inline objects going to be handled
          if self.metrics_interval > 0:
              print ('    object metrics_collector {', file=op)
              print ('      interval', str(self.metrics_interval) + ';', file=op)
              print ('    };', file=op)



#          print ('  };', file=op)
        self.entities[tempEntity2.name] = tempEntity2

#How to handle inline objects
        if self.metrics_interval > 0:
            print ('  object metrics_collector {', file=op)
            print ('    interval', str(self.metrics_interval) + ';', file=op)
            print ('  };', file=op)
        print ('}', file=op)
        # if PV is allowed, then only single-family houses can buy it, and only the single-family houses with PV will also consider storage
        # if PV is not allowed, then any single-family house may consider storage (if allowed)
        # apartments and mobile homes may always consider storage, but not PV
        bConsiderStorage = True
        if bldg == 0:  # Single-family homes
            if self.solar_percentage > 0.0:
                bConsiderStorage = False
            if np.random.uniform (0, 1) <= self.solar_percentage:  # some single-family houses have PV
                bConsiderStorage = True
                panel_area = 0.1 * floor_area
                if panel_area < 162:
                    panel_area = 162
                elif panel_area > 270:
                    panel_area = 270
                inv_power = self.solar['inv_undersizing'] * (panel_area/10.7642) * self.solar['rated_insolation'] * self.solar['array_efficiency']
                self.solar_count += 1
                self.solar_kw += 0.001 * inv_power


                #print ('object {:s} {{'.format (meter_class), file=op)
                tempEntity2 = Entity(sol_m_name, self.objects['{:s} {{'.format (meter_class)])
                #print ('  name', sol_m_name + ';', file=op)
                tempEntity2.name = sol_m_name
                #print ('  parent', mtrname + ';', file=op)
                tempEntity2.parent = mtrname
                #print ('  phases', phs + ';', file=op)
                tempEntity2.phases = phs
                #print ('  nominal_voltage ' + str(vnom) + ';', file=op)
                tempEntity2.nominal_voltage = str(vnom)
                #print ('  object inverter {', file=op)
                tempEntity3 = Entity(sol_i_name, self.objects['inverter'])
                #print ('    name', sol_i_name + ';', file=op)
                tempEntity3.name = sol_i_name
                #print ('    phases', phs + ';', file=op)
                tempEntity3.phases = phs
                #print ('    generator_status ONLINE;', file=op)
                tempEntity3.generator_status = 'ONLINE'
                #print ('    inverter_type FOUR_QUADRANT;', file=op)
                tempEntity3.inverter_type = 'FOUR_QUADRANT'
                #print ('    inverter_efficiency 1;', file=op)
                tempEntity3.inverter_efficiency = 1
                #print ('    rated_power','{:.0f}'.format(inv_power) + ';', file=op)
                tempEntity3.rated_power = '{:.0f}'.format(inv_power)
                #print ('    power_factor 1.0;', file=op)
                tempEntity3.power_factor = 1.0


                write_solar_inv_settings (op)


                #print ('    object solar {', file=op)
                tempEntity4 = Entity(solname,self.objects['solar'])
                #print ('      name', solname + ';', file=op)
                tempEntity4.name = solname
                #print ('      panel_type SINGLE_CRYSTAL_SILICON;', file=op)
                tempEntity4.panel_type = 'SINGLE_CRYSTAL_SILICON'
                #print ('      efficiency','{:.2f}'.format(ConfigDict['solar']['array_efficiency']['value']) + ';', file=op)
                tempEntity4.efficiency = '{:.2f}'.format(self.solar['array_efficiency'])
                #print ('      area','{:.2f}'.format(panel_area) + ';', file=op)
                tempEntity4.area = '{:.2f}'.format(panel_area)
                #print ('    };', file=op)
                self.entities[tempEntity4.name] = tempEntity4
                if self.metrics_interval > 0:
                    print ('    object metrics_collector {', file=op)
                    #print ('      interval', str(metrics_interval) + ';', file=op)
                    print ('      interval', str(ConfigDict['metrics_interval']['value']) + ';', file=op)
                    print ('    };', file=op)
                print ('  };', file=op)
                print ('}', file=op)
        if bConsiderStorage:
            if np.random.uniform (0, 1) <= ConfigDict['storage_percentage']['value']:
                ConfigDict['battery_count']['value'] += 1
                print ('object {:s} {{'.format (meter_class), file=op)
#                print ('object triplex_meter {', file=op)
                print ('  name', bat_m_name + ';', file=op)
                print ('  parent', mtrname + ';', file=op)
                print ('  phases', phs + ';', file=op)
                print ('  nominal_voltage ' + str(vnom) + ';', file=op)
                print ('  object inverter {', file=op)
                print ('    name', bat_i_name + ';', file=op)
                print ('    phases', phs + ';', file=op)
                print ('    generator_status ONLINE;', file=op)
                print ('    generator_mode CONSTANT_PQ;', file=op)
                print ('    inverter_type FOUR_QUADRANT;', file=op)
                print ('    four_quadrant_control_mode', ConfigDict['storage_inv_mode']['value'] + ';', file=op)
                print ('    V_base ${INV_VBASE};', file=op)
                print ('    charge_lockout_time 1;', file=op)
                print ('    discharge_lockout_time 1;', file=op)
                print ('    rated_power 5000;', file=op)
                print ('    max_charge_rate 5000;', file=op)
                print ('    max_discharge_rate 5000;', file=op)
                print ('    sense_object', mtrname + ';', file=op)
                print ('    charge_on_threshold -100;', file=op)
                print ('    charge_off_threshold 0;', file=op)
                print ('    discharge_off_threshold 2000;', file=op)
                print ('    discharge_on_threshold 3000;', file=op)
                print ('    inverter_efficiency 0.97;', file=op)
                print ('    power_factor 1.0;', file=op)
                print ('    object battery { // Tesla Powerwall 2', file=op)
                print ('      name', batname + ';', file=op)
                print ('      use_internal_battery_model true;', file=op)
                print ('      battery_type LI_ION;', file=op)
                print ('      nominal_voltage 480;', file=op)
                print ('      battery_capacity 13500;', file=op)
                print ('      round_trip_efficiency 0.86;', file=op)
                print ('      state_of_charge 0.50;', file=op)
                print ('    };', file=op)
                if ConfigDict['metrics_interval']['value'] > 0:
                    print ('    object metrics_collector {', file=op)
                    print ('      interval', str(ConfigDict['metrics_interval']['value']) + ';', file=op)
                    print ('    };', file=op)
                print ('  };', file=op)
                print ('}', file=op)

