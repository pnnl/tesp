# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: process_matpower_v2.4.py

import json
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

# first, read and print a dictionary of relevant MATPOWER objects

casepath = r'''C:\Qiuhua\FY2016_Project_Transactive_system\Simulation_Year1\SGIP1\SGIP1a\\'''
casename = 'SGIP1a'
lp = open(casepath + casename + "_m_dict.json").read()
dict = json.loads(lp)
baseMVA = dict['baseMVA']
ampFactor = dict['ampFactor']
gen_keys = list(dict['generators'].keys())
gen_keys.sort()
bus_keys = list(dict['fncsBuses'].keys())
bus_keys.sort()
print("\n\nFile", casename, "has baseMVA", baseMVA, "with GLD load scaling =", ampFactor)
print("\nGenerator Dictionary:")
print("Unit Bus Type Pnom Pmax Costs[Start Stop C2 C1 C0]")
for key in gen_keys:
    row = dict['generators'][key]
    print(key, row['bus'], row['bustype'], row['Pnom'], row['Pmax'], "[", row['StartupCost'], row['ShutdownCost'],
          row['c2'], row['c1'], row['c0'], "]")
print("\nFNCS Bus Dictionary:")
print("Bus Pnom Qnom [GridLAB-D Substations]")
for key in bus_keys:
    row = dict['fncsBuses'][key]
    print(key, row['Pnom'], row['Qnom'], row['GLDsubstations'])

# read the bus metrics file
lp_b = open(casepath + "bus_" + casename + "_metrics.json").read()
lst_b = json.loads(lp_b)
print("\nBus Metrics data starting", lst_b['StartTime'])

# make a sorted list of the times, and NumPy array of times in hours
lst_b.pop('StartTime')
# lst_b.pop('System base MVA')
# lst_b.pop('Number of buses')
# lst_b.pop('Number of generators')
# lst_b.pop('Network name')
meta_b = lst_b.pop('Metadata')
times = list(map(int, list(lst_b.keys())))
times.sort()
print("There are", len(times), "sample times at", times[1] - times[0], "second intervals")

hrs = np.array(times, dtype=np.float)
denom = 3600.0
hrs /= denom
time_interval_hours = (times[1] - times[0]) / denom

# parse the metadata for things of specific interest
print("\nBus Metadata [Variable Index Units] for", len(lst_b[str(times[0])]), "objects")
for key, val in meta_b.items():
    #    print (key, val['index'], val['units'])
    if key == 'LMP_P':
        LMP_P_IDX = val['index']
        LMP_P_UNITS = val['units']
    elif key == 'LMP_Q':
        LMP_Q_IDX = val['index']
        LMP_Q_UNITS = val['units']
    elif key == 'PD':
        PD_IDX = val['index']
        PD_UNITS = val['units']
    elif key == 'PQ':
        QD_IDX = val['index']
        QD_UNITS = val['units']
    elif key == 'Vang':
        VANG_IDX = val['index']
        VANG_UNITS = val['units']
    elif key == 'Vmag':
        VMAG_IDX = val['index']
        VMAG_UNITS = val['units']
    elif key == 'Vmax':
        VMAX_IDX = val['index']
        VMAX_UNITS = val['units']
    elif key == 'Vmin':
        VMIN_IDX = val['index']
        VMIN_UNITS = val['units']

# create a NumPy array of all bus metrics
data_b = np.empty(shape=(len(bus_keys), len(times), len(lst_b[str(times[0])][bus_keys[0]])), dtype=np.float)
print("\nConstructed", data_b.shape, "NumPy array for Buses")
j = 0
for key in bus_keys:
    i = 0
    for t in times:
        ary = lst_b[str(t)][bus_keys[j]]
        data_b[j, i, :] = ary
        i = i + 1
    j = j + 1

