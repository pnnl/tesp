#!/usr/local/bin/python

from pyfmi import load_fmu
import numpy as np
import joblib
import pandas as pd
import json

class LargeOffice (object):
    def __init__(self, start_day, duration, input_settings=None):
        self.modelType    = "LO"
        self.modelSubType = "Prototype2007"
        self.startYearOn  = 7 #start the year on a Sunday, to calculate the day of week for schedules. Mon=1,Tue=2...Sun=7
        self.zoneNames    = self.get_zone_name(self.modelType)
        self.startDay     = start_day
        self.duration     = duration
        self.startTime    = (start_day - 1) * 86400
        self.stopTime     = (start_day - 1 + duration) * 86400
        self.stepSize     = 60

        self.envelop      = np.genfromtxt('./core/ETP/co_all.csv', delimiter=',')
        self.etp_init_file = './core/ETP/init.csv'
        #self.Q_ES_init_file = './core/_EnergyStorage/Q_ES_init.csv'
        #self.ETP_init()
        
        #self.SurfaceConvection = Predictor('./core/_SurfaceConvection')
        #self.ThermalStorage = Predictor_ThermalStorage('./core/_EnergyStorage')
        
        
        #self.systems = self.load_all_fmu('./core/Modelica_HVAC') #load fmu to call modelica system
        self.system = load_fmu('./core/Modelica_HVAC/basement.fmu')
	self.init()
        self.print_system_info()

    def load_all_fmu(self,fmu_location):
        systems={'basement':load_fmu(fmu_location+'/basement.fmu'),
		'bot':load_fmu(fmu_location+'/bot.fmu'),
		'mid':load_fmu(fmu_location+'/mid.fmu'),
		'top':load_fmu(fmu_location+'/top.fmu')
		}
        return systems
    
    def FMU_init(self,fmu_init_inputs): #this is a function to set fmu parameters
        fmu = self.system
        for key, value in fmu_init_inputs.iteritems():
            self.system.set(key, value)
        self.system.initialize(start_time=self.startTime,stop_time=self.stopTime)

    def FMU_step(self,current_t,fmu_inputs):
        inputs = fmu_inputs
        for key, value in inputs.iteritems():
            print(key)
            self.system.set(key, value)
        self.system.do_step(current_t = current_t, step_size = self.stepSize) 
        TSup = self.system.get('TSupOutput')
        mSup = self.system.get('mSupOutput')
        QSup = mSup * 1 * (TSup-inputs['TRetInput'])
        PSup = self.system.get('PHVACOutput')
        print(TSup)
        print(mSup)
        return QSup, PSup


    def init(self,fmu_init_inputs=None):
        self.internalLoad_init()
        self.ETP_init()
        if fmu_init_inputs==None:
            fmu_init_inputs = {'Tout':273.15+self.T[0],
			       'TRetInput':273.15+self.T[0],
			       'TSetCooling':273.15+22,
			       'TSetHeating':273.15+18}
        self.FMU_init(fmu_init_inputs)
	
    def step(self,current_t,weather,control_inputs): #TODO: Q_current needs to be delete, testing with 1 zone here
        if 'TSetHeating' in control_inputs.keys():
            TSetHeating = control_inputs['TSetHeating']
        else:
            TSetHeating = 20

        if 'TSetCooling' in control_inputs.keys():
            TSetCooling = control_inputs['TSetCooling']
        else:
            TSetCooling = 24

        if 'LightDimmer' in control_inputs.keys():
            LightDimmer = control_inputs['LightDimmer']
        else:
            LightDimmer = 1
   
        
        FMU_inputs = {'Tout':weather['TO'],
                      'TRetInput':self.T[0]+273.15,
                      'TSetHeating':TSetHeating+273.15,
                      'TSetCooling':TSetCooling+273.15}
    
        Q_HVAC,P_HVAC = self.FMU_step(current_t,FMU_inputs) 
        print("Q_HVAC = " + str(Q_HVAC))
        
        Q_InternalLoad,P_InternalLoad,Output_InternalLoad = self.internalLoad_step(current_t,{"LightDimmer":LightDimmer},weather['windSpeed'])
	#print "Q_internalLoad = " + str(Q_InternalLoad)
        
	#Q_SurfaceConvection = self.SurfaceConvection.predict(TO,self.T_prev) #not converge right on Linux, need further investigation
        #Q_ThermalStorage = self.ThermalStorage.predict(TO, Q_HVAC, self.Q_ThermalStorage_prev, self.T_prev) #not converge right on Linux, need further investigation
        #Q_total = Q_SurfaceConvection + Q_InternalLoad + Q_ThermalStorage + Q_HVAC
        Q_total = Q_InternalLoad + Q_HVAC
        
        ETP_inputs = {'T_prev':self.T_prev,
                      'TO_current':weather['TO'],
                      'Q_current':Q_total,
                      #'Q_prev':self.Q_prev,
                      'TG': 18}
        T = self.ETP_step(current_t, ETP_inputs)
        self.T_prev = T
        #self.Q_ThermalStorage_prev = Q_ThermalStorage
        self.Q_prev = Q_total

        P_total = P_HVAC + P_InternalLoad
        print("P_HVAC = " + str(P_HVAC))
        print("P_InternalLoad = " + str(P_InternalLoad))
        
        #T_baseline = self.T_Baseline.predict(current_t)
        
        return P_total, T

    def ETP_init(self):
        self.initTemp = np.genfromtxt(self.etp_init_file, delimiter=',', max_rows=self.startDay -1 + self.duration)[self.startDay-1:,1:] #mid-night reset
        #self.Q_ES_init = np.genfromtxt(self.Q_ES_init_file, delimiter=',')[:,1:]
        self.T = self.initTemp[0]
        self.T_prev = self.initTemp[0]
        #self.Q_prev = np.zeros(19)
        #self.Q_ThermalStorage_prev = self.Q_ES_init[self.startDay-1]

    def ETP_step(self,current_t, ETP_inputs):
        if current_t%86400 == 0:
            self.T = self.initTemp[int((current_t-self.startTime)/86400)]
        N_zone = 19
        T_prev = ETP_inputs['T_prev']
        TO_current = ETP_inputs['TO_current']
        Q_current = ETP_inputs['Q_current']
        TG = ETP_inputs['TG']
        co = self.envelop
        R = np.multiply(T_prev, co[N_zone])+ np.multiply(TO_current,co[N_zone+1])+np.multiply(Q_current,co[N_zone+2])+np.multiply(TG,co[N_zone+3])
        T = np.dot(R,np.transpose(co[0:N_zone,:]))
        return T

    
    def loadDefaults(self):
        with open('./core/_InternalLoad/EPextraction.json') as json_data:
                data = json.load(json_data,) 
        self.zoneArea   = data['zoneArea'] #zone area (m2)
        self.zoneHeight = data['zoneHeight'] #zone height (m)
        self.multiplier = data['multiplier'] #zone multiplier (unitless)
        self.LPD        = data['LPD'] #LPD=lighting power density (W/m2)
        self.OccD       = data['OccD'] #OccD = occupancy density (m2/#)
        self.EPD        = data['EPD'] #EPD=equipment power density (W/m2)
        self.ExWall     = data['ExteriorWallArea'] #exterior wall area (m2)
        self.InfRatePerEW = data['InfilDesignRatePerExtWall'] #infiltration rate per EWall area (m3/s-m2)

        with open('./core/_InternalLoad/sch.json') as sch_json:
                sch = json.load(sch_json,) 
        self.sch_eqip = sch['BLDG_EQUIP_SCH_ADV']
        self.sch_occ  = sch['BLDG_OCC_SCH']
        self.sch_inf  = sch['INFIL_SCH_PNNL']
        self.sch_lgt  = sch['BLDG_LIGHT_SCH']

    def internalLoad_init(self): 
        self.loadDefaults()
        self.LP = np.multiply(self.LPD, self.zoneArea)  
        self.EP = np.multiply(self.EPD, self.zoneArea) 
        with np.errstate(divide='ignore', invalid='ignore'):
                occ = np.true_divide(self.zoneArea,self.OccD)
                occ[occ == np.inf] = 0
                occ = np.nan_to_num(occ)
        self.Occ = occ
        self.Inf = np.multiply(self.ExWall, self.InfRatePerEW) 

    def internalLoad_step(self,current_t,control_inputs,windSpeed):
        Sch_LP = self.getSchedule(self.sch_lgt, current_t) #lightingSchedule
        Q_LP = np.multiply(self.LP, Sch_LP)
        Q_LP = np.multiply(Q_LP, control_inputs['LightDimmer']*0.7) #use Fraction of Raidant = 0.7
        P_Light = 0

        Sch_EP = self.getSchedule(self.sch_eqip, current_t) # this is not a controllable dynamic input
        Q_EP = np.multiply(self.EP, Sch_EP*0.5) #use Franction of Radiant = 0.5
        P_Equip = 0 

        Sch_Occ = self.getSchedule(self.sch_occ, current_t) # this is not a controllable dynamic input
        Q_Occ = np.multiply(self.Occ, Sch_Occ*0.3) #use Fraction of Radiant = 0.3

        Sch_Inf = self.getSchedule(self.sch_inf, current_t)
        Q_Inf = np.multiply(self.Inf, Sch_Inf*1.3716*windSpeed) #EP count in the hights of the level. 1.3716 is for mid-level

        Q_total = Q_LP + Q_EP + Q_Occ + Q_Inf
        P_total = P_Light + P_Equip
        output = {"Q_LP":Q_LP,
                  "Q_EP":Q_EP,
                  "Q_Occ":Q_Occ,
		  "Q_Inf":Q_Inf,
                  "P_Light":P_Light,
                  "P_Equip":P_Equip}
        return Q_total,P_total,output

    def getSchedule(self, sch, current_t):
        curDay = int(current_t/86400)
        dayOfWk = (curDay%7+self.startYearOn)%7
        if dayOfWk == 0:
            dayOfWk = 7
        curHour = int((current_t-curDay*86400)%86400/3600)
        return sch[str(dayOfWk)][curHour]

    def get_zone_name(self,model_type):
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

    def set_io_structure(self,model_type):
        if model_type == "LO":
            inputs={
                # the dynamic input flags take "Y" or "N" values in the initialization.
                # Y-the fmu will expect a new value at every timestep
                # N-use fmu/EnergyPlus default schedules/values.
                "DIFlag_OATemp":"N",                
                "DIFlag_intLightingSch":"N",
                "DIFlag_extLightingSch":"N",
                "DIFlag__basementThermostat":"N",
                "DIFlag__coreBotThermostat":"N",
                "DIFlag__coreMidThermostat":"N",
                "DIFlag__coreTopThermostat":"N",
                "DIFlag__zn1BotThermostat":"N",
                "DIFlag__zn1MidThermostat":"N",
                "DIFlag__zn1TopThermostat":"N",
                "DIFlag__zn2BotThermostat":"N",
                "DIFlag__zn2MidThermostat":"N",
                "DIFlag__zn2TopThermostat":"N",
                "DIFlag__zn3BotThermostat":"N",
                "DIFlag__zn3MidThermostat":"N",
                "DIFlag__zn3TopThermostat":"N",
                "DIFlag__zn4BotThermostat":"N",
                "DIFlag__zn4MidThermostat":"N",
                "DIFlag__zn4TopThermostat":"N"

                # the static input takes a initial setting value, such as system capacity, lighting density, occupancy etc.
                # the EP-fmu doesn't take these static settings.  This is a placeholder for the final model.
                # "intLightingDensity":"1", #LD in w/ft2
                # "extLightingWattage":"62782.82" #total watts
            }
            
            # all the outputs here will be available to call by default
            outputs = {
                "totalBldgPower":"Y",
                "basementTemp":"N",
                "coreBotTemp":"N",
                "coreMidTemp":"N",
                "coreTopTemp":"N",
                "zn1BotTemp":"N",
                "zn1MidTemp":"N",
                "zn1TopTemp":"N",
                "zn2BotTemp":"N",
                "zn2MidTemp":"N",
                "zn2TopTemp":"N",
                "zn3BotTemp":"N",
                "zn3MidTemp":"N",
                "zn3TopTemp":"N",
                "zn4BotTemp":"N",
                "zn4MidTemp":"N",
                "zn4TopTemp":"N",
                "zn5BotTemp":"N",
                "zn5MidTemp":"N",
                "zn5TopTemp":"N"
            }
        return inputs, outputs

    def terminate(self):
        #self.model.terminate() #terminate the fmu, commented out for now
        print ("End of simulation")

    def print_system_info(self):
        print ("===================Large Office model===================")
        print ("1 Large Office is loaded.")

