# Copyright (C) 2017-2023 Battelle Memorial Institute
# file: PSMv3toDAT.py
# Created 8/7/2019
# @author: Ebony Mayhorn
"""This code reads in PSM v3 csv files obtained from https://maps.nrel.gov/nsrdb-viewer/.

The csv file includes 6 columns for the following, in addition to date and time information:
temperature, humidity, DNI, DHI, pressure and wind_speed
"""
import os

import pandas as pd


def datetimev1(YYYY_MM_DD:str):
    data_range = pd.date_range(YYYY_MM_DD.split("-")[0]+"-01-01", periods=8760, freq='H')
    return data_range

def weatherdat(epw3csvfile, bus_str, location_str, YYYY_MM_DD):
    """ Takes a weather csv file name obtained from NREL PSM v3 and does a conversion.

    The function reads the file, converts the data to the desired units,
    and outputs dat file with the desired format

    Args:
        psmv3csvfile (str): name of the file to be converted, without ext '.csv'
        bus_str (str): id of the bus
        location_str (str):
    """
    # reads in weather file
    weather_df = pd.read_csv(epw3csvfile + '.csv', header=None, skiprows=8)

    # get the required information for dat file in gridlabd
    temperature = weather_df.iloc[:, 6] * 1.8 + 32.0 # convert to Fahrenheit
    humidity = weather_df.iloc[:, 9] / 100.0  # convert to per-unit
    solar_direct = weather_df.iloc[:, 15] * 0.09290304  # convert to W/sq foot
    solar_diffuse = weather_df.iloc[:, 16] * 0.09290304  # convert to W/sq foot
    pressure = weather_df.iloc[:, 10] * 0.01 # Convert from Pa to mbar (Kishan: 0.01 not present in TMYtoDAT.py, but the
    # meta data of epw said units are in Pa and not in mbar)
    # Source: https://designbuilder.co.uk/cahelp/Content/EnergyPlusWeatherFileFormat.htm
    wind_speed = weather_df.iloc[:, 22] * 3600.0 / 1609.0  # convert to mph (Kishan: epw has m/s and I do not understand
    # this conversion logic, logic received from TMY3toDAT.py)

    # datetime_info = pd.to_datetime(weather_df.iloc[:, 0].astype(str) + '-' +
    #                                         weather_df.iloc[:, 1].astype(str) + '-' +
    #                                         weather_df.iloc[:, 2].astype(str) + ' ' +
    #                                         weather_df.iloc[:, 3].astype(str) + ':' +
    #                                         weather_df.iloc[:, 4].astype(str) + ':00')

    weather_df = pd.DataFrame({'temperature':list(temperature), 'humidity':list(humidity),
                               'solar_direct':list(solar_direct), 'solar_diffuse':list(solar_diffuse),
                               'pressure':list(pressure), 'wind_speed':list(wind_speed)})
    weather_df.insert(loc=0, column='datetime', value=datetimev1(YYYY_MM_DD))

    weather_df['temperature'] = weather_df['temperature'].rolling(window=5, min_periods=1, center=True).mean().tolist()

    # renames the columns as desired
    weather_df.rename(columns={'Relative Humidity': 'humidity', 'Temperature': 'temperature', 'Pressure': 'pressure',
                               'DNI': 'solar_direct', 'DHI': 'solar_diffuse', 'Wind Speed': 'wind_speed'}, inplace=True)

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
    os.chdir("../EPW source weather files in csvformat")

    return 'weather_' + bus_str + '_' + location_str + '.dat'

def main(weather_path, bus_loc, extract:bool, getnames:bool, YYYY_MM_DD:str):



    if getnames:
        name_list = []
        for bus in bus_loc:
            bus_str = bus_loc[bus][0]
            location_str = bus_loc[bus][1]
            name_list.append('weather_' + bus + '_' + location_str + '.dat')


    if extract:
        name_list = []
        my_current_cwd = os.getcwd()
        os.chdir(weather_path + "EPW source weather files in csvformat")

        for bus in bus_loc:
            weather_file = bus_loc[bus][0]
            out_file = bus_loc[bus][1]
            filename = weatherdat(weather_file, bus, out_file, YYYY_MM_DD)
            name_list.append(filename)

        os.chdir(my_current_cwd)
    return name_list

if __name__ == '__main__':
    extract = True
    getnames = True
    YYYY_MM_DD = '2002-01-01'
    weather_path = "/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/data/8-node data/"
    bus_loc = {'AZ_Tucson': ['AZ_file', '_'],
    'WA_Tacoma': ['WA_file', '_'],
    'MT_Greatfalls': ['MT_file', '_']}

    name_list = main(weather_path, bus_loc, extract, getnames, YYYY_MM_DD)
