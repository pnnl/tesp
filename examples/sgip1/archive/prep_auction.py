#	Copyright (C) 2018 Battelle Memorial Institute
import sys
import json
import numpy as np

# write yaml for auction.py to subscribe meter voltages, house temperatures, hvac load and hvac state
# write txt for gridlabd to subscribe house setpoints and meter price; publish meter voltages
# write the json agent dictionary for post-processing, and run-time configuration of auction.py

# we want the same psuedo-random thermostat schedules each time, for repeatability
np.random.seed (0)

# top-level data:
dt = 15
period = 300
broker = 'tcp://localhost:5570'
network_node = 'network_node'
Eplus_load = 'R1_12_47_1_load_4_Eplus_load4' # Eplus_load
Eplus_meter = 'R1_12_47_1_load_4_Eplus_meter4' # Eplus_meter

# controller data:
periodController = period
bid_delay = 3.0 * dt # time controller bids before market clearing
control_mode = 'CN_RAMP'
use_predictive_bidding = 0
use_override = 'OFF'

wakeup_start_lo = 5.0
wakeup_start_hi = 6.5
daylight_start_lo = 8.0
daylight_start_hi = 9.0
evening_start_lo = 17.0
evening_start_hi = 18.5
night_start_lo = 22.0
night_start_hi = 23.5

wakeup_set_lo = 78.0
wakeup_set_hi = 80.0
daylight_set_lo = 84.0
daylight_set_hi = 86.0
evening_set_lo = 78.0
evening_set_hi = 80.0
night_set_lo = 72.0
night_set_hi = 74.0

ramp_lo = 0.5
ramp_hi = 3.0
deadband_lo = 2.0
deadband_hi = 3.0
offset_limit_lo = 2.0
offset_limit_hi = 4.0
ctrl_cap_lo = 1.0
ctrl_cap_hi = 3.0

# market data:
marketName = 'Market_1'
unit = 'kW'
periodMarket = period
initial_price = 0.02078
std_dev = 0.01 # 0.00361
price_cap = 3.78
special_mode = 'MD_NONE' #'MD_BUYERS'
use_future_mean_price = 0
clearing_scalar = 0.0
latency = 0
ignore_pricecap = 0
ignore_failedmarket = 0
statistic_mode = 1
stat_mode =  ['ST_CURR', 'ST_CURR']
interval = [86400, 86400]
stat_type = ['SY_MEAN', 'SY_STDEV']
value = [0.02078, 0.01] # 0.00361]
capacity_reference_object = 'substation_transformer'
max_capacity_reference_bid_quantity = 5000

# house data:
air_temperature = 78.0 # 0.0

# GridLAB-D file parsing
fileroot = sys.argv[1]
ip = open (fileroot + '.glm', 'r')

controllers = {}
auctions = {}
ip.seek(0,0)
inFNCSmsg = False
inHouses = False
inTriplexMeters = False
endedHouse = False
isELECTRIC = False

houseName = ''
meterName = ''
FNCSmsgName = ''

# Obtain controller dictionary based on houses with electric cooling
for line in ip:
	lst = line.split()
	if len(lst) > 1:
		if lst[1] == 'triplex_meter':
			inTriplexMeters = True
		if lst[1] == 'house':
			inHouses = True
		if lst[1] == 'fncs_msg':
			inFNCSmsg = True
		# Check for ANY object within the house, and don't use its name:
		if inHouses == True and lst[0] == 'object' and lst[1] != 'house':
			endedHouse = True
		if inFNCSmsg == True:
			if lst[0] == 'name':
				FNCSmsgName = lst[1].strip(';')
				inFNCSmsg = False
		if inTriplexMeters == True:
			if lst[0] == 'name':
				meterName = lst[1].strip(';')
				inTriplexMeters = False
		if inHouses == True:
			if lst[0] == 'name' and endedHouse == False:
				houseName = lst[1].strip(';')
			if lst[0] == 'air_temperature':
				air_temperature = lst[1].strip(';')
			if lst[0] == 'cooling_system_type':
				if (lst[1].strip(';') == 'ELECTRIC'):
					isELECTRIC = True
	elif len(lst) == 1:
		if inHouses == True: 
			inHouses = False
			endedHouse = False
			if isELECTRIC == True:
				controller_name = houseName + '_hvac'
