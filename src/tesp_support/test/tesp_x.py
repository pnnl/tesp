# Copyright (C) 2021 Battelle Memorial Institute
# file: tesp_x.py

import sys
import json
import numpy as np

config = {'BackboneFiles':{},'FeederGenerator':{},'EplusConfiguration':{},'PYPOWERConfiguration':{},
	'AgentPrep':{},'ThermostatSchedule':{},'WeatherPrep':{},'SimulationConfig':{},'MonteCarloCase':{}}

StartTime = "2013-07-01 00:00:00"
EndTime = "2013-07-03 00:00:00"

taxonomyChoices = ['GC-12.47-1',
									 'R1-12.47-1',
									 'R1-12.47-2',
									 'R1-12.47-3',
									 'R1-12.47-4',
									 'R1-25.00-1',
									 'R2-12.47-1',
									 'R2-12.47-2',
									 'R2-12.47-3',
									 'R2-25.00-1',
									 'R2-35.00-1',
									 'R3-12.47-1',
									 'R3-12.47-2',
									 'R3-12.47-3',
									 'R4-12.47-1',
									 'R4-12.47-2',
									 'R4-25.00-1',
									 'R5-12.47-1',
									 'R5-12.47-2',
									 'R5-12.47-3',
									 'R5-12.47-4',
									 'R5-12.47-5',
									 'R5-25.00-1',
									 'R5-35.00-1'
									 ];

inverterModesBattery = ['GROUP_LOAD_FOLLOWING','LOAD_FOLLOWING','VOLT_VAR_FREQ_PWR','VOLT_WATT','VOLT_VAR','CONSTANT_PF','CONSTANT_PQ','NONE'];
inverterModesPV = ['VOLT_VAR_FREQ_PWR','VOLT_WATT','VOLT_VAR','CONSTANT_PF','CONSTANT_PQ','NONE'];

billingModes = ['TIERED_TOU','TIERED_RTP','HOURLY','TIERED','UNIFORM','NONE'];

eplusVoltageChoices = ['208', '480'];

powerFlowChoices = ['AC','DC'];
optimalPowerFlowChoices = ['AC','DC'];

# if one of these ends in 'Mid' we need to supply a 'Band' input
monteCarloChoices = ['None','ElectricCoolingParticipation','ThermostatRampMid','ThermostatOffsetLimitMid',
										 'WeekdayEveningStartMid','WeekdayEveningSetMid'];

weatherChoices = ['TMY3','CSV','WeatherBug']

# var columns are label, value, hint, JSON class, JSON attribute
varsTM = [['Start Time',StartTime,'GLD Date/Time','SimulationConfig','StartTime'],
					['End Time',EndTime,'GLD Date/Time','SimulationConfig','EndTime'],
					['Market Clearing Period',300,'s','AgentPrep','MarketClearingPeriod'],
					['GridLAB-D Time Step',15,'s','FeederGenerator','MinimumStep'],
					['Metrics Time Step',300,'s','FeederGenerator','MetricsInterval'],
					['Power Flow Time Step',15,'s','PYPOWERConfiguration','PFStep'],
					['Energy+ Time Step',5,'m','EplusConfiguration','TimeStep'],
					['Agent Time Step',5,'s','AgentPrep','TimeStepGldAgents'],
					['GridLAB-D Taxonomy Choice','R1-12.47-1','','BackboneFiles','TaxonomyChoice','taxonomyChoices'],
					['Energy+ Base File','SchoolDualController.idf','','BackboneFiles','EnergyPlusFile'],
					['PYPOWER Base File','ppbasefile.py','','BackboneFiles','PYPOWERFile'],
					['Weather Type','TMY3','','WeatherPrep','WeatherChoice','weatherChoices'],
					['Weather Source','WA-Yakima_Air_Terminal.tmy3','File or URL','WeatherPrep','DataSource'],
					['Airport Code','YKM','','WeatherPrep','AirportCode'],
					['Weather Year','2001','','WeatherPrep','Year'],
					['Source Directory','~/src/tesp/support','Parent directory of base model files','SimulationConfig','SourceDirectory'],
					['Working Directory','./','','SimulationConfig','WorkingDirectory'],
					['Case Name','Case1','','SimulationConfig','CaseName']
					];
