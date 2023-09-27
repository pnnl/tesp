#!/usr/bin/env python3
# from pyfmi.master import Master
# from pyfmi.common.io import ResultHandler,ResultHandlerMemory
import numpy as np
from pyfmi import load_fmu


class LargeOffice(object):
    def __init__(self, envelop_coefficients_file, init_file, fmu_location, start_day, duration, step_size,
                 input_settings=None):
        self.modelType = "LO"
        self.modelSubType = "Prototype2007"
        self.zoneNames = self.get_zone_name(self.modelType)
        self.system = load_fmu(fmu_location)  # load fmu to call modelica system
        self.envelop = np.genfromtxt(envelop_coefficients_file, delimiter=',')

        self.etp_init_file = init_file

        # self.inputs, self.outputs, self.initTemp = self.set_init_values(init_file) #to set the initial values in the fmu

        self.startDay = start_day
        self.duration = duration
        self.startTime = (start_day - 1) * 86400
        self.stopTime = (start_day - 1 + duration) * 86400
        self.stepSize = step_size
        # self.inputSettings = input_settings

        # temporary files
        # Q should be provided by the fmu in the final model, here use a dummy Q provided by CSV #TODO
        self.Q = np.genfromtxt("./core/Q.csv", delimiter=',', max_rows=(start_day - 1 + duration) * 1440 + 1)[
                 (start_day - 1) * 1440 + 1:, 1:]

        self.print_system_info()

    def FMU_init(self, fmu_init_inputs):
        fmu = self.system
        for key, value in fmu_init_inputs.items():
            self.system.set(key, value)
        self.system.initialize(start_time=self.startTime, stop_time=self.stopTime)

    def FMU_step(self, current_t, fmu_inputs):
        inputs = fmu_inputs
        for key, value in inputs.items():
            self.system.set(key, value)
        self.system.do_step(current_t=current_t, step_size=self.stepSize)
        TSup = self.system.get('TSupOutput')
        mSup = self.system.get('mSupOutput')
        QSup = mSup * 1 * (TSup - inputs['TRetInput'])
        PSup = self.system.get('PHVACOutput')
        return QSup, PSup

    def ETP_midNightReset(self, current_t):
        if current_t % 86400 == 0:
            self.T = self.initTemp[int((current_t - self.startTime) / 86400)]

    def ETP_init(self):
        midNightResetTemp = np.genfromtxt(self.etp_init_file, delimiter=',',
                                          max_rows=self.startDay - 1 + self.duration)[self.startDay - 1:,
                            1:]  # mid-night reset
        self.initTemp = midNightResetTemp
        self.T = self.initTemp[0]
        print(self.T)

    def ETP_step(self, ETP_inputs):
        N_zone = 19
        T_prev = ETP_inputs['T_prev']
        TO_current = ETP_inputs['TO_current']
        Q_current = ETP_inputs['Q_current']
        TG = ETP_inputs['TG']
        co = self.envelop
        R = np.multiply(T_prev, co[N_zone]) + np.multiply(TO_current, co[N_zone + 1]) + np.multiply(Q_current, co[
            N_zone + 2]) + np.multiply(TG, co[N_zone + 3])
        T = np.dot(R, np.transpose(co[0:N_zone, :]))
        return T

    def init(self, fmu_init_inputs=None):
        self.ETP_init()
        if fmu_init_inputs == None:
            fmu_init_inputs = {'Tout': 273.15 + self.T[0],
                               'TRetInput': 273.15 + self.T[0],
                               'TSetCooling': 273.15 + 22,
                               'TSetHeating': 273.15 + 18}
        self.FMU_init(fmu_init_inputs)

    def step(self, TO, current_t, control_inputs,
             Q_current):  # TODO: Q_current needs to be delete, testing with 1 zone here
        if 'TSetHeating' in control_inputs.keys():
            TSetHeating = control_inputs['TSetHeating']
        else:
            TSetHeating = 20

        if 'TSetCooling' in control_inputs.keys():
            TSetCooling = control_inputs['TSetCooling']
        else:
            TSetCooling = 24

        FMU_inputs = {'Tout': TO,
                      'TRetInput': self.T[0] + 273.15,
                      'TSetHeating': TSetHeating + 273.15,
                      'TSetCooling': TSetCooling + 273.15}

        Q_HVAC, P_HVAC = self.FMU_step(current_t, FMU_inputs)
        Q_SurfaceConvection = 0  # TODO: get Q_SurfaceConvection
        Q_InternalHeatGain = 0  # TODO: get Q_InternalHeatGain==>take control_inputs['LightDimmer']
        Q_EnergyStorage = 0  # TODO: get Q_EnergyStorage

        Q_total = Q_HVAC + Q_SurfaceConvection + Q_InternalHeatGain + Q_EnergyStorage
        Q_current[0] = Q_total  # TODO: Q_current = Q_total, here just testing for 1 zone

        self.ETP_midNightReset(current_t)  # reset self.T at mid-night
        ETP_inputs = {'T_prev': self.T,
                      'TO_current': TO,
                      'Q_current': Q_current,
                      'TG': 18}
        self.T = self.ETP_step(ETP_inputs)

        # P_total = P_HVAC + P_lighting + P_equipments #TODO
        P_total = P_HVAC
        return P_total, self.T[0]

    def get_zone_name(self, model_type):
        if model_type == "LO":
            zoneNames = [
                "BASEMENT",
                "CORE_BOTTOM",
                "CORE_MID",
                "CORE_TOP",
                "PERIMETER_BOT_ZN_3",
                "PERIMETER_BOT_ZN_2",
                "PERIMETER_BOT_ZN_1",
                "PERIMETER_BOT_ZN_4",
                "PERIMETER_MID_ZN_3",
                "PERIMETER_MID_ZN_2",
                "PERIMETER_MID_ZN_1",
                "PERIMETER_MID_ZN_4",
                "PERIMETER_TOP_ZN_3",
                "PERIMETER_TOP_ZN_2",
                "PERIMETER_TOP_ZN_1",
                "PERIMETER_TOP_ZN_4",
                "GROUNDFLOOR_PLENUM",
                "MIDFLOOR_PLENUM",
                "TOPFLOOR_PLENUM"
            ]
        return zoneNames

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

    def terminate(self):
        # self.model.terminate() #terminate the fmu, commented out for now
        print("End of simulation")

    def print_system_info(self):
        print("===================Large Office model===================")
        print("1 Large Office is loaded.")
