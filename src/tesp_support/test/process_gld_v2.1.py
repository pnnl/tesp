#	Copyright (C) 2017 Battelle Memorial Institute
# file: process_gld_v2.1.py
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;
import xarray as xr

# first, read and print a dictionary of all the monitored GridLAB-D objects
casepath = r'''..\SGIP1a\\'''
casepath = r'''C:\Qiuhua\FY2016_Project_Transactive_system\Simulation_Year1\SGIP1\SGIP1e\\'''
casename = 'SGIP1e'
lp = open (casepath+casename + "_glm_dict.json").read()
dict = json.loads(lp)
sub_keys = list(dict['feeders'].keys())
sub_keys.sort()
inv_keys = list(dict['inverters'].keys())
inv_keys.sort()
hse_keys = list(dict['houses'].keys())
hse_keys.sort()
mtr_keys = list(dict['billingmeters'].keys())
mtr_keys.sort()
xfMVA = dict['transformer_MVA']
matBus = dict['matpower_id']
print ("\n\nFile", casename, "has substation <", sub_keys[0], ">at Matpower bus<", matBus, ">with", xfMVA, "MVA transformer")
print("\nFeeder Dictionary:")
for key in sub_keys:
        row = dict['feeders'][key]
        print (key, "has", row['house_count'], "houses and", row['inverter_count'], "inverters")
print("\nBilling Meter Dictionary:")
for key in mtr_keys:
        row = dict['billingmeters'][key]
#         print (key, "on phase", row['phases'], "of", row['feeder_id'], "with", row['children'])
print("\nHouse Dictionary:")
for key in hse_keys:
        row = dict['houses'][key]
#         print (key, "on", row['billingmeter_id'], "has", row['sqft'], "sqft", row['cooling'], "cooling", row['heating'], "heating", row['wh_gallons'], "gal WH")
        # row['feeder_id'] is also available

solar_id_array =[]
battery_id_array =[]
print("\nInverter Dictionary:")
for key in inv_keys:
        row = dict['inverters'][key]
        print (key, "on", row['billingmeter_id'], "has", row['rated_W'], "W", row['resource'], "resource")
        if(row['resource'] =='solar'):
            solar_id_array.append(key)
        elif(row['resource'] =='battery'):
            battery_id_array.append(key)
        else:
            print ('A new inverter source type not considered yet', row['resource'])
        # row['feeder_id'] is also available

# parse the substation metrics file first; there should just be one entity per time sample
# each metrics file should have matching time points
lp_s = open (casepath + "substation_" + casename + "_metrics.json").read()
lst_s = json.loads(lp_s)
print ("\nMetrics data starting", lst_s['StartTime'])

# make a sorted list of the sample times in hours
lst_s.pop('StartTime')
meta_s = lst_s.pop('Metadata')
times = list(map(int,list(lst_s.keys())))
times.sort()
print ("There are", len (times), "sample times at", times[1] - times[0], "second intervals")
hrs = np.array(times, dtype=np.float)
denom = 3600.0
hrs /= denom

time_interval_hours = (times[1] - times[0])/denom

# parse the substation metadata for 2 things of specific interest
print ("\nSubstation Metadata for", len(lst_s['3600']), "objects")
for key, val in meta_s.items():
    print (key, val['index'], val['units'])
    if key == 'real_power_avg':
        SUB_POWER_IDX = val['index']
        SUB_POWER_UNITS = val['units']
    elif key == 'real_power_losses_avg':
        SUB_LOSSES_IDX = val['index']
        SUB_LOSSES_UNITS = val['units']

# create a NumPy array of all metrics for the substation
data_s = np.empty(shape=(len(sub_keys), len(times), len(lst_s['3600'][sub_keys[0]])), dtype=np.float)
print ("\nConstructed", data_s.shape, "NumPy array for Substations")
j = 0
for key in sub_keys:
        i = 0
        for t in times:
                ary = lst_s[str(t)][sub_keys[j]]
                data_s[j, i,:] = ary
                i = i + 1
        j = j + 1

# display some averages
print ("Average power =", data_s[0,:,SUB_POWER_IDX].mean(), SUB_POWER_UNITS)
print ("Average losses =", data_s[0,:,SUB_LOSSES_IDX].mean(), SUB_LOSSES_UNITS)

