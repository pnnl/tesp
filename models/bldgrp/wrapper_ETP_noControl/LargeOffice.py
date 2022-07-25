#!/usr/local/bin/python
# from pyfmi import load_fmu
# from pyfmi.master import Master
# from pyfmi.common.io import ResultHandler,ResultHandlerMemory
import numpy as np


class LargeOffice(object):
    def __init__(self, envelop_coefficients_file, init_file, fmu_location, start_day, duration, step_size,
                 input_settings):
        self.modelType = "LO"
        self.modelSubType = "Prototype2007"
        # self.model = load_fmu(fmu_location) #load fmu to call modelica system
        self.zoneNames = ["BASEMENT", "CORE_BOTTOM", "CORE_MID", "CORE_TOP", "PERIMETER_BOT_ZN_3", "PERIMETER_BOT_ZN_2",
                          "PERIMETER_BOT_ZN_1", "PERIMETER_BOT_ZN_4", "PERIMETER_MID_ZN_3", "PERIMETER_MID_ZN_2",
                          "PERIMETER_MID_ZN_1", "PERIMETER_MID_ZN_4", "PERIMETER_TOP_ZN_3", "PERIMETER_TOP_ZN_2",
                          "PERIMETER_TOP_ZN_1", "PERIMETER_TOP_ZN_4", "GROUNDFLOOR_PLENUM", "MIDFLOOR_PLENUM",
                          "TOPFLOOR_PLENUM"]

        self.startDay = start_day
        self.duration = duration
        self.startTime = start_day * 86400
        self.stopTime = (start_day + duration) * 86400
        self.stepSize = step_size
        # defines the dynamic inputs' initial values
        self.inputSettings = input_settings

        self.Q = np.genfromtxt('./core/Q.csv', delimiter=',', max_rows=(start_day + duration) * 1440)
        # self.model.initialize(self.startTime, self.stopTime) #initialize the fmu model -- temporarily comment out
        self.co = np.genfromtxt(envelop_coefficients_file, delimiter=',')
        self.init = np.genfromtxt(init_file, delimiter=',', max_rows=start_day + duration)[:, 1:]

        # temporary files
        # Q should be provided by the fmu in the final model, here use a dummy Q provided by CSV
        self.Q = np.genfromtxt('./core/Q.csv', delimiter=',', max_rows=(start_day + duration) * 1440)
        # TO should be provided by weather files through FNCS at 1-minute interval (could be changed to second interval. provided by CSV for now.
        self.TO = np.genfromtxt('./core/TO.csv', delimiter=',', max_rows=(start_day + duration) * 1440)

        # self.inputs, self.outputs = self.set_init_values() #to set the initial values in the fmu
        self.print_system_info()

    def set_init_values(self):
        initTemp = np.genfromtxt('./init2.csv', delimiter=',', max_rows=self.start_day + self.duration)
        inputs, outputs = self.set_io_structure(self.modelType)  # get inputs/outputs structure
        for key, value in self.inputSettings.iteritems():  # over-write with user defined values
            inputs[key] = value
            # self.model.set(key, value) #set initial values in fmu,
            print("set " + key + " to " + value)
        return inputs, outputs

    def set_io_structure(self, model_type):
        if model_type == "LO":
            inputs = {
                # the dynamic input flags take "Y" or "N" values in the initialization.
                # Y-the fmu will expect a new value at every timestep
                # N-use fmu/EnergyPlus default schedules/values.
                "DIFlag_OATemp": "N",
                "DIFlag_intLightingSch": "N",
                "DIFlag_extLightingSch": "N",
                "DIFlag__basementThermostat": "N",
                "DIFlag__coreBotThermostat": "N",
                "DIFlag__coreMidThermostat": "N",
                "DIFlag__coreTopThermostat": "N",
                "DIFlag__zn1BotThermostat": "N",
                "DIFlag__zn1MidThermostat": "N",
                "DIFlag__zn1TopThermostat": "N",
                "DIFlag__zn2BotThermostat": "N",
                "DIFlag__zn2MidThermostat": "N",
                "DIFlag__zn2TopThermostat": "N",
                "DIFlag__zn3BotThermostat": "N",
                "DIFlag__zn3MidThermostat": "N",
                "DIFlag__zn3TopThermostat": "N",
                "DIFlag__zn4BotThermostat": "N",
                "DIFlag__zn4MidThermostat": "N",
                "DIFlag__zn4TopThermostat": "N"

                # the static input takes a initial setting value, such as system capacity, lighting density, occupancy etc.
                # the EP-fmu doesn't take these static settings.  This is a placeholder for the final model.
                # "intLightingDensity":"1", #LD in w/ft2
                # "extLightingWattage":"62782.82" #total watts
            }

            # all the outputs here will be available to call by default
            outputs = {
                "totalBldgPower": "Y",
                "basementTemp": "N",
                "coreBotTemp": "N",
                "coreMidTemp": "N",
                "coreTopTemp": "N",
                "zn1BotTemp": "N",
                "zn1MidTemp": "N",
                "zn1TopTemp": "N",
                "zn2BotTemp": "N",
                "zn2MidTemp": "N",
                "zn2TopTemp": "N",
                "zn3BotTemp": "N",
                "zn3MidTemp": "N",
                "zn3TopTemp": "N",
                "zn4BotTemp": "N",
                "zn4MidTemp": "N",
                "zn4TopTemp": "N",
                "zn5BotTemp": "N",
                "zn5MidTemp": "N",
                "zn5TopTemp": "N"
            }
        return inputs, outputs

    def reinitialize(self, init_inputs):
        self.model.initialize(self.startTime, self.stopTime)
        self.setInitValues()
        # initialize the inputs variables
        for key, value in init_inputs.iteritems():
            # self.model.set(key, value)
            print("set " + key + " to " + value)

    def step(self, current_t, curInputs, T_prev, TO_current, Q_current, TG):
        # -----FMU step, temporarily commented out ----
        # for key, value in curInputs.iteritems():
        #	if value == "Y":
        #		value = "1"
        #	elif value == "N":
        #		value = "0"
        #	self.model.set(key, value)
        #	print ("set "+key+" to "+value)

        # self.model.do_step(current_t = current_t, step_size = self.stepSize) #fmu should provide the Q in the step

        # ------ETP temperature calculation---------
        N_zone = 19
        R = np.multiply(T_prev, self.co[N_zone]) + np.multiply(TO_current, self.co[N_zone + 1]) + np.multiply(Q_current,
                                                                                                              self.co[
                                                                                                                  N_zone + 2]) + np.multiply(
            TG, self.co[N_zone + 3])
        T = np.dot(R, np.transpose(self.co[0:N_zone, :]))

        # -------FMU outputs----------
        curOutputs = {}
        # for _output in self.outputs:
        #	if _output == "model_time":
        #		curOutputs[_output] = current_t/3600.0 #convert time in seconds into time in hours
        #	elif self.outputs[_output]=="Y":
        #		curOutputs[_output] = self.model.get(_output)[0]
        # print(curOutputs)
        # -----------------------------

        return T, curOutputs

    def terminate(self):
        # self.model.terminate() #terminate the fmu, commented out for now
        print("End of simulation")

    def print_system_info(self):
        print("===================Large Office model===================")
        print("1 Large Office is loaded.")
