import tesp_support.api as tesp
import os

tmy_file = os.getenv('TESP_INSTALL') + '/share/support/weather/AZ-Tucson_International_Ap.tmy3'
tesp.weathercsv (tmy_file, 'weather.dat', 
                 '2013-07-01 00:00:00', '2013-07-03 00:00:00',2013)
tesp.glm_dict ('TE_Challenge',te30=True)
tesp.prep_substation ('TE_Challenge')

