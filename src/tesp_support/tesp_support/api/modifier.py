# Copyright (C) 2019-2023 Battelle Memorial Institute
# file: glm_modifier.py

from .data import feeder_entities_path
from .entity import assign_defaults
from .model import GLModel

class GLMModifier:
    # instances of entity values

    def __init__(self):
        self.model = GLModel()
        assign_defaults(self, feeder_entities_path)
        return

    # get/add/del module calls to modify GridLabD module entities
    def get_module(self, gld_type):
        return self.model.module_entities[gld_type]

    def get_module_named_instance(self, gld_type):
        return self.get_module(gld_type).instances[gld_type]

    def get_module_names(self, gld_type):
        return list(self.get_module(gld_type).instances.keys())

    def add_module(self, gld_type, params):
        return self.get_module(gld_type).set_instance(gld_type, params)

    def del_module(self, gld_type, name):
        self.get_module(gld_type).del_instance(name)
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
        return self.get_module(gld_type).set_item(name, item_name, item_value)

    def del_module_attr(self, gld_type, name, item_name):
        self.get_module(gld_type).del_item(name, item_name)

    # get/add/del object calls to modify GridLabD objects entities
    def get_object(self, gld_type):
        return self.model.object_entities[gld_type]

    def get_object_named_instance(self, gld_type, name):
        return self.get_object(gld_type).instances[name]
        
    def get_object_names(self, gld_type):
        return list(self.get_object(gld_type).instances.keys())

    def add_object(self, gld_type, name, params):
        # TODO make sure that module exist (i.e. auction object needs market module)
        return self.model.add_object(gld_type, name, params)

    def rename_object(self, gld_type, old_name, new_name):
        object_entity = self.get_object(gld_type)
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
        self.get_object(gld_type).del_instance(name)
        for obj in self.model.object_entities:
            myObj = self.model.object_entities[obj]
            myArr = []
            if myObj.find_item('parent'):
                for myName in myObj.instances:
                    instance = myObj.instances[myName]
                    if 'parent' in instance.keys():
                        if instance['parent'] == name:
                            myArr.append(myName)
            for myName in myArr:
                self.model.del_object(gld_type, name)
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
    if not testMod.model.readBackboneModel(feeder):
        exit()
    testMod.rename_object("node", "n3", "mynode3")
    testMod.model.plot_model()
    loads = testMod.get_object('load')
    meter_counter = 0
    house_counter = 0
    house_meter_counter = 0
    for obj_id in loads.instances:
        # add meter for this load
        meter_counter = meter_counter + 1
        meter_name = 'meter_' + str(meter_counter)
        meter = testMod.add_object('meter', meter_name, { 'parent': obj_id })
        # how much power is going to be needed
        # while kva < total_kva:
        house_meter_counter = house_meter_counter + 1
        # add parent meter for houses to follow
        house_meter_name = 'house_meter_' + str(house_meter_counter)
        meter = testMod.add_object('meter', house_meter_name, { 'parent': meter_name })
        # add house
        house_counter = house_counter + 1
        house_name = 'house_' + str(house_counter)
        house = testMod.add_object('house', house_name, [])
        house['parent'] = house_meter_name
        meter = testMod.add_object('transformer', 'f2_transformer', { 'from': 'meter_1', 'to': 'meter_2' })
        meter = testMod.add_object('meter', 'meter_2', { 'parent': 'meter_1'})

    testMod.model.plot_model()
    testMod.write_model(tesp_test + "api/modifier_test2.glm")

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    _test1()
    _test2()
