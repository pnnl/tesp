import tesp_support.api as tesp
import prep_ercot_auction as prep

tesp.glm_dict ('Bus1', True)
tesp.glm_dict ('Bus2', True)
tesp.glm_dict ('Bus3', True)
tesp.glm_dict ('Bus4', True)
tesp.glm_dict ('Bus5', True)
tesp.glm_dict ('Bus6', True)
tesp.glm_dict ('Bus7', True)
tesp.glm_dict ('Bus8', True)

prep.prep_ercot_auction ('Bus1')
prep.prep_ercot_auction ('Bus2')
prep.prep_ercot_auction ('Bus3')
prep.prep_ercot_auction ('Bus4')
prep.prep_ercot_auction ('Bus5')
prep.prep_ercot_auction ('Bus6')
prep.prep_ercot_auction ('Bus7')
prep.prep_ercot_auction ('Bus8')

