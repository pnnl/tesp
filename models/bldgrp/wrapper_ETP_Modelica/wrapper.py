#!/usr/bin/env python3
from pyfmi import load_fmu


class LargeOffice(object):
	def __init__(self, fmu_location, startTime, duration, stepSize, inputSettings):
		self.modelType = "LO"
		self.modelSubType = "Prototype2007"

		self.model = load_fmu(fmu_location)
		self.stepSize = stepSize
		# defines the dynamic inputs' initial values
		self.inputSettings = inputSettings

		self.startTime = startTime * 86400
		self.stopTime = (startTime + duration) * 86400
		self.model.initialize(self.startTime, self.stopTime)

		self.setInitValues()

		self.print_system_info()

	def setInitValues(self):
		self.inputs, self.outputs = self.setIOStructure(self.modelType)
		for key, value in self.inputSettings.items():
			self.inputs[key] = value
			# self.model.set(key, value)
			print("set " + key + " to " + value)

	def setIOStructure(self, modelType):
		if (modelType == "LO"):
			self.inputs = {
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
				# the EP-fmu dosn't take these static settings.  this is a placeholder for the final model.
				# "intLightingDensity":"1", #LD in w/ft2
				# "extLightingWattage":"62782.82" #total watts
			}

			# all the outputs here will be available to call by default
			self.outputs = {
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
		return self.inputs, self.outputs

	def reinitialize(self, initInputs):
		self.model.initialize(self.startTime, self.stopTime)
		self.setInitValues()
		# initialize the inputs variables
		for key, value in initInputs.items():
			# self.model.set(key, value)
			print("set " + key + " to " + value)

	def step(self, current_t, curInputs):
		for key, value in curInputs.items():
			if value == "Y":
				value = "1"
			elif value == "N":
				value = "0"
			self.model.set(key, value)
			print("set " + key + " to " + value)

		self.model.do_step(current_t=current_t, step_size=self.stepSize)
		curOutputs = {}
		for _output in self.outputs:
			if _output == "model_time":
				curOutputs[_output] = current_t / 3600.0  # convert time in seconds into time in hours
			elif self.outputs[_output] == "Y":
				curOutputs[_output] = self.model.get(_output)[0]

		print(curOutputs)

		return curOutputs

	def terminate(self):
		self.model.terminate()

	def print_system_info(self):
		print("===================Large Office model===================")
		print("1 Large Office is loaded.")
