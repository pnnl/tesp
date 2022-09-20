# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: forecasting_dsot.py
"""Class responsible for forecasting 

Implements the substation level DA price forecast and load forecast

"""

import math
import re
import time as ti
from copy import deepcopy
from datetime import datetime, timedelta
from math import cos, sin

import glm
import numpy as np
import pandas as pd
import pytz

from .hvac_dsot import HVACDSOT
from .schedule_client import *


class Forecasting:
    """This Class perform the forecast

    Args:
        # TODO: update inputs
        # TODO: Load base case run files

    Attributes:
        # TODO: update attributes

    """

    def __init__(self, port, config_Q):
        """Initializes the class
        TODO: update __init__
        """
        """
           df : schedule dataframe for a year for schedule forecast
           windowLength : number of values that is to be forecast
           DA_output : forecast values as output
        """
        self.correct_Q_DA = config_Q['correct']
        if self.correct_Q_DA:
            self.gain_Q_DA = list(config_Q['Q_gain'])
            self.gain_t_65 = list(config_Q['t_65'])
            self.gain_t_65_2 = list(config_Q['t_65_2'])
            self.DC_change_Q_DA = list(config_Q['DC_change_Q_DA'])

        self.gProxy = DataClient(port).proxy
        self.sch_df_dict = {}
        self.solar_df = {}
        self.windowLength = 48
        self.sch_year = 2016
        self.DA_output = []
        self.extra_forecast_hours = 24

        # surface_angles from gridlabd
        self.surface_angles = {
            'H': 360,
            'N': 180,
            'NE': 135,
            'E': 90,
            'SE': 45,
            'S': 0,
            'SW': -45,
            'W': -90,
            'NW': -135
        }
        self.solar_gain_forecast = [0.0] * 48  # creating list of 48 length with all zeros
        self.solar_direct_forecast = [0.0] * 48
        self.solar_diffuse_forecast = [0.0] * 48

        self.NOerrors = bool(True)
        self.base_run_load = np.array([0.43, 0.41, 0.40, 0.39, 0.39, 0.40, 0.45, 0.45, 0.55, 0.80, 0.90, 0.98,
                                       0.99, 1.00, 1.00, 0.99, 0.98, 0.97, 0.97, 0.90, 0.70, 0.60, 0.55, 0.45,
                                       0.43, 0.41, 0.40, 0.39, 0.39, 0.40, 0.45, 0.45, 0.55, 0.80, 0.90, 0.98,
                                       0.99, 1.00, 1.00, 0.99, 0.98, 0.97, 0.97, 0.90, 0.70, 0.60, 0.55, 0.45])

        self.base_run_load_industrial = np.array([0.97, 0.99, 1.0, 1.01, 1.01, 1.0, 0.95, 0.95, 0.85, 0.6, 0.5,
                                                  0.42, 0.41, 0.4, 0.4, 0.41, 0.42, 0.43, 0.43, 0.5, 0.7, 0.8,
                                                  0.85, 0.95, 0.97, 0.99, 1.0, 1.01, 1.01, 1.0, 0.95, 0.95, 0.85,
                                                  0.6, 0.5, 0.42, 0.41, 0.4, 0.4, 0.41, 0.42, 0.43, 0.43, 0.5,
                                                  0.7, 0.8, 0.85, 0.95])

        self.retail_price_forecast = list()
        self.firstRun = True
        # data = pd.read_csv("C:\\Users\\sing492\\OneDrive - PNNL\\Documents\\Projects\\TESP_DSOT\\Hvac Debug Ahmad\\Qi_individual.csv",
        #                        index_col=0)
        # date_rng = pd.date_range(start='7/1/2013', end='7/10/2013', freq='H')
        # df = pd.DataFrame(date_rng, columns=['date'])
        # df['solar_gain'] = data['solar_gain'].tolist()
        # df['internal_gain'] = data['internal_gain'].tolist()
        # df['house_184'] = data['house_184'].tolist()
        # df['house_213'] = data['house_213'].tolist()
        # df['house_690'] = data['house_690'].tolist()
        # df['datetime'] = pd.to_datetime(df['date'])
        # df = df.set_index('datetime')
        # df.drop(['date'], axis=1, inplace=True)
        # self.solar_gain_data = df['solar_gain']
        # # self.solar_gain_forecast = self.solar_gain_data['2013-07-01':'2013-07-03']
        # self.internal_gain_data = df['internal_gain']
        # self.internal_gain_special1 = df['house_184']
        # self.internal_gain_special2 = df['house_213']
        # self.internal_gain_special3 = df['house_690']
        # # self.internal_gain_forecast = self.internal_gain_data['2013-07-01':'2013-07-03']

    def set_sch_year(self, year):
        self.sch_year = year

    @staticmethod
    def initialize_schedule_dataframe(start_time, end_time):
        """Initialize the data frame for one year

        Args:
            start_time (datetime, str) : time in str format - DD/MM/YYY HH:MT:SS
            end_time (datetime, str) : time in str format - DD/MM/YYY HH:MT:SS
        """
        # convert start_time and end_time to strings if they are in datetime
        if isinstance(start_time, datetime):
            start_time = start_time.strftime("%m/%d/%Y, %H:%M:%S")
        if isinstance(end_time, datetime):
            end_time = end_time.strftime("%m/%d/%Y, %H:%M:%S")
        # =============================================================================
        # #creating a time series data for a year with a minute of resolution
        # =============================================================================
        date_rng = pd.date_range(start=start_time, end=end_time, freq='T')
        sch_df = pd.DataFrame(index=date_rng)
        sch_df['data'] = np.ones((len(date_rng)), dtype=float)
        sch_df['month'] = pd.DatetimeIndex(sch_df.index).month
        sch_df['day'] = pd.DatetimeIndex(sch_df.index).day
        sch_df['dow'] = (pd.DatetimeIndex(sch_df.index).dayofweek + 1) % 7
        sch_df['hour'] = pd.DatetimeIndex(sch_df.index).hour
        sch_df['minute'] = pd.DatetimeIndex(sch_df.index).minute
        return sch_df

    def make_dataframe_schedule(self, filename, schedule_name):
        """Reads .glm files with multiple schedule names and makes dataframe for a year for given schedule name

        Args:
            filename (str): name of glm file to be loaded
            schedule_name (str): name of the schedule to be laoded
        """
        print("Reading and constructing 1 year dataframe for {} schedule from {}".format(schedule_name, filename))
        ip_file = glm.load(filename)
        data = [n for n in ip_file["schedules"] if n["name"] == schedule_name]
        temp1 = []
        if data[0]['values']:  # if value is not empty
            data_1 = data[0]['values']
            for i in range(len(data_1)):
                temp1.append(data_1[i].split())  # splitting each data with spaces as delimiter
        elif data[0]['children']:  # if children is not empty
            # flatten all children to one list
            data_1 = [[j for sub in data[0]['children'] for j in sub]]
            for i in range(len(data_1[0])):
                temp1.append(data_1[0][i].split())  # splitting each data with spaces as delimiter
        else:
            raise ValueError("Given schedules is empty!!")
        # =============================================================================
        #  ###Reading the values from teh glm file and modifying it in the dataframe
        # =============================================================================
        #        temp1 =[]
        #        for i in range(len(data_1)):
        #            temp1.append(data_1[i].split())  #splitting each data with spaces as delimiter

        ########## Initializing the datframe for 1 year with values as 1
        sch_df_start_time = datetime(self.sch_year, 1, 1, 0, 0)
        sch_df_end_time = datetime(self.sch_year, 12, 31, 23, 59, 0)
        sch_df = self.initialize_schedule_dataframe(sch_df_start_time, sch_df_end_time)

        for temp_i in range(len(temp1)):
            # minute
            minute = temp1[temp_i][0]
            if minute == '*':
                pass
            else:
                min_1 = minute.split("-")
                min_1 = list(map(int, min_1))
                ###making list of the values in the schedule for this data
                if len(min_1) == 2:
                    min_1 = list(range(min_1[0], min_1[1] + 1))
                elif len(min_1) == 4:
                    min_1 = list(range(min_1[0], min_1[1] + 1)) + list(range(min_1[2], min_1[3] + 1))
                temp1[temp_i][0] = min_1
            # hour
            hour = temp1[temp_i][1]
            if hour == '*':
                pass
            else:
                hour_1 = hour.split("-")
                hour_1 = list(map(int, hour_1))
                ###making list of the values in the schedule for this data
                if len(hour_1) == 2:
                    hour_1 = list(range(hour_1[0], hour_1[1] + 1))
                elif len(hour_1) == 4:
                    hour_1 = list(range(hour_1[0], hour_1[1] + 1)) + list(range(hour_1[2], hour_1[3] + 1))
                temp1[temp_i][1] = hour_1
            # second
            second = temp1[temp_i][2]
            # month
            month = temp1[temp_i][3]
            if month == '*':
                pass
            else:
                month_1 = re.split('[-,]', month)
                month_1 = list(map(int, month_1))
                ###making list of the values in the schedule for this data
                if len(month_1) == 2:
                    month_1 = list(range(month_1[0], month_1[1] + 1))
                elif len(month_1) == 4:
                    month_1 = list(range(month_1[0], month_1[1] + 1)) + list(range(month_1[2], month_1[3] + 1))
                elif len(month_1) == 6:
                    month_1 = list(range(month_1[0], month_1[1] + 1)) + list(
                        range(month_1[2], month_1[3] + 1)) + list(range(month_1[4], month_1[5] + 1))
                temp1[temp_i][3] = month_1
                ############day of the week
            dayofWeek = temp1[temp_i][4]
            if dayofWeek == '*':
                pass
            else:
                dow_1 = re.split('[-,]', dayofWeek)
                dow_1 = list(map(int, dow_1))
                ###making list of the values in the schedule for this data
                if 0 in dow_1 or 6 in dow_1:
                    dow_1 = dow_1
                else:
                    if len(dow_1) == 2:
                        dow_1 = list(range(dow_1[0], dow_1[1] + 1))
                    elif len(dow_1) == 4:
                        dow_1 = list(range(dow_1[0], dow_1[1] + 1)) + list(range(dow_1[2], dow_1[3] + 1))
                temp1[temp_i][4] = dow_1
            ##############value from GLD
            temp1[temp_i][5] = float(temp1[temp_i][5])
            ##########replacing the datframe with value from GLD
            # print('Iteration', temp_i)
            month = list(temp1[temp_i][3])
            dayofWeek = list(temp1[temp_i][4])
            hour = list(temp1[temp_i][1])
            minute = list(temp1[temp_i][0])

            if '*' in month:
                df_m = deepcopy(sch_df)
            else:
                df_m = sch_df[(sch_df['month'].isin(month))]
            if '*' in dayofWeek:
                df_d = deepcopy(df_m)
            else:
                df_d = df_m[(df_m['dow'].isin(dayofWeek))]
            if '*' in hour:
                df_h = deepcopy(df_d)
            else:
                df_h = df_d[(df_d['hour'].isin(hour))]
            if '*' in minute:
                df_mt = deepcopy(df_h)
            else:
                df_mt = df_h[(df_h['minute'].isin(minute))]
            sch_df.loc[sch_df.index.isin(list(df_mt.index)), 'data'] = temp1[temp_i][5]
            sch_df.index.name = 'Timestamp'
        self.sch_df_dict[schedule_name] = sch_df

    def add_skew_scalar(self, datafr, N_skew, N_scalar):
        """ Skew the values with given seconds and multiply by scalar in the whole year dataframe

            Args:
            datafr (DataFrame): dataframe created with the schedule name for a year
            N_skew (int): number of seconds to skew either (+ or -)
       """
        df = deepcopy(datafr)
        if N_skew != 0:
            if N_skew < 0:  # saving the values of shifted data
                # print(N_skew)
                # print(abs(N_skew // 60))
                df_shifted = df.data[0:abs(N_skew // 60)]
            else:
                df_shifted = df.data[len(df) - abs(N_skew // 60):len(df)]

            df_skewed = df.data.shift(periods=N_skew // 60)  # #skew the data

            if N_skew < 0:  # #replacing the shifted values in a circular way
                df_skewed[len(df) - abs(N_skew // 60):len(df)] = df_shifted
            else:
                df_skewed[0:abs(N_skew // 60)] = df_shifted

            df.data = df_skewed * N_scalar
        else:
            df.data = df.data * N_scalar
        return df

    def forecasting_schedules(self, name, time, len_forecast=48):
        self.DA_output = self.gProxy.forecasting_schedules(name, time, len_forecast)
        return self.DA_output

    def set_solar_diffuse_forecast(self, fncs_str):
        """ Set the 48-hour solar diffuse forecast
        Args:
            param fncs_str: solar_diffuse_forecast ([float x 48]):
        """
        solar_diffuse_forecast = eval(fncs_str)
        self.solar_diffuse_forecast = [float(solar_diffuse_forecast[key]) for key in solar_diffuse_forecast.keys()]

    def set_solar_direct_forecast(self, fncs_str):
        """ Set the 48-hour solar direct forecast
        Args:
            param fncs_str: solar_direct_forecast ([float x 48]):
        """
        solar_direct_forecast = eval(fncs_str)
        self.solar_direct_forecast = [float(solar_direct_forecast[key]) for key in solar_direct_forecast.keys()]

    def set_temperature_forecast(self, fncs_str):
        """ Set the 48-hour temperature forecast

        Args:
            fncs_str: temperature_forecast ([float x 48]): predicted temperature in F
        """
        temperature_forecast = eval(fncs_str)
        self.temperature_forecast = [float(temperature_forecast[key]) for key in temperature_forecast.keys()]
        # log.info('FORECAST AGENT ' + str(self.temperature_forecast) )

    def get_substation_unresponsive_load_forecast(self, peak_load=7500.0):
        """Get substation unresponsive load forecast

        TODO: Update to model that make use of the base case run files
        TODO: Get weather forecast from weather agent

        Args:
            peak_load (float): peak load in kWh

        Return:
            base_run_load (float x 48): forecast of next 48-hours unresponsive load
        """
        if self.NOerrors:
            self.base_run_load = np.roll(self.base_run_load, -1)

        load = self.base_run_load / max(self.base_run_load) * peak_load

        return deepcopy(load.tolist())

    def calc_solargain(self, day_of_yr, time, dnr, dhr, lat, lon, tz_offset):
        # implementing gridlabd solargain calculation from climate.cpp and house_e.cpp
        rad = (2.0 * math.pi * day_of_yr) / 365.0
        eq_time = (0.5501 * cos(rad) - 3.0195 * cos(2 * rad) - 0.0771 * cos(3 * rad)
                   - 7.3403 * sin(rad) - 9.4583 * sin(2 * rad) - 0.3284 * sin(3 * rad)) / 60.0
        tz_meridian = 15 * tz_offset
        std_meridian = tz_meridian * math.pi / 180
        solar_gain_forecast = []
        for i in range(len(time)):
            std_time = time[i]
            sol_time = std_time + eq_time + 12.0 / math.pi * (lon - std_meridian)
            dnr_i = dnr[i]
            dhr_i = dhr[i]
            solar_flux = []
            for cpt in self.surface_angles.keys():
                vertical_angle = math.radians(90)
                if cpt == 'H':
                    vertical_angle = math.radians(0)
                solar_flux.append(self.calc_solar_flux(cpt, day_of_yr, lat, sol_time, dnr_i, dhr_i, vertical_angle))
            avg_solar_flux = sum(solar_flux[1:9]) / 8
            solar_btu = avg_solar_flux * 3.412  # incident_solar_radiation is now in Btu/(h*sf)
            solar_gain_forecast.append(solar_btu)
        return solar_gain_forecast

    def calc_solar_flux(self, cpt, day_of_yr, lat, sol_time, dnr_i, dhr_i, vertical_angle):
        az = math.radians(self.surface_angles[cpt])
        if cpt == 'H':
            az = math.radians(self.surface_angles['E'])
        # based on GLD calculations
        # cos_incident(lat,RAD(vert_angle),RAD(surface_angle),sol_time,doy)
        hr_ang = -(15.0 * math.pi / 180) * (sol_time - 12.0)
        decl = 0.409280 * sin(2.0 * math.pi * (284 + day_of_yr) / 365)
        slope = vertical_angle
        sindecl = sin(decl)
        cosdecl = cos(decl)
        sinlat = sin(lat)
        coslat = cos(lat)
        sinslope = sin(slope)
        cosslope = cos(slope)
        sinaz = sin(az)
        cosaz = cos(az)
        sinhr = sin(hr_ang)
        coshr = cos(hr_ang)
        cos_incident = sindecl * sinlat * cosslope \
                       - sindecl * coslat * sinslope * cosaz \
                       + cosdecl * coslat * cosslope * coshr \
                       + cosdecl * sinlat * sinslope * cosaz * coshr \
                       + cosdecl * sinslope * sinaz * sinhr
        if cos_incident < 0:
            cos_incident = 0
        return dnr_i * cos_incident + dhr_i

    def get_solar_gain_forecast(self, climate_conf, current_time):
        lat = math.radians(float(climate_conf['latitude']))  # converting to radians
        lon = math.radians(float(climate_conf['longitude']))
        tz = pytz.timezone("US/Central")  # TODO: should pull from somewhere rather than hardcoding
        dst = tz.localize(current_time).dst()  # to get if daylight saving is On or not
        if dst:
            tz_offset = -5  # when daylight saving is on, offset for central time zone is UTC-5
        else:
            tz_offset = -6  # otherwise UTC-6
        day_of_yr = current_time.timetuple().tm_yday  # get day of year from datetime
        dnr = self.solar_direct_forecast
        dhr = self.solar_diffuse_forecast
        # start_hour = math.ceil(current_time.hour + current_time.minute/60)
        start_hour = current_time.hour
        time = (np.array(range(start_hour, start_hour + 48)) % 24).tolist()

        self.solar_gain_forecast = self.calc_solargain(day_of_yr, time, dnr, dhr, lat, lon, tz_offset)
        # this solar_gain_forecast is nominal value and needs to be multiplied with heatgain_factor of the house

        # now = pd.Timestamp(time)
        # DA48h = now + pd.Timedelta('2 day') # 48-hour DA forecast window
        # self.solar_gain_forecast = self.solar_gain_data[now:DA48h].to_numpy().tolist()
        return self.solar_gain_forecast

    def get_internal_gain_forecast(self, skew_scalar, time, extra_forecast_hours=0):
        """
        Forecast the electric zip_load and internal gain of all zip loads of a house by reading schedule files and
        applying skew. Forecast is for 48-hours ahead from start time
        :param skew_scalar: dictionary containing 'zip_skew', 'zip_scalar' and 'zip_heatgain_fraction' for each zip load
        'zip_skew' is a scalar and same for all type of zip loads for the given house. 'zip_scalar' and 'zip_heatgain_fraction'
        are dictionary containing different values for each tyoe of zip load
        :param time: Datetime format: forecast start time
        :param extra_forecast_hours: (int) number of hours for which forecast needs to be stored. For example if it is 24, then
        we need to get forecast for 48+24=72 hours so that there is no need to come back to this function for next 24-hours.
        :return: list of (48+extra_forecast_hours) values of total zipl loads and total internal gain due to zip loads
        """
        len_forecast = self.windowLength + extra_forecast_hours
        zip_load = [0.0] * len_forecast
        int_gain = [0.0] * len_forecast
        time_eff = time - timedelta(minutes=skew_scalar['zip_skew'] // 60)
        for zip_name, scalar in skew_scalar['zip_scalar'].items():
            pf = skew_scalar['zip_power_pf'][zip_name]  # power factor
            p_frac = skew_scalar['zip_power_fraction'][zip_name]  # constant power fraction
            temp = self.forecasting_schedules(zip_name, time_eff, len_forecast) * scalar * pf  # forecast values
            # if p_frac > 0, we take it as 1 because we don't consider constant current and impedance load
            # if p_frac = 0, it means the load is heatgain only where zip_load is considered 0 but not internal gain
            if p_frac == 0:
                zip_load = zip_load + temp * p_frac  # adding up zip_loads
                int_gain = int_gain + temp * skew_scalar['zip_heatgain_fraction'][
                    zip_name] * 3412  # adding up int gains
            else:
                zip_load = zip_load + temp * 1  # adding up zip_loads
                int_gain = int_gain + temp * skew_scalar['zip_heatgain_fraction'][
                    zip_name] * 3412  # adding up int gains
        return zip_load.tolist(), int_gain.tolist()

    def get_waterdraw_forecast(self, skew_scalar, time):
        time_eff = time - timedelta(minutes=skew_scalar['wh_skew'] // 60)
        waterdraw_sch = self.forecasting_schedules(skew_scalar['wh_schedule_name'], time_eff)  # forecasted values
        waterdraw_sch = waterdraw_sch * skew_scalar['wh_scalar']  # skewed and scaled data
        waterdraw_sch = waterdraw_sch.tolist()
        return waterdraw_sch

    def get_solar_forecast(self, time, dso_num):
        time = time.replace(minute=0, second=0)
        print("***** time *****", time)
        # temp = self.solar_df.loc[pd.date_range(time, periods=self.windowLength, freq='H')][dso_num]
        temp = self.gProxy.forecasting_pv_schedules('pv_power', time, self.windowLength, dso_num)
        return temp.values.tolist()

    def set_retail_price_forecast(self, DA_SW_prices):
        """Set substation price forecast

        Nonsummable diminishing.

        Args:
            DA_SW_prices (float x 48): cleared price in $/kWh from the last shifting window run

        Return:
            forecasted_price (float x 48): forecasted prices in $/kWh for the next 48-hours
        """
        temp = deepcopy(DA_SW_prices)
        temp = np.array(temp)
        if self.firstRun:
            self.firstRun = False
            self.retail_price_forecast = (np.roll(temp, -1)).tolist()
        else:
            deltaP = np.array(self.retail_price_forecast) - temp
            a = 0.2
            k = np.flip((np.arange(1, 49, 1)))
            alpha = a / (k ** 0.5)
            temp = np.array(self.retail_price_forecast) - alpha * deltaP

            temp = (np.roll(temp, -1)).tolist()

            self.retail_price_forecast = deepcopy(temp)

    def get_substation_unresponsive_industrial_load_forecast(self, peak_load=3500.0):
        """Get substation unresponsive industrial load forecast

         Args:
            peak_load (float): peak load in kWh

        Return:
            base_run_load (float x 48): forecast of next 48-hours unresponsive load
        """
        if self.NOerrors:
            self.base_run_load_industrial = np.roll(self.base_run_load_industrial, -1)

        industrial_load = self.base_run_load_industrial * peak_load

        return deepcopy(industrial_load.tolist())

    def correcting_Q_forecast_10_AM(self, Q_10_AM, offset, day_of_week):
        """ Correcs the quantity submited to the wolsale market at 10 AM
        
        Args:
            Q_10_AM (list of 24 float): DA quantities
        
        Returns:
            Corrected 10 AM Quantities 

        """
        if self.correct_Q_DA:
            day = day_of_week + 1
            if day > 6:
                day = 0
            t_65 = abs(np.array(self.temperature_forecast[offset:offset + 24]) - 65)
            t_65_2 = t_65 ** 2
            Q_10_AM = np.array(Q_10_AM)
            if day < 5:
                idx = 0
            else:
                idx = 1
            new_Q = Q_10_AM * self.gain_Q_DA[idx] + t_65 * self.gain_t_65[idx] + t_65_2 * self.gain_t_65_2[idx] + \
                    self.DC_change_Q_DA[idx]
            return list(new_Q / 100.0)
        else:
            return Q_10_AM


def test():
    # a demo house agent object
    hvac_properties = {
        "feeder_id": "R5_12.47_2",
        "billingmeter_id": "R5_12_47_2_tn_3_mtr_1",
        "sqft": 3977.0,
        "stories": 1,
        "doors": 4,
        "thermal_integrity": "ABOVE_NORMAL",
        "cooling": "ELECTRIC",
        "heating": "GAS",
        "wh_gallons": 0,
        "house_class": "SINGLE_FAMILY",
        "Rroof": 45.95,
        "Rwall": 25.24,
        "Rfloor": 33.73,
        "Rdoors": 12.19,
        "airchange_per_hour": 0.28,
        "ceiling_height": 9,
        "thermal_mass_per_floor_area": 3.406,
        "glazing_layers": 3,
        "glass_type": 2,
        "window_frame": 4,
        "glazing_treatment": 2,
        "cooling_COP": 3.8,
        "over_sizing_factor": 0.3038,
        "fuel_type": "gas",
        "aspect_ratio": 1,
        "exterior_ceiling_fraction": 1,
        "exterior_floor_fraction": 1,
        "exterior_wall_fraction": 1,
        "window_exterior_transmission_coefficient": 1,
        "zip_skew": 1076.0,
        "zip_heatgain_fraction": {
            "constant": 1.0,
            "responsive_loads": 0.9,
            "unresponsive_loads": 0.9
        },
        "zip_scalar": {
            "constant": 0.0,
            "responsive_loads": 1.43,
            "unresponsive_loads": 1.32
        }
    }
    hvac_dict = {
        "houseName": "R5_12_47_2_tn_3_hse_1",
        "meterName": "R5_12_47_2_tn_3_mtr_1",
        "houseClass": "SINGLE_FAMILY",
        "period": 300,
        "wakeup_start": 6.807,
        "daylight_start": 9.178,
        "evening_start": 18.96,
        "night_start": 23.9,
        "weekend_day_start": 9.362,
        "weekend_night_start": 23.749,
        "wakeup_set_cool": 74.0,
        "daylight_set_cool": 74.0,
        "evening_set_cool": 74.0,
        "night_set_cool": 72.0,
        "weekend_day_set_cool": 74.0,
        "weekend_night_set_cool": 72.0,
        "wakeup_set_heat": 69.0,
        "daylight_set_heat": 69.0,
        "evening_set_heat": 69.0,
        "night_set_heat": 69.0,
        "weekend_day_set_heat": 69.0,
        "weekend_night_set_heat": 69.0,
        "deadband": 2.892,
        "ramp_high_limit": 2.0,
        "ramp_low_limit": 2.0,
        "range_high_limit": 5.0,
        "range_low_limit": 5.0,
        "slider_setting": 0.3105,
        "price_cap": 1.0,
        "bid_delay": 45,
        "house_participating": False,
        "cooling_participating": False,
        "heating_participating": False
    }
    start_time = '2016-08-12 05:59:00'
    time_format = '%Y-%m-%d %H:%M:%S'
    sim_time = datetime.strptime(start_time, time_format)
    hvac_obj = HVACDSOT(hvac_dict, hvac_properties, 'abc', 11, sim_time, 'cplex')

    Q_DA = {"correct": True,
            "gain": [10, 0.5, 0.1],
            "DC_change": [1, 2, 3]}
    # testing internal gain calculation and speed
    current_time = datetime(2016, 7, 1, 0, 59)
    obj = Forecasting(800, Q_DA)
    print('\n\n\n\n\n\n\n\n')
    print('Q DA correction')
    temp = obj.correcting_Q_forecast_10_AM([10, 11, 12])
    print(temp)
    print('\n\n\n\n\n\n\n\n')
    # instead of running the following block to load schedules, simply run in a terminal:
    # python -c "import tesp_support.schedule_server as schedule;schedule.schedule_server(5550)"

    # obj.set_sch_year(current_time.year)
    # sch = ['responsive_loads', 'unresponsive_loads']
    # obj.sch_df_dict[sch[0]] = pd.read_csv('../../../examples/analysis/dsot/data/schedule_df/' + sch[0] + '.csv', index_col=0)
    # obj.sch_df_dict[sch[1]] = pd.read_csv('../../../examples/analysis/dsot/data/schedule_df/' + sch[1] + '.csv', index_col=0)
    # just make sure that index of all df is datetime
    # obj.sch_df_dict[sch[0]].index = pd.to_datetime(obj.sch_df_dict[sch[0]].index)
    # obj.sch_df_dict[sch[1]].index = pd.to_datetime(obj.sch_df_dict[sch[1]].index)

    t = ti.time()
    del_t = 3600
    # obj.extra_forecast_hours = 10  # give me forecast enough so that I only need to come back after this duration (hours)
    for h in range(0, 24 * 4):
        for i in range(0, 1):
            skew_scalar = {'zip_skew': int(-4456.0),
                           'zip_scalar': {'responsive_loads': 1.3,
                                          'unresponsive_loads': 1.14},
                           'zip_heatgain_fraction': {'responsive_loads': 0.9,
                                                     'unresponsive_loads': 0.9},
                           'zip_power_fraction': {'responsive_loads': 1,
                                                  'unresponsive_loads': 1},
                           'zip_power_pf': {'responsive_loads': 1,
                                            'unresponsive_loads': 1}
                           }
            if len(hvac_obj.full_internalgain_forecast) < 48:  # after every forecast interval hours
                forecast_zpload, forecast_internalgain = obj.get_internal_gain_forecast(skew_scalar,
                                                                                        current_time + timedelta(0, 60),
                                                                                        obj.extra_forecast_hours)
                hvac_obj.store_full_internalgain_forecast(forecast_internalgain)
                hvac_obj.store_full_zipload_forecast(forecast_zpload)
            hvac_obj.set_internalgain_forecast(hvac_obj.full_internalgain_forecast[0:48])
            hvac_obj.set_zipload_forecast(hvac_obj.full_forecast_ziploads[0:48])
            # remove the first entry to make next hour as the first entry
            hvac_obj.full_internalgain_forecast.pop(0)
            hvac_obj.full_forecast_ziploads.pop(0)
            if len(hvac_obj.internalgain_forecast) != 48:
                raise ValueError()
        current_time = current_time + timedelta(0, del_t)
    elapsed = ti.time() - t
    print('elapsed time is: ', elapsed)
    expected_internalgain = [2446.6813956, 2418.4883807999995, 2469.07674, 2732.7571236000003, 3182.8918770000005,
                             3530.7659195999995, 3712.799872800001, 3889.7608644000006, 3984.3998496000004,
                             4024.4430815999995, 3991.1847822, 3886.551878399999, 3842.1127961999996,
                             3939.2114921999987, 4243.7980026, 4612.4521488, 4662.512330400001, 4650.728135399999,
                             4922.179178399999, 5078.3523894, 4486.8257208, 3492.1291140000003, 2837.5589214,
                             2570.8062024, 2446.6813956, 2418.4883807999995, 2469.07674, 2732.7571236000003,
                             3182.8918770000005, 3530.7659195999995, 3712.799872800001, 3889.7608644000006,
                             3984.3998496000004, 4024.4430815999995, 3991.1847822, 3886.551878399999,
                             3842.1127961999996, 3939.2114921999987, 4243.7980026, 4612.4521488, 4662.512330400001,
                             4650.728135399999, 4922.179178399999, 5078.3523894, 4486.8257208, 3492.1291140000003,
                             2837.5589214, 2570.8062024]

    print(sum(np.array(expected_internalgain) - np.array(hvac_obj.internalgain_forecast)))
    # # Testing solargain calculation
    # obj = Forecasting()
    # solar_dhr = [0.0 for i in range(48)]
    # solar_dhr[0:15] = [0.836127000000000,5.38838000000000,9.01159000000000,11.9845000000000,14.2142000000000,19.9742000000000,26.7561000000000,27.9638000000000,22.3896000000000,25.6412000000000,17.1871000000000,18.2090000000000,14.0284000000000,4.45935000000000,0.185806000000000]
    # solar_dnr = [0.0 for i in range(48)]
    # solar_dnr[0:15] = [2.32258000000000, 31.1225000000000, 52.9547000000000, 64.3818000000000, 70.7921000000000,
    #                    66.7044000000000, 59.8296000000000, 46.3586000000000, 55.1844000000000, 49.6102000000000,
    #                    55.7418000000000, 50.4464000000000, 13.2851000000000, 6.68902000000000, 0]
    # current_time = datetime(2013, 7, 1, 6, 59)
    # climate_conf = {'latitude': 30,
    #                 'longitude': -95.367}
    # obj.solar_direct_forecast = solar_dnr
    # obj.solar_diffuse_forecast = solar_dhr
    # solargain = obj.get_solar_gain_forecast(climate_conf, current_time + timedelta(0, 60))

    # # testing internalgain calculation
    # current_time = datetime(2016, 7, 1, 0, 59)
    # obj = Forecasting()
    # obj.set_sch_year(current_time.year)
    # sch = ['responsive_loads', 'unresponsive_loads']
    # obj.sch_df_dict[sch[0]] = pd.read_csv('../../../examples/analysis/dsot/data/schedule_df/' + sch[0] + '.csv', index_col=0)
    # obj.sch_df_dict[sch[1]] = pd.read_csv('../../../examples/analysis/dsot/data/schedule_df/' + sch[1] + '.csv', index_col=0)
    # # just make sure that index of all df is datetime
    # obj.sch_df_dict[sch[0]].index = pd.to_datetime(obj.sch_df_dict[sch[0]].index)
    # obj.sch_df_dict[sch[1]].index = pd.to_datetime(obj.sch_df_dict[sch[1]].index)
    # t = ti.time()
    # for i in range(0, 1):
    #     skew_scalar = {'zip_skew': int(-4456.0),
    #                    'zip_scalar': {'responsive_loads': 1.3,
    #                                   'unresponsive_loads': 1.14},
    #                    'zip_heatgain_fraction': {'responsive_loads': 0.9,
    #                                              'unresponsive_loads': 0.9}
    #                    }
    #     forecast_zpload, forecast_internalgain = obj.get_internal_gain_forecast(skew_scalar,
    #                                                                             current_time + timedelta(0, 60))
    # elapsed = ti.time() - t
    # print('elapsed time is: ', elapsed)
    # expected_internalgain = [2446.6813956, 2418.4883807999995, 2469.07674, 2732.7571236000003, 3182.8918770000005,
    #                          3530.7659195999995, 3712.799872800001, 3889.7608644000006, 3984.3998496000004,
    #                          4024.4430815999995, 3991.1847822, 3886.551878399999, 3842.1127961999996,
    #                          3939.2114921999987, 4243.7980026, 4612.4521488, 4662.512330400001, 4650.728135399999,
    #                          4922.179178399999, 5078.3523894, 4486.8257208, 3492.1291140000003, 2837.5589214,
    #                          2570.8062024, 2446.6813956, 2418.4883807999995, 2469.07674, 2732.7571236000003,
    #                          3182.8918770000005, 3530.7659195999995, 3712.799872800001, 3889.7608644000006,
    #                          3984.3998496000004, 4024.4430815999995, 3991.1847822, 3886.551878399999,
    #                          3842.1127961999996, 3939.2114921999987, 4243.7980026, 4612.4521488, 4662.512330400001,
    #                          4650.728135399999, 4922.179178399999, 5078.3523894, 4486.8257208, 3492.1291140000003,
    #                          2837.5589214, 2570.8062024]

    # # testing waterdraw calculation
    # current_time = datetime(2016, 7, 1, 1, 59)
    # obj = Forecasting()
    # obj.set_sch_year(current_time.year)
    # sch = ['small_1', 'small_2', 'small_3', 'small_4', 'small_5', 'small_6',
    #           'large_1', 'large_2', 'large_3', 'large_4', 'large_5', 'large_6']
    # for s in sch:
    #     obj.sch_df_dict[s] = pd.read_csv('../../../examples/analysis/dsot/data/schedule_df/' + s + '.csv', index_col=0)
    #     obj.sch_df_dict[s].index = pd.to_datetime(obj.sch_df_dict[s].index)
    # t = ti.time()
    # skew_scalar = {'wh_skew': int(-4456.0),
    #                'wh_scalar': 1,
    #                'wh_schedule_name': 'small_1'
    #                }
    # forecast_draw= obj.get_waterdraw_forecast(skew_scalar, current_time + timedelta(0, 60))
    #
    # # ## ## ## ## ## ## # Plots configuration
    # import matplotlib.pyplot as plt
    # plt.rcParams['figure.figsize'] = (5, 3)
    # plt.rcParams['figure.dpi'] = 100
    # SMALL_SIZE = 10
    # MEDIUM_SIZE = 12
    # BIGGER_SIZE = 14
    # plt.rcParams["font.family"] = "Times New Roman"
    # plt.rc('font', size=SMALL_SIZE)  # controls default text sizes
    # plt.rc('axes', titlesize=SMALL_SIZE)  # fontsize of the axes title
    # plt.rc('axes', labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
    # plt.rc('xtick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
    # plt.rc('ytick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
    # plt.rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
    # plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
    # ############## "Input" get_price_forecast
    # x = np.arange(1, 49, dtype=float)
    # y1 = np.zeros(48)
    # y1[0] = 100.0
    # y1[47] = 100.0
    # y1[24] = 50.0
    # F_obj = Forecasting()  # make object
    # F_obj.set_retail_price_forecast(y1)
    # y2 = F_obj.retail_price_forecast
    # y2[15] = 30
    # F_obj.set_retail_price_forecast(y2)
    # y2 = F_obj.retail_price_forecast
    # y2[14] = 50
    # F_obj.set_retail_price_forecast(y2)
    # y2 = F_obj.retail_price_forecast
    # y2[13] = 80
    # F_obj.set_retail_price_forecast(y2)
    # y2 = F_obj.retail_price_forecast
    # y2[12] = 150
    # F_obj.set_retail_price_forecast(y2)
    # y2 = F_obj.retail_price_forecast
    # # ##Plots
    # plt.step(x, y1, marker='o', label='DA_SW_prices')
    # plt.step(x, y2, marker='x', label='forecasted_price')
    # plt.legend()
    # plt.grid(True)
    # plt.ylabel('price ($/kWh)')
    # plt.xlabel('time ahead (hours)')
    # plt.show()
    # ############## forecast
    # y3 = F_obj.get_substation_unresponsive_load_forecast()
    # y4 = F_obj.get_substation_unresponsive_load_forecast()
    # # ##Plots
    # plt.step(x, y3)
    # plt.step(x, y4)
    # plt.grid(True)
    # plt.ylabel('unresponsive load (kWh)')
    # plt.xlabel('time ahead (hours)')
    # plt.show()


if __name__ == "__main__":
    test()

