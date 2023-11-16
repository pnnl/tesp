# usage 'python ../plots.py metrics_root'
# run it from inside the metrics_root folder
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

import process_gld_dsot as pg

# import tesp_support.api.process_inv as gp
# import tesp_support.api.process_gld as gp

rootname = sys.argv[1]

cur_dir = os.getcwd()
new_dir = cur_dir + "/" + rootname + "_TM/Substation"
os.chdir(new_dir)

if not os.path.exists("Figures"):
    os.mkdir("Figures")
print("*****current working directory is *** " + os.getcwd())

[hrs, times, hse_keys, data_h, HVAC_LOAD_AVG_IDX, WH_AVG_IDX, TOTAL_LOAD_AVG_IDX, DEV_COOL_IDX, data_m,
 MTR_REAL_POWER_AVG, MTR_VOLT_MIN_IDX, MTR_VOLT_MAX_IDX,
 data_s, SUB_POWER_IDX, SUB_LOSSES_IDX] = pg.process_gld("Substation")

# discarded_hours = 24*2  # discarded hours
discarded_hours = 24 * 1
discard_secs = discarded_hours * 60 * 60  # first discard_secs should be discarded while plotting
for l in times:
    if l >= discard_secs:
        hrs_start = times.index(l)
        break

# hrs_start = discard_secs/60/(hrs[1]-hrs[0])
hrs_start = int(hrs_start)
hrs = hrs - discard_secs / 3600
hrs = hrs[hrs_start:]
# display an aggregated plot
fig1, ax1 = plt.subplots(2, 1, sharex='col')

hvac_load = np.sum(data_h, axis=0)[:, HVAC_LOAD_AVG_IDX]
wh_load = np.sum(data_h, axis=0)[:, WH_AVG_IDX]
total_load = np.sum(data_h, axis=0)[:, TOTAL_LOAD_AVG_IDX]
mtr_load = np.sum(data_m, axis=0)[:, MTR_REAL_POWER_AVG] / 1000
sub_load = data_s[0, :, SUB_POWER_IDX] / 1000
sub_losses = data_s[0, :, SUB_LOSSES_IDX] / 1000
net_load = hvac_load + wh_load
# if lst_i[time_key]:
#     inv_load = np.sum(data_i, axis=0)[:, INV_P_AVG_IDX]/1000
#     inv_load_var = np.sum(data_i, axis=0)[:, INV_Q_AVG_IDX] / 1000
#     net_load = hvac_load+wh_load+inv_load

# estimating % of devices in ON state at each time
hvac_on_per = np.count_nonzero(data_h[:, :, HVAC_LOAD_AVG_IDX], 0) / len(data_h[:, 0, HVAC_LOAD_AVG_IDX]) * 100
wh_on_per = np.count_nonzero(data_h[:, :, WH_AVG_IDX], 0) / len(data_h[:, 0, WH_AVG_IDX]) * 100

ax1[0].plot(hrs, hvac_load[hrs_start:], label="hvac")
ax1[0].plot(hrs, wh_load[hrs_start:], label="waterheater")
ax1[0].plot(hrs, total_load[hrs_start:] - hvac_load[hrs_start:] - wh_load[hrs_start:], label="ZIP")
ax1[0].plot(hrs, total_load[hrs_start:], label="total")
# ax1[0,0].plot(hrs, mtr_load[hrs_start:], "k--", label="net meter",)
# if lst_i[time_key]:
#     ax1[0,0].plot(hrs, -inv_load[hrs_start:], label="inverter_real")
#     ax1[0, 0].plot(hrs, -inv_load_var[hrs_start:], label="inverter_var")
#     ax1[0, 0].plot(hrs, total_load[hrs_start:]-inv_load[hrs_start:], label="total+inv")
#     ax1[0, 1].plot(hrs, -inv_load[hrs_start:], label="Total DERs")
ax1[0].set_ylabel("kW")
ax1[0].set_title("Load Composition")
ax1[0].legend(loc='upper left')

ax1[1].plot(hrs, total_load[hrs_start:], label="Total Load")
ax1[1].plot(hrs, sub_losses[hrs_start:], label="Total Losses")
ax1[1].plot(hrs, sub_load[hrs_start:], label="Net Load")
ax1[1].set_ylabel("kW")
ax1[1].set_title("Substation Real Power at ")
ax1[1].legend(loc='upper left')