#				controllers[controller_name] = {}
				wakeup_start = np.random.uniform (wakeup_start_lo, wakeup_start_hi)
				daylight_start = np.random.uniform (daylight_start_lo, daylight_start_hi)
				evening_start = np.random.uniform (evening_start_lo, evening_start_hi)
				night_start = np.random.uniform (night_start_lo, night_start_hi)
				wakeup_set = np.random.uniform (wakeup_set_lo, wakeup_set_hi)
				daylight_set = np.random.uniform (daylight_set_lo, daylight_set_hi)
				evening_set = np.random.uniform (evening_set_lo, evening_set_hi)
				night_set = np.random.uniform (night_set_lo, night_set_hi)
				deadband = np.random.uniform (deadband_lo, deadband_hi)
				offset_limit = np.random.uniform (offset_limit_lo, offset_limit_hi)
				ramp = np.random.uniform (ramp_lo, ramp_hi)
				ctrl_cap = np.random.uniform (ctrl_cap_lo, ctrl_cap_hi)
				controllers[controller_name] = {'control_mode': control_mode, 
																			 'houseName': houseName, 
																			 'meterName': meterName, 
																			 'period': periodController,
																			 'wakeup_start': float('{:.3f}'.format(wakeup_start)),
																			 'daylight_start': float('{:.3f}'.format(daylight_start)),
																			 'evening_start': float('{:.3f}'.format(evening_start)),
																			 'night_start': float('{:.3f}'.format(night_start)),
																			 'wakeup_set': float('{:.3f}'.format(wakeup_set)),
																			 'daylight_set': float('{:.3f}'.format(daylight_set)),
																			 'evening_set': float('{:.3f}'.format(evening_set)),
																			 'night_set': float('{:.3f}'.format(night_set)),
																			 'deadband': float('{:.3f}'.format(deadband)),
																			 'offset_limit': float('{:.3f}'.format(offset_limit)),
																			 'ramp': float('{:.4f}'.format(ramp)), 
																			 'price_cap': float('{:.3f}'.format(ctrl_cap)),
																			 'bid_delay': bid_delay, 
																			 'use_predictive_bidding': use_predictive_bidding, 
																			 'use_override': use_override}
				isELECTRIC = False

# Write market dictionary
auctions[marketName] = {'market_id': 1, 
												'unit': unit, 
												'special_mode': special_mode, 
												'use_future_mean_price': use_future_mean_price, 
												'pricecap': price_cap, 
												'clearing_scalar': clearing_scalar,
												'period': periodMarket, 
												'latency': latency, 
												'init_price': initial_price, 
												'init_stdev': std_dev, 
												'ignore_pricecap': ignore_pricecap, 
												'ignore_failedmarket': ignore_failedmarket,
												'statistic_mode': statistic_mode, 
												'capacity_reference_object': capacity_reference_object, 
												'max_capacity_reference_bid_quantity': max_capacity_reference_bid_quantity,
												'stat_mode': stat_mode, 
												'stat_interval': interval, 
												'stat_type': stat_type, 
												'stat_value': [0 for i in range(len(stat_mode))]}

# Close files
ip.close()

dictfile = fileroot + '_agent_dict.json'
dp = open (dictfile, 'w')
meta = {'markets':auctions,'controllers':controllers,'dt':dt,'GridLABD':FNCSmsgName}
print (json.dumps(meta), file=dp)
dp.close()

