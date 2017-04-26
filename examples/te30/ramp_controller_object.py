"""
This file simulates a controller object
"""
import warnings
import sys
import json
import fncs

# Class definition
class ramp_controller_object:
    
    # ====================Define instance variables ===================================
    def __init__(self, controllerDict):
        
        # Obtain the registration data and initial values data
        agentRegistration = controllerDict['registration']
        agentInitialVal = controllerDict['initial_values']
        
        # Initialize the variables
        self.market = {'name': 'none', 'market_id': 0, 'average_price': -1, 'std_dev': -1, 'clear_price': -1, \
          'initial_price': -1, 'price_cap':9999.0, 'period': -1}   
        
        self.house = {'target': 'air_temperature', 'setpoint0':-1, 'lastsetpoint0': 0, 'controlled_load_all': 1, 'controlled_load_curr': 1, \
         'uncontrolled_load': 1, 'deadband': 0, 'currTemp': -1, 'powerstate': 'UNKNOWN', 'last_pState': 'UNKNOWN', 
         'heating_demand': 0, 'cooling_demand': 0, 'aux_state': 0, 'heat_state': 0, 'cool_state': 0, 
         'thermostat_state': 'UNKNOWN', 
         'heating_setpoint0': -1, 'cooling_setpoint0': -1, 
         're_override': 'NORMAL'
         }
        
        self.controller = {'name': 'none','marketName': 'none', 'houseName': 'none', 'simple_mode': 'none', 'setpoint': 'none', 'lastbid_id': -1, 'lastmkt_id': -1, 'bid_id': 'none', \
              'slider_setting': -0.001, 'period': -1, 'ramp_low': 0, 'ramp_high': 0, 'range_low': 0, \
              'range_high': 0, 'dir': 0, 'direction': 0, 'use_predictive_bidding': 0, 'deadband': 0, 'last_p': 0, \
              'last_q': 0, 'setpoint0': -1, 'minT': 0, 'maxT': 0, 'bid_delay': 60, 'next_run': 0, 't1': 0, 't2': 0, 
              'use_override': 'OFF', 'control_mode': 'CN_RAMP', 'resolve_mode': 'DEADBAND', 
              'slider_setting': -0.001, 'slider_setting_heat': -0.001, 'slider_setting_cool': -0.001, 'sliding_time_delay': -1,
              'heat_range_high': 3, 'heat_range_low': -5, 'heat_ramp_high': 0, 'heating_ramp_low': 0,
              'cool_range_high': 5, 'cool_range_low': -3, 'cooling_ramp_high': 0, 'cooling_ramp_low': 0,
              'heating_setpoint0': -1, 'cooling_setpoint0': -1, 'heating_demand': 0, 'cooling_demand': 0,
              'sliding_time_delay': -1, 
              'thermostat_mode': 'INVALID',  'last_mode': 'INVALID', 'previous_mode': 'INVALID',
              'time_off': sys.maxsize
              }
        
        self.controller_bid = {'market_id': -1, 'bid_id': 'none', 'bid_price': 0.0, 'bid_quantity': 0, 'bid_accepted': 1, \
                               'state': 'UNKNOWN', 'rebid': 0}
      
      
        self.controller['name'] = agentRegistration['agentName']

        # Read and assign initial values from agentInitialVal
        # controller information
        self.controller['control_mode'] = agentInitialVal['controller_information']['control_mode']
        self.controller['marketName'] = agentInitialVal['controller_information']['marketName']
        self.controller['houseName'] = agentInitialVal['controller_information']['houseName']
        self.controller['bid_id'] = agentInitialVal['controller_information']['bid_id']
        self.controller['period'] = agentInitialVal['controller_information']['period']
        self.controller['ramp_low'] = agentInitialVal['controller_information']['ramp_low']
        self.controller['ramp_high'] = agentInitialVal['controller_information']['ramp_high']
        self.controller['range_low'] = agentInitialVal['controller_information']['range_low']
        self.controller['range_high'] = agentInitialVal['controller_information']['range_high']
        self.controller['setpoint0'] = agentInitialVal['controller_information']['base_setpoint']
        self.controller['bid_delay'] = agentInitialVal['controller_information']['bid_delay']
        self.controller['use_predictive_bidding'] = agentInitialVal['controller_information']['use_predictive_bidding']
        self.controller['use_override'] = agentInitialVal['controller_information']['use_override']
        self.controller['last_setpoint'] = self.controller['setpoint0']
        
        # market information - Market registration information
        self.market['name'] = self.controller['marketName']
        self.market['market_id'] = agentInitialVal['market_information']['market_id']
        self.market['market_unit'] = agentInitialVal['market_information']['market_unit']
        self.market['initial_price'] = agentInitialVal['market_information']['initial_price']
        self.market['average_price'] = agentInitialVal['market_information']['average_price']
        self.market['std_dev'] = agentInitialVal['market_information']['std_dev']
        self.market['clear_price'] = agentInitialVal['market_information']['clear_price']
        self.market['price_cap'] = agentInitialVal['market_information']['price_cap']
        self.market['period'] = agentInitialVal['market_information']['period']
        
        # house information  - values will be given after the first time step, thereforely here set as default zero values
        self.house['currTemp'] = 0
        self.house['powerstate'] = "ON"
        self.house['controlled_load_all'] = 0 
        self.house['target'] = "air_temperature"
        self.house['deadband'] = 2 
        self.house['setpoint0'] = 0
        self.house['lastsetpoint0'] = self.house['setpoint0']
        

        # Generate agent publication dictionary
        self.fncs_publish = {
            'controller': {
                self.controller['name']: {
                    'market_id': {'propertyType': 'integer', 'propertyUnit': '', 'propertyValue': 0},
                    'bid_id': {'propertyType': 'string', 'propertyUnit': '', 'propertyValue': 0},
                    'bid_name': {'propertyType': 'string', 'propertyUnit': '', 'propertyValue': 'none'},
                    'price': {'propertyType': 'double', 'propertyUnit': '', 'propertyValue': 0.0},
                    'quantity': {'propertyType': 'double', 'propertyUnit': '', 'propertyValue': 0.0},
                    'bid_accepted': {'propertyType': 'integer', 'propertyUnit': '', 'propertyValue': 1},
                    'state': {'propertyType': 'string', 'propertyUnit': '', 'propertyValue': 'BS_UNKNOWN'},
                    'rebid': {'propertyType': 'integer', 'propertyUnit': '', 'propertyValue': 0}
                    }
                }
            } 
        
        # Registrate the agent      
        agentRegistrationString = json.dumps(agentRegistration)
        
        fncs.agentRegister(agentRegistrationString.encode('utf-8'))

    # ====================extract float from string ===============================
    def get_num(self,fncs_string):
        return float(''.join(ele for ele in fncs_string if ele.isdigit() or ele == '.'))
    
    # ====================Obtain values from the broker ===========================
    def subscribeVal(self, fncs_sub_value_String):    
        
        # Update market and house information at this time step from subscribed key values:  
        if "auction" in fncs_sub_value_String:
            self.market['market_id'] = fncs_sub_value_String['auction'][self.market['name']]['market_id']['propertyValue']
            self.market['average_price'] = fncs_sub_value_String['auction'][self.market['name']]['average_price']['propertyValue']
            self.market['std_dev'] = fncs_sub_value_String['auction'][self.market['name']]['std_dev']['propertyValue']
            self.market['clear_price'] = fncs_sub_value_String['auction'][self.market['name']]['clear_price']['propertyValue']
            self.market['price_cap'] = fncs_sub_value_String['auction'][self.market['name']]['price_cap']['propertyValue']
            self.market['initial_price'] = fncs_sub_value_String['auction'][self.market['name']]['initial_price']['propertyValue']

        # Read from GLD house published data
        if "air_temperature" in fncs_sub_value_String:
            self.house['currTemp'] = self.get_num(fncs_sub_value_String['air_temperature'])  #fncs_sub_value_String['values']['air_temperature']
        if "power_state" in fncs_sub_value_String:
            self.house['powerstate'] = fncs_sub_value_String['power_state'] # fncs.get_value('power_state') #fncs_sub_value_String['values']['power_state']
        if "hvac_load" in fncs_sub_value_String:
            self.house['controlled_load_all'] = self.get_num(fncs_sub_value_String['hvac_load'] ) #fncs_sub_value_String['values']['hvac_load']