# display some averages
print("Average real power LMP =", data_b[0, :, LMP_P_IDX].mean(), LMP_P_UNITS)
print("Maximum bus voltage =", data_b[0, :, VMAG_IDX].max(), VMAG_UNITS)
print("Minimum bus voltage =", data_b[0, :, VMIN_IDX].max(), VMIN_UNITS)

# read the generator metrics file
lp_g = open(casepath + "gen_" + casename + "_metrics.json").read()
lst_g = json.loads(lp_g)
print("\nGenerator Metrics data starting", lst_g['StartTime'])
# make a sorted list of the times, and NumPy array of times in hours
lst_g.pop('StartTime')
meta_g = lst_g.pop('Metadata')
print("\nGenerator Metadata [Variable Index Units] for", len(lst_g[str(times[0])]), "objects")
for key, val in meta_g.items():
    print(key, val['index'], val['units'])
    if key == 'Pgen':
        PGEN_IDX = val['index']
        PGEN_UNITS = val['units']
    elif key == 'Qgen':
        QGEN_IDX = val['index']
        QGEN_UNITS = val['units']

# create a NumPy array of all bus metrics
data_g = np.empty(shape=(len(gen_keys), len(times), len(lst_g[str(times[0])][gen_keys[0]])), dtype=np.float)
print("\nConstructed", data_g.shape, "NumPy array for Generators")
j = 0
for key in gen_keys:
    i = 0
    for t in times:
        ary = lst_g[str(t)][gen_keys[j]]
        data_g[j, i, :] = ary
        i = i + 1
    j = j + 1

# display a plot - hard-wired assumption of 3 generators from Case 9
fig, ax = plt.subplots(3, 2, sharex='col')

ax[0, 0].plot(hrs, data_b[0, :, PD_IDX], color="blue", label="Real")
ax[0, 0].plot(hrs, data_b[0, :, QD_IDX], color="red", label="Reactive")
ax[0, 0].set_ylabel(PD_UNITS + "/" + QD_UNITS)
ax[0, 0].set_title("Demands at " + bus_keys[0])
ax[0, 0].legend(loc='best')

ax[1, 0].plot(hrs, data_b[0, :, LMP_P_IDX], color="blue", label="Real")
ax[1, 0].plot(hrs, data_b[0, :, LMP_Q_IDX], color="red", label="Reactive")
ax[1, 0].set_ylabel(LMP_P_UNITS)
ax[1, 0].set_title("Prices at " + bus_keys[0])
ax[1, 0].legend(loc='best')

ax[2, 0].plot(hrs, data_b[0, :, VMAG_IDX], color="blue", label="Magnitude")
ax[2, 0].plot(hrs, data_b[0, :, VMAX_IDX], color="red", label="Vmax")
ax[2, 0].plot(hrs, data_b[0, :, VMIN_IDX], color="green", label="Vmin")
ax[2, 0].set_xlabel("Hours")
ax[2, 0].set_ylabel(VMAG_UNITS)
ax[2, 0].set_title("Voltages at " + bus_keys[0])
ax[2, 0].legend(loc='best')

for i in range(0, 3):
    ax[i, 1].plot(hrs, data_g[i, :, PGEN_IDX], color="blue", label="P")
    ax[i, 1].plot(hrs, data_g[i, :, QGEN_IDX], color="red", label="Q")
    ax[i, 1].set_ylabel(PGEN_UNITS + "/" + QGEN_UNITS)
    ax[i, 1].set_title("Output from unit " + gen_keys[i])
    ax[i, 1].legend(loc='best')
ax[2, 1].set_xlabel("Hours")

# plt.show()

## transform to a xarray dataset


mp_bus_metrics = xr.Dataset({'LMP_P': (['busNum', 'time'], data_b[:, :, LMP_P_IDX]),
                             'PD': (['busNum', 'time'], data_b[:, :, PD_IDX]),
                             'QD': (['busNum', 'time'], data_b[:, :, QD_IDX]),
                             'VMAG': (['busNum', 'time'], data_b[:, :, VMAG_IDX]),
                             },
                            coords={'busNum': list(map(int, bus_keys)),
                                    'time': times})  # or hrs
