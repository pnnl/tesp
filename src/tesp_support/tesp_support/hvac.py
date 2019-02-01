# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: hvac.py
import math
import tesp_support.helpers as helpers

class hvac:
    def __init__(self,dict,key,aucObj):
        self.name = key
        self.control_mode = dict['control_mode']
        self.houseName = dict['houseName']
        self.meterName = dict['meterName']
        self.period = float(dict['period'])
        self.wakeup_start = float(dict['wakeup_start'])
        self.daylight_start = float(dict['daylight_start'])
        self.evening_start = float(dict['evening_start'])
        self.night_start = float(dict['night_start'])
        self.wakeup_set = float(dict['wakeup_set'])
        self.daylight_set = float(dict['daylight_set'])
        self.evening_set = float(dict['evening_set'])
        self.night_set = float(dict['night_set'])
        self.weekend_day_start = float(dict['weekend_day_start'])
        self.weekend_day_set = float(dict['weekend_day_set'])
        self.weekend_night_start = float(dict['weekend_night_start'])
        self.weekend_night_set = float(dict['weekend_night_set'])
        self.deadband = float(dict['deadband'])
        self.offset_limit = float(dict['offset_limit'])
        self.ramp = float(dict['ramp'])
        self.price_cap = float(dict['price_cap'])
        self.bid_delay = float(dict['bid_delay'])
        self.use_predictive_bidding = float(dict['use_predictive_bidding'])

        self.std_dev = aucObj.std_dev
        self.mean = aucObj.clearing_price

        self.Trange = abs (2.0 * self.offset_limit)

        self.air_temp = 78.0
        self.hvac_kw = 3.0
        self.mtr_v = 120.0
        self.hvac_on = False

        self.basepoint = 0.0
        self.setpoint = 0.0
        self.cleared_price = 0.0
        self.bid_price = 0.0

    def inform_bid (self,price):
        self.cleared_price = price

    # bid is always "accepted"; if I didn't bid high enough, I might have to turn the thermostat up
    def bid_accepted (self):
        if self.std_dev > 0.0:
            offset = (self.cleared_price - self.mean) * self.Trange / self.ramp / self.std_dev
            if offset < -self.offset_limit:
                offset = -self.offset_limit
            elif offset > self.offset_limit:
                offset = self.offset_limit
            self.setpoint = self.basepoint + offset
            return True
        return False

    def formulate_bid (self):
        p = self.mean + (self.air_temp - self.basepoint) * self.ramp * self.std_dev / self.Trange
        if p >= self.price_cap:
            self.bid_price = self.price_cap
        elif p <= 0.0:
            self.bid_price = 0.0
        else:
            self.bid_price = p
        return [self.bid_price, self.hvac_kw, self.hvac_on]

    def change_basepoint (self,hod,dow):
        if dow > 4: # a weekend
            val = self.weekend_night_set
            if hod >= self.weekend_day_start and hod < self.weekend_night_start:
                val = self.weekend_day_set
        else: # a weekday
            val = self.night_set
            if hod >= self.wakeup_start and hod < self.daylight_start:
                val = self.wakeup_set
            elif hod >= self.daylight_start and hod < self.evening_start:
                val = self.daylight_set
            elif hod >= self.evening_start and hod < self.night_start:
                val = self.evening_set
        if abs(self.basepoint - val) > 0.1:
            self.basepoint = val
            return True
        return False

    def set_hvac_load (self,str):
        val = helpers.parse_fncs_number (str)
        if val > 0.0:
            self.hvac_kw = val

    def set_hvac_state (self,str):
        if str == 'OFF':
            self.hvac_on = False
        else:
            self.hvac_on = True

    def set_air_temp (self,str):
        self.air_temp = helpers.parse_fncs_number (str)

    def set_voltage (self,str):
        self.mtr_v = helpers.parse_fncs_magnitude (str)