# read the other JSON files; their times (hrs) should be the same
lp_h = open (casepath + "house_" + casename + "_metrics.json").read()
lst_h = json.loads(lp_h)
lp_m = open (casepath + "billing_meter_" + casename + "_metrics.json").read()
lst_m = json.loads(lp_m)
lp_i = open (casepath + "inverter_" + casename + "_metrics.json").read()
lst_i = json.loads(lp_i)

# houses
lst_h.pop('StartTime')
meta_h = lst_h.pop('Metadata')
print("\nHouse Metadata for", len(lst_h['3600']), "objects")
for key, val in meta_h.items():
        print (key, val['index'], val['units'])
        if key == 'air_temperature_max':
                HSE_AIR_MAX_IDX = val['index']
                HSE_AIR_MAX_UNITS = val['units']
        elif key == 'air_temperature_min':
                HSE_AIR_MIN_IDX = val['index']
                HSE_AIR_MIN_UNITS = val['units']
        elif key == 'air_temperature_avg':
                HSE_AIR_AVG_IDX = val['index']
                HSE_AIR_AVG_UNITS = val['units']
        elif key == 'air_temperature_median':
                HSE_AIR_MED_IDX = val['index']
                HSE_AIR_MED_UNITS = val['units']
        elif key == 'air_temperature_deviation_cooling':
                HSE_AIR_DEV_COOLING_IDX = val['index']
                HSE_AIR_DEV_COOLING_UNITS = val['units']
        elif key == 'air_temperature_deviation_heating':
                HSE_AIR_DEV_HEATING_IDX = val['index']
                HSE_AIR_DEV_HEATING_UNITS = val['units']
data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h['3600'][hse_keys[0]])), dtype=np.float)
print ("\nConstructed", data_h.shape, "NumPy array for Houses")
j = 0
for key in hse_keys:
        i = 0
        for t in times:
                ary = lst_h[str(t)][hse_keys[j]]
                data_h[j, i,:] = ary
                i = i + 1
        j = j + 1

# Billing Meters - currently only Triplex Meters but eventually primary Meters as well
lst_m.pop('StartTime')
meta_m = lst_m.pop('Metadata')
print("\nTriplex Meter Metadata for", len(lst_m['3600']), "objects")
for key, val in meta_m.items():
        print (key, val['index'], val['units'])
        if key == 'voltage_max':
                MTR_VOLT_MAX_IDX = val['index']
                MTR_VOLT_MAX_UNITS = val['units']
        elif key == 'voltage_min':
                MTR_VOLT_MIN_IDX = val['index']
                MTR_VOLT_MIN_UNITS = val['units']
        elif key == 'voltage12_max':
                MTR_VOLT12_MAX_IDX = val['index']
                MTR_VOLT12_MAX_UNITS = val['units']
        elif key == 'voltage12_min':
                MTR_VOLT12_MIN_IDX = val['index']
                MTR_VOLT12_MIN_UNITS = val['units']
        elif key == 'above_RangeA_Count':
                MTR_VOLT_ABOVE_A_COUNT_IDX = val['index']
                MTR_VOLT_ABOVE_A_COUNT_UNITS = val['units']
        elif key == 'above_RangeB_Count':
                MTR_VOLT_ABOVE_B_COUNT_IDX = val['index']
                MTR_VOLT_ABOVE_B_COUNT_UNITS = val['units']
        elif key == 'above_RangeA_Duration':
                MTR_VOLT_ABOVE_A_DURATION_IDX = val['index']
                MTR_VOLT_ABOVE_A_DURATION_UNITS = val['units']
        elif key == 'above_RangeB_Duration':
                MTR_VOLT_ABOVE_B_DURATION_IDX = val['index']
                MTR_VOLT_ABOVE_B_DURATION_UNITS = val['units']
        elif key == 'below_RangeA_Count':
                MTR_VOLT_BELOW_A_COUNT_IDX = val['index']
                MTR_VOLT_BELOW_A_COUNT_UNITS = val['units']
        elif key == 'below_RangeB_Count':
                MTR_VOLT_BELOW_B_COUNT_IDX = val['index']
                MTR_VOLT_BELOW_B_COUNT_UNITS = val['units']
        elif key == 'below_RangeA_Duration':
                MTR_VOLT_BELOW_A_DURATION_IDX = val['index']
                MTR_VOLT_BELOW_A_DURATION_UNITS = val['units']
        elif key == 'below_RangeB_Duration':
                MTR_VOLT_BELOW_B_DURATION_IDX = val['index']
                MTR_VOLT_BELOW_B_DURATION_UNITS = val['units']
        elif key == 'bill':
                MTR_BILL_IDX = val['index']
                MTR_BILL_UNITS = val['units']
