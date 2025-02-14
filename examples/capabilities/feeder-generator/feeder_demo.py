
import os
os.environ['TESPDIR'] = "C:\\Users\\mukh915\\PNNL_Projects\\Code_base\\TESP_Resilience\\tesp"
import tesp_support.api.gld_feeder_generator as gld_feeder
from tesp_support.api.modify_GLM import GLMModifier

import json 

# Set the path to your config file and required metadata
config_path = os.path.expandvars('$TESPDIR/examples/capabilities/feeder-generator/')
config_file = 'feeder_config.json5'

config = gld_feeder.Config(os.path.join(config_path, config_file))
feeder_name = gld_feeder.Feeder(config)


feeder_name_orig = config.taxonomy.split('.glm')[0]
feeder_name_mod = feeder_name_orig.replace('-', '_').replace('.', '_')
feeder_dir = os.environ['TESPDIR'] + '\\data\\feeders\\'
feeder_glm_path = os.path.join(feeder_dir, feeder_name_orig + '.glm')
feeder_pos_file = os.path.join(feeder_dir, feeder_name_mod + '_pos.json')

glmMod = GLMModifier()
glm, success = glmMod.read_model(feeder_glm_path)

print("\nPlotting image of model")
with open(feeder_pos_file, 'r') as json_file:
    pos_data = json.load(json_file)
    
glmMod.model.plot_model(pos_data)

