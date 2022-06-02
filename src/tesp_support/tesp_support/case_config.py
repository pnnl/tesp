"""
"""

import json
import os
import helpers

tesp_share = os.path.expandvars('$TESPDIR/data/')
feeders_path = tesp_share + 'feeders/'
feeders_path = tesp_share + 'entities/'
scheduled_path = tesp_share + 'schedules/'
weather_path = tesp_share + 'weather/'

with open(tesp_share + 'master_config.json', 'r', encoding='utf-8') as json_file:
    master_config = json.load(json_file)


def diction(_object, _default, _override=None):
    default = master_config[_default]
    for parameter in default:
        setattr(_object, parameter, default[parameter])
    if _override is not None:
        override = master_config(_override)
        for parameter in override:
            setattr(_object, parameter, override[parameter])


"""
class Diction(object):
    def __init__(self, diction):
        self.obj = diction

    def __enter__(self):
        return self.obj

    def __exit__(self, exception_type, exception_value, traceback):
        return self

    with Diction(config['BackboneFiles']) as tmp:
        rootname = tmp['TaxonomyChoice']
        if 'weatherpath' in tmp:
            weather_path = tmp['weatherpath']
"""

if __name__ == "__main__":
    cr = helpers.curve()
    diction(cr, "MonteCarloCase")
