#!/usr/local/bin/python

from pyfmi import load_fmu
import numpy as np
import joblib
import pandas as pd
import json

class LargeOffice (object):
    def __init__(self, start_day, duration, init_weather):
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

	##TODO: the ThermalStorage and SurfaceConvection needs further investigating
        #self.Q_ES_init_file = './core/_EnergyStorage/Q_ES_init.csv'
        #self.SurfaceConvection = Predictor('./core/_SurfaceConvection')
        #self.ThermalStorage = Predictor_ThermalStorage('./core/_EnergyStorage')
        
        self.systems = self.load_all_fmu('./core/Modelica_HVAC') #load fmu to call modelica systems
	self.init(init_weather)

        self.print_system_info()

    def load_all_fmu(self,fmu_location):
	systems={'basement':load_fmu(fmu_location+'/SingleZone_basement.fmu'),
		'bot':load_fmu(fmu_location+'/FiveZone_bot.fmu'),
		'mid':load_fmu(fmu_location+'/FiveZone_mid.fmu'),
		'top':load_fmu(fmu_location+'/FiveZone_top.fmu')
		}
	return systems

    def init(self,init_weather,fmu_init_inputs=None):
	self.ETP_init()
	self.internalLoad_init()
	if fmu_init_inputs==None:
		fmu_init_inputs = {'Tout':init_weather['TO'],
				   'TRetInput':[k+273.15 for k in self.T_prev],
				   'TSetCooling':[22+273.15 for k in self.T_prev],
				   'TSetHeating':[18+273.15 for k in self.T_prev]}
	self.FMU_init(fmu_init_inputs)


    def ETP_init(self):
        self.initTemp = np.genfromtxt(self.etp_init_file, delimiter=',', max_rows=self.startDay -1 + self.duration)[self.startDay-1:,1:] #mid-night reset
        self.T = self.initTemp[0]
        self.T_prev = self.initTemp[0]

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
    
    def FMU_init(self,fmu_init_inputs): #this is a function to set fmu parameters
        for key, value in fmu_init_inputs.iteritems():
	    if key == 'Tout':
		#print 'Tout setting: '+str(value)
		self.systems['basement'].set(key,value)
		self.systems['bot'].set(key,value)
		self.systems['mid'].set(key,value)
		self.systems['top'].set(key,value)
	    else:
		#print key +' setting: '+str(value) #value is a list of 19
	    	self.systems['basement'].set(key,value[0])
	    	self.systems['bot'].set(key+'_C',value[1])
	    	self.systems['bot'].set(key+'_P1',value[4])
	    	self.systems['bot'].set(key+'_P2',value[5])
	    	self.systems['bot'].set(key+'_P3',value[6])
	    	self.systems['bot'].set(key+'_P4',value[7])
	    	self.systems['mid'].set(key+'_C',value[2])
	    	self.systems['mid'].set(key+'_P1',value[8])
	    	self.systems['mid'].set(key+'_P2',value[9])
	    	self.systems['mid'].set(key+'_P3',value[10])
	    	self.systems['mid'].set(key+'_P4',value[11])
	    	self.systems['top'].set(key+'_C',value[3])
	    	self.systems['top'].set(key+'_P1',value[12])
	    	self.systems['top'].set(key+'_P2',value[13])
	    	self.systems['top'].set(key+'_P3',value[14])
	    	self.systems['top'].set(key+'_P4',value[15])
	self.systems['basement'].initialize(start_time=self.startTime,stop_time=self.stopTime)
	self.systems['bot'].initialize(start_time=self.startTime,stop_time=self.stopTime)
	self.systems['mid'].initialize(start_time=self.startTime,stop_time=self.stopTime)
	self.systems['top'].initialize(start_time=self.startTime,stop_time=self.stopTime)

    def FMU_step(self,current_t,fmu_inputs):
        for key, value in fmu_inputs.iteritems():
	    if key == 'Tout':
		self.systems['basement'].set(key,value)
		self.systems['bot'].set(key,value)
		self.systems['mid'].set(key,value)
		self.systems['top'].set(key,value)
	    else:
		#print key +' setting: '+str(value) #value is a list of 19
	    	self.systems['basement'].set(key,value[0])
	    	self.systems['bot'].set(key+'_C',value[1])
	    	self.systems['bot'].set(key+'_P1',value[4])
	    	self.systems['bot'].set(key+'_P2',value[5])
	    	self.systems['bot'].set(key+'_P3',value[6])
	    	self.systems['bot'].set(key+'_P4',value[7])
	    	self.systems['mid'].set(key+'_C',value[2])
	    	self.systems['mid'].set(key+'_P1',value[8])
	    	self.systems['mid'].set(key+'_P2',value[9])
	    	self.systems['mid'].set(key+'_P3',value[10])
	    	self.systems['mid'].set(key+'_P4',value[11])
	    	self.systems['top'].set(key+'_C',value[3])
	    	self.systems['top'].set(key+'_P1',value[12])
	    	self.systems['top'].set(key+'_P2',value[13])
	    	self.systems['top'].set(key+'_P3',value[14])
	    	self.systems['top'].set(key+'_P4',value[15])
	self.systems['basement'].do_step(current_t = current_t, step_size = self.stepSize) 
	self.systems['bot'].do_step(current_t = current_t, step_size = self.stepSize) 
	self.systems['mid'].do_step(current_t = current_t, step_size = self.stepSize) 
	self.systems['top'].do_step(current_t = current_t, step_size = self.stepSize) 

	TSup_basement = self.systems['basement'].get('TSupOutput')
	TSup_bot_c = self.systems['bot'].get('TSupOutput_C')
	TSup_bot_1 = self.systems['bot'].get('TSupOutput_P1')
	TSup_bot_2 = self.systems['bot'].get('TSupOutput_P2')
	TSup_bot_3 = self.systems['bot'].get('TSupOutput_P3')
	TSup_bot_4 = self.systems['bot'].get('TSupOutput_P4')
	TSup_mid_c = self.systems['mid'].get('TSupOutput_C')
	TSup_mid_1 = self.systems['mid'].get('TSupOutput_P1')
	TSup_mid_2 = self.systems['mid'].get('TSupOutput_P2')
	TSup_mid_3 = self.systems['mid'].get('TSupOutput_P3')
	TSup_mid_4 = self.systems['mid'].get('TSupOutput_P4')
	TSup_top_c = self.systems['top'].get('TSupOutput_C')
	TSup_top_1 = self.systems['top'].get('TSupOutput_P1')
	TSup_top_2 = self.systems['top'].get('TSupOutput_P2')
	TSup_top_3 = self.systems['top'].get('TSupOutput_P3')
	TSup_top_4 = self.systems['top'].get('TSupOutput_P4')

	mSup_basement = self.systems['basement'].get('mSupOutput')
	mSup_bot_c = self.systems['bot'].get('mSupOutput_C')
	mSup_bot_1 = self.systems['bot'].get('mSupOutput_P1')
	mSup_bot_2 = self.systems['bot'].get('mSupOutput_P2')
	mSup_bot_3 = self.systems['bot'].get('mSupOutput_P3')
	mSup_bot_4 = self.systems['bot'].get('mSupOutput_P4')
	mSup_mid_c = self.systems['mid'].get('mSupOutput_C')
	mSup_mid_1 = self.systems['mid'].get('mSupOutput_P1')
	mSup_mid_2 = self.systems['mid'].get('mSupOutput_P2')
	mSup_mid_3 = self.systems['mid'].get('mSupOutput_P3')
	mSup_mid_4 = self.systems['mid'].get('mSupOutput_P4')
	mSup_top_c = self.systems['top'].get('mSupOutput_C')
	mSup_top_1 = self.systems['top'].get('mSupOutput_P1')
	mSup_top_2 = self.systems['top'].get('mSupOutput_P2')
	mSup_top_3 = self.systems['top'].get('mSupOutput_P3')
	mSup_top_4 = self.systems['top'].get('mSupOutput_P4')

	QSup_basement = mSup_basement[0] * 1 * (TSup_basement[0] - fmu_inputs['TRetInput'][0])
	QSup_bot_c    = mSup_bot_c[0]    * 1 * (TSup_bot_c[0]    - fmu_inputs['TRetInput'][1])
	QSup_mid_c    = mSup_mid_c[0]    * 1 * (TSup_mid_c[0]    - fmu_inputs['TRetInput'][2])
	QSup_top_c    = mSup_top_c[0]    * 1 * (TSup_top_c[0]    - fmu_inputs['TRetInput'][3])
	QSup_bot_1    = mSup_bot_1[0]    * 1 * (TSup_bot_1[0]    - fmu_inputs['TRetInput'][4])
	QSup_bot_2    = mSup_bot_2[0]    * 1 * (TSup_bot_2[0]    - fmu_inputs['TRetInput'][5])
	QSup_bot_3    = mSup_bot_3[0]    * 1 * (TSup_bot_3[0]    - fmu_inputs['TRetInput'][6])
	QSup_bot_4    = mSup_bot_4[0]    * 1 * (TSup_bot_4[0]    - fmu_inputs['TRetInput'][7])
	QSup_mid_1    = mSup_mid_1[0]    * 1 * (TSup_mid_1[0]    - fmu_inputs['TRetInput'][8])
	QSup_mid_2    = mSup_mid_2[0]    * 1 * (TSup_mid_2[0]    - fmu_inputs['TRetInput'][9])
	QSup_mid_3    = mSup_mid_3[0]    * 1 * (TSup_mid_3[0]    - fmu_inputs['TRetInput'][10])
	QSup_mid_4    = mSup_mid_4[0]    * 1 * (TSup_mid_4[0]    - fmu_inputs['TRetInput'][11])
	QSup_top_1    = mSup_top_1[0]    * 1 * (TSup_top_1[0]    - fmu_inputs['TRetInput'][12])
	QSup_top_2    = mSup_top_2[0]    * 1 * (TSup_top_2[0]    - fmu_inputs['TRetInput'][13])
	QSup_top_3    = mSup_top_3[0]    * 1 * (TSup_top_3[0]    - fmu_inputs['TRetInput'][14])
	QSup_top_4    = mSup_top_4[0]    * 1 * (TSup_top_4[0]    - fmu_inputs['TRetInput'][15])
	QSup = [
		QSup_basement,QSup_bot_c,QSup_mid_c,QSup_top_c,
		QSup_bot_1,QSup_bot_2,QSup_bot_3,QSup_bot_4,
		QSup_mid_1,QSup_mid_2,QSup_mid_3,QSup_mid_4,
		QSup_top_1,QSup_top_2,QSup_top_3,QSup_top_4,
		0,0,0 #last 3 plenum zones
		]
	#TODO fix the power outputs
        #PSup_basement = self.systems['basement'].get('PHVACOutput')
	#PSup_bot      = self.systems['bot'].get('PHVACOutput')
	#PSup_mid      = self.systems['mid'].get('PHVACOutput')
	#PSup_top      = self.systems['top'].get('PHVACOutput')
	#PSup = PSup_basement + PSup_bot + PSup_mid + PSup_top
	PSup = 0
        return QSup, PSup
	
    def step(self,current_t,weather,control_inputs): 
        if 'TSetHeating' in control_inputs.keys():
            TSetHeating = control_inputs['TSetHeating']
        else:
            TSetHeating = [20 for i in range(16)]
            TSetHeating.extend([0,0,0]) #for 16 conditioned zones
	

        if 'TSetCooling' in control_inputs.keys():
            TSetCooling = control_inputs['TSetCooling']
        else:
            TSetCooling = [24 for i in range(16)]  #for 16 conditioned zones
	    TSetCooling.extend([0,0,0]) #for 16 conditioned zones

        if 'LightDimmer' in control_inputs.keys():
            LightDimmer = control_inputs['LightDimmer']
        else:
            LightDimmer = [1 for i in range(16)]  #for 16 lit zones
	    LightDimmer.extend([0,0,0]) #for 16 conditioned zones

        Q_InternalLoad,P_InternalLoad,Output_InternalLoad = self.internalLoad_step(current_t,{"LightDimmer":LightDimmer},weather['windSpeed'])
        
	#Q_SurfaceConvection = self.SurfaceConvection.predict(TO,self.T_prev) #not converge right on Linux, need further investigation
        #Q_ThermalStorage = self.ThermalStorage.predict(TO, Q_HVAC, self.Q_ThermalStorage_prev, self.T_prev) #not converge right on Linux, need further investigation
        #print ("Q_internalLoad: %s" %str(Q_InternalLoad))
        
        ETP_inputs = {'T_prev':self.T_prev,
                      'TO_current':weather['TO'],
                      'Q_current':Q_InternalLoad,
                      'TG': 18}
	#print ("T-pre: %s" %str(self.T_prev))
        self.T_prev = self.ETP_step(current_t, ETP_inputs)
	#print ("T-post: %s" %str(self.T_prev))

	FMU_inputs = {'Tout':weather['TO'],
		      'TRetInput':self.T_prev+273.15,
                      'TSetHeating':[k+273.15 for k in TSetHeating],
                      'TSetCooling':[k+273.15 for k in TSetCooling]}
	#print ("T-FMU: %s" %str(self.T_prev+273.15))
	#print ("TSetHeating: %s" %str([k+273.15 for k in TSetHeating]))
	#print ("TSetCooling: %s" %str([k+273.15 for k in TSetCooling]))

        Q_HVAC,P_HVAC = self.FMU_step(current_t,FMU_inputs)

	ETP_inputs = {'T_prev':self.T_prev,
                      'TO_current':weather['TO'],
                      'Q_current':Q_HVAC,
                      'TG': 18}
	self.T_prev = self.ETP_step(current_t, ETP_inputs)

	#print ("Q_HVAC: %s" %str(Q_HVAC))
	#Q_total = Q_SurfaceConvection + Q_InternalLoad + Q_ThermalStorage + Q_HVAC
	Q_total = Q_InternalLoad + Q_HVAC
	#print ("Q_total: %s" %str(Q_total))

	print ("time: %s" %str(current_t))
	print ("T: %s" %str(self.T))
	print ("Q_internalLoad: %s" %str(Q_InternalLoad))
	print ("P_internalLoad: %s" %str(P_InternalLoad))
	print ("Q_HVAC: %s" %str(Q_HVAC))

        self.T_prev = self.T
        #self.Q_ThermalStorage_prev = Q_ThermalStorage
        #self.Q_prev = Q_total

        P_total = P_HVAC + P_InternalLoad
        
        return P_total, self.T

    def ETP_step(self,current_t, ETP_inputs):
        if current_t%86400 == 0:
            self.T_prev = self.initTemp[int((current_t-self.startTime)/86400)] #mid-night reset
	    print ("=========================RESET==========================")
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
        self.zoneArea   = data['zoneArea'] # zone area (m2)
        self.zoneHeight = data['zoneHeight'] # zone height (m)
        self.multiplier = data['multiplier'] # zone multiplier (unitless)
        self.LPD        = data['LPD'] # LPD=lighting power density (W/m2)
        self.OccD       = data['OccD'] # OccD = occupancy density (m2/#)
        self.EPD        = data['EPD'] # EPD=equipment power density (W/m2)
        self.ExWall     = data['ExteriorWallArea'] # exterior wall area (m2)
        self.InfRatePerEW = data['InfilDesignRatePerExtWall'] # infiltration rate per EWall area (m3/s-m2)

        with open('./core/_InternalLoad/sch.json') as sch_json:
                sch = json.load(sch_json,) 
        self.sch_eqip = sch['BLDG_EQUIP_SCH_ADV']
        self.sch_occ  = sch['BLDG_OCC_SCH']
        self.sch_inf  = sch['INFIL_SCH_PNNL']
        self.sch_lgt  = sch['BLDG_LIGHT_SCH'] 

    def internalLoad_step(self,current_t,control_inputs,windSpeed):
        Sch_LP = self.getSchedule(self.sch_lgt, current_t) # lighting Schedule
        Q_LP = np.multiply(self.LP, Sch_LP)
	LD = np.multiply(control_inputs['LightDimmer'],0.7) #use Fraction of Raidant = 0.7
        Q_LP = np.multiply(Q_LP, LD) 
        P_Light = 0

        Sch_EP = self.getSchedule(self.sch_eqip, current_t) # currently, this is not a controllable input
        Q_EP = np.multiply(self.EP, Sch_EP*0.5) #use Franction of Radiant = 0.5
        P_Equip = 0 

        Sch_Occ = self.getSchedule(self.sch_occ, current_t) # currently, this is not a controllable input
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
	self.systems['basement'].terminate()
	self.systems['bot'].terminate()
	self.systems['mid'].terminate()
	self.systems['top'].terminate()
        print ("End of simulation")

    def print_system_info(self):
        print ("===================Large Office model===================")
        print "1 Large Office is loaded."

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