## TODO add the bus-feeder and bus substation relationship to the attrs
mp_bus_metrics.attrs["bus_substation_map"] = {7: 'SUBSTATION7'}
mp_bus_metrics.attrs["bus_info_dict"] = dict['fncsBuses']

print(mp_bus_metrics)
print(mp_bus_metrics.time)
# output the metrics for time at 240 sec
print('\n\n metrics for time at 240 sec')
print(mp_bus_metrics.sel(time=240).data_vars)

print('\n\n metrics for time at 240, 840, 2040  sec')
print(mp_bus_metrics.sel(time=[240, 840, 2040]).data_vars)

print('\n\n metrics for time Between 240 and 2040  sec')
print(mp_bus_metrics.where(np.logical_and(mp_bus_metrics.time < 2040, mp_bus_metrics.time > 240)).data_vars)

# output the metrics of bus-7
print('\n\n metrics for bus 7')
print(mp_bus_metrics.sel(busNum=7).data_vars)

print('\n\n metrics for time less than 1000 sec')
print(mp_bus_metrics.where((mp_bus_metrics.time < 1000), drop=True).data_vars)

# print the LMP min and max
print("LMP MIN", mp_bus_metrics.LMP_P.min(), "\n LMP MAX", mp_bus_metrics.LMP_P.max())

print("Real power MIN", mp_bus_metrics.PD.min(), "\n Real power MAX", mp_bus_metrics.PD.max())

# sum of real power demand over the whole simulation period
print("Sum of Real power ", mp_bus_metrics.PD.sum())

# sum of real power demand over the simulation period Between 240 and 2040  sec
print("Sum of Real power during 240s to 2040s ",
      mp_bus_metrics.where(np.logical_and(mp_bus_metrics.time < 2040, mp_bus_metrics.time > 240)).PD.sum())

#  -----------save the dataset to a netCMF format file-------------------------

# mp_bus_metrics.to_netcdf(r'''..\mp_bus_metrics.nc''')

#  -----------load a netCMF format file to dataset-----------------------------
# mp_bus_metrics2 = xr.open_dataset(r'''..\mp_bus_metrics.nc''')


# processing the generation part metrics

# generation emission rate table (lb/MWh)
# Combination of the tables 11.3 and 11. 5 in the last years' report
#                         CO2                SOX        NOX
# coal                   205.57*10.09     0.1*10.09     0.06*10.09
# natrual gas (CC)       117.08*7.67      0.001*7.67    0.0075*7.67
# natrual gas (CT)       117.08*11.37     0.001*11.37   0.0075*11.37

gen_emission_rate = {'coal': [205.57 * 10.09, 0.1 * 10.09, 0.06 * 10.09],
                     'gas_combinedcycle': [117.08 * 7.67, 0.001 * 7.67, 0.0075 * 7.67],
                     'gas_singlecycle': [117.08 * 11.37, 0.001 * 11.37, 0.0075 * 11.37]}
print('gen_emission_rate')

gen_cost = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)
gen_payment = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)
gen_emission_co2 = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)
gen_emission_sox = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)
gen_emission_nox = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)

co2_emission_rate = np.empty(shape=(len(gen_keys)), dtype=np.float)
sox_emission_rate = np.empty(shape=(len(gen_keys)), dtype=np.float)
nox_emission_rate = np.empty(shape=(len(gen_keys)), dtype=np.float)