data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m['3600'][mtr_keys[0]])), dtype=np.float)
print ("\nConstructed", data_m.shape, "NumPy array for Meters")
j = 0
for key in mtr_keys:
        i = 0
        for t in times:
                ary = lst_m[str(t)][mtr_keys[j]]
                data_m[j, i,:] = ary
                i = i + 1
        j = j + 1

lst_i.pop('StartTime')
meta_i = lst_i.pop('Metadata')
print("\nInverter Metadata for", len(lst_i['3600']), "objects")
for key, val in meta_i.items():
        print (key, val['index'], val['units'])
        if key == 'real_power_avg':
                INV_P_AVG_IDX = val['index']
                INV_P_AVG_UNITS = val['units']
        elif key == 'reactive_power_avg':
                INV_Q_AVG_IDX = val['index']
                INV_Q_AVG_UNITS = val['units']
data_i = np.empty(shape=(len(inv_keys), len(times), len(lst_i['3600'][inv_keys[0]])), dtype=np.float)
print ("\nConstructed", data_i.shape, "NumPy array for Inverters")
j = 0
for key in inv_keys:
        i = 0
        for t in times:
                ary = lst_i[str(t)][inv_keys[j]]
                data_i[j, i,:] = ary
                i = i + 1
        j = j + 1


# display a plot
# fig, ax = plt.subplots(2, 2, sharex = 'col')
#
# ax[0,0].plot(hrs, data_s[0,:,SUB_POWER_IDX], color="blue", label="Total")
# ax[0,0].plot(hrs, data_s[0,:,SUB_LOSSES_IDX], color="red", label="Losses")
# #ax[0,0].set_xlabel("Hours")
# ax[0,0].set_ylabel(SUB_POWER_UNITS)
# ax[0,0].set_title ("Substation Real Power at " + sub_keys[0])
# ax[0,0].legend(loc='best')

# vabase = dict['inverters'][inv_keys[0]]['rated_W']
# print ("Inverter base power =", vabase)
# ax[0,1].plot(hrs, data_i[0,:,INV_P_AVG_IDX] / vabase, color="blue", label="Real")
# ax[0,1].plot(hrs, data_i[0,:,INV_Q_AVG_IDX] / vabase, color="red", label="Reactive")
# #ax[0,1].set_xlabel("Hours")
# ax[0,1].set_ylabel("perunit")
# ax[0,1].set_title ("Inverter Power at " + inv_keys[0])
# ax[0,1].legend(loc='best')