#        print ('  subscribed', self.house['currTemp'], self.house['powerstate'], self.house['controlled_load_all'])

#         if self.controller['control_mode'] == "CN_DOUBLE_RAMP": # double_ramp controller receive extra data from house      
#         self.house['thermostat_state'] = house_value['House'][self.controller['houseName']]['thermostat_state']['propertyValue']
#         self.house['heating_demand'] = house_value['House'][self.controller['houseName']]['heating_demand']['propertyValue']
#         self.house['cooling_demand'] = house_value['House'][self.controller['houseName']]['cooling_demand']['propertyValue']
#         self.house['aux_state'] = house_value['House'][self.controller['houseName']]['aux_state']['propertyValue']
#         self.house['heat_state'] = house_value['House'][self.controller['houseName']]['heat_state']['propertyValue']
#         self.house['cool_state'] = house_value['House'][self.controller['houseName']]['cool_state']['propertyValue']
#         self.house['re_override'] = house_value['House'][self.controller['houseName']]['override_prop']['propertyValue']
        
        # Update controller values accordingly
        self.controller['deadband'] = self.house['deadband']
        
    # ====================Rearrange object based on given initial values======================  
    def initController(self):
        
        # Assign default values if it is simple mode:
        if self.controller['simple_mode'] == 'house_heat':
            self.controller['setpoint'] = 'heating_setpoint'
            self.controller['ramp_low'] = self.controller['ramp_high'] = -2
            self.controller['range_low'] = -5
            self.controller['range_high'] = 0
            self.controller['dir'] = -1
        elif self.controller['simple_mode'] == 'house_cool':
            self.controller['setpoint'] = 'cooling_setpoint'
            self.controller['ramp_low'] = self.controller['ramp_high'] = 2
            self.controller['range_low'] = 0
            self.controller['range_high'] = 5
            self.controller['dir'] = 1
        elif self.controller['simple_mode'] == 'house_preheat':
            self.controller['setpoint'] = 'heating_setpoint'
            self.controller['ramp_low'] = self.controller['ramp_high'] = -2
            self.controller['range_low'] = -5
            self.controller['range_high'] = 3
            self.controller['dir'] = -1
        elif self.controller['simple_mode'] == 'house_precool':
            self.controller['setpoint'] = 'cooling_setpoint'
            self.controller['ramp_low'] = self.controller['ramp_high'] = 2
            self.controller['range_low'] = -3
            self.controller['range_high'] = 5
            self.controller['dir'] = 1
        elif self.controller['simple_mode'] == 'waterheater':
            self.controller['setpoint'] = 'tank_setpoint'
            self.controller['ramp_low'] = self.controller['ramp_high'] = -2
            self.controller['range_low'] = 0
            self.controller['range_high'] = 10
        elif self.controller['simple_mode'] == 'double_ramp':
            self.controller['heating_setpoint'] = 'heating_setpoint'
            self.controller['cooling_setpoint'] = 'cooling_setpoint'
            self.controller['heat_ramp_low'] = self.controller['heat_ramp_high'] = -2
            self.controller['heat_range_low'] = -1
            self.controller['heat_range_high'] = 5
            self.controller['cool_ramp_low'] = self.controller['cool_ramp_high'] = 2
            self.controller['cool_range_low'] = 5
            self.controller['cool_range_high'] = 5
            
        # Update controller bidding period:
        if self.controller['period'] == 0.0:
            self.controller['period'] = 300
        
        # If the controller time interval is smaller than the market time interval
        if self.market['period'] > self.controller['period']:
            if self.market['period'] % self.controller['period'] != 0:
                warnings.warn('The supply bid and demand bids do not coincide, with the given market time interval\
                 %d s and controller time interval %d s' % (self.market['period'], self.controller['period']))
                
        elif self.market['period'] < self.controller['period']:
            # It is not allowed to have larger controller time interval than the market time interval
            warnings.warn('The controller time interval %d s is larger than the market time interval %d s' \
                          % (self.controller['period'], self.market['period']))
        
        # Update bid delay:
        if self.controller['bid_delay'] < 0:
            self.controller['bid_delay'] = -self.controller['bid_delay']
            
        if self.controller['bid_delay'] > self.controller['period']:
            warnings.warn('Bid delay is greater than the controller period. Resetting bid delay to 0.')
        
        # Check for abnormal input given
        if self.controller['use_predictive_bidding'] == 1 and self.controller['deadband'] == 0:
            warnings.warn('Controller deadband property not specified')
            
        # Calculate dir:
        if self.controller['dir'] == 0:
            high_val = self.controller['ramp_high'] * self.controller['range_high']
            low_val = self.controller['ramp_low'] * self.controller['range_low']
            if high_val > low_val:
                self.controller['dir'] = 1
            elif high_val < low_val:
                self.controller['dir'] = -1
            elif high_val == low_val and (abs(self.controller['ramp_high']) > 0.001 or abs(self.controller['ramp_low']) > 0.001):
                self.controller['dir'] = 0
                if abs(self.controller['ramp_high']) > 0:
                    self.controller['direction'] = 1
                else:
                    self.controller['direction'] = -1
            if self.controller['ramp_low'] * self.controller['ramp_high'] < 0:
                warnings.warn('controller price curve is not injective and may behave strangely')
        
        # Check double_ramp controller mode:
        if self.controller['sliding_time_delay'] < 0:
            self.controller['sliding_time_delay'] = 21600 # default sliding_time_delay of 6 hours
        else:
            self.controller['sliding_time_delay'] = int(self.controller['sliding_time_delay'])
        
        # use_override
        if self.controller['use_override'] == 'ON' and self.controller['bid_delay'] <= 0:
            self.controller['bid_delay'] = 1
          
        # Check slider_setting values
        if self.controller['control_mode'] == 'CN_RAMP':
            if self.controller['slider_setting'] < -0.001:
                warnings.warn('slider_setting is negative, reseting to 0.0')
                self.controller['slider_setting'] = 0.0
            elif self.controller['slider_setting'] > 1.0:
                warnings.warn('slider_setting is greater than 1.0, reseting to 1.0')
                self.controller['slider_setting'] = 1.0
        
        if self.controller['control_mode'] == 'CN_DOUBLE_RAMP':
            if self.controller['slider_setting_heat'] < -0.001:
                warnings.warn('slider_setting_heat is negative, reseting to 0.0')
                self.controller['slider_setting_heat'] = 0.0
            if self.controller['slider_setting_cool'] < 0.001:
                warnings.warn('slider_setting_cool is negative, reseting to 0.0')
                self.controller['slider_setting_cool'] = 0.0
            if self.controller['slider_setting_heat'] > 1.0:
                warnings.warn('slider_setting_heat is greater than 1.0, reseting to 1.0')
                self.controller['slider_setting_heat'] = 1.0
            if self.controller['slider_setting_cool'] > 1.0:
                warnings.warn('slider_setting_cool is greater than 1.0, reseting to 1.0')
                self.controller['slider_setting_cool'] = 1.0
                
        
        # Intialize controller next_run time as the starting time
        self.controller['next_run'] = 0
        
        # Intialize the controller last time price and quantity 
        self.controller['last_p'] = self.market['initial_price']
        self.controller['last_q'] = 0
         
    # ==================================Presync content===========================  
    def presync(self):   
        
        # Assign base set point - not used for test cases since base setpoint is always given to controller
