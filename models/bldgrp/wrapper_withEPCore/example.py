from LargeOffice import LargeOffice
import numpy as N
import os
import matplotlib.pyplot as plt

if __name__ == "__main__":
	fmu_location = "core/OfficeLarge_Denver_85_win64.fmu"
	startDay = 17  # day of year --> Jan 17th,
	duration = 1   # number of days

	# only defines those that needs to get changed from the default values.
	inputSettings = {
		# set dynamic input flags
		"DIFlag_intLightingSch": "Y",
		"DIFlag_basementThermostat": "Y"

		# set static input values, EP-fmu doens't support static parameter settings.  This is place-holders for final Modelica-fmu.
		# "intLightingDensity":"1.2" #LD in w/ft2
	}

	# initialize a large office model
	timeStep = 60*15 # number of seconds/step, this setting needs to meet the time step defined in the fmu
	LO_model1 = LargeOffice(fmu_location,startDay, duration, timeStep, inputSettings) 
	
	# for final plotting
	plotting = {"totalBldgPower":[], "time":[]}
	
	# start simulation
	model_time = LO_model1.startTime # startTime = startDay * 86400
	curInputs = inputSettings
	while model_time < LO_model1.stopTime:  # stopTime = (startDay + duration) * 86400

		curInputs["intLightingSch"] = "1"; #provide the dynamic inputs here if DIFlag_intLightingSch is set to "Y"

		curInputs["basementThermostat"]="21"  #provide the dynamic inputs here if DIFlag_basementThermostat is set to "Y", default at 23C
		curOutputs = LO_model1.step(model_time, curInputs)
		
		plotting["totalBldgPower"].append(curOutputs["totalBldgPower"])
		plotting["time"].append(model_time)

		model_time = model_time + timeStep

	#end of simulation and terminate the fmu instance
	LO_model1.terminate()
	print("=======================Simulation Done=======================")

	# Plot simulation result in phase plane plot
	pltTime = plotting["time"]
	pltBldgPower = plotting["totalBldgPower"]
	plt.plot(pltTime, pltBldgPower, label = "total building power")
	plt.xlabel("Time [hr]")
	plt.ylabel("Total Power [W]")
	plt.legend()
	plt.grid()
	plt.show()
