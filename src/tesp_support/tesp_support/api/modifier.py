# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: glm_modifier.py

import os

from .data import entities_path
from .entity import assign_defaults
from .model import GLModel


class GLMModifier:
    # instances of entity values
    # objects = [batteries, meters, capacitors, fuses, houses, lines, loads,
    #            secondary_transformers, solar_pvs, substation_transformers,
    #            switches, triplex_lines, triplex_loads, zip_loads, recorder]

    def __init__(self):
        self.model = GLModel()
        assign_defaults(self, os.path.join(entities_path, 'feeder_defaults.json'))
        return

    # Modify GridLabD module entities
    def get_module(self, gld_type):
        return self.model.module_entities[gld_type]

    def get_module_named_instance(self, gld_type):
        return self.get_module(gld_type).instance[gld_type]

    def get_module_names(self, gld_type):
        return list(self.get_module(gld_type).instance.keys())

    def add_module(self, gld_type, params):
        return self.get_module(gld_type).set_instance(gld_type, params)

    def del_module(self, gld_type, name):
        self.get_module(gld_type).del_instance(name)
        # delete all object in the module
        # for obj in self.model.module_entities:
        #     myObj = self.model.module_entities[obj]
        #     myArr = []
        #     if myObj.find_item('parent'):
        #         for myName in myObj.instance:
        #             instance = myObj.instance[myName]
        #             if 'parent' in instance.keys():
        #                 if instance['parent'] == name:
        #                     myArr.append(myName)
        #     for myName in myArr:
        #         myObj.del_instance(myName)

    def add_module_attr(self, gld_type, name, item_name, item_value):
        return self.get_module(gld_type).set_item(name, item_name, item_value)

    def del_module_attr(self, gld_type, name, item_name):
        self.get_module(gld_type).del_item(name, item_name)

    # Modify GridLabD objects entities
    def get_object(self, gld_type):
        return self.model.object_entities[gld_type]

    def get_object_named_instance(self, gld_type, name):
        return self.get_object(gld_type).instance[name]
        
    def get_object_names(self, gld_type):
        return list(self.get_object(gld_type).instance.keys())

    def add_object(self, gld_type, name, params):
        # TODO make sure that module exist
        return self.get_object(gld_type).set_instance(name, params)

    def del_object(self, gld_type, name):
        self.get_object(gld_type).del_instance(name)
        for obj in self.model.object_entities:
            myObj = self.model.object_entities[obj]
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

    # Read and Write .GLM files
    def read_model(self, filepath):
        self.model.read(filepath)
        return True

    def write_model(self, filepath):
        self.model.write(filepath)
        return True

    # normal objects
    def resize(self):
        return True

    # custom objects
    def resize_secondary_transformers(self):
        return True

    def resize_substation_transformer(self):
        return True

    def set_simulation_times(self):
        return True


def test1():
    from .data import tesp_test

    testMod = GLMModifier()
    testMod.model.read(tesp_test + "api/dsot_in.glm")
    testMod.write_model(tesp_test + "api/dsot_out.glm")

    testMod = GLMModifier()
    testMod.model.read(tesp_test + "api/testing.glm")
    testMod.write_model(tesp_test + "api/testing_out.glm")

    testMod = GLMModifier()
    f = "../../../../examples/capabilities/loadshed/loadshed.glm"
    testMod.model.read(f)
    testMod.write_model(tesp_test + "api/loadshed_out.glm")


def test2():
    from .data import tesp_test

    testMod = GLMModifier()
    testMod.model.readBackboneModel("GLD_three_phase_house.glm")
    loads = testMod.get_object('load')
    meter_counter = 0
    house_counter = 0
    house_meter_counter = 0
    for obj_id in loads.instance:
        # add meter for this load
        meter_counter = meter_counter + 1
        meter_name = 'meter_' + str(meter_counter)
        meter = testMod.add_object('meter', meter_name, [])
        meter['parent'] = obj_id
        # how much power is going to be needed
        # while kva < total_kva:
        house_meter_counter = house_meter_counter + 1
        # add parent meter for houses to follow
        house_meter_name = 'house_meter_' + str(house_meter_counter)
        meter = testMod.add_object('meter', house_meter_name, [])
        meter['parent'] = meter_name
        # add house
        house_counter = house_counter + 1
        house_name = 'house_' + str(house_counter)
        house = testMod.add_object('house', house_name, [])
        house['parent'] = house_meter_name
    testMod.write_model(tesp_test + "api/modifier_test2.glm")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    test1()
    test2()