#         if self.controller['control_mode'] == 'CN_RAMP' and self.controller['setpoint0'] <= 0:
#             self.controller['setpoint0'] = self.controller['last_setpoint'] = self.house['setpoint0']
#             
#         if self.controller['control_mode'] == 'CN_DOUBLE_RAMP' and self.controller['heating_setpoint0'] <= 0:
#             self.controller['heating_setpoint0'] = self.controller['last_heating_setpoint'] = self.house['heating_setpoint0']
#         
#         if self.controller['control_mode'] == 'CN_DOUBLE_RAMP' and self.controller['cooling_setpoint0'] <= 0:
#             self.controller['cooling_setpoint0'] = self.controller['last_cooling_setpoint'] = self.house['cooling_setpoint0']

        # Obtain min and max values:
        if self.controller['control_mode'] == 'CN_RAMP':
            if self.controller['slider_setting'] == -0.001:
                minT = self.controller['setpoint0'] + self.controller['range_low']
                maxT = self.controller['setpoint0'] + self.controller['range_high']
                
            elif self.controller['slider_setting'] > 0:
                minT = self.controller['setpoint0'] + self.controller['range_low'] * self.controller['slider_setting']
                maxT = self.controller['setpoint0'] + self.controller['range_high'] * self.controller['slider_setting']
                if self.controller['range_low'] != 0:
                    self.controller['ramp_low'] = 2 + (1 - self.controller['slider_setting'])
                else:
                    self.controller['ramp_low'] = 0
                if self.controller['range_high'] != 0:
                    self.controller['ramp_high'] = 2 + (1 - self.controller['slider_setting'])
                else:
                    self.controller['ramp_high'] = 0
                    
            else:
                minT = maxT = self.controller['setpoint0']
            
            # Update controller parameters
            self.controller['minT'] = minT;
            self.controller['maxT'] = maxT;
            
        elif self.controller['control_mode'] == 'CN_DOUBLE_RAMP':
            # Cooling curve
            if self.controller['slider_setting_cool'] == -0.001:
                self.controller['cool_minT'] = self.controller['cooling_setpoint0'] + self.controller['cool_range_low']
                self.controller['cool_maxT'] = self.controller['cooling_setpoint0'] + self.controller['cool_range_high']
                
            elif self.controller['slider_setting_cool'] > 0:
                self.controller['cool_minT'] = self.controller['cooling_setpoint0'] + self.controller['cool_range_low'] * self.controller['slider_setting_cool']
                self.controller['cool_maxT'] = self.controller['cooling_setpoint0'] + self.controller['cool_range_high'] * self.controller['slider_setting_cool']
                if self.controller['cool_range_low'] != 0:
                    self.controller['cool_ramp_low'] = 2 + (1 - self.controller['slider_setting_cool'])
                else:
                    self.controller['cool_ramp_low'] = 0
                if self.controller['cool_range_high'] != 0:
                    self.controller['cool_ramp_high'] = 2 + (1 - self.controller['slider_setting_cool'])
                else:
                    self.controller['cool_ramp_high'] = 0       
            else:
                self.controller['cool_minT'] = self.controller['cool_maxT'] = self.controller['cooling_setpoint0']
            # Heating curve
            if self.controller['slider_setting_heat'] == -0.001:
                self.controller['heat_minT'] = self.controller['heating_setpoint0'] + self.controller['heat_range_low']
                self.controller['heat_maxT'] = self.controller['heating_setpoint0'] + self.controller['heat_range_high']
                
            elif self.controller['slider_setting_cool'] > 0:
                self.controller['heat_minT'] = self.controller['heating_setpoint0'] + self.controller['heat_range_low'] * self.controller['slider_setting_heat']
                self.controller['heat_maxT'] = self.controller['heating_setpoint0'] + self.controller['heat_range_high'] * self.controller['slider_setting_heat']
                if self.controller['heat_range_low'] != 0:
                    self.controller['heat_ramp_low'] = 2 + (1 - self.controller['slider_setting_heat'])
                else:
                    self.controller['heat_ramp_low'] = 0
                if self.controller['heat_range_high'] != 0:
                    self.controller['heat_ramp_high'] = 2 + (1 - self.controller['slider_setting_heat'])
                else:
                    self.controller['heat_ramp_high'] = 0
                    
            else:
                self.controller['heat_minT'] = self.controller['heat_maxT'] = self.controller['heating_setpoint0']
        
        # Thermostat mode 
        if self.controller['thermostat_mode'] != 'INVALID' and self.controller['thermostat_mode'] != 'OFF':
            self.controller['last_mode'] = self.controller['thermostat_mode']
        elif self.controller['thermostat_mode'] == 'INVALID':
            self.controller['last_mode'] = 'OFF'
        
        if self.controller['thermostat_mode'] != 'INVALID':
            self.controller['previous_mode'] = self.controller['thermostat_mode']
        else:
            self.controller['previous_mode'] = 'OFF'        
        
        # override
