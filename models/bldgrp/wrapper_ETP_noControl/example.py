from LargeOffice import LargeOffice
import numpy as np
# import os
import matplotlib.pyplot as plt

if __name__ == "__main__":

    startDay = 1  # day of year --> Jan 17th,
    duration = 2  # number of days
    fmu_location = "core/OfficeLarge_Denver_85_win64.fmu"

    # env = LargeOfficeETPEnv('./co_all.csv','./init2.csv',startDay,duration)

    # only defines those that needs to get changed from the default values.
    inputSettings = {
        # set dynamic input flags
        "DIFlag_intLightingSch": "Y",
        "DIFlag_basementThermostat": "Y"

        # set static input values, EP-fmu doens't support static parameter settings.
        # This is place-holders for final Modelica-fmu.
        # "intLightingDensity":"1.2" #LD in w/ft2
    }

    # initialize a large office model
    timeStep = 60 * 1  # number of seconds/step, this setting needs to meet the time step defined in the fmu
    LO_model1 = LargeOffice('./core/co_all.csv', './core/init2.csv', fmu_location, startDay, duration, timeStep,
                            inputSettings)

    # ------temporary read in from CSVs, should be from FMU/TESP---------------------
    Q = np.genfromtxt('./core/Q.csv', delimiter=',',
                      max_rows=(startDay + duration) * 1440)[1:, 1:]  # the csv used is at 1min interval, timeStep = 60
    TO = np.genfromtxt('./core/TO.csv', delimiter=',',
                       max_rows=(startDay + duration) * 1440)[1:, 1]  # the csv used is at 1min interval, timeStep = 60

    # for final plotting
    # plotting = {"totalBldgPower":[], "time":[],"T_zones":[]}
    plotting = {"time": [], "T_zones": []}

    # start simulation
    model_time = LO_model1.startTime  # startTime = startDay * 86400
    curInputs = inputSettings
    while model_time < LO_model1.stopTime:  # stopTime = (startDay + duration) * 86400
        curInputs["intLightingSch"] = "1"  # provide the dynamic inputs here if DIFlag_intLightingSch is set to "Y"
        curInputs[
            "basementThermostat"] = "21"  # provide the dynamic inputs here if DIFlag_basementThermostat is set to "Y", default at 23C

        if model_time % 86400 == 0:  # temporarily added for initial values, Q and TO CSV read in.
            curDay = int(model_time / 86400)
            initValues = LO_model1.init[curDay - 1, :]
            QValues = Q[(curDay - 1) * 1440:curDay * 1440, :]
            TOValues = TO[(curDay - 1) * 1440:curDay * 1440]
            T_prev = initValues
            plotting["time"].append(model_time)
            plotting["T_zones"].append(T_prev)

        elif model_time % 60 == 0:  # current ETP coefficients works for 1-minute interval, can change to 1-second interval later
            plotting["time"].append(model_time)
            curMinofDay = int((model_time % 86400) / 60)
            T_cur, curOutputs = LO_model1.step(model_time, curInputs, T_prev, TOValues[curMinofDay],
                                               QValues[curMinofDay], 18)
            T_prev = T_cur
            plotting["T_zones"].append(T_prev)
        # plotting["totalBldgPower"].append(curOutputs["totalBldgPower"])

        model_time = model_time + timeStep

    # end of simulation and terminate the fmu instance
    # LO_model1.terminate()
    print("=======================Simulation Done=======================")

    # Plot simulation result in phase plane plot
    plotZone = 0
    pltTime = plotting["time"]
    pltZoneTemp = np.array(plotting["T_zones"])[:, plotZone]
    plt.plot(pltTime, pltZoneTemp, label="Zone Temperature: " + LO_model1.zoneNames[plotZone])
    plt.xlabel("Time [hr]")
    plt.ylabel("Temperature [W]")
    plt.legend()
    plt.grid()
    plt.show()
