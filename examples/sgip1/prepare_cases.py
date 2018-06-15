import shutil
import tesp_support.api as tesp

tesp.glm_dict ('SGIP1a')
tesp.glm_dict ('SGIP1b')
tesp.glm_dict ('SGIP1c')
tesp.glm_dict ('SGIP1d')
tesp.glm_dict ('SGIP1e')

tesp.prep_auction ('SGIP1a')
tesp.prep_auction ('SGIP1b')
tesp.prep_auction ('SGIP1c')
tesp.prep_auction ('SGIP1d')
tesp.prep_auction ('SGIP1e')

shutil.copy ('SGIP1e_glm_dict.json', 'SGIP1ex_glm_dict.json')
shutil.copy ('SGIP1e_agent_dict.json', 'SGIP1ex_agent_dict.json')


