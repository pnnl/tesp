# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: TMY3toCSV.py
"""TMY3toCSV

Convert typical meteorological year version 3 (TMY3) data to
comma separated values (CSV) for common use by TESP agents.

Created on Tue Aug 14 10:05:06 2018
@author: liub725
"""

import io
import warnings
import dateutil

import pandas as pd
import matplotlib.pyplot as plt

from urllib.request import urlopen, Request


# DateOffset is not vectorized and will throw a nuisance warning
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)


def readtmy3(filename=None, coerce_year=None, recolumn=True):
    """
    Read a TMY3 file in to a pandas dataframe.
    """

    if filename is None:
        try:
            filename = _interactive_load()
        except:
            raise Exception('Interactive load failed. Tkinter not supported '
                            'on this system. Try installing X-Quartz and '
                            'reloading')

    head = ['USAF', 'Name', 'State', 'TZ', 'latitude', 'longitude', 'altitude']

    if filename.startswith('http'):
        request = Request(filename, headers={
            'User-Agent':
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 '
                'Safari/537.36'})
        response = urlopen(request)
        csvdata = io.StringIO(response.read().decode(errors='ignore'))
    else:
        # assume it's accessible via the file system
        csvdata = open(filename, 'r')

    # read in file metadata, advance buffer to second line
    firstline = csvdata.readline()
    if 'Request Rejected' in firstline:
        raise IOError('Remote server rejected TMY file request')

    meta = dict(zip(head, firstline.rstrip('\n').split(",")))

    # convert metadata strings to numeric types
    meta['altitude'] = float(meta['altitude'])
    meta['latitude'] = float(meta['latitude'])
    meta['longitude'] = float(meta['longitude'])
    meta['TZ'] = float(meta['TZ'])
    meta['USAF'] = int(meta['USAF'])

    # use pandas to read the csv file/stringio buffer
    # header is actually the second line in file, but tell pandas to look for
    # header information on the 1st line (0 indexing) because we've already
    # advanced past the true first line with the readline call above.
    data = pd.read_csv(
        csvdata, header=0,
        parse_dates={'datetime': ['Date (MM/DD/YYYY)', 'Time (HH:MM)']},
        date_parser=lambda *x: _parsedate(*x, year=coerce_year),
        index_col='datetime')

    # converters = {
    #     'Time (HH:MM)': lambda x: _parsehour(x),
    # }
    #
    # data = pd.read_csv(
    #     csvdata, header=0,
    #     parse_dates={'datetime': ['Date (MM/DD/YYYY)', 'Time (HH:MM)']},
    #     converters=converters,
    #     index_col='datetime'
    # )
    #
    # if coerce_year is not None:
    #     data['datetime'] = data['datetime'].replace(year=coerce_year)

    if recolumn:
        data = _recolumn(data)  # rename to standard column names

    data = data.tz_localize(int(meta['TZ'] * 3600))
    return data, meta


def _interactive_load():
    import Tkinter
    from tkFileDialog import askopenfilename
    Tkinter.Tk().withdraw()  # Start interactive file input
    return askopenfilename()


def _parsehour(hour):
    # return hour + ":00"
    if hour[0] == "0":
        return "0" + str(int(hour[1]) - 1) + hour[2:5] + ":00"
    return str(int(hour[0:2]) - 1) + hour[2:5] + ":00"


def _parsedate(ymd, hour, year=None):
    # stupidly complicated due to TMY3's usage of hour 24
    # and dateutil's inability to handle that.
    offset_hour = int(hour[:2]) - 1
    offset_datetime = '{} {}:00'.format(ymd, offset_hour)
    offset_date = dateutil.parser.parse(offset_datetime)
    true_date = offset_date + dateutil.relativedelta.relativedelta(hours=1)
    if year is not None:
        true_date = true_date.replace(year=year)
    return true_date


