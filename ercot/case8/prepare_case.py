import tesp_support.api as tesp
import prep_ercot_auction as prep

tesp.glm_dict ('Bus1')
tesp.glm_dict ('Bus2')
tesp.glm_dict ('Bus3')
tesp.glm_dict ('Bus4')
tesp.glm_dict ('Bus5')
tesp.glm_dict ('Bus6')
tesp.glm_dict ('Bus7')
tesp.glm_dict ('Bus8')

prep.prep_ercot_auction ('Bus1')
prep.prep_ercot_auction ('Bus2')
prep.prep_ercot_auction ('Bus3')
prep.prep_ercot_auction ('Bus4')
prep.prep_ercot_auction ('Bus5')
prep.prep_ercot_auction ('Bus6')
prep.prep_ercot_auction ('Bus7')
prep.prep_ercot_auction ('Bus8')

