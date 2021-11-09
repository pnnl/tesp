import os
import shutil
import tesp_support.api as tesp

tmy_file = os.getenv('TESPDIR') + '/data/weather/AZ-Tucson_International_Ap.tmy3'
tesp.weathercsv(tmy_file, 'weather.dat', '2013-07-01 00:00:00', '2013-07-03 00:00:00', 2013)

tesp.glm_dict('SGIP1a', te30=True)
tesp.glm_dict('SGIP1b', te30=True)
tesp.glm_dict('SGIP1c', te30=True)
tesp.glm_dict('SGIP1d', te30=True)
tesp.glm_dict('SGIP1e', te30=True)

tesp.prep_substation('SGIP1a')
tesp.prep_substation('SGIP1b')
tesp.prep_substation('SGIP1c')
tesp.prep_substation('SGIP1d')
tesp.prep_substation('SGIP1e')

shutil.copy('SGIP1e_glm_dict.json', 'SGIP1ex_glm_dict.json')
shutil.copy('SGIP1e_agent_dict.json', 'SGIP1ex_agent_dict.json')