#         if self.controller['use_override'] == 'OFF' and self.house['re_override'] != 'NORMAL':
#             self.fncs_publish['override_prop'] = 'NORMAL'
        
        return sys.maxsize
    
    # ==================================Sync content===========================  
    def sync(self, timeSim):    
        
        # Update controller t1 information
        self.controller['t1'] = timeSim
        
        # Inputs from market object:
        marketId = self.market['market_id']
        clear_price = self.market['clear_price']
        avgP = self.market['average_price']
        stdP = self.market['std_dev']
        
        # Inputs from controller:
        ramp_low = self.controller['ramp_low']
        ramp_high = self.controller['ramp_high']
        range_low = self.controller['range_low']
        range_high = self.controller['range_high']
        lastmkt_id = self.controller['lastmkt_id']
        deadband = self.controller['deadband']
        setpoint0 = self.controller['setpoint0']
        last_setpoint = self.controller['last_setpoint']
        minT = self.controller['minT']
        maxT = self.controller['maxT']
        bid_delay = self.controller['bid_delay']
        direction = self.controller['direction']
        
        # Inputs from house object:
        demand = self.house['controlled_load_all']
        monitor = self.house['currTemp']
        powerstate = self.house['powerstate']

#        print ("  sync:", demand, powerstate, monitor, last_setpoint, deadband, direction, clear_price, avgP, stdP)
        
        # Check t1 to determine if the sync part is needed to be processed or not
        if self.controller['t1'] == self.controller['next_run'] and marketId == lastmkt_id :
            return sys.maxsize
        
        if  self.controller['t1'] < self.controller['next_run'] and marketId == lastmkt_id :
            if self.controller['t1'] <= self.controller['next_run'] - bid_delay :
                if self.controller['use_predictive_bidding'] == 1 and ((self.controller['control_mode'] == 'CN_RAMP' and setpoint0 != last_setpoint) or (self.controller['control_mode'] == 'CN_DOUBLE_RAMP' and (self.controller['heating_setpoint0']  != self.controller['last_heating_setpoint'] or self.controller['cooling_setpoint0']  != self.controller['last_cooling_setpoint']))):
                    # Base set point setpoint0 is changed, and therefore sync is needed:
                    pass
                elif self.controller['use_override'] == 'ON' and self.controller['t1'] == self.controller['next_run']- bid_delay :
                    # At the exact time that controller is operating, therefore sync is needed:
                    pass
                else:
                    if self.house['last_pState'] == powerstate:
                        # If house state not changed, then do not go through sync part:
                        return self.controller['next_run']
            else:
                return self.controller['next_run']
        
        # If market get updated, then update the set point                
        deadband_shift = 0
        # Set deadband shift if user predictive bidding is true
        if self.controller['use_predictive_bidding'] == 1:
            deadband_shift = 0.5 * deadband
        
        #  
        if self.controller['control_mode'] == 'CN_RAMP':
            if marketId != lastmkt_id: 
                
                # Update controller last market id and bid id
                self.controller['lastmkt_id'] = marketId
                self.controller['lastbid_id'] = -1
                self.controller_bid['rebid'] = 0 
                
                # Calculate shift direction
                shift_direction = 0
                if self.controller['use_predictive_bidding'] == 1:
                    if (self.controller['dir'] > 0 and clear_price < self.controller['last_p']) or (self.controller['dir'] < 0 and clear_price > self.controller['last_p']):
                        shift_direction = -1
                    elif (self.controller['dir'] > 0 and clear_price >= self.controller['last_p']) or (self.controller['dir'] < 0 and clear_price <= self.controller['last_p']):
                        shift_direction = 1
                    else:
                        shift_direction = 0
                        
                # Calculate updated set_temp
                if abs(stdP) < 0.0001:
                    set_temp = setpoint0
                elif clear_price < avgP and range_low != 0:
                    set_temp = setpoint0 + (clear_price - avgP) * abs(range_low) / (ramp_low * stdP) + deadband_shift*shift_direction
                elif clear_price > avgP and range_high != 0:
                    set_temp = setpoint0 + (clear_price - avgP) * abs(range_high) / (ramp_high * stdP) + deadband_shift*shift_direction
                else:
                    set_temp = setpoint0 + deadband_shift*shift_direction
                
                # override
