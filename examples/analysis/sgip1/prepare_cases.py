import os
import shutil

from tesp_support.api.data import weather_path
from tesp_support.TMY3toCSV import weathercsv
from tesp_support.glm_dictionary import glm_dict
from tesp_support.prep_substation import prep_substation

tmy_file = weather_path + 'AZ-Tucson_International_Ap.tmy3'
weathercsv(tmy_file, 'weather.dat', '2013-07-01 00:00:00', '2013-07-03 00:00:00', 2013)

glm_dict('SGIP1a', te30=True)
glm_dict('SGIP1b', te30=True)
glm_dict('SGIP1c', te30=True)
glm_dict('SGIP1d', te30=True)
glm_dict('SGIP1e', te30=True)

prep_substation('SGIP1a', bus_id=7)
prep_substation('SGIP1b', bus_id=7)
prep_substation('SGIP1c', bus_id=7)
prep_substation('SGIP1d', bus_id=7)
prep_substation('SGIP1e', bus_id=7)

shutil.copy('SGIP1e_glm_dict.json', 'SGIP1ex_glm_dict.json')
shutil.copy('SGIP1e_agent_dict.json', 'SGIP1ex_agent_dict.json')

cases = ['a', 'c', 'd', 'e']
for idx in cases:
    os.remove('SGIP1' + idx + '_gridlabd.txt')
    os.remove('SGIP1' + idx + '_gridlabd.json')
    os.remove('SGIP1' + idx + '_substation.yaml')
    os.remove('SGIP1' + idx + '_substation.json')
    os.remove('SGIP1' + idx + '_weather.json')
    os.remove('SGIP1' + idx + '_weather_f.json')
