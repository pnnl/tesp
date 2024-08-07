# Copyright (C) 2019-2023 Battelle Memorial Institute
# file: glm_modifier.py
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

    def identify_seg_loads(self):
        swing_node = ''
        G = self.model.draw_network()
        for n1, data in G.nodes(data=True):
            if 'nclass' in data:
                if 'bustype' in data['ndata']:
                    if data['ndata']['bustype'] == 'SWING':
                        swing_node = n1
                        return swing_node
        seg_loads = {}  # [name][kva, phases]
        total_kva = 0.0
        for n1, data in G.nodes(data=True):
            if 'ndata' in data:
                kva = self.accumulate_load_kva(data['ndata'])
                # need to account for large-building loads added through transformer connections
                if kva > 0:
                    total_kva += kva
                    nodes = self.glm.nx.shortest_path(G, n1, swing_node)
                    edges = zip(nodes[0:], nodes[1:])
                    for u, v in edges:
                        eclass = G[u][v]['eclass']
                        if self.model.is_edge_class(eclass):
                            ename = G[u][v]['ename']
                            if ename not in seg_loads:
                                seg_loads[ename] = [0.0, '']
                            seg_loads[ename][0] += kva
                            seg_loads[ename][1] = self.union_of_phases(seg_loads[ename][1], data['ndata']['phases'])
        # sub_graphs = self.glm.nx.connected_components(G)
        # print('  swing node', swing_node, 'with', len(list(sub_graphs)), 'subgraphs and',
        #       '{:.2f}'.format(total_kva), 'total kva')
        return seg_loads






    def resize(self):
        return True

    def resize_secondary_transformers(self):
        return True

    def resize_substation_transformer(self):
        return True

    def set_simulation_times(self):
        return True


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
