"""
"""

import json
import os

tesp_share = os.path.expandvars('$TESPDIR/data/')
feeders_path = tesp_share + 'feeders/'
entities_path = tesp_share + 'entities/'
scheduled_path = tesp_share + 'schedules/'
weather_path = tesp_share + 'weather/'

# 'module climate;'
# 'module connection;'
# 'module generators;'
# 'module residential'


class Entity:
    def __init__(self, name):
        with open(entities_path + 'master_settings.json', 'r', encoding='utf-8') as json_file:
            config = json.load(json_file)
        for row in config[name]:
            setattr(self, row[4], row[1])
            setattr(self, row[4] + '__l', row[0])
            setattr(self, row[4] + '__u', row[2])
            setattr(self, row[4] + '__e', row[3])
            # setattr(self, row[4] + '__s', row[5])

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        return self

    def print(self):
        # print(vars(self))
        for field in self.__dict__:
            if "__" not in field:
                value = getattr(self, field)
                print(field, "=", value)
        return ""


if __name__ == "__main__":

    mylist = {}
    entities = ["SimulationConfig", "BackboneFiles",  "WeatherPrep", "FeederGenerator",
                "EplusConfiguration", "PYPOWERConfiguration", "AgentPrep", "ThermostatSchedule"]
    # , 'house', 'inverter', 'battery', 'object solar', 'waterheater' ...]

    for obj in entities:
        mylist[obj] = Entity(obj)
        mylist[obj].print()