#                 if self.controller['use_override'] == 'ON' and self.house['re_override'] != 'none':
#                     if clear_price <= self.controller['last_p']:
#                         self.fncs_publish['controller'][self.controller['name']]['override_prop'] = 'ON'
#                     else:
#                         self.fncs_publish['controller'][self.controller['name']]['override_prop'] = 'OFF'
                
                # Check if set_temp is out of limit
                if set_temp > maxT:
                    set_temp = maxT
                elif set_temp < minT:
                    set_temp = minT
                # Update house set point - output delta setpoint0
                if timeSim != 0:
                    self.house['setpoint0'] = set_temp - self.house['lastsetpoint0'] 
                    fncs.publish('cooling_setpoint', set_temp)
#                    print('  ', timeSim,'Setting (clear price, avgP, stdP, range_high, ramp_high, rang_low, ramp_low',
#                          set_temp, clear_price, avgP, stdP, range_high, ramp_high, range_low, ramp_low)
                    self.house['lastsetpoint0'] = set_temp
            else:
                # Change of house setpoint only changes when market changes
                self.house['setpoint0'] = 0;
                
            # Calculate bidding price
            # Bidding price when monitored load temperature is at the min and max limit of the controller
            bid_price = -1
            no_bid = 0
            if self.controller['dir'] > 0:
                if self.controller['use_predictive_bidding'] == 1:
                    if powerstate == 'OFF' and monitor > (maxT - deadband_shift):
                        bid_price = self.market['price_cap']
                    elif powerstate != 'OFF' and monitor < (minT + deadband_shift):
                        bid_price = 0
                        no_bid = 1
                    elif powerstate != 'OFF' and monitor > maxT:
                        bid_price = self.market['price_cap']
                    elif powerstate == 'OFF' and monitor < minT:
                        bid_price = 0
                        no_bid = 1
                else:
                    if monitor > maxT:
                        bid_price = self.market['price_cap']
                    elif monitor < minT:
                        bid_price = 0
                        no_bid = 1
            elif self.controller['dir'] < 0:
                if self.controller['use_predictive_bidding'] == 1:
                    if powerstate == 'OFF' and monitor < (minT + deadband_shift):
                        bid_price = self.market['price_cap']
                    elif powerstate != 'OFF' and monitor > (maxT - deadband_shift):
                        bid_price = 0
                        no_bid = 1
                    elif powerstate != 'OFF' and monitor < minT:
                        bid_price = self.market['price_cap']
                    elif powerstate == 'OFF' and monitor > maxT:
                        bid_price = 0
                        no_bid = 1
                else:
                    if monitor < minT:
                        bid_price = self.market['price_cap']
                    elif monitor > maxT:
                        bid_price = 0
                        no_bid = 1
            elif self.controller['dir'] == 0:
                if self.controller['use_predictive_bidding'] == 1:
                    if not(direction):
                        warnings.warn('the variable direction did not get set correctly')
                    elif ((monitor > maxT + deadband_shift) or  (powerstate != 'OFF' and monitor > minT - deadband_shift)) and direction > 0:
                        bid_price = self.market['price_cap']
                    elif ((monitor < minT - deadband_shift) or  (powerstate != 'OFF' and monitor < maxT + deadband_shift)) and direction < 0:
                        bid_price = self.market['price_cap']
                    elif powerstate == 'OFF' and monitor > maxT:
                        bid_price = 0
                        no_bid = 1
                else:
                    if monitor < minT:
                        bid_price = self.market['price_cap']
                    elif monitor > maxT:
                        bid_price = 0
                        no_bid = 1
                    else:
                        bid_price = avgP
            
            # Bidding price when the monitored load temperature is within the controller temp limit
            if monitor > setpoint0:
                k_T = ramp_high
                T_lim = range_high
            elif monitor < setpoint0:
                k_T = ramp_low
                T_lim = range_low
            else:
                k_T = 0
                T_lim = 0
            
            bid_offset = 0.0001
            if bid_price < 0 and monitor != setpoint0:
                if abs(stdP) < bid_offset:
                    bid_price = avgP
                else:
                    bid_price = avgP + (monitor - setpoint0)*(k_T * stdP) / abs(T_lim)   
            elif monitor == setpoint0:
                bid_price = avgP
            
            # Update the outputs
            if demand > 0 and no_bid != 1:
                # Update bid price and quantity
                self.controller['last_p'] = bid_price
                self.controller['last_q'] = demand
