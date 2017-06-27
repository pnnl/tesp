"""
This file simulates an auction object
"""
# import from library or functions
import numpy as np
import math
import warnings
import re
import sys
from copy import deepcopy

from get_curve import curve

import fncs
import json
from pprint import pprint

def parse_kw(arg):
    tok = arg.strip('; MWVAKdrij')
    nsign = nexp = ndot = 0
    for i in range(len(tok)):
        if (tok[i] == '+') or (tok[i] == '-'):
            nsign += 1
        elif (tok[i] == 'e') or (tok[i] == 'E'):
            nexp += 1
        elif tok[i] == '.':
            ndot += 1
        if nsign == 2 and nexp == 0:
            kpos = i
            break
        if nsign == 3:
            kpos = i
            break

    vals = [tok[:kpos],tok[kpos:]]
#    print(arg,vals)

    vals = [float(v) for v in vals]

    if 'd' in arg:
        vals[1] *= (math.pi / 180.0)
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    elif 'r' in arg:
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    else:
        p = vals[0]
        q = vals[1]

    if 'KVA' in arg:
        p *= 1.0
        q *= 1.0
    elif 'MVA' in arg:
        p *= 1000.0
        q *= 1000.0
    else:  # VA
        p /= 1000.0
        q /= 1000.0

    return p

