import prep_ercot_substation as prep
import tesp_support.glm_dict as gd
import utilities

gd.glm_dict ('Bus1', True)
gd.glm_dict ('Bus2', True)
gd.glm_dict ('Bus3', True)
gd.glm_dict ('Bus4', True)
gd.glm_dict ('Bus5', True)
gd.glm_dict ('Bus6', True)
gd.glm_dict ('Bus7', True)
gd.glm_dict ('Bus8', True)

utilities.write_FNCS_config_yaml_file_header()

prep.prep_ercot_substation ('Bus1')
prep.prep_ercot_substation ('Bus2')
prep.prep_ercot_substation ('Bus3')
prep.prep_ercot_substation ('Bus4')
prep.prep_ercot_substation ('Bus5')
prep.prep_ercot_substation ('Bus6')
prep.prep_ercot_substation ('Bus7')
prep.prep_ercot_substation ('Bus8')

utilities.write_json_for_ercot_monitor(3600, 15, 10)