#                 self.controller['bid_id'] += 1
                # Check market unit with controller default unit kW
                if (self.market['market_unit']).lower() != "kW":
                    if (self.market['market_unit']).lower() == "w":
                        self.controller['last_q'] = self.controller['last_q']*1000
                    elif (self.market['market_unit']).lower() == "mw":
                        self.controller['last_q'] = self.controller['last_q']/1000
                # Update  parameters
                self.controller_bid['market_id'] = self.controller['lastmkt_id']
                self.controller_bid['bid_price'] = self.controller['last_p']
                self.controller_bid['bid_quantity'] = self.controller['last_q']
               
                # Set controller_bid state
                self.controller_bid['state'] = powerstate
                    
            else:
                # Update bid price and quantity
                self.controller['last_p'] = 0
                self.controller['last_q'] = 0
                # Update controller_bid parameters
                self.controller_bid['market_id'] = 0
                self.controller_bid['bid_price'] = 0
                self.controller_bid['bid_quantity'] = 0
        
        # If the controller is double_ramp type
        elif self.controller['control_mode'] == 'CN_DOUBLE_RAMP':
            midpoint = 0.0
            if self.controller['cool_minT'] - self.controller['heat_maxT'] < deadband:
                if self.controller_bid['resolve_mode'] == 'DEADBAND':
                    midpoint = (self.controller['heat_maxT'] + self.controller['cool_minT']) / 2
                    if (midpoint - deadband/2) < self.controller['heating_setpoint0'] or (midpoint + deadband/2) < self.controller['cooling_setpoint0']:
                        warnings.warn('The midpoint between the max heating setpoint and the min cooling setpoint must be half a deadband away from each base setpoint')
                        return -1
                    else:
                        self.controller['heat_maxT'] = midpoint - deadband/2
                        self.controller['cool_minT'] = midpoint + deadband/2
                elif self.controller_bid['resolve_mode'] == 'SLIDING':
                    if self.controller['heat_maxT'] > self.controller['cooling_setpoint0'] - deadband:
                        warnings.warn('The max heating setpoint must be a full deadband less than the cooling_base_setpoint')
                        return -1
                
                    if self.controller['cool_minT'] < self.controller['heating_setpoint0'] + deadband:
                        warnings.warn('The min cooling setpoint must be a full deadband greater than the heating_base_setpoint')
                        return -1
                    
                    if self.controller['last_mode'] == 'OFF' or self.controller['last_mode'] == 'COOL':
                        self.controller['heat_maxT'] = self.controller['cool_minT'] - deadband
                    elif self.controller['last_mode'] == 'HEAT':
                        self.controller['cool_minT'] = self.controller['heat_maxT'] + deadband
                else:
                    warnings.warn('Unrecognized resolve_mode when double_ramp overlap resolution is needed')
                    return -1
                
            if marketId != lastmkt_id :
                
                # Update controller last market id and bid id
                self.controller['lastmkt_id'] = marketId
                self.controller['lastbid_id'] = -1
                self.controller_bid['rebid'] = 0 
                
                # Calculate shift direction
                shift_direction = 0
                if self.controller['use_predictive_bidding'] == 1:
                    if (self.controller['thermostat_mode'] == 'COOL' and clear_price < self.controller['last_p']) or (self.controller['thermostat_mode'] == 'HEAT' and clear_price > self.controller['last_p']):
                        shift_direction = -1
                    elif (self.controller['thermostat_mode'] == 'COOL' and clear_price >= self.controller['last_p']) or (self.controller['thermostat_mode'] == 'HEAT' and clear_price <= self.controller['last_p']):
                        shift_direction = 1
                    else:
                        shift_direction = 0
                        
                # Calculate updated set_temp
                if abs(stdP) < 0.0001:
                    set_temp_cooling = self.controller['cooling_setpoint0']
                    set_temp_heating = self.controller['heating_setpoint0']
                elif clear_price > avgP:
                    set_temp_cooling = self.controller['cooling_setpoint0'] + (clear_price - avgP) * abs(self.controller['cool_range_high']) / (self.controller['cool_ramp_high'] * stdP) + deadband_shift*shift_direction
                    set_temp_heating = self.controller['heating_setpoint0'] + (clear_price - avgP) * abs(self.controller['heat_range_low']) / (self.controller['heat_ramp_low'] * stdP) + deadband_shift*shift_direction
                elif clear_price < avgP:
                    set_temp_cooling = self.controller['cooling_setpoint0'] + (clear_price - avgP) * abs(self.controller['cool_range_low']) / (self.controller['cool_ramp_low'] * stdP) + deadband_shift*shift_direction
                    set_temp_heating = self.controller['heating_setpoint0'] + (clear_price - avgP) * abs(self.controller['heat_range_high']) / (self.controller['heat_ramp_high'] * stdP) + deadband_shift*shift_direction
                else:
                    set_temp_cooling = self.controller['cooling_setpoint0'] + deadband_shift*shift_direction
                    set_temp_heating = self.controller['heating_setpoint0'] + deadband_shift*shift_direction
                    
                # Check if set_temp is out of limit
                if set_temp_cooling > self.controller['cool_maxT']:
                    set_temp_cooling = self.controller['cool_maxT']
                elif set_temp_cooling < self.controller['cool_minT']:
                    set_temp_cooling = self.controller['cool_minT']
                if set_temp_heating > self.controller['heat_maxT']:
                    set_temp_heating = self.controller['heat_maxT']
                elif set_temp_heating < self.controller['heat_minT']:
                    set_temp_heating = self.controller['heat_minT']
                    
                # Update house set point - output delta setpoint0
                if timeSim != 0:
                    self.house['cooling_setpoint0'] = set_temp_cooling - self.house['lastcooling_setpoint0']
                    self.house['lastcooling_setpoint0'] = set_temp_cooling
                    self.house['heating_setpoint0'] = set_temp_heating - self.house['lastheating_setpoint0']
                    self.house['lastheating_setpoint0'] = set_temp_heating
