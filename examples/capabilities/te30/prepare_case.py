# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: prepare_case.py

from tesp_support.api.data import weather_path
from tesp_support.weather.TMY3toCSV import weathercsv
from tesp_support.glm_dictionary import glm_dict
from tesp_support.api.make_ems import merge_idf
from tesp_support.prep_substation import prep_substation

tmy_file = weather_path + 'AZ-Tucson_International_Ap.tmy3'
weathercsv(tmy_file, 'weather.dat', '2013-07-01 00:00:00', '2013-07-03 00:00:00', 2013)
glm_dict('TE_Challenge', te30=True)
prep_substation('TE_Challenge', bus_id=7)

# to run the original E+ model with heating/cooling, copy the following file to Merged.idf
# base_idf = energyplus_path + 'SchoolDualController.idf'

base_idf = '../energyplus/SchoolBase.idf'
ems_idf = '../energyplus/forSchoolBase/emsSchoolBase.idf'
merge_idf(base_idf, ems_idf, '2013-07-01 00:00:00', '2013-07-03 00:00:00', 'Merged_f.idf', 12)
ems_idf = '../energyplus/forSchoolBase/emsSchoolBaseH.idf'
merge_idf(base_idf, ems_idf, '2013-07-01 00:00:00', '2013-07-03 00:00:00', 'Merged.idf', 12)