# ax[1,0].plot(hrs, data_m[0,:,MTR_VOLT_MAX_IDX], color="blue", label="Max LN")
# ax[1,0].plot(hrs, data_m[0,:,MTR_VOLT_MIN_IDX], color="red", label="Min LN")
# ax[1,0].plot(hrs, data_m[0,:,MTR_VOLT12_MAX_IDX], color="green", label="Max LL")
# ax[1,0].plot(hrs, data_m[0,:,MTR_VOLT12_MIN_IDX], color="magenta", label="Min LL")
# ax[1,0].set_xlabel("Hours")
# ax[1,0].set_ylabel(MTR_VOLT_MAX_UNITS)
# ax[1,0].set_title ("Meter Voltages at " + mtr_keys[0])
# ax[1,0].legend(loc='best')
# 
# ax[0,1].plot(hrs, data_m[0,:,MTR_VOLT_ABOVE_A_COUNT_IDX], color="blue", label="Above_A_count")
# # ax[0,1].plot(hrs, data_m[0,:,MTR_VOLT_ABOVE_A_DURATION_IDX], color="red", label="Above_A_duration")
# ax[0,1].plot(hrs, data_m[0,:,MTR_VOLT_BELOW_A_COUNT_IDX], color="green", label="below_A_count")
# # ax[0,1].plot(hrs, data_m[0,:,MTR_VOLT_BELOW_A_DURATION_IDX], color="magenta", label="below_A_duration")
# ax[0,1].set_xlabel("Hours")
# ax[0,1].set_ylabel("counts")
# ax[0,1].set_title ("Meter Voltages Violation counts at " + mtr_keys[0])
# ax[0,1].legend(loc='best')
# 
# ax[1,1].plot(hrs, data_m[0,:,MTR_VOLT_ABOVE_A_DURATION_IDX], color="blue", label="Above_A_duration")
# # ax[1,1].plot(hrs, data_m[0,:,MTR_VOLT_ABOVE_A_DURATION_IDX], color="red", label="Above_B_duration")
# ax[1,1].plot(hrs, data_m[0,:,MTR_VOLT_BELOW_A_DURATION_IDX], color="green", label="below_A_duration")
# # ax[1,1].plot(hrs, data_m[0,:,MTR_VOLT_BELOW_A_DURATION_IDX], color="magenta", label="below_B_duration")
# ax[1,1].set_xlabel("Hours")
# ax[1,1].set_ylabel("Durations (sec)")
# ax[1,1].set_title ("Meter Voltages Violation durations at " + mtr_keys[0])
# ax[1,1].legend(loc='best')

# ax[1,1].plot(hrs, data_h[0,:,HSE_AIR_AVG_IDX], color="blue", label="Mean")
# ax[1,1].plot(hrs, data_h[0,:,HSE_AIR_MIN_IDX], color="red", label="Min")
# ax[1,1].plot(hrs, data_h[0,:,HSE_AIR_MAX_IDX], color="green", label="Max")
# ax[1,1].plot(hrs, data_h[0,:,HSE_AIR_MED_IDX], color="magenta", label="Median")
# ax[1,1].set_xlabel("Hours")
# ax[1,1].set_ylabel(HSE_AIR_AVG_UNITS)
# ax[1,1].set_title ("House Air at " + hse_keys[0])
# ax[1,1].legend(loc='best')

# plt.show()

## =========================== transform to a xarray dataset =====================================================
# ============================ billing_meter metrics =============================================================
mp_meter_metrics = xr.Dataset({'Vmax': (['meterID', 'time'],  data_m[:, :, MTR_VOLT_MAX_IDX]),
                         'Vmin':(['meterID', 'time'],  data_m[:, :, MTR_VOLT_MIN_IDX]),
#                          'Losses':(['meterID', 'time'], data_s[:, :, SUB_LOSSES_IDX]),
                         'VolatgeViolationCounts_aboveRangeA':(['meterID', 'time'], data_m[:, :, MTR_VOLT_ABOVE_A_COUNT_IDX]),
                         'VolatgeViolationCounts_belowRangeB':(['meterID', 'time'], data_m[:, :, MTR_VOLT_BELOW_B_COUNT_IDX]),
                         'VolatgeViolationCounts_aboveRangeA':(['meterID', 'time'], data_m[:, :, MTR_VOLT_ABOVE_A_COUNT_IDX]),
                         'VolatgeViolationCounts_belowRangeB':(['meterID', 'time'], data_m[:, :, MTR_VOLT_BELOW_B_COUNT_IDX]),
                         'bill':(['meterID', 'time'], data_m[:, :, MTR_BILL_IDX]),
                         },
                coords={'meterID':list(map(str,mtr_keys)),
                        'time': times}) # or hrs
mp_meter_metrics.attrs["billingmeter_dict"] = dict['billingmeters']

print("\n\nmeter metrics",mp_meter_metrics)
#print(mp_meter_metrics.time)

# output the metrics for time at 300 sec
print('\n\n metrics for time at 300 sec')
print(mp_meter_metrics.sel(time = 300).data_vars)

print('\n\n metrics for time at 300, 900, 2400  sec')
print(mp_meter_metrics.sel(time = [300,900,2400]).data_vars)

print('\n\n metrics for time Between 1 and 3000  sec')
print(mp_meter_metrics.where(np.logical_and(mp_meter_metrics.time > 1,mp_meter_metrics.time < 3000)).data_vars)