#               fncs.publish('cooling_setpoint', set_temp_cooling)
#               fncs.publish('heating_setpoint', set_temp_heating)
            else:
                self.house['cooling_setpoint0'] = 0
                self.house['heating_setpoint0'] = 0
            
            # Calculate bidding price
            # Bidding price when monitored load temperature is at the min and max limit of the controller
            last_p = last_q = 0.0
            # We have to cool:
            if monitor > self.controller['cool_maxT'] and (self.house['thermostat_state'] == 'UNKNOWN' or self.house['thermostat_state'] == 'OFF'
                                                           or self.house['thermostat_state'] == 'COOL'):
                last_p = self.market['price_cap']
                last_q = self.house['cooling_demand']
            # We have to heat:
            elif monitor < self.controller['heat_minT'] and (self.house['thermostat_state'] == 'UNKNOWN' or self.house['thermostat_state'] == 'OFF'
                                                           or self.house['thermostat_state'] == 'HEAT'):
                last_p = self.market['price_cap']
                last_q = self.house['heating_demand']    
            # We are floating in between heating and cooling
            elif monitor > self.controller['heat_maxT'] and monitor < self.controller['cool_minT']:
                last_p = last_q = 0.0
            # We might heat, if the price is right
            elif monitor <= self.controller['heat_maxT'] and monitor >= self.controller['heat_minT'] and (self.house['thermostat_state'] == 'UNKNOWN' or self.house['thermostat_state'] == 'OFF'
                                                           or self.house['thermostat_state'] == 'HEAT'):
                ramp = self.controller['heat_ramp_high'] if monitor > self.controller['heating_setpoint0'] else self.controller['heat_ramp_low']
                range = self.controller['heat_range_high'] if monitor > self.controller['heating_setpoint0'] else self.controller['heat_range_low']
                if monitor != self.controller['heating_setpoint0']:
                    if abs(stdP) < 0.0001:
                        last_p = avgP
                    else:
                        last_p = avgP + (monitor - self.controller['heating_setpoint0'])*(ramp * stdP) / abs(range)
                last_q = self.house['heating_demand']  
            # We might cool, if the price is right
            elif monitor <= self.controller['cool_maxT'] and monitor >= self.controller['cool_minT'] and (self.house['thermostat_state'] == 'UNKNOWN' or self.house['thermostat_state'] == 'OFF'
                                                           or self.house['thermostat_state'] == 'COOL'):
                ramp = self.controller['cool_ramp_high'] if monitor > self.controller['cooling_setpoint0'] else self.controller['cool_ramp_low']
                range = self.controller['cool_range_high'] if monitor > self.controller['cooling_setpoint0'] else self.controller['cool_range_low']
                if monitor != self.controller['cooling_setpoint0']:
                    if abs(stdP) < 0.0001:
                        last_p = avgP
                    else:
                        last_p = avgP + (monitor - self.controller['cooling_setpoint0'])*(ramp * stdP) / abs(range)
                last_q = self.house['cooling_demand']  
            
            if last_p > self.market['price_cap']:
                last_p = self.market['price_cap']
            if last_p < -self.market['price_cap']:
                last_p = -self.market['price_cap']
            
            # Update the outputs
            # Update bid price and quantity
            self.controller['last_p'] = bid_price
            self.controller['last_q'] = demand
            self.controller['bid_id'] += 1
            
            # Check market unit with controller default unit kW
            if (self.market['market_unit']).lower() != "kW":
                if (self.market['market_unit']).lower() == "w":
                    self.controller['last_q'] = self.controller['last_q']*1000
                elif (self.market['market_unit']).lower() == "mw":
                    self.controller['last_q'] = self.controller['last_q']/1000
                    
            # Update  parameters
            self.controller_bid['market_id'] = self.controller['lastmkt_id']
            self.controller_bid['bid_price'] = last_p
            self.controller_bid['bid_quantity'] = last_q
           
            if last_q > 0.001:
                # Set controller_bid state
                self.controller_bid['state'] = powerstate
            else:
                if self.house['last_pState'] !=  powerstate:
                    # Set controller_bid state
                    self.controller_bid['state'] = powerstate
         
        # Update house last power state
        self.house['last_pState'] = powerstate
        
        # Display some outputs for test only when sync part is processed