new_dir = cur_dir + "/" + rootname + "_Base/Substation"
os.chdir(new_dir)

[hrs, times, hse_keys, data_h, HVAC_LOAD_AVG_IDX, WH_AVG_IDX, TOTAL_LOAD_AVG_IDX, DEV_COOL_IDX, data_m,
 MTR_REAL_POWER_AVG, MTR_VOLT_MIN_IDX, MTR_VOLT_MAX_IDX,
 data_s, SUB_POWER_IDX, SUB_LOSSES_IDX] = pg.process_gld("Substation")

# discarded_hours = 24*2  # discarded hours
discarded_hours = 24 * 1
discard_secs = discarded_hours * 60 * 60  # first discard_secs should be discarded while plotting
for l in times:
    if l >= discard_secs:
        hrs_start = times.index(l)
        break

# hrs_start = discard_secs/60/(hrs[1]-hrs[0])
hrs_start = int(hrs_start)
hrs = hrs - discard_secs / 3600
hrs = hrs[hrs_start:]

hvac_load = np.sum(data_h, axis=0)[:, HVAC_LOAD_AVG_IDX]
wh_load = np.sum(data_h, axis=0)[:, WH_AVG_IDX]
total_load = np.sum(data_h, axis=0)[:, TOTAL_LOAD_AVG_IDX]
mtr_load = np.sum(data_m, axis=0)[:, MTR_REAL_POWER_AVG] / 1000
sub_load = data_s[0, :, SUB_POWER_IDX] / 1000
sub_losses = data_s[0, :, SUB_LOSSES_IDX] / 1000
net_load = hvac_load + wh_load
# if lst_i[time_key]:
#     inv_load = np.sum(data_i, axis=0)[:, INV_P_AVG_IDX]/1000
#     inv_load_var = np.sum(data_i, axis=0)[:, INV_Q_AVG_IDX] / 1000
#     net_load = hvac_load+wh_load+inv_load

# estimating % of devices in ON state at each time
hvac_on_per = np.count_nonzero(data_h[:, :, HVAC_LOAD_AVG_IDX], 0) / len(data_h[:, 0, HVAC_LOAD_AVG_IDX]) * 100
wh_on_per = np.count_nonzero(data_h[:, :, WH_AVG_IDX], 0) / len(data_h[:, 0, WH_AVG_IDX]) * 100

ax1[0].plot(hrs, hvac_load[hrs_start:], label="hvac_base")
ax1[0].plot(hrs, wh_load[hrs_start:], label="waterheater_base")
ax1[0].plot(hrs, total_load[hrs_start:] - hvac_load[hrs_start:] - wh_load[hrs_start:], label="ZIP_base")
ax1[0].plot(hrs, total_load[hrs_start:], label="total_base")
# ax1[0,0].plot(hrs, mtr_load[hrs_start:], "k--", label="net meter",)
# if lst_i[time_key]:
#     ax1[0,0].plot(hrs, -inv_load[hrs_start:], label="inverter_real")
#     ax1[0, 0].plot(hrs, -inv_load_var[hrs_start:], label="inverter_var")
#     ax1[0, 0].plot(hrs, total_load[hrs_start:]-inv_load[hrs_start:], label="total+inv")
#     ax1[0, 1].plot(hrs, -inv_load[hrs_start:], label="Total DERs")
ax1[0].set_ylabel("kW")
ax1[0].set_title("Load Composition")
ax1[0].legend(loc='upper left')

ax1[1].plot(hrs, total_load[hrs_start:], label="Total Load_base")
ax1[1].plot(hrs, sub_losses[hrs_start:], label="Total Losses_base")
ax1[1].plot(hrs, sub_load[hrs_start:], label="Net Load_base")
ax1[1].set_ylabel("kW")
ax1[1].set_title("Substation Real Power at ")
ax1[1].legend(loc='upper left')

# fig1.savefig('Figures/aggregated.png')
plt.show(block=True)
plt.pause(0.5)
plt.close()

# ph.process_houses(rootname)
# pi.process_inv(rootname)
# pv.process_voltages(rootname)
plt.show()