print('\n\n metrics for time less than 1000 sec')
print(mp_meter_metrics.where((mp_meter_metrics.time < 1000) , drop= True ).data_vars)

# output the metrics of one meter
print('\n\n metrics for meter 1, time 300')
print(mp_meter_metrics.sel(meterID = mtr_keys[0], time = 300).data_vars)

# print the voltage min and max over the whole simulation period
print("\n\n Voltage maximum value:",mp_meter_metrics.Vmax.max(),"\n Voltage minimum value:",mp_meter_metrics.Vmin.min())

# sum of counts of voltage violation above Range A over the whole simulation period
print("\n\n Sum of voltage violation counts: ",mp_meter_metrics.VolatgeViolationCounts_aboveRangeA.sum(), "\n")

# sum of bill over the whole simulation period
print("\n\n Sum of bill: ",mp_meter_metrics.bill.sum(), "\n")

# ============================ substation metrics =============================================================
mp_subs_metrics = xr.Dataset({
                         'Losses':(['substationID', 'time'], data_s[:, :, SUB_LOSSES_IDX]),
                         'Real_power':(['substationID', 'time'],data_s[:,:,SUB_POWER_IDX]),
                         },
                coords={'substationID':list(map(str,sub_keys)),
                        'time': times},# or hrs
                 attrs={"Transformer_MVA": dict['transformer_MVA'],
                        "Transmission_Bus" : dict['matpower_id'],
                        "Feeder Dictionary": dict['feeders']})




print("\n\nsubstation metrics: ",mp_subs_metrics)
# print(mp_subs_metrics.time)

# output the metrics for time at 300 sec
print('\n\n metrics for time at 300 sec')
print(mp_subs_metrics.sel(time = 300).data_vars)

# ============================ house metrics =============================================================
mp_house_metrics = xr.Dataset({
                         'temperature':(['houseID', 'time'], data_h[:, :, HSE_AIR_AVG_IDX]),
#                         'temperature_deviation':(['houseID', 'time'], data_h[:, :, HSE_AIR_DEV_COOLING_IDX]),              
                         },
                coords={'houseID':list(map(str,hse_keys)),
                        'time': times}, # or hrs
                attrs= {'houses_dict': dict['houses']})

print("\n\n house metrics: ",mp_house_metrics)
#print(mp_house_metrics.time)

# output the metrics for time at 300 sec
print('\n\n house metrics for time at 300 sec')
print(mp_house_metrics.sel(time = 300).data_vars)


# ============================ PV and solar metrics =============================================================

dict['inverters'][key]
mp_inverter_metrics = xr.Dataset({
                         'real_power_avg':(['inverterID', 'time'], data_i[:,:,INV_P_AVG_IDX]),
                         'reactive_power_avg':(['inverterID', 'time'], data_i[:,:,INV_Q_AVG_IDX]),
#                         'temperature_deviation':(['houseID', 'time'], data_h[:, :, HSE_AIR_DEV_COOLING_IDX]),
                         },
                coords={'inverterID':list(map(str,inv_keys)),
                        'time': times}, # or hrs
                attrs={'solar_inverter_ids': solar_id_array,'battery_inverter_ids': battery_id_array }
                )

print('\n\ninverter metrics: ', mp_inverter_metrics)

# filter diffferent source types by where (inverterID in solar_dict)
print('\nsolar inverter ids: ', mp_inverter_metrics.attrs['solar_inverter_ids'])
print('\n\n solar inverter metrics: ', mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['solar_inverter_ids']).data_vars)

print('\n\n battery inverter metrics: ', mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).data_vars)


# total solar generated energy
print('\n\n total solar energy [wh]: ', (mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['solar_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)

# total battery output (power > 0) energy
print('\n\n total battery generated energy [wh]: ', (mp_inverter_metrics.where(mp_inverter_metrics.real_power_avg > 0).sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)

# total batter charging (avg power < 0) energy
print('\n\n total battery charging energy [wh]: ', (mp_inverter_metrics.where(mp_inverter_metrics.real_power_avg < 0).sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)

# total battery net energy
print('\n\n battery net energy [wh]: ', (mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)


#TODO Yingying please help add the clearing prices to the inverters, then we can calculate the revenues of PV and battery

# battery revunue ( income from generated energy minus payment paid to charged energy