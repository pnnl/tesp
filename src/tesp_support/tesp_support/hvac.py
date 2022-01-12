# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: hvac.py
"""Class that controls the responsive thermostat for one house.

Implements the ramp bidding method, with HVAC power as the
bid quantity, and thermostat setting changes as the response
mechanism.
"""

from .helpers import parse_magnitude
from .helpers import parse_number


class hvac:
    """This agent manages thermostat setpoint and bidding for a house

    Args:
        dict (dict): dictionary row for this agent from the JSON configuration file
        key (str): name of this agent, also key for its dictionary row
        aucObj (simple_auction): the auction this agent bids into

    Attributes:
        name (str): name of this agent
        control_mode (str): control mode from dict (CN_RAMP or CN_NONE, which still implements the setpoint schedule)
        houseName (str): name of the corresponding house in GridLAB-D, from dict
        meterName (str): name of the corresponding triplex_meter in GridLAB-D, from dict
        period (float): market clearing period, in seconds, from dict
        wakeup_start (float): hour of the day (0..24) for scheduled weekday wakeup period thermostat setpoint, from dict
        daylight_start (float): hour of the day (0..24) for scheduled weekday daytime period thermostat setpoint, from dict
        evening_start (float): hour of the day (0..24) for scheduled weekday evening (return home) period thermostat setpoint, from dict
        night_start (float): hour of the day (0..24) for scheduled weekday nighttime period thermostat setpoint, from dict
        wakeup_set (float): preferred thermostat setpoint for the weekday wakeup period, in deg F, from dict
        daylight_set (float): preferred thermostat setpoint for the weekday daytime period, in deg F, from dict
        evening_set (float): preferred thermostat setpoint for the weekday evening (return home) period, in deg F, from dict
        night_set (float): preferred thermostat setpoint for the weekday nighttime period, in deg F, from dict
        weekend_day_start (float): hour of the day (0..24) for scheduled weekend daytime period thermostat setpoint, from dict
        weekend_day_set (float): preferred thermostat setpoint for the weekend daytime period, in deg F, from dict
        weekend_night_start (float): hour of the day (0..24) for scheduled weekend nighttime period thermostat setpoint, from dict
        weekend_night_set (float): preferred thermostat setpoint for the weekend nighttime period, in deg F, from dict
        deadband (float): thermostat deadband in deg F, invariant, from dict
        offset_limit (float): maximum allowed change from the time-scheduled setpoint, in deg F, from dict
        ramp (float): bidding ramp denominator in multiples of the price standard deviation, from dict
        price_cap (float): the highest allowed bid price in $/kwh, from dict
        bid_delay (float): from dict, not implemented
        use_predictive_bidding (float): from dict, not implemented
        std_dev (float): standard deviation of expected price, determines the bidding ramp slope, initialized from aucObj
        mean (float): mean of the expected price, determines the bidding ramp origin, initialized from aucObj
        Trange (float): the allowed range of setpoint variation, bracketing the preferred time-scheduled setpoint
        air_temp (float): current air temperature of the house in deg F
        hvac_kw (float): most recent non-zero HVAC power in kW, this will be the bid quantity
        mtr_v (float): current line-neutral voltage at the triplex meter
        hvac_on (Boolean): True if the house HVAC is currently running
        basepoint (float): the preferred time-scheduled thermostat setpoint in deg F
        setpoint (float): the thermostat setpoint, including price response, in deg F
        bid_price (float): the current bid price in $/kwh
        cleared_price (float): the cleared market price in $/kwh
    """

    def __init__(self, dict, key, aucObj):
        """Initializes the class
        """
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

        self.Trange = abs(2.0 * self.offset_limit)

        self.air_temp = 78.0
        self.hvac_kw = 3.0
        self.mtr_v = 120.0
        self.hvac_on = False

        self.basepoint = 0.0
        self.setpoint = 0.0
        self.cleared_price = 0.0
        self.bid_price = 0.0

    def inform_bid(self, price):
        """ Set the cleared_price attribute

        Args:
            price (float): cleared price in $/kwh
        """
        self.cleared_price = price

    def bid_accepted(self):
        """ Update the thermostat setting if the last bid was accepted

        The last bid is always "accepted". If it wasn't high enough,
        then the thermostat could be turned up.p

        Returns:
            Boolean: True if the thermostat setting changes, False if not.
        """
        if self.control_mode == 'CN_RAMP' and self.std_dev > 0.0:
            offset = (self.cleared_price - self.mean) * self.Trange / self.ramp / self.std_dev
            if offset < -self.offset_limit:
                offset = -self.offset_limit
            elif offset > self.offset_limit:
                offset = self.offset_limit
            self.setpoint = self.basepoint + offset
            return True
        return False

    def formulate_bid(self):
        """ Bid to run the air conditioner through the next period
        
        Returns:
            [float, float, Boolean]: bid price in $/kwh, bid quantity in kW and current HVAC on state, or None if not bidding 
        """

        # print (' = formulating bid for {:s} kw={:.2f} on={:d} T={:.2f} Base={:.2f} mu={:.5f} ramp={:.3f} std={:.5f} Trange={:.2f} mode={:s}'.format (self.name,
        #  self.hvac_kw, self.hvac_on, self.air_temp, self.basepoint, self.mean, self.ramp, self.std_dev, self.Trange, self.control_mode))

        if self.control_mode == 'CN_NONE':
            return None

        p = self.mean + (self.air_temp - self.basepoint) * self.ramp * self.std_dev / self.Trange
        if p >= self.price_cap:
            self.bid_price = self.price_cap
        elif p <= 0.0:
            self.bid_price = 0.0
        else:
            self.bid_price = p
        return [self.bid_price, self.hvac_kw, self.hvac_on]

    def change_basepoint(self, hod, dow):
        """ Updates the time-scheduled thermostat setting

        Args:
            hod (float): the hour of the day, from 0 to 24
            dow (int): the day of the week, zero being Monday

        Returns:
            Boolean: True if the setting changed, Falso if not
        """
        if dow > 4:  # a weekend
            val = self.weekend_night_set
            if self.weekend_day_start <= hod < self.weekend_night_start:
                val = self.weekend_day_set
        else:  # a weekday
            val = self.night_set
            if self.wakeup_start <= hod < self.daylight_start:
                val = self.wakeup_set
            elif self.daylight_start <= hod < self.evening_start:
                val = self.daylight_set
            elif self.evening_start <= hod < self.night_start:
                val = self.evening_set
        if abs(self.basepoint - val) > 0.1:
            self.basepoint = val
            return True
        return False

    def set_hvac_load_from_fncs_str(self, val):
        """ Sets the hvac_load attribute, if greater than zero

        Args:
            val (str): FNCS message with load in kW
        """
        kw = parse_number(val)
        if kw > 0.0:
            self.hvac_kw = kw

    def set_hvac_state_from_fncs_str(self, val):
        """ Sets the hvac_on attribute

        Args:
            val (str): FNCS message with state, ON or OFF
        """
        if val == 'OFF':
            self.hvac_on = False
        else:
            self.hvac_on = True

    def set_air_temp_from_fncs_str(self, val):
        """ Sets the air_temp attribute

        Args:
            val (str): FNCS message with temperature in degrees Fahrenheit
        """
        self.air_temp = parse_number(val)

    def set_voltage_from_fncs_str(self, val):
        """ Sets the mtr_v attribute

        Args:
            val (str): FNCS message with meter line-neutral voltage
        """
        self.mtr_v = parse_magnitude(val)

    def set_hvac_load_from_helics(self, val):
        if val > 0.0:
            self.hvac_kw = val

    def set_hvac_state_from_helics(self, val):
        if val == 'OFF':
            self.hvac_on = False
        else:
            self.hvac_on = True

    def set_air_temp_from_helics(self, val):
        self.air_temp = val

    def set_voltage_from_helics(self, val):
        self.mtr_v = abs(val)