varsFD = [['Electric Cooling Penetration',90,'%','FeederGenerator','ElectricCoolingPercentage'],
					['Electric Cooling Participation',50,'%','FeederGenerator','ElectricCoolingParticipation'],
					['Solar Penetration',20,'%','FeederGenerator','SolarPercentage'],
					['Storage Penetration',10,'%','FeederGenerator','StoragePercentage'],
					['Solar Inverter Mode','VOLT_VAR','','FeederGenerator','SolarInverterMode','inverterModesPV'],
					['Storage Inverter Mode','LOAD_FOLLOWING','','FeederGenerator','StorageInverterMode','inverterModesBattery'],
					['Eplus Bus','R1-12-47-1_node_346','','FeederGenerator','EnergyPlusBus'],
					['Eplus Service Voltage',480,'V','FeederGenerator','EnergyPlusServiceV','eplusVoltageChoices'],
					['Eplus Transformer Size',150,'kVA','FeederGenerator','EnergyPlusXfmrKva'],
					['Billing Mode','UNIFORM','','FeederGenerator','BillingMode','billingModes'],
					['Monthly Fee',13,'$','FeederGenerator','MonthlyFee'],
					['Price',0.102013,'$/kwh','FeederGenerator','Price'],
					['Tier 1 Energy',500,'kwh','FeederGenerator','Tier1Energy'],
					['Tier 1 Price',0.117013,'$/kwh','FeederGenerator','Tier1Price'],
					['Tier 2 Energy',1000,'kwh','FeederGenerator','Tier2Energy'],
					['Tier 2 Price',0.122513,'$/kwh','FeederGenerator','Tier2Price'],
					['Tier 3 Energy',0,'kwh','FeederGenerator','Tier3Energy'],
					['Tier 3 Price',0,'$/kwh','FeederGenerator','Tier3Price']
					];
varsPP = [['OPF Type','DC','for dispatch and price','PYPOWERConfiguration','ACOPF','optimalPowerFlowChoices'],
					['PF Type','AC','for voltage','PYPOWERConfiguration','ACPF','powerFlowChoices'],
					['Substation Voltage',230.0,'kV','PYPOWERConfiguration','TransmissionVoltage'],
					['Substation Base',12.0,'MVA','PYPOWERConfiguration','TransformerBase'],
					['GLD Bus Number',7,'','PYPOWERConfiguration','GLDBus'],
					['GLD Load Scale',400,'','PYPOWERConfiguration','GLDScale'],
					['Non-responsive Loads','NonGLDLoad.txt','CSV File','PYPOWERConfiguration','CSVLoadFile'],
					['Unit Out',2,'','PYPOWERConfiguration','UnitOut'],
					['Unit Outage Start','2013-07-02 07:00:00','GLD Date/Time','PYPOWERConfiguration','UnitOutStart'],
					['Unit Outage End','2013-07-02 19:00:00','GLD Date/Time','PYPOWERConfiguration','UnitOutEnd'],
					['Branch Out',3,'','PYPOWERConfiguration','BranchOut'],
					['Branch Outage Start','','GLD Date/Time','PYPOWERConfiguration','BranchOutStart'],
					['Branch Outage End','','GLD Date/Time','PYPOWERConfiguration','BranchOutEnd']
					];
varsEP = [['Reference Price',0.02078,'$','EplusConfiguration','ReferencePrice'],
					['Ramp',25,'degF/$','EplusConfiguration','Slope'],
					['Delta Limit Hi',3,'degF','EplusConfiguration','OffsetLimitHi'],
					['Delta Limit Lo',3,'degF','EplusConfiguration','OffsetLimitLo'],
					['Energy+ Weather File','USA_AZ_Tucson.Intl.AP.722740_TMY3.epw','','EplusConfiguration','EnergyPlusWeather']
					];