#        print ('At %d min, with market_id %d, bidding price is %f, bidding quantity is %f, house set point change is %f, rebid is %d' % (timeSim/60, self.controller_bid['market_id'], self.controller_bid['bid_price'], self.controller_bid['bid_quantity'], self.house['setpoint0'], self.controller_bid['rebid']))
        
        # Issue a bid, if appropriate
        if self.controller_bid['bid_quantity'] > 0.0 and self.controller_bid['bid_price'] > 0.0:
            self.fncs_publish['controller'][self.controller['name']]['market_id']['propertyValue'] = self.controller_bid['market_id']
            self.fncs_publish['controller'][self.controller['name']]['bid_id']['propertyValue'] = self.controller['name'] # bid_id is unique for each controller unchanged
            self.fncs_publish['controller'][self.controller['name']]['price']['propertyValue'] = self.controller_bid['bid_price']
            self.fncs_publish['controller'][self.controller['name']]['quantity']['propertyValue'] = self.controller_bid['bid_quantity']
            self.fncs_publish['controller'][self.controller['name']]['bid_accepted']['propertyValue'] = 1 if no_bid == 0 else 0
            self.fncs_publish['controller'][self.controller['name']]['state']['propertyValue'] = self.controller_bid['state']
            self.fncs_publish['controller'][self.controller['name']]['rebid']['propertyValue'] = self.controller_bid['rebid'] 
            self.fncs_publish['controller'][self.controller['name']]['bid_name'] = self.controller['name']
           
#            print('  (temp,state,load,avg,std,clear,cap,init)',self.house['currTemp'],self.house['powerstate'],self.house['controlled_load_all'],self.market['average_price'],self.market['std_dev'],self.market['clear_price'],self.market['price_cap'],self.market['initial_price'])      
#            print (timeSim, 'Bidding PQSrebid',self.controller_bid['bid_price'],self.controller_bid['bid_quantity'],self.controller_bid['state'],self.controller_bid['rebid'])
            # Set controller_bid rebid value to true after publishing
            self.controller_bid['rebid'] = 1
                  
            fncs_publishString = json.dumps(self.fncs_publish)
            
            fncs.agentPublish(fncs_publishString)
        
        # Return sync time t2
        return sys.maxsize
    
    # ==================================Postsync content===========================   
    def postsync(self):     
        # Update last setpoint if setpoint0 changed
        if self.controller['control_mode'] == 'CN_RAMP' and self.controller['last_setpoint'] != self.controller['setpoint0']:
            self.controller['last_setpoint'] = self.controller['setpoint0']
        
        if self.controller['control_mode'] == 'CN_DOUBLE_RAMP' and self.controller['lastcooling_setpoint0'] != self.controller['cooling_setpoint0']:
            self.controller['lastcooling_setpoint0'] = self.controller['cooling_setpoint0']
        
        if self.controller['control_mode'] == 'CN_DOUBLE_RAMP' and self.controller['lastheating_setpoint0'] != self.controller['heating_setpoint0']:
            self.controller['heating_setpoint0'] = self.controller['heating_setpoint0']   
             
        # Compare t1 with next_run to determine the return time stamp heating_setpoint0
        if self.controller['t1'] < self.controller['next_run'] - self.controller['bid_delay']:
            postsyncReturn = self.controller['next_run'] - self.controller['bid_delay']
            return postsyncReturn
        
        if self.controller['resolve_mode'] == 'SLIDING':
            aux_state = self.house['aux_state']
            heat_state = self.house['heat_state']
            cool_state = self.house['cool_state']
            if heat_state == 1 or aux_state == 1:
                self.controller['thermostat_mode'] = 'HEAT'
                if self.controller['last_mode'] == 'OFF':
                    self.controller['time_off'] = sys.maxsize
            elif cool_state == 1:
                self.controller['thermostat_mode'] = 'COOL'
                if self.controller['last_mode'] == 'OFF':
                    self.controller['time_off'] = sys.maxsize
            elif heat_state == 0 and aux_state == 0 and cool_state == 0:
                self.controller['thermostat_mode'] = 'OFF'
                if self.controller['previous_mode'] != 'OFF':
                    self.controller['time_off'] = self.controller['t1'] + self.controller['sliding_time_delay']
            else:
                warnings.warn('The HVAC is in two or more modes at once. This is impossible')
                return -1     
        
        if self.controller['t1'] - self.controller['next_run'] < self.controller['bid_delay']:
            postsyncReturn = self.controller['next_run']
        
        if self.controller['t1'] == self.controller['next_run']:
            self.controller['next_run'] += self.controller['period']
            postsyncReturn = self.controller['next_run'] - self.controller['bid_delay']
        
        return postsyncReturn
        
     
            
            
            
        
        
        
        
        
        
        
        