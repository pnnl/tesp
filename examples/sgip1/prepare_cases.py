import shutil
import tesp_support.api as tesp

tesp.glm_dict ('SGIP1a',te30=True)
tesp.glm_dict ('SGIP1b',te30=True)
tesp.glm_dict ('SGIP1c',te30=True)
tesp.glm_dict ('SGIP1d',te30=True)
tesp.glm_dict ('SGIP1e',te30=True)

tesp.prep_substation ('SGIP1a')
tesp.prep_substation ('SGIP1b')
tesp.prep_substation ('SGIP1c')
tesp.prep_substation ('SGIP1d')
tesp.prep_substation ('SGIP1e')

shutil.copy ('SGIP1e_glm_dict.json', 'SGIP1ex_glm_dict.json')
shutil.copy ('SGIP1e_agent_dict.json', 'SGIP1ex_agent_dict.json')


