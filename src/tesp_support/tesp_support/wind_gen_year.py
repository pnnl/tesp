# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: wind_gen_year.py

"""
Written by Ankit Singhal and Mitch Pelton
This scripts use Tom's wind model to generate wind power generation and write in csv files.
This script should be kept in tesp_support folder

It writes two files:
    1. wind.csv: can be considered as actual wind value. It is written with 5 minute resolution.
    Tom's model generates hourly data which is interpolated to 5 minute (300 seconds) resolution.

    2. wind_forecast.csv: a gaussian distribution of error is added to generate hourly wind forecast.
    First error is added in 5 minute resolution data which then averaged to hourly data.
"""

import math
import numpy as np
import pandas as pd

from .tso_helpers import load_json_case

resolution = 300  # seconds
# casename = '../../../examples/analysis/dsot/code/system_case_config_new'
casename = '../../../examples/analysis/dsot/code/system_case_config'
output_Path = '../../../examples/analysis/dsot/data/'


def make_wind_plants(ppc):
    gen = ppc['gen']
    genCost = ppc['gencost']
    genFuel = np.array(ppc['genfuel'])
    plants = {}
    Pnorm = 165.6
    for idx in range(gen.shape[0]):
        busnum = int(gen[idx, 0])
        # this ensures that legacy cases (len==18) still work
        if len(gen) == 18:
            c2 = float(genCost[idx, 4])
            if c2 < 2e-5:  # genfuel would be 'wind'
                gen_type = 'wind'
            else:
                gen_type = 'other'
        else:
            gen_type = genFuel[idx, 0]
        if 'wind' in gen_type:
            MW = float(gen[idx, 8])
            if len(gen) == 18:
                ERCOT_scaling_sdev = 2 / 3
                ERCOT_scaling_ave = 0.2
            else:
                ERCOT_scaling_sdev = 13 / 3
                ERCOT_scaling_ave = 0.17
            scale = MW / Pnorm
            Theta0 = ERCOT_scaling_ave * 0.05 * math.sqrt(scale)
            Theta1 = -0.1 * scale
            StdDev = ERCOT_scaling_sdev * math.sqrt(1.172 * math.sqrt(scale))
            Psi1 = 1.0
            Ylim = math.sqrt(MW)
            alag = Theta0
            ylag = Ylim
            unRespMW = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            plants[str(i)] = [busnum, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, unRespMW]
    return plants


def generate_wind_data_24hr():
    for j in range(24):
        for key, row in wind_plants.items():
            # return dict with rows like
            # wind['unit'] = [bus, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, [24-hour p]]
            Theta0 = row[2]
            Theta1 = row[3]
            StdDev = row[4]
            Psi1 = row[5]
            Ylim = row[6]
            alag = row[7]
            ylag = row[8]
            if j > 0:
                a = np.random.normal(0.0, StdDev)
                y = Theta0 + a - Theta1 * alag + Psi1 * ylag
                alag = a
            else:
                y = ylag
            if y > Ylim:
                y = Ylim
            elif y < 0.0:
                y = 0.0
            p = y * y
            if j > 0:
                ylag = y
            row[7] = alag
            row[8] = ylag
            # set the max and min
            row[9][j] = p
    return wind_plants


ppc = load_json_case(casename + ".json")
# initialize for variable wind
wind_plants = make_wind_plants(ppc)
Pbase = [row[1] for key, row in wind_plants.items()]  # base MW for wind generators
day = 0
# year = 2016
# max_days = 366  # days in 2016
# start_day = pd.datetime(year,1,1)
year = 2015
max_days = 371  # days in 2016
start_day = pd.datetime(year, 12, 29)
df_wind_yr = pd.DataFrame()
if len(ppc['gen']) == 18:
    plant_name = ['wind1', 'wind2', 'wind3', 'wind4', 'wind5']
else:
    plant_name = []
    for i in range(len(ppc['genfuel'])):
        if 'wind' in ppc['genfuel'][i][0]:
            plant_name.append('wind' + str(ppc['genfuel'][i][2]))

# Create Dataframe for a year wind generation with 1 hour resolution
while day < max_days:
    df_wind_day = pd.DataFrame(columns=plant_name,
                               index=pd.date_range(start=start_day + pd.Timedelta(day, unit='d'), periods=24, freq='H'))
    wind_plant = generate_wind_data_24hr()  # generate 24-hour wind data with hourly resolution
    i = 0
    for key, row in wind_plants.items():
        df_wind_day[plant_name[i]] = row[9]
        i += 1
    df_wind_yr = df_wind_yr.append(df_wind_day)
    day += 1

# Interpolate to convert to 5 minutes from hourly
end_day = start_day + pd.Timedelta(max_days, unit='d')
min_index = pd.date_range(start=start_day, end=end_day, freq=str(resolution) + 's', closed='left')
df_wind_yr_minute = df_wind_yr.reindex(min_index).interpolate()  # linear interpolation
df_wind_yr_minute.index.name = 'time'
# Write to csv
df_wind_yr_minute.to_csv(output_Path + 'wind_Revised.csv', float_format='%.3f')
print('writing wind_Revised.csv with', resolution, 'seconds resolution')

# ------- Add Error to get forecast ------------------------------
# create normal distribution error for 24-hours with 5 minute resolution
wd_err_mean = 0.0177
wd_err_std = 0.1187
error_df = pd.DataFrame(columns=plant_name)
for err in range(max_days):
    temp_df = pd.DataFrame(columns=plant_name)
    for name in plant_name:
        err_mean = wd_err_mean * (1 + 0.05 * 2 * np.random.rand() - 0.05)  # +-5%
        err_std = wd_err_std * (1 + 0.1 * 2 * np.random.rand() - 0.1)  # +-10%
        wd_error = np.random.normal(err_mean, err_std, int(24 * 3600 / resolution))
        temp_df[name] = wd_error
    error_df = error_df.append(temp_df)
error_df = error_df.set_index(df_wind_yr_minute.index)

wd_forecast = df_wind_yr_minute + error_df * Pbase
# downsampling to hourly average
wd_forecast_hour = wd_forecast.resample('H').mean()
# Write to csv
wd_forecast_hour.to_csv(output_Path + 'wind_forecast_Revised.csv', float_format='%.3f')
print('writing wind_forecast_Revised.csv with', resolution, 'seconds resolution')

# downsampling to hourly average
df_wind_yr_hour = df_wind_yr_minute.resample('H').mean()
# Write to csv
df_wind_yr_hour.to_csv(output_Path + 'wind_hour_Revised.csv', float_format='%.3f')
print('writing wind_hour_Revised.csv with', resolution, 'seconds resolution')

# wd_hourly_err_df_min = (wd_forecast-df_wind_yr_minute)/Pbase # 5 minute error
# wd_hourly_err_df = (wd_forecast_hour - df_wind_yr) /Pbase # hourly error
# for name in plant_name:
#     plt.hist(wd_hourly_err_df[name].values, 100)
# plt.legend(plant_name)
# plt.title("Day ahead error distribution in 5 wind plants")
# plt.show()
