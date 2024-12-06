
import os
import tesp_support.api.gld_feeder_generator as gld_feeder

# Set the path to your config file and required metadata
config_path = os.path.expandvars('$TESPDIR/examples/capabilities/feeder-generator/')
config_file = 'feeder_config.json5'

config = gld_feeder.Config(os.path.join(config_path, config_file))
feeder = gld_feeder.Feeder(config)