# write YAML file
yamlfile = fileroot + '_auction.yaml'
yp = open (yamlfile, 'w')
print ('name: auction', file=yp)
print ('time_delta: ' + str(dt) + 's', file=yp)
print ('broker:', broker, file=yp)
print ('values:', file=yp)
print ('  LMP:', file=yp)
print ('    topic: pypower/LMP_B7', file=yp)
print ('    default: 0.1', file=yp)
print ('    type: double', file=yp)
print ('    list: false', file=yp)
print ('  refload:', file=yp)
print ('    topic: gridlabdSimulator1/distribution_load', file=yp)
print ('    default: 0', file=yp)
print ('    type: complex', file=yp)
print ('    list: false', file=yp)
for key,val in controllers.items():
	houseName = val['houseName']
	meterName = val['meterName']
	print ('  ' + key + '#V1:', file=yp)
	print ('    topic: gridlabdSimulator1/' + meterName + '/measured_voltage_1', file=yp)
	print ('    default: 120', file=yp)
	print ('  ' + key + '#Tair:', file=yp)
	print ('    topic: gridlabdSimulator1/' + houseName + '/air_temperature', file=yp)
	print ('    default: 80', file=yp)
	print ('  ' + key + '#Load:', file=yp)
	print ('    topic: gridlabdSimulator1/' + houseName + '/hvac_load', file=yp)
	print ('    default: 0', file=yp)
	print ('  ' + key + '#On:', file=yp)
	print ('    topic: gridlabdSimulator1/' + houseName + '/power_state', file=yp)
	print ('    default: 0', file=yp)
yp.close ()

op = open ('launch_' + fileroot + '_auction.sh', 'w')
arg = fileroot + '.glm'
print ('(export FNCS_FATAL=NO && exec gridlabd -D USE_FNCS -D METRICS_FILE=' + fileroot + '_metrics.json', 
			 arg, '&> gridlabd.log &)', file=op)
print ('(export FNCS_CONFIG_FILE=' + yamlfile, '&& export FNCS_FATAL=NO && exec python auction.py', 
	   dictfile, fileroot, '&> auction.log &)', file=op)
op.close()

op = open (fileroot + '_FNCS_Config.txt', 'w')
print ('publish "commit:network_node.distribution_load -> distribution_load; 1000";', file=op)
print ('subscribe "precommit:' + network_node + '.positive_sequence_voltage <- pypower/three_phase_voltage_B7";', file=op)
print ('subscribe "precommit:' + Eplus_load + '.constant_power_A <- eplus_json/power_A";', file=op)
print ('subscribe "precommit:' + Eplus_load + '.constant_power_B <- eplus_json/power_B";', file=op)
print ('subscribe "precommit:' + Eplus_load + '.constant_power_C <- eplus_json/power_C";', file=op)
print ('subscribe "precommit:' + Eplus_meter + '.bill_mode <- eplus_json/bill_mode";', file=op)
print ('subscribe "precommit:' + Eplus_meter + '.price <- eplus_json/price";', file=op)
print ('subscribe "precommit:' + Eplus_meter + '.monthly_fee <- eplus_json/monthly_fee";', file=op)
for key, val in controllers.items():
	houseName = val['houseName']
	meterName = val['meterName']
	print ('publish "commit:' + houseName + '.air_temperature -> ' + houseName + '/air_temperature";', file=op)
	print ('publish "commit:' + houseName + '.power_state -> ' + houseName + '/power_state";', file=op)
	print ('publish "commit:' + houseName + '.hvac_load -> ' + houseName + '/hvac_load";', file=op)
	print ('publish "commit:' + meterName + '.measured_voltage_1 -> ' + meterName + '/measured_voltage_1";', file=op)
	print ('subscribe "precommit:' + houseName + '.cooling_setpoint <- auction/' + key + '/cooling_setpoint";', file=op)
	print ('subscribe "precommit:' + houseName + '.thermostat_deadband <- auction/' + key + '/thermostat_deadband";', file=op)
	print ('subscribe "precommit:' + meterName + '.bill_mode <- auction/' + key + '/bill_mode";', file=op)
	print ('subscribe "precommit:' + meterName + '.price <- auction/' + key + '/price";', file=op)
	print ('subscribe "precommit:' + meterName + '.monthly_fee <- auction/' + key + '/monthly_fee";', file=op)
op.close()
