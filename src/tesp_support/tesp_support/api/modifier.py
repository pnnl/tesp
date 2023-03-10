# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: glm_modifier.py

import os

from tesp_support.api.store import entities_path
from tesp_support.api.entity import assign_defaults
from tesp_support.api.model import GLModel


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