varsAC = [['Initial Price',0.02078,'$','AgentPrep','InitialPriceMean'],
					['Std Dev Price',0.00361,'$','AgentPrep','InitialPriceStdDev'],
					['Ramp Lo',0.5,'$(std dev)/degF','AgentPrep','ThermostatRampLo'],
					['Ramp Hi',3.0,'$(std dev)/degF','AgentPrep','ThermostatRampHi'],
					['Band Lo',1.0,'degF','AgentPrep','ThermostatBandLo'],
					['Band Hi',3.0,'degF','AgentPrep','ThermostatBandHi'],
					['Offset Limit Lo',2.0,'degF','AgentPrep','ThermostatOffsetLimitLo'],
					['Offset Limit Hi',6.0,'degF','AgentPrep','ThermostatOffsetLimitHi'],
					['Price Cap Lo',1.00,'$','AgentPrep','PriceCapLo'],
					['Price Cap Hi',3.00,'$','AgentPrep','PriceCapHi']
					];
varsTS = [['Weekday Wakeup Start Lo',5.0,'hour of day','ThermostatSchedule','WeekdayWakeStartLo'],
					['Weekday Wakeup Start Hi',6.5,'hour of day','ThermostatSchedule','WeekdayWakeStartHi'],
					['Weekday Wakeup Set Lo',78,'degF','ThermostatSchedule','WeekdayWakeSetLo'],
					['Weekday Wakeup Set Hi',80,'degF','ThermostatSchedule','WeekdayWakeSetHi'],
					['Weekday Daylight Start Lo',8.0,'hour of day','ThermostatSchedule','WeekdayDaylightStartLo'],
					['Weekday Daylight Start Hi',9.0,'hour of day','ThermostatSchedule','WeekdayDaylightStartHi'],
					['Weekday Daylight Set Lo',84,'degF','ThermostatSchedule','WeekdayDaylightSetLo'],
					['Weekday Daylight Set Hi',86,'degF','ThermostatSchedule','WeekdayDaylightSetHi'],
					['Weekday Evening Start Lo',17.0,'hour of day','ThermostatSchedule','WeekdayEveningStartLo'],
					['Weekday Evening Start Hi',18.5,'hour of day','ThermostatSchedule','WeekdayEveningStartHi'],
					['Weekday Evening Set Lo',78,'degF','ThermostatSchedule','WeekdayEveningSetLo'],
					['Weekday Evening Set Hi',80,'degF','ThermostatSchedule','WeekdayEveningSetHi'],
					['Weekday Night Start Lo',22.0,'hour of day','ThermostatSchedule','WeekdayNightStartLo'],
					['Weekday Night Start Hi',23.5,'hour of day','ThermostatSchedule','WeekdayNightStartHi'],
					['Weekday Night Set Lo',72,'degF','ThermostatSchedule','WeekdayNightSetLo'],
					['Weekday Night Set Hi',74,'degF','ThermostatSchedule','WeekdayNightSetHi'],
					['Weekend Daylight Start Lo',8.0,'hour of day','ThermostatSchedule','WeekendDaylightStartLo'],
					['Weekend Daylight Start Hi',9.0,'hour of day','ThermostatSchedule','WeekendDaylightStartHi'],
					['Weekend Daylight Set Lo',76,'degF','ThermostatSchedule','WeekendDaylightSetLo'],
					['Weekend Daylight Set Hi',84,'degF','ThermostatSchedule','WeekendDaylightSetHi'],
					['Weekend Night Start Lo',22.0,'hour of day','ThermostatSchedule','WeekendNightStartLo'],
					['Weekend Night Start Hi',24.0,'hour of day','ThermostatSchedule','WeekendNightStartHi'],
					['Weekend Night Set Lo',72,'degF','ThermostatSchedule','WeekendNightSetLo'],
					['Weekend Night Set Hi',74,'degF','ThermostatSchedule','WeekendNightSetHi']
					];

def AttachVars (tab):
    for row in tab:
        val = row[1]
        section = row[3]
        attr = row[4]
        config[section][attr] = val
    
op = open ('test.json', 'w')
AttachVars (varsTM)
AttachVars (varsFD)
AttachVars (varsPP)
AttachVars (varsEP)
AttachVars (varsAC)
AttachVars (varsTS)
print (json.dumps(config), file=op)
op.close()

