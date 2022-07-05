# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: prepare_case.py

import tesp_support.api as tesp
import utilities
import json
from datetime import datetime
import os

_FNCS = False
#_FNCS = True
if _FNCS:
    import prep_ercot_substation_f as prep
else:
    import prep_ercot_substation as prep


tesp_share = os.path.expandvars('$TESPDIR/data/')

# for reduced-order feeder models
ercotFlag = True
# for full-order feeder
# ercotFlag = False 

te30Flag = False

tesp.glm_dict('Bus1', ercot=ercotFlag, te30=te30Flag)
tesp.glm_dict('Bus2', ercot=ercotFlag, te30=te30Flag)
tesp.glm_dict('Bus3', ercot=ercotFlag, te30=te30Flag)
tesp.glm_dict('Bus4', ercot=ercotFlag, te30=te30Flag)
tesp.glm_dict('Bus5', ercot=ercotFlag, te30=te30Flag)
tesp.glm_dict('Bus6', ercot=ercotFlag, te30=te30Flag)
tesp.glm_dict('Bus7', ercot=ercotFlag, te30=te30Flag)
tesp.glm_dict('Bus8', ercot=ercotFlag, te30=te30Flag)

if _FNCS:
    broker = 'tcp://localhost:5570'
    # FNCS for monitor each sub adds to monitor
    utilities.write_FNCS_config_yaml_file_header()
    # FNCS for monitor
    utilities.write_json_for_ercot_monitor(3600, 15, 10)
else:
    broker = 'HELICS'
    utilities.write_ercot_tso_msg(8)

prep.prep_ercot_substation('Bus1', weatherName='weatherIAH')
prep.prep_ercot_substation('Bus2', weatherName='weatherIAH')
prep.prep_ercot_substation('Bus3', weatherName='weatherSPS')
prep.prep_ercot_substation('Bus4', weatherName='weatherIAH')
prep.prep_ercot_substation('Bus5', weatherName='weatherIAH')
prep.prep_ercot_substation('Bus6', weatherName='weatherIAH')
prep.prep_ercot_substation('Bus7', weatherName='weatherIAH')
prep.prep_ercot_substation('Bus8', weatherName='weatherELP')

weather_agents = [
    {'weatherName': 'weatherIAH', 'tmy3': 'TX-Houston_Bush_Intercontinental.tmy3', 'lat': 30.000, 'lon': -95.367},
    {'weatherName': 'weatherSPS', 'tmy3': 'TX-Wichita_Falls_Municipal_Arpt.tmy3', 'lat': 33.983, 'lon': -98.500},
    {'weatherName': 'weatherELP', 'tmy3': 'TX-El_Paso_International_Ap_Ut.tmy3', 'lat': 31.770, 'lon': -106.500}
]

# configure the weather agents to be shared among all the buses
StartTime = '2013-07-01 00:00:00'
EndTime = '2013-07-04 00:00:00'
time_fmt = '%Y-%m-%d %H:%M:%S'
dt1 = datetime.strptime(StartTime, time_fmt)
dt2 = datetime.strptime(EndTime, time_fmt)
seconds = int((dt2 - dt1).total_seconds())
days = int(seconds / 86400)
minutes = int(seconds / 60)
hours = int(seconds / 3600)
for i in range(len(weather_agents)):
    tmy3file = tesp_share + 'weather/' + weather_agents[i]['tmy3']
    weatherName = weather_agents[i]['weatherName']
    csvfile = weatherName + '.dat'
    print(weatherName, tmy3file, csvfile)
    # convert TMY3 to CSV
    tesp.weathercsv(tmy3file, csvfile, StartTime, EndTime, 2013)
    # write the weather agent's configuration file
    wconfig = {'name': weatherName,
               'StartTime': StartTime,
               'time_stop': str(minutes) + 'm',
               'time_delta': '1s',
               'publishInterval': '5m',
               'Forecast': 1,
               'ForecastLength': '24h',
               'PublishTimeAhead': '3s',
               'AddErrorToForecast': 1,
               'broker': broker,
               'forecastPeriod': 48,
               'parameters': {}}
    for parm in ['temperature', 'humidity', 'pressure', 'solar_diffuse', 'solar_direct', 'wind_speed']:
        wconfig['parameters'][parm] = {'distribution': 2,
                                       'P_e_bias': 0.5,
                                       'P_e_envelope': 0.08,
                                       'Lower_e_bound': 0.5}
    wp = open(weatherName + '.json', 'w')
    print(json.dumps(wconfig), file=wp)
    wp.close()