# Class definition
class auction_object:
    # ====================Define instance variables ===================================
    def __init__(self,auctionDict):
        # Obtain the registration data and initial values data
        agentRegistration = auctionDict['registration']
        agentInitialVal = auctionDict['initial_values']
        
        # Initialize the variables
        self.stats = {'stat_mode': [], 'interval': [], 'stat_type': [], 'value': [], 'statistic_count': 0}
        self.market = {'name': 'none',' period': -1, 'latency': 0, 'market_id': 1, 'network': 'none', 'linkref': 'none', 'pricecap': 0.0, 
                       'special_mode': 'MD_NONE', 'statistic_mode': 1, 'fixed_price': 50.0, 'fixed_quantity': 0.0,
                       'init_price': 0.0, 'init_stdev': 0.0, 'future_mean_price': 0.0, 'use_future_mean_price': 0, 
                       'capacity_reference_object': {'name': 'none', 'capacity_reference_property': 0.0, 'capacity_reference_bid_price': 0.0, 
                                                     'max_capacity_reference_bid_quantity': 0.0, 'capacity_reference_bid_quantity': 0.0},
                       'current_frame': {'start_time': 0.0, 'end_time': 0.0, 'clearing_price':0.0, 'clearing_quantity': 0.0, 'clearing_type': 'CT_NULL', 
                                          'marginal_quantity': 0.0, 'total_marginal_quantity': 0.0, 'marginal_frac': 0.0, 'seller_total_quantity': 0.0, 
                                          'buyer_total_quantity': 0.0, 'seller_min_price': 0.0, 'buyer_total_unrep': 0.0, 'cap_ref_unrep': 0.0, 
                                          'statistics': []}, 
                       'past_frame': {'start_time': 0.0, 'end_time': 0.0, 'clearing_price':0.0, 'clearing_quantity': 0.0, 'clearing_type': 'CT_NULL', 
                                          'marginal_quantity': 0.0, 'total_marginal_quantity': 0.0, 'marginal_frac': 0.0, 'seller_total_quantity': 0.0, 
                                          'buyer_total_quantity': 0.0, 'seller_min_price': 0.0, 'buyer_total_unrep': 0.0, 'cap_ref_unrep': 0.0, 
                                          'statistics': []}, 
                       'cleared_frame': {'start_time': 0.0, 'end_time': 0.0, 'clearing_price':0.0, 'clearing_quantity': 0.0, 'clearing_type': 'CT_NULL', 
                                          'marginal_quantity': 0.0, 'total_marginal_quantity': 0.0, 'marginal_frac': 0.0, 'seller_total_quantity': 0.0, 
                                          'buyer_total_quantity': 0.0, 'seller_min_price': 0.0, 'buyer_total_unrep': 0.0, 'cap_ref_unrep': 0.0, 
                                          'statistics': []}, 
                       'margin_mode': 'AM_NONE', 'ignore_pricecap': 0,'ignore_failedmarket': 0, 'warmup': 1,
                       'total_samples': 0,'clearat': 0,  'clearing_scalar': 0.5, 'longest_statistic': 0.0}  
            
        self.market_output = {'std': -1, 'mean': -1, 'clear_price': -1, 'market_id': 'none', 'pricecap': 0.0} # Initialize market output with default values
        self.buyer = {'name': [], 'price': [], 'quantity': [], 'state': [], 'bid_id': []}
        self.seller = {'name': [], 'price': [], 'quantity': [], 'state': [], 'bid_id': []} 
        self.nextClear = {'from':0, 'quantity':0, 'price':0}
        self.offers = {'name': [], 'price': [], 'quantity': []}
        
        self.market['name'] = agentRegistration['agentName']
        
        # Read and assign initial values from agentInitialVal
        # Market information
        self.market['special_mode'] = agentInitialVal['market_information']['special_mode']
        self.market['market_id'] = agentInitialVal['market_information']['market_id']
        self.market['use_future_mean_price'] = agentInitialVal['market_information']['use_future_mean_price']
        self.market['pricecap'] = agentInitialVal['market_information']['pricecap']
        self.market['clearing_scalar'] = agentInitialVal['market_information']['clearing_scalar']
        self.market['period'] = agentInitialVal['market_information']['period']
        self.market['latency'] = agentInitialVal['market_information']['latency']
        self.market['init_price'] = agentInitialVal['market_information']['init_price']
        self.market['init_stdev'] = agentInitialVal['market_information']['init_stdev']
        self.market['ignore_pricecap'] = agentInitialVal['market_information']['ignore_pricecap']
        self.market['ignore_failedmarket'] = agentInitialVal['market_information']['ignore_failedmarket']
        self.market['statistic_mode'] = agentInitialVal['market_information']['statistic_mode']
        self.market['capacity_reference_object']['name'] = agentInitialVal['market_information']['capacity_reference_object']
        self.market['capacity_reference_object']['max_capacity_reference_bid_quantity'] = agentInitialVal['market_information']['max_capacity_reference_bid_quantity']
        
        # Stats information
        self.stats['stat_mode'] = agentInitialVal['statistics_information']['stat_mode']
        self.stats['interval'] = agentInitialVal['statistics_information']['interval']
        self.stats['stat_type'] = agentInitialVal['statistics_information']['stat_type']
        self.stats['value'] = agentInitialVal['statistics_information']['value']
        
        # Controller information
        self.controller = {'name': [], 'price': [], 'quantity': [], 'state': []}
        self.controller['name'] = agentInitialVal['controller_information']['name']
        self.controller['price'] = agentInitialVal['controller_information']['price']
        self.controller['quantity'] = agentInitialVal['controller_information']['quantity']
        self.controller['state'] = agentInitialVal['controller_information']['state']
        
        # Update market data based on given stats data
        self.market['statistic_count'] = len(self.stats['stat_mode'])
        self.market['longest_statistic'] = max(self.stats['interval'])
        
        # Give the updated mean and std values to the market_output        
        if self.market['statistic_mode'] == 1:
            for k in range(0, len(self.stats['value'])):
                if self.stats['stat_type'][k] == 'SY_MEAN':
                    self.market_output['mean'] = self.stats['value'][k]
                elif self.stats['stat_type'][k] == 'SY_STDEV':
                    self.market_output['std'] = self.stats['value'][k]
        
        # Generate agent publication dictionary
        self.fncs_publish = {
            'auction': {
                self.market['name']: {
                    'market_id': {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 0},
                    'std_dev': {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 0.0},
                    'average_price': {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0},
                    'clear_price': {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0},
                    'price_cap': {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 0.0},
                    'period': {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': -1.0},
                    'initial_price':{'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}                    
                    }
                }
            } 
                
        # Register the agent
        agentRegistrationString = json.dumps(agentRegistration)
        
        fncs.agentRegister(agentRegistrationString.encode('utf-8'))

    # ====================extract float from string ===============================
    def get_num(self,fncs_string):
        return float(''.join(ele for ele in fncs_string if ele.isdigit() or ele == '.'))

    # ====================Obtain values from the broker ================================
    def subscribeVal(self, fncs_sub_value_String):
        if 'refload' in fncs_sub_value_String:
            self.market['capacity_reference_object']['capacity_reference_property'] = parse_kw(fncs_sub_value_String['refload'])
        if "LMP" in fncs_sub_value_String:
            if self.market['capacity_reference_object']['name'] != 'none':
                self.market['capacity_reference_object']['capacity_reference_bid_price'] = self.get_num(fncs_sub_value_String['LMP'])
        # bidder infromation read from fncs_sub_value
        # Assign values to buyers
        if "controller" in fncs_sub_value_String:
            controllerKeys = list (fncs_sub_value_String['controller'].keys())
            for i in range(len(controllerKeys)):
                # Check if it is rebid. If true, then have to delete the existing bid if any
                if self.market['market_id'] == fncs_sub_value_String['controller'][controllerKeys[i]]['market_id']['propertyValue']:
                    if fncs_sub_value_String['controller'][controllerKeys[i]]['rebid']['propertyValue'] != 0:
                        # Check if the bid from the same bid_id is stored, if so, delete
                        if (fncs_sub_value_String['controller'][controllerKeys[i]]['bid_id'] in self.buyer['bid_id']):
                            index_delete = self.buyer['bid_id'].index(fncs_sub_value_String['controller'][controllerKeys[i]]['bid_id'])
                            print ('  rebid', index_delete)
                            for ele in self.buyer.itervalues():
                                del ele[index_delete]
                # Add the new bid:
                self.buyer['name'].append(fncs_sub_value_String['controller'][controllerKeys[i]]['bid_name'])
                self.buyer['price'].append(fncs_sub_value_String['controller'][controllerKeys[i]]['price']['propertyValue'])
                self.buyer['quantity'].append(fncs_sub_value_String['controller'][controllerKeys[i]]['quantity']['propertyValue'])
                self.buyer['state'].append(fncs_sub_value_String['controller'][controllerKeys[i]]['state']['propertyValue'])
                self.buyer['bid_id'].append(fncs_sub_value_String['controller'][controllerKeys[i]]['bid_id']['propertyValue'])
                    
    # turning these off for now
    #            if self.market['market_id'] > fncs_sub_value_String['controller'][controllerKeys[i]]['market_id']['propertyValue']:
    #                if fncs_sub_value_String['controller'][controllerKeys[i]]['market_id']['propertyValue'] == 0:
    #                    print ('controller %s does not have bid for this market period' % (fncs_sub_value_String['controller'][controllerKeys[i]]['bid_name']))
    #                else:
    #                    print('market %d receives controller bid from a previously cleared market with id %d' %(self.market['market_id'], fncs_sub_value_String['controller'][controllerKeys[i]]['market_id']['propertyValue']))
                    
                if self.market['market_id'] < fncs_sub_value_String['controller'][controllerKeys[i]]['market_id']['propertyValue']:
                    print('bidding into future markets is not yet supported')
                
    # ====================Rearrange object based on given initial values =============== 
    def initAuction(self):
        # Initialization when time = 0    
        # Check market pricap values assigned or not
        if self.market['pricecap'] == 0.0:
            self.market['pricecap'] = 9999.0
        
        # Check market period values assigned or not
        if self.market['period'] == 0:
            self.market['period'] = 300
        
        # Check market latency values assigned or not
        if self.market['latency'] < 0:
            self.market['latency'] = 0
        
        # Check the statistic period
        for i in range(0, len(self.stats['interval'])):
            if self.stats['interval'][i] < self.market['period']:
                warnings.warn('market statistic samples faster than the market updates and will be filled with immediate data')
                
            if self.stats['interval'][i] % float(self.market['period']) != 0:
                warnings.warn('market statistic  interval not a multiple of market period, rounding towards one interval')
                self.stats['interval'][i] = self.stats['interval'][i] - (self.stats['interval'][i] % float(self.market['period']))
               
        # Check special mode
        if self.market['special_mode'] != 'MD_NONE' and self.market['fixed_quantity'] < 0.0:
            sys.exit('Auction is using a one-sided market with a negative fixed quantity')
        
        # Initialize latency queue
        self.market['latency_count'] = int (self.market['latency'] / self.market['period']) + 2
        self.market['framedata'] = [[] for i in range(self.market['latency_count'])]  
        self.market['latency_front'] = self.market['latency_back'] = 0
            
        # Assign new keys and values to the market
        if self.market['longest_statistic'] > 0: 
            self.market['history_count'] = int(self.market['longest_statistic'] / self.market['period']) + 2
            self.market['new_prices'] = self.market['init_price']*np.ones(self.market['history_count'])
            self.market['new_market_failures'] = ['CT_EXACT']*self.market['history_count']
        else:
            self.market['history_count'] = 1
            self.market['new_prices'] = self.market['init_price']
            self.market['new_market_failures'] = 'CT_EXACT'
            
        self.market['price_index'] = self.market['price_count'] = 0
        
        if self.market['init_stdev'] < 0.0:
            sys.exit('auction init_stdev is negative!')
            
        # Assign initial values to the market outputs
        self.market_output['std'] = self.market['init_stdev']
        self.market_output['mean'] = self.market['init_price']
        
        if self.market['clearing_scalar'] <= 0.0:
            self.market['clearing_scalar'] = 0.5
        elif self.market['clearing_scalar'] >= 1.0:
            self.market['clearing_scalar'] = 0.5
        
        self.market['current_frame']['clearing_price'] = self.market['past_frame']['clearing_price'] = self.market['init_price']   

    # ====================Presync content=============================================================        
    def presync(self, timeSim):
        
        if len (self.offers['name']) > 0:
            self.offers = {'name': [], 'price': [], 'quantity': []}
        self.timeSim = timeSim
        
        # Define a next dictionary to contain the market clearing information
        self.nextClear = {'from':0, 'quantity':0, 'price':0}
        
        # Define the next time step that market clears
        if self.timeSim == 0:
            self.market['clearat'] = self.timeSim + self.market['period'] - (self.timeSim + self.market['period']) % float(self.market['period'])    
            
            # Update statistics
            self.update_statistics()
            
            # Publish market data at the initial time step
            self.fncs_publish['auction'][self.market['name']]['market_id']['propertyValue'] = self.market['market_id']
            self.fncs_publish['auction'][self.market['name']]['std_dev']['propertyValue'] = self.market['init_stdev']
            self.fncs_publish['auction'][self.market['name']]['average_price']['propertyValue'] = self.market['init_price']
            self.fncs_publish['auction'][self.market['name']]['clear_price']['propertyValue'] = self.market['init_price']
            self.fncs_publish['auction'][self.market['name']]['price_cap']['propertyValue'] = self.market['pricecap']
            self.fncs_publish['auction'][self.market['name']]['period']['propertyValue'] = self.market['period']
            self.fncs_publish['auction'][self.market['name']]['initial_price']['propertyValue'] = self.market['init_price']
            
            fncs_publishString = json.dumps(self.fncs_publish)
            fncs.agentPublish(fncs_publishString)
        
        elif self.timeSim % self.market['period'] == 0:
            self.nextClear['from'] = self.nextClear['quantity'] = self.nextClear['price'] = 0
        
        # Start market clearing process
        if timeSim >= self.market['clearat']:
            self.clear_market()
            self.market['market_id'] += 1
            
            # Display the opening of the next market
            self.market['clearat'] = self.timeSim + self.market['period'] - (self.timeSim + self.market['period']) % self.market['period']
        
            # Update to be published values only when market clears
            if self.market_output['market_id'] != 'none':
                self.market_output['market_id'] = self.market['market_id'] # UPdate the market_id sent to controller
            self.fncs_publish['auction'][self.market['name']]['market_id']['propertyValue'] = self.market_output['market_id']
            self.fncs_publish['auction'][self.market['name']]['std_dev']['propertyValue'] = self.market_output['std']
            self.fncs_publish['auction'][self.market['name']]['average_price']['propertyValue'] = self.market_output['mean']
            self.fncs_publish['auction'][self.market['name']]['clear_price']['propertyValue'] = self.market_output['clear_price']
            self.fncs_publish['auction'][self.market['name']]['price_cap']['propertyValue'] = self.market_output['pricecap']
            self.fncs_publish['auction'][self.market['name']]['period']['propertyValue'] = self.market['period']
            self.fncs_publish['auction'][self.market['name']]['initial_price']['propertyValue'] = self.market['init_price']
            
            fncs_publishString = json.dumps(self.fncs_publish)
            
            fncs.agentPublish(fncs_publishString)
            fncs.publish ("clear_price", self.market_output['clear_price'])
        
    # ====================Sync content============================================================= 
    # Do nothing in sync process
    
    # ====================Postsync content========================================================= 
    # Do nothing in postsync process        
               
    # ======================== Update statistics for the calculation of std and mean ==============    
    def update_statistics(self):
        sample_need = skipped = 0
        meanVal = stdev = 0.0
        startIdx = stopIdx = idx = 0
        
        # If no statistics
        if self.market['statistic_count'] < 1:
            return
        
        if self.market['new_prices'][0] == 0:
            return
        
        # Caluclate values for each stat mode
        for k in range(0, len(self.stats['interval'])):
            meanVal = 0.0
            sample_need = int (self.stats['interval'][k]/self.market['period'])
            if self.stats['stat_mode'][k] == 'ST_CURR':
                stopIdx = self.market['price_index']
            elif self.stats['stat_mode'][k] == 'ST_PAST':
                stopIdx = self.market['price_index'] - 1
                
            # Calculate start index
            startIdx = (self.market['history_count'] + stopIdx - sample_need) % self.market['history_count']
            for i in range(0, sample_need):
                idx = (startIdx + i + self.market['history_count']) % self.market['history_count']
                if self.market['ignore_pricecap'] == 'IP_TRUE' and (self.market['new_prices'][idx] == self.market['pricecap'] or self.market['new_prices'][idx] == -self.market['pricecap']):
                    skipped+= 1
                elif self.market['ignore_failedmarket'] == 'IFM_TRUE' and self.market['new_market_failures'][idx] == 'CT_FAILURE':
                    skipped+= 1
                else:
                    meanVal += self.market['new_prices'][idx]
            
            # Calculate mean values:
            if skipped != sample_need:
                meanVal /= (sample_need - skipped)
            else:
                meanVal = 0.0
                warnings.warn('All values in auction statistic calculations were skipped. Setting mean to zero.')
            if self.market['use_future_mean_price'] == 1:
                meanVal = self.market['future_mean_price']
            if self.stats['stat_type'][k] == 'SY_MEAN':
                self.stats['value'][k] = meanVal
            elif self.stats['stat_type'][k] == 'SY_STDEV':
                x = 0.0
                if (sample_need + (1 if self.stats['stat_mode'][k] == 'ST_PAST' else 0)) > self.market['total_samples']:
                    self.stats['value'][k] = self.market['init_stdev']
                else:
                    stdev = 0.0
                    for j in range(0, sample_need):
                        idx = (startIdx + j + self.market['history_count']) % self.market['history_count']
                        if self.market['ignore_pricecap'] == 'IP_TRUE' and (self.market['new_prices'][idx] == self.market['pricecap'] or self.market['new_prices'][idx] == self.market['pricecap']):
                            pass # ignore the value
                        if self.market['ignore_pricecap'] == 'IFM_TRUE' and self.market['new_market_failures'][idx] == 'CT_FAILURE':
                            pass # ignore the value
                        else:
                            x = self.market['new_prices'][idx] - meanVal
                            stdev += x*x
                    if skipped != sample_need:
                        stdev /= (sample_need - skipped)
                    else:
                        stdev = 0.0
                    self.stats['value'][k] = math.sqrt(stdev)
                    
            # Give the updated mean snd std values to the market_output        
            if self.market['statistic_mode'] == 1:
                if self.market['latency'] == 0:
                    if self.stats['stat_type'][k] == 'SY_MEAN':
                        self.market_output['mean'] = self.stats['value'][k]
                    elif self.stats['stat_type'][k] == 'SY_STDEV':
                        self.market_output['std'] = self.stats['value'][k]

    # =========================================== Clear market ======================================================            
    def clear_market(self):
        
        bid_offset = 0.0001
        cap_ref_unrep = 0.0
        
        # for metrics output
        self.offers['name'] = self.buyer['name']
        self.offers['price'] = self.buyer['price']
        self.offers['quantity'] = self.buyer['quantity']

        # These need to be re-initialized
        curve_seller = curve()
        curve_buyer = curve()
        unresponsive_sell = unresponsive_buy =  responsive_sell =  responsive_buy = 0
        
        # Bid from the capacity reference (i.e. MATPOWER/PYPOWER)
        if self.market['capacity_reference_object']['name'] != 'none' and self.market['special_mode'] == 'MD_NONE':
            max_capacity_reference_bid_quantity = self.market['capacity_reference_object']['max_capacity_reference_bid_quantity']
            capacity_reference_bid_price = self.market['capacity_reference_object']['capacity_reference_bid_price']
            print("  Capacity reference bids", capacity_reference_bid_price, "up to", max_capacity_reference_bid_quantity)
            # Submit bid
            if max_capacity_reference_bid_quantity < 0: 
                # Negative quantity is buyer
                self.buyer['name'].append(self.market['capacity_reference_object']['name'])
                self.buyer['price'].append(capacity_reference_bid_price)
                self.buyer['quantity'].append(float(-max_capacity_reference_bid_quantity))
                self.buyer['state'].append('ON')
                self.buyer['bid_id'].append(self.market['capacity_reference_object']['name'])
            elif max_capacity_reference_bid_quantity > 0: 
                # Positive quantity is seller
                self.seller['name'].append(self.market['capacity_reference_object']['name'])
                self.seller['price'].append(capacity_reference_bid_price)
                self.seller['quantity'].append(max_capacity_reference_bid_quantity)
                self.seller['state'].append('ON')
                self.seller['bid_id'].append(self.market['capacity_reference_object']['name'])
                
        # Check special_mode and sort buyers and sellers curves
        single_quantity = single_price = 0.0
        
        if self.market['special_mode'] == 'MD_SELLERS':
            # Sort offers curve:
            seller = self.seller 
            # Iterate each seller to obtain the final seller curve    
            for i in range (len(seller['name'])):
                curve_seller.add_to_curve(seller['price'][i], seller['quantity'][i], seller['name'][i], seller['state'][i])
            
            # Rearranged fixed price or quantity 
            if self.market['fixed_price'] * self.market['fixed_quantity'] != 0:
                warnings.warn('fixed_price and fixed_quantity are set in the same single auction market ~ only fixed_price will be used')
           
            if self.market['fixed_quantity'] > 0.0:
                for i in range(curve_seller.count):
                    single_price = curve_seller.price[i]
                    single_quantity += curve_seller.quantity[i]
                    if single_quantity >= self.market['fixed_quantity']: 
                        break
                if single_quantity > self.market['fixed_quantity']: 
                    single_quantity = self.market['fixed_quantity']
                    clearing_type = 'CT_SELLER'
                elif single_quantity == self.market['fixed_quantity']:
                    clearing_type = 'CT_EXACT'
                else:
                    clearing_type = 'CT_FAILURE'
                    single_quantity = 0.0
                    single_price = 0 if curve_seller.count == 0 else curve_seller.price[0] - bid_offset
                    
            elif self.market['fixed_quantity'] < 0.0:
                warnings.warn('fixed_quantity is negative')
                
            else:
                single_price = self.market['fixed_price']
                for i in range(curve_seller.count):
                    if curve_seller.price[i] <= self.market['fixed_price']:
                        single_quantity += curve_seller.quantity[i]
                    else: break
                if single_quantity > 0.0: 
                    clearing_type = 'CT_EXACT'
                else: 
                    clearing_type = 'CT_NULL'
                    
            self.nextClear['price'] = single_price
            self.nextClear['quantity'] = single_quantity    

        elif self.market['special_mode'] == 'MD_BUYERS':
            # Sort buyers curve:
            buyer = self.buyer 
            # Iterate each buyer to obtain the final buyer curve    
            for i in range (len(buyer['name'])):
                curve_buyer.add_to_curve(buyer['price'][i], buyer['quantity'][i], buyer['name'][i], buyer['state'][i])
            
            # Rearranged fix price or quantity 
            if self.market['fixed_price'] * self.market['fixed_quantity'] != 0:
                warnings.warn('fixed_price and fixed_quantity are set in the same single auction market ~ only fixed_price will be used')
            
            if self.market['fixed_quantity'] > 0.0:
                for i in range(curve_buyer.count):
                    single_price = curve_buyer.price[i]
                    single_quantity += curve_buyer.quantity[i]
                    if single_quantity >= self.market['fixed_quantity']: 
                        break
                if single_quantity > self.market['fixed_quantity']: 
                        single_quantity = self.market['fixed_quantity']
                        clearing_type = 'CT_BUYER'
                elif single_quantity == self.market['fixed_quantity']:
                        clearing_type = 'CT_EXACT'
                else:
                    clearing_type = 'CT_FAILURE'
                    single_quantity = 0.0
                    single_price = 0 if curve_buyer.count == 0 else curve_buyer.price[0] + bid_offset
            
            elif self.market['fixed_quantity'] < 0.0:
                warnings.warn('fixed_quantity is negative')
           
            else:
                single_price = self.market['fixed_price']
                for i in range(curve_buyer.count):
                    if curve_buyer.price[i] >= self.market['fixed_price']:
                        single_quantity += curve_buyer.quantity[i]
                    else: break
                if single_quantity > 0.0: 
                    clearing_type = 'CT_EXACT'
                else: 
                    clearing_type = 'CT_NULL'
                    
            self.nextClear['price'] = single_price
            self.nextClear['quantity'] = single_quantity  
        
        elif self.market['special_mode'] == 'MD_FIXED_SELLER':
            # Sort offers curve:
            buyer = self.buyer
            seller = self.seller 
            # Iterate each seller to obtain the final seller curve    
            for i in range (len(seller['name'])):
                curve_seller.add_to_curve(seller['price'][i], seller['quantity'][i], seller['name'][i], seller['state'][i])
            if len(buyer['quantity']) > 0:
                warnings.warn('Seller-only auction was given purchasing bids')
            
            # Since  assumes no buyers will bid into the market and uses a fixed price or quantity 
            # (defined by fixed_price or fixed_quantity below) for the buyer's market            
            self.buyer['name'].append(self.market['name'])
            self.buyer['price'].append(float(self.market['fixed_price']))
            self.buyer['quantity'].append(int(self.market['fixed_quantity']))
            self.buyer['state'].append('ON')
            # Iterate each buyer to obtain the final buyer curve
            for i in range (len(buyer['name'])):
                curve_buyer.add_to_curve(buyer['price'][i], buyer['quantity'][i], buyer['name'][i], buyer['state'][i])
            
        elif self.market['special_mode'] == 'MD_FIXED_BUYER':
            # Sort buyers curve:
            buyer = self.buyer
            seller = self.seller 
            # Iterate each buyer to obtain the final buyer curve    
            for i in range (len(buyer['name'])):
                curve_buyer.add_to_curve(buyer['price'][i], buyer['quantity'][i], buyer['name'][i], buyer['state'][i])
            if len(seller['quantity']) > 0:
                warnings.warn('Buyer-only auction was given offering bids')
            
            # Since assuming no sellers are on the system. 
            # The seller's market is then defined by the fixed_price or fixed_quantity inputs.           
            self.seller['name'].append(self.market['name'])
            self.seller['price'].append(float(self.market['fixed_price']))
            self.seller['quantity'].append(int(self.market['fixed_quantity']))
            self.seller['state'].append('ON')
            # Iterate each seller to obtain the final seller curve
            for i in range (len(seller['name'])):
                curve_seller.add_to_curve(seller['price'][i], seller['quantity'][i], seller['name'][i], seller['state'][i])
                
        elif self.market['special_mode'] == 'MD_NONE':
            # Obtain buyer and seller curves at this time step
            buyer = self.buyer 
            seller = self.seller 
            # Iterate each buyer to obtain the final buyer curve
            for i in range (len(buyer['name'])):
                curve_buyer.add_to_curve(buyer['price'][i], buyer['quantity'][i], buyer['name'][i], buyer['state'][i])
            # Iterate each seller to obtain the final seller curve    
            for i in range (len(seller['name'])):
                curve_seller.add_to_curve(seller['price'][i], seller['quantity'][i], seller['name'][i], seller['state'][i])
            
        # "Bid" at the price cap from the unresponsive load (add this last, when we have a summary of the responsive bids)
        if self.market['capacity_reference_object']['name'] != 'none' and self.market['special_mode'] != 'MD_FIXED_BUYER':
            total_unknown = curve_buyer.total - curve_buyer.total_on - curve_buyer.total_off
            if total_unknown > 0.001:
                warnings.warn('total_unknown is non-zero; some controllers are not providing their states with their bids')
            refload = self.market['capacity_reference_object']['capacity_reference_property']
            unresp = refload - curve_buyer.total_on - total_unknown/2
            print('  Unresponsive load bid: Refload,#buyers,on,off,unresp=', refload, curve_buyer.count, curve_buyer.total_on, curve_buyer.total_off, unresp)
#            unresp = 2000.0
            unresp = 30.0
            print('  MANUAL override', unresp, 'kW unresponsive load bid')

            if unresp < -0.001:
                warnings.warn('capacity_reference has negative unresponsive load--this is probably due to improper bidding')
            elif unresp > 0.001:
                self.buyer['name'].append(self.market['capacity_reference_object']['name'])
                self.buyer['price'].append(float(self.market['pricecap']))
                self.buyer['quantity'].append(unresp) # buyer bid in cpp codes is negative, here bidder quantity always set positive
                self.buyer['state'].append('ON')
                self.buyer['bid_id'].append(self.market['capacity_reference_object']['name'])
                curve_buyer.add_to_curve(self.market['pricecap'], unresp, self.market['capacity_reference_object']['name'], 'ON')

        # Calculate clearing price and quantity
        if curve_buyer.count > 0:
            curve_buyer.set_curve_order ('descending')
        if curve_seller.count > 0:
            curve_seller.set_curve_order ('ascending')

        # If the market mode is MD_SELLERS or MD_BUYERS:
        if self.market['special_mode'] == 'MD_SELLERS' or self.market['special_mode'] == 'MD_BUYERS':
            # Update market output information
            self.market_output['clear_price'] = self.nextClear['price']
            self.market_output['pricecap'] = self.market['pricecap']
            self.market_output['market_id'] = self.market['market_id']
            
        elif curve_buyer.count > 0 and curve_seller.count > 0:
            
            a = self.market['pricecap']
            b = -self.market['pricecap']
            check = 0 # The flag
            demand_quantity = supply_quantity = 0

            for i in range(curve_seller.count):
                # Calculate numbers of responsive_sell and unresponsive_sell
                if curve_seller.price[i] == self.market['pricecap']:
                    unresponsive_sell += curve_seller.quantity[i]
                else:
                    responsive_sell += curve_seller.quantity[i]
            total_sell = unresponsive_sell + responsive_sell; # Did not see it used anywhere
            for i in range(curve_buyer.count):
                if curve_buyer.price[i] == self.market['pricecap']:
                    unresponsive_buy += curve_buyer.quantity[i]
                else:
                    responsive_buy += curve_buyer.quantity[i]
            total_buy = unresponsive_buy + responsive_buy; # Did not see it used anywhere

            print('  curve summaries (sell #-resp-unresp, buy #-resp-unresp)',curve_seller.count, responsive_sell, unresponsive_sell, curve_buyer.count, responsive_buy, unresponsive_buy)
            
            # Calculate clearing quantity and price here
            # Define the section number of the buyer and the seller curves respectively as i and j
            i = j = 0
            clearing_type = 'CT_NULL'
            clear_quantity = clear_price = 0
            while i < curve_buyer.count and j < curve_seller.count and curve_buyer.price[i] >= curve_seller.price[j]:
                buy_quantity = demand_quantity + curve_buyer.quantity[i]
                sell_quantity = supply_quantity + curve_seller.quantity[j]
                # If marginal buyer currently:
                if buy_quantity > sell_quantity:
                    clear_quantity = supply_quantity = sell_quantity
                    a = b = curve_buyer.price[i]
                    j += 1
                    check = 0
                    clearing_type = 'CT_BUYER'
                # If marginal seller currently:
                elif buy_quantity < sell_quantity:
                    clear_quantity = demand_quantity = buy_quantity
                    a = b = curve_seller.price[j]
                    i += 1
                    check = 0
                    clearing_type = 'CT_SELLER'
                # Buy quantity equal sell quantity but price split  
                else:
                    clear_quantity = demand_quantity = supply_quantity = buy_quantity
                    a = curve_buyer.price[i]
                    b = curve_seller.price[j]
                    i += 1
                    j += 1
                    check = 1
            # End of the curve comparison, and if CT_EXACT, get the clear price
            if a == b:
                clear_price = a 
            # If there was price agreement or quantity disagreement
            if check:
                clear_price = a 
                if supply_quantity == demand_quantity:
                    # At least one side exhausted at same quantity
                    if i == curve_buyer.count or j == curve_seller.count:
                        if a == b:
                            clearing_type = 'CT_EXACT'
                        else:
                            clearing_type = 'CT_PRICE'
                    # Exhausted buyers, sellers unsatisfied at same price
                    elif i == curve_buyer.count and b == curve_seller.price[j]:
                        clearing_type = 'CT_SELLER'
                    # Exhausted sellers, buyers unsatisfied at same price
                    elif j == curve_seller.count and a == curve_buyer.price[i]:
                        clearing_type = 'CT_BUYER'
                    # Both sides satisfied at price, but one side exhausted  
                    else:
                        if a == b:
                            clearing_type = 'CT_EXACT'
                        else:
                            clearing_type = 'CT_PRICE'
                # No side exausted
                else:
                    # Price changed in both directions
                    if a != curve_buyer.price[i] and b != curve_seller.price[j] and a == b:
                        clearing_type = 'CT_EXACT'
                    # Sell price increased ~ marginal buyer since all sellers satisfied
                    elif a == curve_buyer.price[i] and b != curve_seller.price[j]:
                        clearing_type = 'CT_BUYER'
                    # Buy price increased ~ marginal seller since all buyers satisfied
                    elif a != curve_buyer.price[i] and b == curve_seller.price[j]:
                        clearing_type = 'CT_SELLER'
                        clear_price = b # use seller's price, not buyer's price
                    # Possible when a == b, q_buy == q_sell, and either the buyers or sellers are exhausted
                    elif a == curve_buyer.price[i] and b == curve_seller.price[j]:
                        if i == curve_buyer.count and j == curve_seller.count:
                            clearing_type = 'CT_EXACT'
                        elif i == curve_buyer.count:
                            clearing_type = 'CT_SELLER'
                        elif j == curve_seller.count:
                            clearing_type = 'CT_BUYER'
                    else:
                        # Marginal price
                        clearing_type = 'CT_PRICE'
                
                # If CT_PRICE, calculate the clearing price here
                dHigh = dLow = 0
                if clearing_type == 'CT_PRICE':
                    avg = (a+b)/2.0
                    # Calculating clearing price limits:   
                    dHigh = a if i == curve_buyer.count else curve_buyer.price[i]
                    dLow = b if j == curve_seller.count else curve_seller.price[j]
                    # Needs to be just off such that it does not trigger any other bids
                    if a == self.market['pricecap'] and b != -self.market['pricecap']:
                        if curve_buyer.price[i] > b:
                            clear_price = curve_buyer.price[i] + bid_offset
                        else:
                            clear_price = b 
                    elif a != self.market['pricecap'] and b == -self.market['pricecap']:
                        if curve_seller.price[j] < a:
                            clear_price = curve_seller.price[j] - bid_offset
                        else:
                            clear_price = a 
                    elif a == self.market['pricecap'] and b == -self.market['pricecap']:
                        if i == curve_buyer.count and j == curve_seller.count:
                            clear_price = 0 # no additional bids on either side
                        elif j == curve_seller.count: # buyers left
                            clear_price = curve_buyer.price[i] + bid_offset
                        elif i == curve_buyer.count: # sellers left
                            clear_price = curve_seller.price[j] - bid_offset
                        else: # additional bids on both sides, just no clearing
                            clear_price = (dHigh + dLow)/2
                    else:
                        if i != curve_buyer.count and curve_buyer.price[i] == a:
                            clear_price = a 
                        elif j != curve_seller.count and curve_seller.price[j] == b:
                            clear_price = b 
                        elif i != curve_buyer.count and avg < curve_buyer.price[i]:
                            clear_price = dHigh + bid_offset
                        elif j != curve_seller.count and avg > curve_seller.price[j]:
                            clear_price = dLow - bid_offset
                        else:
                            clear_price = avg 
                                
            # Check for zero demand but non-zero first unit sell price
            if clear_quantity == 0:
                clearing_type = 'CT_NULL'
                if curve_seller.count > 0 and curve_buyer.count == 0:
                    clear_price = curve_seller.price[0] - bid_offset
                elif curve_seller.count == 0 and curve_buyer.count > 0:
                    clear_price = curve_buyer.price[0] + bid_offset
                else:
                    if curve_seller.price[0] == self.market['pricecap']:
                        clear_price = curve_buyer.price[0] + bid_offset
                    elif curve_seller.price[0] == -self.market['pricecap']:
                        clear_price = curve_seller.price[0] - bid_offset  
                    else:
                        clear_price = curve_seller.price[0] + (curve_buyer.price[0] - curve_seller.price[0]) * self.market['clearing_scalar']
           
            elif clear_quantity < unresponsive_buy:
                clearing_type = 'CT_FAILURE'
                clear_price = self.market['pricecap']
            
            elif clear_quantity < unresponsive_sell:
                clearing_type = 'CT_FAILURE'
                clear_price = -self.market['pricecap']
            
            elif clear_quantity == unresponsive_buy and clear_quantity == unresponsive_sell:
                # only cleared unresponsive loads
                clearing_type = 'CT_PRICE'
                clear_price = 0.0
            
            self.nextClear['price'] = clear_price
            self.nextClear['quantity'] = clear_quantity
            
            # Update market output information
            self.market_output['clear_price'] = clear_price
            self.market_output['pricecap'] = self.market['pricecap']
            self.market_output['market_id'] = self.market['market_id']

        # If the market mode MD_NONE and at least one side is not given
        else:
            if curve_seller.count > 0 and curve_buyer.count == 0:
                self.nextClear['price'] = curve_seller.price[0] - bid_offset
            elif curve_seller.count == 0 and curve_buyer.count > 0:
                self.nextClear['price'] = curve_buyer.price[0] + bid_offset
            elif curve_seller.count > 0 and curve_buyer.count > 0:
                self.nextClear['price'] = curve_seller.price[0] + (curve_buyer.price[0] - curve_seller.price[0]) * self.market['clearing_scalar']
            elif curve_seller.count == 0 and curve_buyer.count == 0:
                self.nextClear['price'] = 0.0
            self.nextClear['quantity'] = 0
            clearing_type = 'CT_NULL'
            # Display warining for CT_NULL case
            if curve_seller.count == 0 :
                missingBidder = "seller"
            elif curve_buyer.count == 0:
                missingBidder = "buyer"
            print ('  Market %s fails to clear due to missing %s' % (self.market['name'], missingBidder))
            
            # Update market output information
            self.market_output['clear_price'] = self.nextClear['price']
            self.market_output['pricecap'] = self.market['pricecap']
            self.market_output['market_id'] = self.market['market_id']
        
        # Calculation of the marginal 
        marginal_total = marginal_quantity = marginal_frac = 0.0
        if clearing_type == 'CT_BUYER':
            marginal_subtotal = 0
            i = 0
            for i in range(curve_buyer.count):
                if curve_buyer.price[i] > self.nextClear['price']:
                    marginal_subtotal = marginal_subtotal + curve_buyer.quantity[i]
                else:
                    break
            marginal_quantity =  self.nextClear['quantity'] - marginal_subtotal
            for j in range(i, curve_buyer.count):
                if curve_buyer.price[i] == self.nextClear['price']:
                    marginal_total += curve_buyer.quantity[i]
                else:
                    break
            if marginal_total > 0.0:
                marginal_frac = float(marginal_quantity) / marginal_total
       
        elif clearing_type == 'CT_SELLER':
            marginal_subtotal = 0
            i = 0
            for i in range(0, curve_seller.count):
                if curve_seller.price[i] > self.nextClear['price']:
                    marginal_subtotal = marginal_subtotal + curve_seller.quantity[i]
                else:
                    break
            marginal_quantity =  self.nextClear['quantity'] - marginal_subtotal
            for j in range(i, curve_seller.count):
                if curve_seller.price[i] == self.nextClear['price']:
                    marginal_total += curve_seller.quantity[i]
                else:
                    break
            if marginal_total > 0.0:
                marginal_frac = float(marginal_quantity) / marginal_total 
        
        else:
            marginal_quantity = 0.0
            marginal_frac = 0.0
        

        print(self.timeSim,'(Type,Price,MargQ,MargT,MargF)',clearing_type, self.nextClear['price'], marginal_quantity, marginal_total, marginal_frac)

        # Update new_price and price_index, for the calculation of sdv and mean from update_statistics later
        if self.market['history_count'] > 0:
            # If the market clearing times equal to the described statistic interval, update it from 0
            if self.market['price_index'] == self.market['history_count']:
                self.market['price_index'] = 0
            # Put the newly cleared price into the new_prices array
            self.market['new_prices'][self.market['price_index']] = self.nextClear['price']
            self.market['new_market_failures'][self.market['price_index']] = self.market['current_frame']['clearing_type']
            # Update price_index
            self.market['price_index'] += 1
        
        # Limit price within the pricecap
        if self.nextClear['price'] < -self.market['pricecap']:
            self.nextClear['price'] = -self.market['pricecap']
        
        elif self.nextClear['price'] > self.market['pricecap']:
            self.nextClear['price'] = self.market['pricecap']
        
        # Update cleared_frame data
        self.market['cleared_frame']['market_id'] = self.market['market_id']
        self.market['cleared_frame']['start_time'] = self.timeSim + self.market['latency']
        self.market['cleared_frame']['end_time'] = self.timeSim + self.market['latency'] + self.market['period']
        self.market['cleared_frame']['clearing_price'] = self.nextClear['price']
        self.market['cleared_frame']['clearing_quantity'] = self.nextClear['quantity']
        self.market['cleared_frame']['clearing_type'] = clearing_type
        self.market['cleared_frame']['marginal_quantity'] = marginal_quantity
        self.market['cleared_frame']['total_marginal_quantity'] = marginal_total
        self.market['cleared_frame']['buyer_total_quantity'] = curve_buyer.count
        self.market['cleared_frame']['seller_total_quantity'] = curve_seller.count
        if curve_seller.count > 0:
            self.market['cleared_frame']['seller_min_price'] = min(curve_seller.price)
        self.market['cleared_frame']['marginal_frac'] = marginal_frac
        self.market['cleared_frame']['buyer_total_unrep'] = unresponsive_buy
        self.market['cleared_frame']['cap_ref_unrep'] = cap_ref_unrep
        
        # Update current_frame
        if self.market['latency'] > 0:
            
            self.pop_market_frame()
            self.update_statistics()
            self.push_market_frame()
            
        else:
            
            self.market['past_frame'] = deepcopy(self.market['current_frame'])
            # Copy new data in
            self.market['current_frame']= deepcopy(self.market['cleared_frame'])
            # Update market total_samples numbers
            self.market['total_samples'] += 1
            # Update statistics for the calculation of std and mean
            self.update_statistics()
        
        # End of the clear_market def
        curve_seller = None
        curve_buyer = None
        
        # initialize the seller and buyer dictionary
        self.buyer = {'name': [], 'price': [], 'quantity': [], 'state': [], 'bid_id': []}
        self.seller = {'name': [], 'price': [], 'quantity': [], 'state': [], 'bid_id': []} 
            
    # =========================================== Pop market ======================================================
    # Fill in the exposed current market values with those within the
    def pop_market_frame(self):
        
        # Check if market framedata queue has any data
        if self.market['latency_front'] == self.market['latency_back']:
            print ('market latency queue has no data')
            return
        
        # Obtain the current market frame used
        frame = self.market['framedata'][self.market['latency_front']]
        
        # Check if the starting the frame
        if self.timeSim < frame['start_time']:
            print ('market latency queue data is not yet applicable')
            return 
        
        # Copy current frame data to past_frame
        self.market['past_frame'] = deepcopy(self.market['current_frame'])
        
        # Copy new data to the current frame
        self.market['current_frame'] = deepcopy(frame)
        
        # Copy statistics
        # Give the updated mean snd std values to the market_output        
        if self.market['statistic_mode'] == 1:
            for k in range(0, len(self.stats['stat_type'])):
                if self.stats['stat_type'][k] == 'SY_MEAN':
                    self.market_output['mean'] = frame['statistics'][k]
                elif self.stats['stat_type'][k] == 'SY_STDEV':
                    self.market_output['std'] = frame['statistics'][k]

        # Having used latency_front index, push the index forward
        self.market['latency_front'] = (self.market['latency_front'] + 1) / self.market['latency_count']    
    
    # =========================================== push market ======================================================
    # Take the current market values and enqueue them on the end of the latency frame queue
    def push_market_frame(self):
    
        if (self.market['latency_back'] + 1) % self.market['latency_count'] == self.market['latency_front']:
            sys.exit('market latency queue is overwriting as-yet unused data, so is not long enough or is not consuming data')
        
        # Copy cleared frame data into the current market frame used
        self.market['framedata'][self.market['latency_back']] = deepcopy(self.market['cleared_frame'])
        self.market['framedata'][self.market['latency_back']]['statistics'] = deepcopy(self.stats['value'])
        
        # Update latency_back index:
        self.market['latency_back'] = (self.market['latency_back'] + 1) % self.market['latency_count']  
        
        if self.market['latency'] > 0:
            self.market['total_samples'] += 1
    
    # =========================================== check next market ================================================
    # Seems the next_frame is not used    
