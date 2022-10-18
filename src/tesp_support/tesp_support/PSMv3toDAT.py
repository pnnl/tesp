# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: PSMv3toDAT.py

# Written by Ebony Mayhorn
# 8/7/2019
# This code reads in PSM v3 csv files obtained from  https://maps.nrel.gov/nsrdb-viewer/
# The csv file include 6 columns for the following in addition to date and time information:
# temperature, humidity, DNI, DHI, pressure and wind_speed

import os

import pandas as pd


def weatherdat(psmv3csvfile, bus_str, location_str):
    """ Takes a weather csv file name obtained from NREL PSM v3, reads the file, converts the data to the desired units,
    and outputs dat file with the desired format """
    # reads in weather file
    weather_df = pd.read_csv(psmv3csvfile + '.csv', header=2)
    # renames the columns as desired
    weather_df.rename(columns={'Relative Humidity': 'humidity', 'Temperature': 'temperature', 'Pressure': 'pressure',
                               'DNI': 'solar_direct', 'DHI': 'solar_diffuse', 'Wind Speed': 'wind_speed'}, inplace=True)
    # converts date and time columns to on datetime column
    weather_df['datetime'] = pd.to_datetime(weather_df['Year'].astype(str) + '-' +
                                            weather_df['Month'].astype(str) + '-' +
                                            weather_df['Day'].astype(str) + ' ' +
                                            weather_df['Hour'].astype(str) + ':' +
                                            weather_df['Minute'].astype(str) + ':00')
    # drops all columns and headings
    weather_df.drop(['Year', 'Month', 'Day', 'Hour', 'Minute'], axis=1, inplace=True)
    cols = ['datetime', 'temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed']
    weather_df = weather_df[cols]

    # converts data to desired units
    weather_df['temperature'] = weather_df['temperature'] * 9 / 5 + 32  # convert to deg F from C
    weather_df['solar_direct'] = weather_df['solar_direct'] * 0.09290304  # convert to W/sq meter from W/sqft
    weather_df['solar_diffuse'] = weather_df['solar_diffuse'] * 0.09290304  # convert to W/sq meter from W/sqft
    weather_df['humidity'] = weather_df['humidity'] / 100
    weather_df.set_index(['datetime'], inplace=True)

    # Use a rolling window to smooth out temperature values which suffer from discretization
    # as they only have one significant figure
    weather_df['temperature'] = weather_df['temperature'].rolling(window=5, min_periods=1, center=True).mean().tolist()
    # temp = weather_df['temperature'].rolling(window=5, min_periods=1).mean()
    # weather_df['temperature'] = temp.tolist()

    # converts from 30-min data to 5-min data 
    weather_df_5min = weather_df.resample(rule='5Min', closed='left').first()
    weather_df_5min = weather_df_5min.interpolate(method='linear')

    weather_df_5min.solar_direct[weather_df_5min.solar_direct < 1e-4] = 0.0000
    weather_df_5min.solar_diffuse[weather_df_5min.solar_diffuse < 1e-4] = 0.0000
    weather_df_5min.wind_speed[weather_df_5min.wind_speed < 1e-4] = 0.0000

    # outputs dat file in desired format
    os.chdir("../DAT formatted files")
    weather_df_5min.to_csv('weather_' + bus_str + '_' + location_str + '.dat',
                           float_format='%.4f')
    os.chdir("../PSM source weather files")


if __name__ == '__main__':
    from .data import weather_path

    # loop to read and convert weather data files downloaded from NREL PSM v3
    # dictionary of csv weather datafile names corresponding to each bus
    bus_loc = {'Bus_1': ['704199_32.49_-96.7_2016', '32.49_-96.71'],
               'Bus_2': ['732873_29.65_-95.42_2016', '29.65_-95.42'],
               'Bus_3': ['616667_33.93_-99.98_2016', '33.93_-99.98'],
               'Bus_4': ['582402_32.09_-101.26_2016', '32.09_-101.26'],
               'Bus_5': ['672038_29.81_-97.94_2016', '29.81_-97.94'],
               'Bus_6': ['606672_29.25_-100.34_2016', '29.25_-100.34'],
               'Bus_7': ['677635_27.37_-97.74_2016', '27.37_-97.74'],
               'Bus_8': ['509223_29.93_-104.02_2016', '29.93_-104.02']}

    os.chdir(weather_path + "8-node data/PSM source weather files")

    for bus in bus_loc:
        weather_file = bus_loc[bus][0]
        out_file = bus_loc[bus][1]
        weatherdat(weather_file, bus, out_file)
