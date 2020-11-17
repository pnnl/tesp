import tesp_support.api as tesp
import os

tmy_file = os.getenv('TESP_INSTALL') + '/share/support/weather/AZ-Tucson_International_Ap.tmy3'
tesp.weathercsv (tmy_file, 'weather.dat', 
                 '2013-07-01 00:00:00', '2013-07-03 00:00:00',2013)
tesp.glm_dict ('TE_Challenge',te30=True)
tesp.prep_substation ('TE_Challenge')

# to run the original E+ model with heating/cooling, copy the following file to Merged.idf
#base_idf = os.getenv('TESP_INSTALL') + '/share/support/energyplus/SchoolDualController.idf'

base_idf = '../energyplus/SchoolBase.idf'
ems_idf = '../energyplus/forSchoolBase/emsSchoolBase.idf'
tesp.merge_idf (base_idf, ems_idf, '2013-07-01 00:00:00', '2013-07-03 00:00:00', 'Merged.idf', 12)
ems_idf = '../energyplus/forSchoolBase/emsSchoolBaseH.idf'
tesp.merge_idf (base_idf, ems_idf, '2013-07-01 00:00:00', '2013-07-03 00:00:00', 'MergedH.idf', 12)

