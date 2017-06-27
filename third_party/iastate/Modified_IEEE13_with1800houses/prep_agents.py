#	Copyright (C) 2017 Battelle Memorial Institute
import sys
import json
from writeRegistration import writeRegistration

auctions, controllers = writeRegistration(sys.argv[1])

print ("launch_agents.sh executes", 2 + len (controllers), "processes")

dp = open (sys.argv[1] + '_agent_dict.json', 'w')
m_meta = {}
c_meta = {}
for key,val in auctions.items():
	inf = val['market_information']
	m_meta[key] = {'period':inf['period'],'init_price':inf['init_price'],'init_stdev':inf['init_stdev'],'statistic_mode':inf['statistic_mode'], \
		'capacity_reference_object':inf['capacity_reference_object'],'max_capacity_reference_bid_quantity':inf['max_capacity_reference_bid_quantity'], \
		'unit':inf['unit'],'special_mode':inf['special_mode'],'pricecap':inf['pricecap'],'ignore_failed_market':inf['ignore_failedmarket'], \
		'use_future_mean_price':inf['use_future_mean_price'],'clearing_scalar':inf['clearing_scalar'],'latency':inf['latency'],'ignore_pricecap':inf['ignore_pricecap']}
for key,val in controllers.items():
	inf = val['controller_information']
	c_meta[key] = {'period':inf['period'],'control_mode':inf['control_mode'],'houseName':inf['houseName'],'ramp_high':inf['ramp_high'], \
		'range_low':inf['range_low'],'range_high':inf['range_high'],'base_setpoint':inf['base_setpoint'],'bid_delay':inf['bid_delay'], \
		'use_predictive_bidding':inf['use_predictive_bidding'],'use_override':inf['use_override'],'ramp_low':inf['ramp_low']}
meta = {'markets':m_meta,'controllers':c_meta}
print (json.dumps(meta), file=dp)
dp.close()

want_logs = False

if want_logs:
	prefix = "(export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec"
else:
	prefix = "(export FNCS_FATAL=NO && exec"
suffix_auc = "&> auction.log &)"
suffix_gld = "&> gridlabd.log &)"

metrics = sys.argv[1]

op = open ("launch_" + sys.argv[1] + "_agents.sh", "w")

arg = sys.argv[1] + ".glm"
print (prefix, "gridlabd", arg, suffix_gld, file=op)
print (prefix, "python double_auction.py input/auction_registration.json", metrics, suffix_auc, file=op)

i = 1
suffix_ctrl = "&)"
for key, value in controllers.items():
	arg = "input/controller_registration_" + key + ".json"
	if want_logs:
		suffix_ctrl = "&> ctrl" + str(i) + ".log &)"
	print (prefix, "python house_controller.py", arg, suffix_ctrl, file=op)
	i += 1
op.close()

op = open(sys.argv[1] + "_FNCS_Config.txt", "w")
print ("publish \"commit:network_node.distribution_load -> distribution_load; 1000\";", file=op)
print ("publish \"commit:meter_645.measured_voltage_B -> voltageM645BN; 10\";", file=op)
print ("publish \"commit:meter_645.measured_voltage_C -> voltageM645CN; 10\";", file=op)
print ("publish \"commit:meter_646.measured_voltage_B -> voltageM646BN; 10\";", file=op)
print ("publish \"commit:meter_646.measured_voltage_C -> voltageM646CN; 10\";", file=op)
print ("publish \"commit:meter_611.measured_voltage_C -> voltageM611CN; 10\";", file=op)
print ("publish \"commit:meter_652.measured_voltage_A -> voltageM652AN; 10\";", file=op)
print ("publish \"commit:meter_692.measured_voltage_A -> voltageM692AN; 10\";", file=op)
print ("publish \"commit:meter_692.measured_voltage_B -> voltageM692BN; 10\";", file=op)
print ("publish \"commit:meter_692.measured_voltage_C -> voltageM692CN; 10\";", file=op)
print ("publish \"commit:meter_675.measured_voltage_A -> voltageM675AN; 10\";", file=op)
print ("publish \"commit:meter_675.measured_voltage_B -> voltageM675BN; 10\";", file=op)
print ("publish \"commit:meter_675.measured_voltage_C -> voltageM675CN; 10\";", file=op)
print ("publish \"commit:meter_634.measured_voltage_A -> voltageM635AN; 10\";", file=op)
print ("publish \"commit:meter_634.measured_voltage_B -> voltageM635BN; 10\";", file=op)
print ("publish \"commit:meter_634.measured_voltage_C -> voltageM635CN; 10\";", file=op)

