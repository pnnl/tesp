#	Copyright (C) 2018 Battelle Memorial Institute
import sys
import json
import numpy as np

# write yaml for precool.py to subscribe meter voltages and house setpoints
# write txt for gridlabd to subscribe house setpoints and publish meter voltages

dt = 1
period = 300
mean_price = 0.1167
std_dev_price = 0.0149

gp = open (sys.argv[1] + '.glm', 'r')
dp = open (sys.argv[1] + '_agent_dict.json', 'w')
yp = open (sys.argv[1] + '_precool.yaml', 'w')
cp = open (sys.argv[1] + '_FNCS_Config.txt', 'w')

# write preambles
print ('name: precool', file=yp)
print ('time_delta: ' + str(dt) + 's', file=yp)
print ('broker: tcp://localhost:5570', file=yp)
print ('values:', file=yp)
print ('  price:', file=yp)
print ('    topic: player/price', file=yp)
print ('    default:', mean_price, file=yp)

# find the house and meter names
inHouses = False
endedHouse = False
isELECTRIC = False
houseName = ""
meterName = ""
houses = {}

for line in gp:
	lst = line.split()
	if len(lst) > 1:
		if lst[1] == "house":
			inHouses = True
		# Check for ANY object within the house, and don't use its name:
		if inHouses == True and lst[0] == "object" and lst[1] != "house":
			endedHouse = True
		# Check house object with controller inside
		if inHouses == True:
			if lst[0] == "name" and endedHouse == False:
				houseName = lst[1].strip(";")
			if lst[0] == "parent":
				meterName = lst[1].strip(";")
			if lst[0] == "cooling_system_type":
				if (lst[1].strip(";") == "ELECTRIC"):
					isELECTRIC = True
	elif len(lst) == 1:
		if inHouses == True: 
			inHouses = False
			endedHouse = False
			if isELECTRIC == True:
				night_set = np.random.uniform (70, 76)
				day_set = np.random.uniform (78, 82)
				day_start = np.random.uniform (6, 8)
				day_end = np.random.uniform (17, 19)
				deadband = np.random.uniform (2, 3)
				houses[houseName] = {'meter':meterName,'night_set':float('{:.3f}'.format(night_set)),
					'day_set':float('{:.3f}'.format(day_set)),'day_start_hour':float('{:.3f}'.format(day_start)),
					'day_end_hour':float('{:.3f}'.format(day_end)),'deadband':float('{:.3f}'.format(deadband))}
				print ('  ' + houseName + '_V1:', file=yp)
				print ('    topic: gridlabdSimulator1/' + meterName + '/measured_voltage_1', file=yp)
				print ('    default: 120', file=yp)
				print ('  ' + houseName + '_Tair:', file=yp)
				print ('    topic: gridlabdSimulator1/' + houseName + '/air_temperature', file=yp)
				print ('    default: 80', file=yp)
				print ('publish \"commit:' + meterName + '.measured_voltage_1 -> ' + meterName + '/measured_voltage_1\";', file=cp)
				print ('publish \"commit:' + houseName + '.air_temperature -> ' + houseName + '/air_temperature\";', file=cp)
				print ('subscribe \"precommit:' + houseName + '.cooling_setpoint <- precool/' + houseName + '_cooling_setpoint\";', file=cp)
				isELECTRIC = False

meta = {'houses':houses,'period':period,'mean':mean_price,'stddev':std_dev_price}
print (json.dumps(meta), file=dp)

dp.close()
gp.close()
yp.close()
cp.close()