class Predictor(object):
    def __init__(self,folder_surfaceConvection):
        self.loadModel(folder_surfaceConvection)

    def loadModel(self,folder):
        self.scalerX = joblib.load(folder+"/scalerX.sav") 
        self.scalery = joblib.load(folder+"/scalerY.sav") 
        self.model   = joblib.load(folder+"/Regressor.sav")

    def predict(self,TO,T):
        X           = pd.DataFrame(np.insert(T,0,TO))
        X           = X.values.astype(np.float64).reshape(1, -1)
        X           = self.scalerX.transform(X)
        predictions = self.model.predict(X)                   
        predictions = self.scalery.inverse_transform(predictions)
        return predictions.reshape(-1,)


        
class Predictor_file(object):
    def __init__(self,fileName,start_day,duration):
        self.start_day = start_day
        self.model = np.genfromtxt(fileName, delimiter=',',max_rows=(start_day - 1 + duration)*1440+1)[(start_day-1)*1440+1:,:]
        
    def predict(self,current_t):
        index = (current_t-((self.start_day - 1) * 86400))/60
        return self.model[index]
    
class Predictor_ThermalStorage(object):
    # In folder folder_ThermalStorage, there will be 19 subfolders naming 0-18
    def __init__(self,folder_ThermalStorage):
        for i in range(19):
            inputfolder = folder_ThermalStorage + '/'+ str(i)
            x = 'self.scalerX_' + str(i) + ', self.scalery_' + str(i) + ', self.model_' + str(i)
            exec(x + '=' + 'self.loadModel("%s")' % inputfolder)
            
    def loadModel(self,folder):
        self.scalerX = joblib.load(folder+"/scalerX.sav") 
        self.scalery = joblib.load(folder+"/scalery.sav") 
        self.model   = joblib.load(folder+"/Regressor.sav")
        return self.scalerX,self.scalery,self.model

    def predict(self,TO,Q_HVAC,TS,T): 
        # IndexX   = [0] + [IndexY-2] + [IndexY] + range(134,NV)
        #22 features from last step used: 
        #TO, its zone's System Air Transfer Rate (AT), itself at previous timestep(TS), and 19 temp(T)
        # AT has 19 values also TS has 19 values
        AT = Q_HVAC
        predictions = np.zeros(19)
        for i in range(19):
            X           = pd.DataFrame(np.insert(T,0,[TO,AT[i],TS[i]]))
            X           = X.values.astype(np.float64).reshape(1, -1)
            exec('X = self.scalerX_'+ str(i)+'.transform(X)')
            exec('prediction  = self.model_'+ str(i)+'.predict(X)')
            exec('prediction  = self.scalery_'+ str(i)+'.inverse_transform(prediction)')
            exec('predictions[i] = prediction.reshape(-1,)')
#             X           = self.scalerX.transform(X)
#             prediction  = self.model.predict(X)                   
#             prediction  = self.scalery.inverse_transform(prediction)
#             predictions[i] = prediction.reshape(-1,)

        return predictions