print("\nConstructed", gen_cost.shape, "NumPy array for Generators")
j = 0
for key in gen_keys:
    c0 = dict['generators'][key]['c0']
    c1 = dict['generators'][key]['c1']
    c2 = dict['generators'][key]['c2']
    co2_emission_rate[j] = 0
    sox_emission_rate[j] = 0
    nox_emission_rate[j] = 0

    if (dict['generators'][key]['genfuel']) == 'gas':
        if ((dict['generators'][key]['gentype'] == 'combinedcycle') | (
                dict['generators'][key]['gentype'] == 'combinedcycle')):
            co2_emission_rate[j] = \
            gen_emission_rate[dict['generators'][key]['genfuel'] + "_" + dict['generators'][key]['gentype']][0]
            sox_emission_rate[j] = \
                gen_emission_rate[dict['generators'][key]['genfuel'] + "_" + dict['generators'][key]['gentype']][1]
            nox_emission_rate[j] = \
                gen_emission_rate[dict['generators'][key]['genfuel'] + "_" + dict['generators'][key]['gentype']][2]

    elif (dict['generators'][key]['genfuel']) == 'coal':
        co2_emission_rate[j] = gen_emission_rate[dict['generators'][key]['genfuel']][0]
        sox_emission_rate[j] = gen_emission_rate[dict['generators'][key]['genfuel']][1]
        nox_emission_rate[j] = gen_emission_rate[dict['generators'][key]['genfuel']][2]
    else:
        print('genfuel type', dict['generators'][key]['genfuel'], ' has zero emission or not supported yet!!')

    print('gen_id, c0, c1, c2:', key, c0, c1, c2)
    i = 0
    for t in times:
        pgen = data_g[j, i, PGEN_IDX]
        gen_cost[j, i] = c2 * pgen * pgen + c1 * pgen + c0
        print("gen:", key, co2_emission_rate[j], pgen, time_interval_hours)
        gen_emission_co2[j, i] = co2_emission_rate[j] * pgen * time_interval_hours
        gen_emission_sox[j, i] = sox_emission_rate[j] * pgen * time_interval_hours
        gen_emission_nox[j, i] = nox_emission_rate[j] * pgen * time_interval_hours
        # TODO
        # gen_payment[j,i]=pgen*LMP

        i = i + 1
    j = j + 1

# print ( "\nco2 rate:",co2_emission_rate)
# print ( "\nsox rate:",sox_emission_rate)

mp_gen_metrics = xr.Dataset({'PGEN': (['busNum', 'time'], data_g[:, :, PGEN_IDX]),
                             'QGEN': (['busNum', 'time'], data_g[:, :, QGEN_IDX]),
                             'GENCOST': (['busNum', 'time'], gen_cost),
                             'EMISSION_CO2': (['busNum', 'time'], gen_emission_co2),
                             'EMISSION_SOX': (['busNum', 'time'], gen_emission_sox),
                             'EMISSION_NOX': (['busNum', 'time'], gen_emission_nox),
                             },
                            coords={'busNum': list(map(int, gen_keys)),
                                    'time': times})  # or hrs

# add the generator dictionary to the attributes of the dataset
mp_gen_metrics.attrs["gen_info_dict"] = dict['generators']

# print the generator metric dataset
print("\n mp_gen_metrics: ", mp_gen_metrics)

print('\ncost of each generator between 240 - 2040 seconds: ')
print(mp_gen_metrics.where(np.logical_and(mp_bus_metrics.time < 2040, mp_bus_metrics.time > 240), drop=True).GENCOST)

# cost of each generator,  note: dim-- str or str array, means Dimension(s) over which to apply sum
print('\ncost of each generator', mp_gen_metrics.GENCOST.sum(dim='time').values)

# cost of all generators
print('\ncost of all generators', mp_gen_metrics.GENCOST.sum().values)

# total generation energy
print('\ntotal generation energy of each generator: ',
      (mp_gen_metrics.PGEN * time_interval_hours).sum(dim='time').values)

# TODO Generator emission calculation
# print('\n emission of all generators',mp_gen_metrics.where(mp_bus_metrics.time == 240 , drop=True).EMISSION_CO2.values)
print('\n emission of all generators', mp_gen_metrics.EMISSION_CO2.sum(dim='time').values)

# TODO Generator shutdown, startup, ramp up/down statistics
