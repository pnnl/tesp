from __future__ import print_function
from LargeOffice import LargeOffice
import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsRegressor
import joblib
import sys
try:
	import fncs
except:
	print('fncs problem')
	pass

def startLOSimulation(startDay, duration, timeStep=60):
	#startDay        = 1  # day of year --> 1=Jan; 32=Feb; 60=Mar; 91=Apr; 121=May; 152=Jun; 182=Jul; 213=Aug; 244=Sep; 274=Oct; 305=Nov; 335=Dec;
	#duration        = 2   # number of days

	# ------temporary read in from CSVs, eventually read in from FNCS---------------------
	#TO = np.genfromtxt('./core/_temp/TO.csv', delimiter=',',max_rows=(startDay - 1 + duration)*1440+1)[(startDay-1)*1440+1:,1] 

	# initialize a large office model
	LO1 = LargeOffice(int(startDay), int(duration)) 
	#LO2 = LargeOffice(startDay, duration,initation2) 
		
	# start simulation
	model_time = LO1.startTime
	time_stop = LO1.stopTime
	TO_current = None
	windSpeed = None
	weather_current = {}
	fncs.initialize()
	print('FNCS initialized')
	while(model_time < time_stop): #fmu uses second of year as model_time
		currentDay = int(model_time/86400)
		currentHour = int((model_time-currentDay*86400)%86400/3600)
		currentMin = int((model_time-(currentDay*86400+currentHour*3600))/60)
		currentSec = int((model_time-(currentDay*86400+currentHour*3600))%60)

		events = fncs.get_events()
		for topic in events:
			value = fncs.get_value(topic)
			if topic == 'temperature':
				weather_current['TO'] = float(value)
			if topic == 'wind_speed':
				weather_current['windSpeed'] = float(value)
			print(topic)
			print(value)
		#weather_current={'TO':TO_current,'windSpeed':windSpeed}
		control_inputs={} #use default control inputs, or define dynamic values here
		if weather_current:#['TO'] and weather_current['windSpeed']:
			P_total,T_room = LO1.step(model_time,weather_current,control_inputs)
			fncs.publish('total_power', P_total[0])
			fncs.publish('room_temps', T_room)
			print('P_total: ', P_total, ', T_room: ', T_room)
		model_time = model_time + timeStep
		nextFNCSTime = min(model_time, time_stop)
		print('nextFNCSTime: ', nextFNCSTime)
		time_granted = fncs.time_request(nextFNCSTime)
		print('time granted: ', time_granted)
		model_time = time_granted

	LO1.terminate()
	print("=======================Simulation Done=======================")
	print('finalizing FNCS')
	fncs.finalize()

def usage():
	print("usage: python largeBuilding.py <startDay of year> <duration by day> <time step by seconds(optional, default to 60 seconds)>")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        usage()
        sys.exit()
    startDay = sys.argv[1]
    duration = sys.argv[2]
    if len(sys.argv) > 3:
        timeStep = sys.argv[3]
        startLOSimulation(startDay, duration, timeStep)
    else:
        startLOSimulation(startDay, duration)
