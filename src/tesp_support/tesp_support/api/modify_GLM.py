# Copyright (C) 2019-2023 Battelle Memorial Institute
# file: glm_modifier.py
import math

import numpy as np

from .data import feeder_entities_path
from .entity import assign_defaults
from .model_GLM import GLModel
from .parse_helpers import parse_kva


class Defaults:
    pass


class GLMModifier:
    # instances of entity values

    def __init__(self):
        self.model = GLModel()
        self.glm = self.model.glm
        self.defaults = Defaults
        self.extra_billing_meters = set()
        assign_defaults(self.defaults, feeder_entities_path)

    # get/add/del module calls to modify GridLabD module entities
    def add_module(self, gld_type, params):
        return self.model.module_entities[gld_type].set_instance(gld_type, params)

    def del_module(self, gld_type, name):
        self.model.module_entities[gld_type].del_instance(name)
        # delete all object in the module
        # for obj in self.model.module_entities:
        #     myObj = self.model.module_entities[obj]
        #     myArr = []
        #     if myObj.find_item('parent'):
        #         for myName in myObj.instances:
        #             instance = myObj.instances[myName]
        #             if 'parent' in instance.keys():
        #                 if instance['parent'] == name:
        #                     myArr.append(myName)
        #     for myName in myArr:
        #         myObj.del_instance(myName)

    def add_module_attr(self, gld_type, name, item_name, item_value):
        return self.model.module_entities[gld_type].set_item(name, item_name, item_value)

    def del_module_attr(self, gld_type, name, item_name):
        self.model.module_entities[gld_type].del_item(name, item_name)

    def add_object(self, gld_type, name, params):
        # TODO make sure that module exist (i.e. auction object needs market module)
        return self.model.add_object(gld_type, name, params)

    def rename_object(self, gld_type, old_name, new_name):
        object_entity = self.model.object_entities[gld_type]
        if object_entity:
            if object_entity.instances[old_name]:
                model_object = self.model.model[gld_type]
                for object_name in self.model.object_entities:
                    _instances = self.model.object_entities[object_name].instances
                    for _instance_name, _instance in _instances.items():
                        for _attr, _val in _instance.items():
                            if _val == old_name:
                                _instances[_instance_name][_attr] = new_name
                if new_name != old_name:
                    object_entity.instances[new_name] = object_entity.instances[old_name]
                    del object_entity.instances[old_name]
                    model_object[new_name] = model_object[old_name]
                    del model_object[old_name]
                return True
        return False

    def del_object(self, gld_type, name):
        self.model.object_entities[gld_type].del_instance(name)
        for obj in self.model.object_entities:
            myObj = self.model.object_entities[obj]
            myArr = []
            if myObj.find_item('parent'):
                for myName in myObj.instances:
                    instance = myObj.instances[myName]
                    if 'parent' in instance.keys():
                        if instance['parent'] == name:
                            myArr.append(myName)
            # TODO from-to relations
            for myName in myArr:
                self.model.del_object(gld_type, name)
                myObj.del_instance(myName)

    def replace_object_type(self):
        # TODO replace node with node or edge with edge classes
        pass

    def add_object_attr(self, gld_type, name, item_name, item_value):
        return self.model.object_entities[gld_type].set_item(name, item_name, item_value)

    def del_object_attr(self, gld_type, name, item_name):
        self.model.object_entities[gld_type].del_item(name, item_name)

    # Read and Write .GLM files
    def read_model(self, filepath):
        return self.model.read(filepath)

    def write_model(self, filepath):
        return self.model.write(filepath)

    # normal objects that use feeder system 'defaults'
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

    def find_1phase_xfmr_kva(self, kva):
        """Select a standard 1-phase transformer size, with some margin

        Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            float: the kva size, or 0 if none found
        """
        kva *= self.defaults.xfmrMargin
        for row in self.defaults.single_phase:
            if row[0] >= kva:
                return row[0]
        n500 = int((kva + 250.0) / 500.0)
        return 500.0 * n500

    def find_1phase_xfmr(self, kva):
        """Select a standard 1-phase transformer size, with data

        Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
        """
        for row in self.defaults.single_phase:
            if row[0] >= kva:
                return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
        return self.find_1phase_xfmr_kva(kva)

    def find_3phase_xfmr_kva(self, kva):
        """Select a standard 3-phase transformer size, with some margin

        Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500,
        2000, 2500, 3750, 5000, 7500 or 10000 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            float: the kva size, or 0 if none found
        """
        kva *= self.defaults.xfmrMargin
        for row in self.defaults.three_phase:
            if row[0] >= kva:
                return row[0]
        n10 = int((kva + 5000.0) / 10000.0)
        return 500.0 * n10

    def find_3phase_xfmr(self, kva):
        """Select a standard 3-phase transformer size, with data

        Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500,
        2000, 2500, 3750, 5000, 7500 or 10000 kVA

        Args:
            kva (float): the minimum transformer rating

        Returns:
            [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
        """
        for row in self.defaults.three_phase:
            if row[0] >= kva:
                return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
        return self.find_3phase_xfmr_kva(kva)

    def find_fuse_limit(self, amps):
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
        amps *= self.defaults.fuseMargin
        for row in self.defaults.standard_fuses:
            if row >= amps:
                return row
        for row in self.defaults.standard_reclosers:
            if row >= amps:
                return row
        for row in self.defaults.standard_breakers:
            if row >= amps:
                return row
        return 999999

    def randomize_residential_skew(self):
        return self.randomize_skew(self.defaults.residential_skew_std, self.defaults.residential_skew_max)

    def randomize_commercial_skew(self):
        return self.randomize_skew(self.defaults.residential_skew_std, self.defaults.residential_skew_max)

    def randomize_skew(self, value, skew_max):
        sk = value * np.random.randn()
        if sk < -skew_max:
            sk = -skew_max
        elif sk > skew_max:
            sk = skew_max
        return sk

    # custom objects
    def add_tariff(self, params):
        """Writes tariff information to billing meters

        Args:
            params:
        """
        params["bill_mode"] = self.defaults.bill_mode
        params["price"] = self.defaults.kwh_price
        params["monthly_fee"] = self.defaults.monthly_fee
        params["bill_day"] = "1"
        if 'TIERED' in self.defaults.bill_mode:
            if self.defaults.tier1_energy > 0.0:
                params["first_tier_energy"] = self.defaults.tier1_energy
                params["first_tier_price"] = self.defaults.tier1_price
            if self.defaults.tier2_energy > 0.0:
                params["second_tier_energy"] = self.defaults.tier2_energy
                params["second_tier_price"] = self.defaults.tier2_price
            if self.defaults.tier3_energy > 0.0:
                params["third_tier_energy"] = self.defaults.tier3_energy
                params["third_tier_price"] = self.defaults.tier3_price

    def add_collector(self, parent: str, metric: str):
        if self.defaults.metrics_interval > 0 and metric in self.defaults.metrics:
            params = {"parent": parent,
                      "interval": str(self.defaults.metrics_interval)}
            self.add_object("metrics_collector", "mc_" + parent, params)

    def add_recorder(self, parent: str, property_name: str, file: str):
        if self.defaults.metrics_interval > 0:
            params = {"parent": parent,
                      "property": property_name,
                      "file": file,
                      "interval": str(self.defaults.metrics_interval)}
            self.add_object("recorder", property_name, params)

    def add_config_class(self, t: str):
        """Write a GridLAB-D configuration (i.e., not a link or node) class

        Args:
            t (str): the GridLAB-D class
        """
        try:
            entity = self.glm.__getattribute__(t)
        except:
            return
        for e_name, e_object in entity.items():
            params = dict()
            for p in e_object:
                if ':' in str(e_object[p]):
                    params[p] = self.glm.hash[e_object[p]]
                else:
                    params[p] = e_object[p]
            self.glm.add_object(t, e_name, params)

    def add_link_class(self, t: str, seg_loads: dict, want_metrics=False):
        """Write a GridLAB-D link (i.e., edge) class

        Args:
            t (str): the GridLAB-D class
            seg_loads (dict) : a dictionary of downstream loads for each link
            want_metrics (bool): true or false

        """
        try:
            entity = self.glm.__getattribute__(t)
        except:
            return
        for e_name, e_object in entity.items():
            params = dict()
            if e_name in seg_loads:
                # print('// downstream', '{:.2f}'.format(seg_loads[o][0]), 'kva on', seg_loads[o][1])
                for p in e_object:
                    if ':' in e_object[p]:
                        params[p] = self.glm.hash[e_object[p]]
                    else:
                        if p == "from" or p == "to" or p == "parent":
                            params[p] = self.glm.gld_strict_name(e_object[p])
                        else:
                            params[p] = e_object[p]
            self.glm.add_object(t, e_name, params)

            if want_metrics:
                self.glm.add_collector(e_name, t)

    def add_voltage_class(self, t: str, v_prim: float, v_ll: float, secmtrnode: dict):
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
        try:
            entity = self.glm.__getattribute__(t)
        except:
            return
        for e_name, e_object in entity.items():
            #            if 'load_class' in model[t][o]:
            #                if model[t][o]['load_class'] == 'C':
            #                    continue
            phs = e_object['phases']
            vnom = v_prim
            if 'bustype' in e_object:
                if e_object['bustype'] == 'SWING':
                    self.add_substation(e_name, phs, vnom, v_ll)
            parent = ''
            prefix = ''
            if str.find(phs, 'S') >= 0:
                bHadS = True
            else:
                bHadS = False
            if str.find(e_name, '_tn_') >= 0 or str.find(e_name, '_tm_') >= 0:
                vnom = 120.0
            if e_name in secmtrnode:
                vnom = secmtrnode[e_name][2]
                phs = secmtrnode[e_name][1]
            if 'parent' in e_object:
                parent = e_object['parent']
                if parent in secmtrnode:
                    vnom = secmtrnode[parent][2]
                    phs = secmtrnode[parent][1]
            if str.find(phs, 'S') >= 0:
                bHaveS = True
            else:
                bHaveS = False
            if bHaveS and not bHadS:
                prefix = 'triplex_'
            params = {}
            if len(parent) > 0:
                params["parent"] = parent
            if 'groupid' in e_object:
                params["groupid"] = e_object['groupid']
            if 'bustype' in e_object:  # already moved the SWING bus behind substation transformer
                if e_object['bustype'] != 'SWING':
                    params["bustype"] = e_object['bustype']
            params["phases"] = phs
            params["nominal_voltage"] = str(vnom)
            if 'load_class' in e_object:
                params["load_class"] = e_object['load_class']
            if 'constant_power_A' in e_object:
                if bHaveS:
                    params["power_1"] = e_object['constant_power_A']
                else:
                    params["constant_power_A"] = e_object['constant_power_A']
            if 'constant_power_B' in e_object:
                if bHaveS:
                    params["power_1"] = e_object['constant_power_B']
                else:
                    params["constant_power_B"] = e_object['constant_power_B']
            if 'constant_power_C' in e_object:
                if bHaveS:
                    params["power_1"] = e_object['constant_power_C']
                else:
                    params["constant_power_C"] = e_object['constant_power_C']
            if 'power_1' in e_object:
                params["power_1"] = e_object['power_1']
            if 'power_2' in e_object:
                params["power_2"] = e_object['power_2']
            if 'power_12' in e_object:
                params["power_12"] = e_object['power_12']
            vstarta = str(vnom) + '+0.0j'
            vstartb = format(-0.5 * vnom, '.2f') + format(-0.866025 * vnom, '.2f') + 'j'
            vstartc = format(-0.5 * vnom, '.2f') + '+' + format(0.866025 * vnom, '.2f') + 'j'
            if 'voltage_A' in e_object:
                if bHaveS:
                    params["voltage_1"] = vstarta
                    params["voltage_2"] = vstarta
                else:
                    params["voltage_A"] = vstarta
            if 'voltage_B' in e_object:
                if bHaveS:
                    params["voltage_1"] = vstartb
                    params["voltage_2"] = vstartb
                else:
                    params["voltage_B"] = vstartb
            if 'voltage_C' in e_object:
                if bHaveS:
                    params["voltage_1"] = vstartc
                    params["voltage_2"] = vstartc
                else:
                    params["voltage_C"] = vstartc
            if 'power_1' in e_object:
                params["power_1"] = e_object['power_1']
            if 'power_2' in e_object:
                params["power_2"] = e_object['power_2']
            if 'voltage_1' in e_object:
                if str.find(phs, 'A') >= 0:
                    params["voltage_1"] = vstarta
                    params["voltage_2"] = vstarta
                if str.find(phs, 'B') >= 0:
                    params["voltage_1"] = vstartb
                    params["voltage_2"] = vstartb
                if str.find(phs, 'C') >= 0:
                    params["voltage_1"] = vstartc
                    params["voltage_2"] = vstartc
            if e_name in self.extra_billing_meters:
                self.add_tariff(params)
                self.add_collector(e_name, prefix + t)
            self.add_object(prefix + t, e_name, params)

    def add_xfmr_config(self, key: str, phs: str, kvat: float, v_nom: float, v_sec: float, install_type: str,
                        vprimll: float, vprimln: float):
        """Write a transformer_configuration

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
        name = self.defaults.name_prefix + key
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

    def add_local_triplex_configurations(self):
        """Adds local triplex configurations"""
        params = dict()
        for row in self.defaults.triplex_conductors:
            name = self.defaults.name_prefix + row[0]
            params["resistance"] = row[1]
            params["geometric_mean_radius"] = row[2]
            rating_str = str(row[2])
            params["rating.summer.continuous"] = rating_str
            params["rating.summer.emergency"] = rating_str
            params["rating.winter.continuous"] = rating_str
            params["rating.winter.emergency"] = rating_str
            self.glm.add_object("triplex_line_conductor", name, params)
        for row in self.defaults.triplex_configurations:
            params = dict()
            name = self.defaults.name_prefix + row[0]
            params["conductor_1"] = self.defaults.name_prefix + row[0]
            params["conductor_2"] = self.defaults.name_prefix + row[1]
            params["conductor_N"] = self.defaults.name_prefix + row[2]
            params["insulation_thickness"] = str(row[3])
            params["diameter"] = str(row[4])
            self.glm.add_object("triplex_line_configuration", name, params)


    def resize(self):
        return True

    def resize_secondary_transformers(self):
        return True

    def resize_substation_transformer(self):
        return True

    def set_simulation_times(self):
        return True

    def add_substation(self, name: str, phs: str, v_ll: float):
        """Write the substation swing node, transformer, metrics collector and
        fncs_msg object

        Args:
            name (str): node name of the primary (not transmission) substation bus
            phs (str): primary phasing in the substation
            v_ll (float): feeder primary line-to-line voltage
        """
        # if this feeder will be combined with others, need USE_FNCS to appear first as a marker for the substation
        if len(self.defaults.case_name) > 0:
            if self.defaults.message_broker == "fncs_msg":
                def_params = dict()
                t_name = "gld" + self.defaults.substation_name
                def_params["parent"] = "network_node"
                def_params["configure"] = self.defaults.case_name + '_gridlabd.txt'
                def_params["option"] = "transport:hostname localhost, port " + str(self.defaults.port)
                def_params["aggregate_subscriptions"] = "true"
                def_params["aggregate_publications"] = "true"
                self.glm.add_object("fncs_msg", t_name, def_params)
            if self.defaults.message_broker == "helics_msg":
                def_params = dict()
                t_name = "gld" + self.defaults.substation_name
                def_params["configure"] = self.defaults.case_name + '.json'
                self.glm.add_object("helics_msg", t_name, def_params)

        name = 'substation_xfmr_config'
        params = {"connect_type": 'WYE_WYE',
                  "install_type": 'PADMOUNT',
                  "primary_voltage": '{:.2f}'.format(self.defaults.transmissionVoltage),
                  "secondary_voltage": '{:.2f}'.format(v_ll),
                  "power_rating": '{:.2f}'.format(self.defaults.transmissionXfmrMVAbase * 1000.0),
                  "resistance": '{:.2f}'.format(0.01 * self.defaults.transmissionXfmrRpct),
                  "reactance": '{:.2f}'.format(0.01 * self.defaults.transmissionXfmrXpct),
                  "shunt_resistance": '{:.2f}'.format(100.0 / self.defaults.transmissionXfmrNLLpct),
                  "shunt_reactance": '{:.2f}'.format(100.0 / self.defaults.transmissionXfmrImagpct)}
        self.glm.add_object("transformer_configuration", name, params)

        name = "substation_transformer"
        params = {"from": "network_node",
                  "to": name, "phases": phs,
                  "configuration": "substation_xfmr_config"}
        self.glm.add_object("transformer", name, params)

        vsrcln = self.defaults.transmissionVoltage / math.sqrt(3.0)
        name = "network_node"
        params = {"groupid": self.defaults.base_feeder_name,
                  "bustype": 'SWING',
                  "nominal_voltage": '{:.2f}'.format(vsrcln),
                  "positive_sequence_voltage": '{:.2f}'.format(vsrcln),
                  "base_power": '{:.2f}'.format(self.defaults.transmissionXfmrMVAbase * 1000000.0),
                  "power_convergence_value": "100.0",
                  "phases": phs}
        self.glm.add_object("substation", name, params)
        self.glm.add_collector(name, "meter")
        self.glm.add_recorder(name, "distribution_power_A", "sub_power.csv")



def _test1():
    from .data import tesp_test

    testMod = GLMModifier()
    testMod.model.read(tesp_test + "api/dsot_in.glm")
    testMod.write_model(tesp_test + "api/dsot_out.glm")
    # Takes some time to draw the layout
    # testMod.model.plot_model()

    testMod = GLMModifier()
    testMod.model.read(tesp_test + "api/testing.glm")
    testMod.write_model(tesp_test + "api/testing_out.glm")
    testMod.model.plot_model()

    testMod = GLMModifier()
    f = "../../../../examples/capabilities/loadshed/loadshed.glm"
    testMod.model.read(f)
    testMod.write_model(tesp_test + "api/loadshed_out.glm")
    testMod.model.plot_model()


def _test2():
    from .data import tesp_test

    # feeder = "GLD_three_phase_house.glm"
    feeder = "IEEE-123.glm"
    # feeder = "R3-12.47-3.glm"
    testMod = GLMModifier()
    glm, success = testMod.model.readBackboneModel(feeder)
    if not success:
        exit()

    testMod.rename_object("node", "n3", "mynode3")
    # testMod.model.plot_model()
    meter_counter = 0
    house_counter = 0
    house_meter_counter = 0
    for key, value in glm.load.items():
        # add meter for this load
        meter_counter = meter_counter + 1
        meter_name = 'meter_' + str(meter_counter)
        meter = testMod.add_object('meter', meter_name, {'parent': key})
        # how much power is going to be needed
        # while kva < total_kva:
        house_meter_counter = house_meter_counter + 1
        # add parent meter for houses to follow
        house_meter_name = 'house_meter_' + str(house_meter_counter)
        meter = testMod.add_object('meter', house_meter_name, {'parent': meter_name})
        # add house
        house_counter = house_counter + 1
        house_name = 'house_' + str(house_counter)
        house = testMod.add_object('house', house_name, [])
        house['parent'] = house_meter_name
        meter = testMod.add_object('transformer', 'f2_transformer', {'from': 'meter_1', 'to': 'meter_2'})
        meter = testMod.add_object('meter', 'meter_2', {'parent': 'meter_1'})

    testMod.model.plot_model()
    testMod.write_model(tesp_test + "api/modifier_test2.glm")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    _test1()
    _test2()