def _recolumn(tmy3_dataframe):
    """
    Rename the columns of the TMY3 DataFrame.

    Parameters
    ----------
    tmy3_dataframe : DataFrame
    inplace : bool
        passed to DataFrame.rename()

    Returns
    -------
    Recolumned DataFrame.
    """
    raw_columns = 'ETR (W/m^2),ETRN (W/m^2),GHI (W/m^2),GHI source,GHI uncert (%),DNI (W/m^2),DNI source,DNI uncert (%),DHI (W/m^2),DHI source,DHI uncert (%),GH illum (lx),GH illum source,Global illum uncert (%),DN illum (lx),DN illum source,DN illum uncert (%),DH illum (lx),DH illum source,DH illum uncert (%),Zenith lum (cd/m^2),Zenith lum source,Zenith lum uncert (%),TotCld (tenths),TotCld source,TotCld uncert (code),OpqCld (tenths),OpqCld source,OpqCld uncert (code),Dry-bulb (C),Dry-bulb source,Dry-bulb uncert (code),Dew-point (C),Dew-point source,Dew-point uncert (code),RHum (%),RHum source,RHum uncert (code),Pressure (mbar),Pressure source,Pressure uncert (code),Wdir (degrees),Wdir source,Wdir uncert (code),Wspd (m/s),Wspd source,Wspd uncert (code),Hvis (m),Hvis source,Hvis uncert (code),CeilHgt (m),CeilHgt source,CeilHgt uncert (code),Pwat (cm),Pwat source,Pwat uncert (code),AOD (unitless),AOD source,AOD uncert (code),Alb (unitless),Alb source,Alb uncert (code),Lprecip depth (mm),Lprecip quantity (hr),Lprecip source,Lprecip uncert (code),PresWth (METAR code),PresWth source,PresWth uncert (code)'

    new_columns = [
        'ETR', 'ETRN', 'GHI', 'GHISource', 'GHIUncertainty',
        'DNI', 'DNISource', 'DNIUncertainty', 'DHI', 'DHISource',
        'DHIUncertainty', 'GHillum', 'GHillumSource', 'GHillumUncertainty',
        'DNillum', 'DNillumSource', 'DNillumUncertainty', 'DHillum',
        'DHillumSource', 'DHillumUncertainty', 'Zenithlum',
        'ZenithlumSource', 'ZenithlumUncertainty', 'TotCld', 'TotCldSource',
        'TotCldUnertainty', 'OpqCld', 'OpqCldSource', 'OpqCldUncertainty',
        'DryBulb', 'DryBulbSource', 'DryBulbUncertainty', 'DewPoint',
        'DewPointSource', 'DewPointUncertainty', 'RHum', 'RHumSource',
        'RHumUncertainty', 'Pressure', 'PressureSource',
        'PressureUncertainty', 'Wdir', 'WdirSource', 'WdirUncertainty',
        'Wspd', 'WspdSource', 'WspdUncertainty', 'Hvis', 'HvisSource',
        'HvisUncertainty', 'CeilHgt', 'CeilHgtSource', 'CeilHgtUncertainty',
        'Pwat', 'PwatSource', 'PwatUncertainty', 'AOD', 'AODSource',
        'AODUncertainty', 'Alb', 'AlbSource', 'AlbUncertainty',
        'Lprecipdepth', 'Lprecipquantity', 'LprecipSource',
        'LprecipUncertainty', 'PresWth', 'PresWthSource',
        'PresWthUncertainty']

    mapping = dict(zip(raw_columns.split(','), new_columns))
    return tmy3_dataframe.rename(columns=mapping)