print ("publish \"commit:meter_645.measured_power_B -> powerM645BN; 10\";", file=op)
print ("publish \"commit:meter_645.measured_power_C -> powerM645CN; 10\";", file=op)
print ("publish \"commit:meter_646.measured_power_B -> powerM646BN; 10\";", file=op)
print ("publish \"commit:meter_646.measured_power_C -> powerM646CN; 10\";", file=op)
print ("publish \"commit:meter_611.measured_power_C -> powerM611CN; 10\";", file=op)
print ("publish \"commit:meter_652.measured_power_A -> powerM652AN; 10\";", file=op)
print ("publish \"commit:meter_692.measured_power_A -> powerM692AN; 10\";", file=op)
print ("publish \"commit:meter_692.measured_power_B -> powerM692BN; 10\";", file=op)
print ("publish \"commit:meter_692.measured_power_C -> powerM692CN; 10\";", file=op)
print ("publish \"commit:meter_675.measured_power_A -> powerM675AN; 10\";", file=op)
print ("publish \"commit:meter_675.measured_power_B -> powerM675BN; 10\";", file=op)
print ("publish \"commit:meter_675.measured_power_C -> powerM675CN; 10\";", file=op)
print ("publish \"commit:meter_634.measured_power_A -> powerM635AN; 10\";", file=op)
print ("publish \"commit:meter_634.measured_power_B -> powerM635BN; 10\";", file=op)
print ("publish \"commit:meter_634.measured_power_C -> powerM635CN; 10\";", file=op)

print ("publish \"commit:trip_meter1_1.measured_real_energy -> PH11; 1000\";", file=op)
print ("publish \"commit:trip_meter1_1.measured_reactive_energy -> QH11; 1000\";", file=op)
print ("publish \"commit:trip_meter1_1.measured_power -> SH11; 1000\";", file=op)

print ("publish \"commit:Reg650630.tap_A -> RtapA; 0\";", file=op)
print ("publish \"commit:Reg650630.tap_B -> RtapB; 0\";", file=op)
print ("publish \"commit:Reg650630.tap_C -> RtapC; 0\";", file=op)

#print ("publish \"presync:network_node.distribution_load -> distribution_load\";", file=op)
# print ("subscribe \"precommit:network_node.positive_sequence_voltage <- pypower/three_phase_voltage_B7\";", file=op)
#print ("subscribe \"precommit:R1_12_47_1_load_4_Eplus_load4.constant_power_A <- eplus_json/power_A\";", file=op)
#print ("subscribe \"precommit:R1_12_47_1_load_4_Eplus_load4.constant_power_B <- eplus_json/power_B\";", file=op)
#print ("subscribe \"precommit:R1_12_47_1_load_4_Eplus_load4.constant_power_C <- eplus_json/power_C\";", file=op)
# print ("subscribe \"precommit:Eplus_load.constant_power_A <- eplus_json/power_A\";", file=op)
# print ("subscribe \"precommit:Eplus_load.constant_power_B <- eplus_json/power_B\";", file=op)
# print ("subscribe \"precommit:Eplus_load.constant_power_C <- eplus_json/power_C\";", file=op)
print ("subscribe \"precommit:Reg650630.tap_A <- auction_Market_1/reg_statusTapA\";", file=op)
print ("subscribe \"precommit:Reg650630.tap_B <- auction_Market_1/reg_statusTapB\";", file=op)
print ("subscribe \"precommit:Reg650630.tap_C <- auction_Market_1/reg_statusTapC\";", file=op)
for key, value in controllers.items():
	arg = value['controller_information']['houseName']
	print ("publish \"commit:" + arg + ".air_temperature -> " + arg + "/air_temperature\";", file=op)
	print ("publish \"commit:" + arg + ".power_state -> " + arg + "/power_state\";", file=op)
	print ("publish \"commit:" + arg + ".hvac_load -> " + arg + "/hvac_load\";", file=op)
	print ("subscribe \"precommit:" + arg + ".cooling_setpoint <- controller_" + key + "/cooling_setpoint\";", file=op)
op.close()
