from LargeOffice import LargeOffice
import numpy as np
import matplotlib.pyplot as plt

def main():
	startDay        = 1  # day of year --> 1=Jan; 32=Feb; 60=Mar; 91=Apr; 121=May; 152=Jun; 182=Jul; 213=Aug; 244=Sep; 274=Oct; 305=Nov; 335=Dec;
	duration        = 365   # number of days
	timeStep        = 60*1 # number of seconds/step
	fmu_location    = "./core/Basement.fmu" # fmu file
	envCo_location  = "./core/co_all.csv" # envelope coefficients file
	envIni_location = "./core/init2.csv" # envelope initialization condition file

	# ------temporary read in from CSVs, eventually read in from FNCS---------------------
	TO = np.genfromtxt('./core/TO.csv', delimiter=',',max_rows=(startDay - 1 + duration)*1440+1)[(startDay-1)*1440+1:,1] 

	# initialize a large office model
	LO = LargeOffice(envCo_location,envIni_location,fmu_location,startDay, duration, timeStep) 
	LO.init()
 
	# for final plotting
	plotting = {"time":[],"T_zones":[],"P_total":[],"TO":[]}
	
	# start simulation
	model_time = LO.startTime 
	while(model_time < LO.stopTime): #fmu uses second of year as model_time
		currentDay = int(model_time/86400)
		currentHour = int((model_time-currentDay*86400)%86400/3600)
		currentMin = int((model_time-(currentDay*86400+currentHour*3600))/60)
		currentSec = int((model_time-(currentDay*86400+currentHour*3600))%60)

		Q_current = LO.Q[(model_time-LO.startTime)/60] #TODO:remove
		TO_current = TO[(model_time-LO.startTime)/60] #TODO:replace with input from FNCS
		control_inputs={} #use default control inputs, or define dynamic values here
		P_total,T_room = LO.step(TO_current,model_time,control_inputs,Q_current)

		plotting["time"].append(model_time)
		plotting["TO"].append(TO_current)
		plotting["T_zones"].append(T_room)
		plotting["P_total"].append(P_total)

		model_time = model_time + timeStep


	#end of simulation and terminate the fmu instance
	LO.terminate()
	print("=======================Simulation Done=======================")
	 
	# Plot simulation result in phase plane plot
	plotZone = 0
	pltTime = plotting["time"]
	#pltZoneTemp = np.array(plotting["T_zones"])[:,plotZone]
	pltZoneTemp = plotting["T_zones"]
	plt.figure()
	plt.plot(pltTime, pltZoneTemp, label = "Zone Temperature [" + LO.zoneNames[plotZone]+"]")
	plt.xlabel("Time [hr]")
	plt.ylabel("Temperature [C]")
	#plt.legend()
	plt.show()

	plt.figure()
	plt.plot(pltTime, plotting["P_total"], label="Total Power [" + LO.zoneNames[plotZone]+"]")
	plt.xlabel("Time [hr]")
	plt.ylabel("Power [W]")
	plt.show()

	plt.figure()
	plt.plot(pltTime, plotting["TO"], label="OAT")
	plt.xlabel("Time [hr]")
	plt.ylabel("OAT [C]")
	plt.show()

if __name__ == "__main__":
	main()