def weathercsv(tmyfile, outputfile, start_time, end_time, year_):
    """Converts TMY3 weather data to CSV in the requested time range

    :param tmyfile: string
        the input TMY3 data file
    :param outputfile: string
        the output CSV data file
    :param start_time: string
        the starting date and time of interest, like `2013-07-01 00:00:00`
    :param end_time: string
        the ending date and time of interest, like `2013-07-08 00:00:00`
    :param year: integer
        the year of interest
    :return: nothing
    """
    global dts
    global result2
    tmydata = readtmy3(tmyfile)
    print('  latitude', tmydata[1]['latitude'])
    print('  longitude', tmydata[1]['longitude'])
    print('  altitude', tmydata[1]['altitude'], 'm')
    print('  TZmeridian', 15.0 * tmydata[1]['TZ'])

    temperature = tmydata[0]['DryBulb'] * 1.8 + 32.0  # convert to Fahrenheit
    humidity = tmydata[0]['RHum'] / 100.0  # convert to per-unit
    solar_direct = tmydata[0].DNI * 0.09290304  # convert to W/sq foot
    solar_diffuse = tmydata[0].DHI * 0.09290304  # convert to W/sq foot
    pressure = tmydata[0]['Pressure']  # stays in mbar
    wind_speed = tmydata[0]['Wspd'] * 3600.0 / 1609.0  # convert to mph
    result = pd.concat([temperature, humidity, solar_direct, solar_diffuse, pressure, wind_speed],
                       axis=1,
                       keys=['temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed'])
    result.index = result.index.tz_localize(None)  # remove the time zone

    # 9.12 is a cloudy day

    result.index = result.index + pd.DateOffset(year=year_)  # change all the year index to a same one
    result2 = result.resample(rule='5Min', closed='left').first()
    result2 = result2.interpolate(method='quadratic')
    # get the weather data for give time period and remove the inproper value generated by interpolation 
    dts = result2.loc[start_time:end_time, :].copy()
    dts.solar_direct[dts.solar_direct < 0] = 0
    dts.solar_direct[dts.solar_direct < 1e-4] = 0
    dts.solar_diffuse[dts.solar_diffuse < 0] = 0
    dts.solar_diffuse[dts.solar_diffuse < 1e-4] = 0
    dts.wind_speed[dts.wind_speed < 0] = 0
    dts.wind_speed[dts.wind_speed < 1e-4] = 0
    dts.to_csv(outputfile, float_format='%.4f')


def weathercsv_cloudy_day(start_time, end_time, outputfile):
    day_weather = result2.loc[start_time:end_time, :]
    a = day_weather.temperature
    b = a.tolist()
    # define start and end time
    start_down = int(13 * 12)
    stop_down = int(13.125 * 12)
    start_up = int(14.5 * 12)
    stop_up = int(16 * 12)
    # define a down magnitude
    mag = 3
    slope_down = -mag / (stop_down - start_down)
    slope_up = mag / (stop_up - start_up)

    for i in range(len(b)):
        if start_down <= i <= stop_down:
            b[i] = b[i] + slope_down * (i - start_down)
        elif (i > stop_down) and (i < start_up):
            b[i] = b[i] - mag
        elif (i >= start_up) and (i <= stop_up):
            b[i] = b[i] - mag + slope_up * (i - start_up)
    plt.subplot(211)
    plt.plot(b)

    c = day_weather.solar_direct
    d = c.tolist()
    # the solar reduced factor
    solarR = 0.9
    start_mag = d[start_down]
    stop_mag = (1 - solarR) * d[stop_down]
    start_up_mag = (1 - solarR) * d[start_up]
    slope_down = -(start_mag - stop_mag) / (stop_down - start_down)
    slope_up = (d[stop_up] - start_up_mag) / (stop_up - start_up)
    for i in range(len(d)):
        if start_down <= i <= stop_down:
            d[i] = d[i] + slope_down * (i - start_down)
        elif (i > stop_down) and (i < start_up):
            d[i] = 0.1 * d[i]
        elif (i >= start_up) and (i <= stop_up):
            d[i] = start_up_mag + slope_up * (i - start_up)
    plt.subplot(212)
    plt.plot(d, color='r')
    pd.set_option('mode.chained_assignment', None)
    day_weather['temperature'] = b
    day_weather['solar_direct'] = d
    day_weather.to_csv(outputfile)


def _tests():
    from .data import weather_path

    # create a csv file contain the weather data for the input time period from the input tmy3 file
    weathercsv(weather_path + 'TX-Houston_Bush_Intercontinental.tmy3',
               'weather.csv', '2000-01-01 00:00:00', '2000-01-14 00:00:00', 2000)
    # create a csv file for a cloudy day for the selected date
    weathercsv_cloudy_day('2000-01-01 00:00:00', '2000-01-02 00:00:00', 'cloudy_day.csv')


if __name__ == '__main__':
    _tests()
