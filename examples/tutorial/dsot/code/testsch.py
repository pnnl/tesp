from datetime import datetime
from tesp_support.api.schedule_client import *

wh_sch = ['small_1', 'small_2', 'small_3', 'small_4', 'small_5', 'small_6',
          'large_1', 'large_2', 'large_3', 'large_4', 'large_5', 'large_6']
comm_sch = [
    "retail_heating",
    "retail_cooling",
    "retail_lights",
    "retail_plugs",
    "retail_gas",
    "retail_exterior",
    "retail_occupancy"]

gProxy = DataClient(5150).proxy
#mytime = datetime(2016, 7, 1, 0, 59)
#mytime = datetime(2016, 7, 31, 0, 59)
mytime = datetime(2015, 12, 31, 0, 59)

for sch in comm_sch:
    array = gProxy.forecasting_schedules(sch, mytime, 24)
    print(array)
for sch in wh_sch:
    array = gProxy.forecasting_schedules(sch, mytime, 24)
    print(array)
for sch in wh_sch:
    array = gProxy.forecasting_schedules(sch, mytime, 24)
    print(array)
mytime = mytime.replace(minute=0, second=0)
array = gProxy.forecasting_pv_schedules('pv_power', mytime, 24, 3)
print("pv ", array)
array = gProxy.forecasting_pv_schedules('pv_power', mytime, 24, 4)
print("pv ", array)
