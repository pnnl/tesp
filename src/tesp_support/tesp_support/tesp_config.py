import sys
import json
import tkinter as tk
import tkinter.ttk as ttk
import numpy as np
from tkinter import filedialog

root = tk.Tk()
root.title('Transactive Energy Simulation Platform: Case Configuration')
nb = ttk.Notebook(root)
nb.pack(fill='both', expand='yes')

config = {'BackboneFiles':{},'FeederGenerator':{},'EplusConfiguration':{},'PYPOWERConfiguration':{},
	'AgentPrep':{},'ThermostatSchedule':{},'WeatherPrep':{},'SimulationConfig':{},'MonteCarloCase':{}}

StartTime = "2013-07-01 00:00:00"
EndTime = "2013-07-03 00:00:00"
#Tmax = 2 * 24 * 3600

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
					['Agent Time Step',15,'s','AgentPrep','TimeStepGldAgents'],
					['GridLAB-D Taxonomy Choice','R1-12.47-1','','BackboneFiles','TaxonomyChoice','taxonomyChoices'],
					['Energy+ Base File','SchoolDualController.idf','','BackboneFiles','EnergyPlusFile'],
					['PYPOWER Base File','ppbasefile.py','','BackboneFiles','PYPOWERFile'],
					['Weather Type','TMY3','','WeatherPrep','WeatherChoice','weatherChoices'],
					['Weather Source','WA-Yakima_Air_Terminal.tmy3','File or URL','WeatherPrep','DataSource'],
					['Airport Code','YKM','','WeatherPrep','AirportCode'],
					['Weather Year','2001','','WeatherPrep','Year'],
					['Source Directory','~/src/tesp/support','Parent directory of base model files','SimulationConfig','SourceDirectory'],
					['Working Directory','./','','SimulationConfig','WorkingDirectory'],
					['Case Name','Test','','SimulationConfig','CaseName']
					];
varsFD = [['Electric Cooling Penetration',90,'%','FeederGenerator','ElectricCoolingPercentage'],
					['Electric Cooling Participation',50,'%','FeederGenerator','ElectricCoolingParticipation'],
					['Solar Penetration',20,'%','FeederGenerator','SolarPercentage'],
					['Storage Penetration',10,'%','FeederGenerator','StoragePercentage'],
					['Solar Inverter Mode','CONSTANT_PF','','FeederGenerator','SolarInverterMode','inverterModesPV'],
					['Storage Inverter Mode','CONSTANT_PF','','FeederGenerator','StorageInverterMode','inverterModesBattery'],
					['Eplus Bus','R1-12-47-1_node_346','','FeederGenerator','EnergyPlusBus'],
					['Eplus Service Voltage',480,'V','FeederGenerator','EnergyPlusServiceV','eplusVoltageChoices'],
					['Eplus Transformer Size',150,'kVA','FeederGenerator','EnergyPlusXfmrKva'],
					['Billing Mode','TIERED','','FeederGenerator','BillingMode','billingModes'],
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
varsEP = [['Reference Price',0.02,'$','EplusConfiguration','ReferencePrice'],
					['Ramp',25,'degF/$','EplusConfiguration','Slope'],
					['Delta Limit Hi',4,'degF','EplusConfiguration','OffsetLimitHi'],
					['Delta Limit Lo',4,'degF','EplusConfiguration','OffsetLimitLo']
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

def AttachFrame(tag, vars):
	f = ttk.Frame(nb, name=tag)
	lab = ttk.Label(f, text='Parameter', relief=tk.RIDGE)
	lab.grid(row=0, column=0, sticky=tk.NSEW)
	lab = ttk.Label(f, text='Value', relief=tk.RIDGE)
	lab.grid(row=0, column=1, sticky=tk.NSEW)
	lab = ttk.Label(f, text='Units/Notes', relief=tk.RIDGE)
	lab.grid(row=0, column=2, sticky=tk.NSEW)
	for i in range(len(vars)):
		lab = ttk.Label(f, text=vars[i][0], relief=tk.RIDGE)
		lab.grid(row=i+1, column=0, sticky=tk.NSEW)
		if len(vars[i]) > 5:
			cb = ttk.Combobox(f, values=globals()[vars[i][5]], name=vars[i][5])
			cb.set(vars[i][1])
			cb.grid(row=i+1, column=1, sticky=tk.NSEW)
		else:
			ent = ttk.Entry(f)
			ent.insert(0, vars[i][1])
			ent.grid(row=i+1, column=1, sticky=tk.NSEW)
		lab = ttk.Label(f, text=vars[i][2], relief=tk.RIDGE)
		lab.grid(row=i+1, column=2, sticky=tk.NSEW)
	return f

def ReloadFrame(f, vars):
	for i in range(len(vars)):
		ent = f.grid_slaves (row=i+1, column=1)[0]
		ent.delete (0, tk.END)
		ent.insert (0, vars[i][1])

def SizeMonteCarlo(n):
	config['MonteCarloCase']['NumCases'] = n
	config['MonteCarloCase']['Band1'] = 0.0
	config['MonteCarloCase']['Band2'] = 0.0
	config['MonteCarloCase']['Band3'] = 0.0
	config['MonteCarloCase']['Samples1'] = [0] * n
	config['MonteCarloCase']['Samples2'] = [0] * n
	config['MonteCarloCase']['Samples3'] = [0] * n
	for i in range(n):
		config['MonteCarloCase']['Samples1'][i] = np.random.uniform (0, 1)
		config['MonteCarloCase']['Samples2'][i] = np.random.uniform (0, 1)
		config['MonteCarloCase']['Samples3'][i] = np.random.uniform (0, 1)

def InitializeMonteCarlo(n):
	SizeMonteCarlo(n)
	config['MonteCarloCase']['Variable1'] = monteCarloChoices[1]
	config['MonteCarloCase']['Variable2'] = monteCarloChoices[2]
	config['MonteCarloCase']['Variable3'] = monteCarloChoices[3]

# row 0 for dropdowns, 1 for update controls, 2 for column headers, 3 for range edits
def SizeMonteCarloFrame(f):
	startRow = 3
	for w in f.grid_slaves():
		if int(w.grid_info()['row']) > startRow:
			w.grid_forget()

	col1 = f.children['cb1'].get()
	col2 = f.children['cb2'].get()
	col3 = f.children['cb3'].get()
	use1 = col1 != 'None'
	use2 = col2 != 'None'
	use3 = col3 != 'None'
	band1 = 'Mid' in col1
	band2 = 'Mid' in col2
	band3 = 'Mid' in col3

	lab = ttk.Label(f, text='Case #', relief=tk.RIDGE)
	lab.grid(row=startRow + 1, column=0, sticky=tk.NSEW)
	lab = ttk.Label(f, text=col1, relief=tk.RIDGE)
	lab.grid(row=startRow - 1, column=1, sticky=tk.NSEW)
	lab = ttk.Label(f, text=col2, relief=tk.RIDGE)
	lab.grid(row=startRow - 1, column=2, sticky=tk.NSEW)
	lab = ttk.Label(f, text=col3, relief=tk.RIDGE)
	lab.grid(row=startRow - 1, column=3, sticky=tk.NSEW)

	lab = ttk.Label(f, text='Band', relief=tk.RIDGE)
	lab.grid(row=startRow, column=0, sticky=tk.NSEW)
	if band1:
		w1 = ttk.Entry(f)
		w1.insert(0, config['MonteCarloCase']['Band1'])
	else:
		w1 = ttk.Label(f, text='n/a', relief=tk.RIDGE)
	if band2:
		w2 = ttk.Entry(f)
		w2.insert(0, config['MonteCarloCase']['Band2'])
	else:
		w2 = ttk.Label(f, text='n/a', relief=tk.RIDGE)
	if band3:
		w3 = ttk.Entry(f)
		w3.insert(0, config['MonteCarloCase']['Band3'])
	else:
		w3 = ttk.Label(f, text='n/a', relief=tk.RIDGE)
	w1.grid(row=startRow, column=1, sticky=tk.NSEW)
	w2.grid(row=startRow, column=2, sticky=tk.NSEW)
	w3.grid(row=startRow, column=3, sticky=tk.NSEW)

	n = int (config['MonteCarloCase']['NumCases'])
	for i in range(n):
		lab = ttk.Label(f, text=str(i+1), relief=tk.RIDGE)
		lab.grid(row=i+2+startRow, column=0, sticky=tk.NSEW)
		if use1:
			w1 = ttk.Entry(f)
			w1.insert(0, config['MonteCarloCase']['Samples1'][i])
		else:
			w1 = ttk.Label(f, text='n/a', relief=tk.RIDGE)
		if use2:
			w2 = ttk.Entry(f)
			w2.insert(0, config['MonteCarloCase']['Samples2'][i])
		else:
			w2 = ttk.Label(f, text='n/a', relief=tk.RIDGE)
		if use3:
			w3 = ttk.Entry(f)
			w3.insert(0, config['MonteCarloCase']['Samples3'][i])
		else:
			w3 = ttk.Label(f, text='n/a', relief=tk.RIDGE)
		w1.grid(row=i+2+startRow, column=1, sticky=tk.NSEW)
		w2.grid(row=i+2+startRow, column=2, sticky=tk.NSEW)
		w3.grid(row=i+2+startRow, column=3, sticky=tk.NSEW)

f1 = AttachFrame ('varsTM', varsTM)
f2 = AttachFrame ('varsFD', varsFD)
f3 = AttachFrame ('varsPP', varsPP)
f4 = AttachFrame ('varsEP', varsEP)
f5 = AttachFrame ('varsAC', varsAC)
f6 = AttachFrame ('varsTS', varsTS)
f7 = ttk.Frame (nb, name='varsMC')

def GenerateFiles():
	print('TODO: save configuration, separate script will write all files to case working directory')

def ReadFrame(f,vars):
	for w in f.grid_slaves():
		col = int(w.grid_info()['column'])
		row = int(w.grid_info()['row'])
		if col == 1 and row > 0 and row <= len(vars):
			val = w.get()
			section = vars[row-1][3]
			attribute = vars[row-1][4]
			config[section][attribute] = val

def SaveConfig():
	ReadFrame(f1, varsTM)
	ReadFrame(f2, varsFD)
	ReadFrame(f3, varsPP)
	ReadFrame(f4, varsEP)
	ReadFrame(f5, varsAC)
	ReadFrame(f6, varsTS)

	col1 = f7.children['cb1'].get()
	col2 = f7.children['cb2'].get()
	col3 = f7.children['cb3'].get()
	use1 = col1 != 'None'
	use2 = col2 != 'None'
	use3 = col3 != 'None'
	band1 = 'Mid' in col1
	band2 = 'Mid' in col2
	band3 = 'Mid' in col3
	numCases = int (f7.children['rows'].get())	# TODO - what if user changed entry and didn't click Update...global numCases?
	InitializeMonteCarlo (numCases)
	for w in f7.grid_slaves():
		row = int(w.grid_info()['row'])
		col = int(w.grid_info()['column'])
		if row == 3:
			if col == 1 and band1:
				val = float(w.get())
				config['MonteCarloCase']['Band1'] = val
			if col == 2 and band2:
				val = float(w.get())
				config['MonteCarloCase']['Band2'] = val
			if col == 3 and band3:
				val = float(w.get())
				config['MonteCarloCase']['Band3'] = val
		elif row > 4:
			if col == 1 and use1:
				val = float(w.get())
				config['MonteCarloCase']['Samples1'][row-5] = val
			if col == 2 and use2:
				val = float(w.get())
				config['MonteCarloCase']['Samples2'][row-5] = val
			if col == 3 and use3:
				val = float(w.get())
				config['MonteCarloCase']['Samples3'][row-5] = val
	fname = filedialog.asksaveasfilename(initialdir = '~/src/examples/te30',
																			 title = 'Save JSON Configuration to',
																			 defaultextension = 'json')
	op = open (fname, 'w')
	print (json.dumps(config), file=op)
	op.close()

def JsonToSection(jsn, vars):
	for i in range(len(vars)):
		section = vars[i][3]
		attribute = vars[i][4]
		vars[i][1] = jsn[section][attribute]
		config[section][attribute] = jsn[section][attribute]

def OpenConfig():
	fname = filedialog.askopenfilename(initialdir = '~/src/examples/te30',
																		title = 'Open JSON Configuration',
																		filetypes = (("JSON files","*.json"),("all files","*.*")),
																		defaultextension = 'json')
	lp = open (fname)
	cfg = json.loads(lp.read())
	lp.close()
	JsonToSection (cfg, varsTM)
	JsonToSection (cfg, varsFD)
	JsonToSection (cfg, varsPP)
	JsonToSection (cfg, varsEP)
	JsonToSection (cfg, varsAC)
	JsonToSection (cfg, varsTS)
	ReloadFrame (f1, varsTM)
	ReloadFrame (f2, varsFD)
	ReloadFrame (f3, varsPP)
	ReloadFrame (f4, varsEP)
	ReloadFrame (f5, varsAC)
	ReloadFrame (f6, varsTS)

	numCases = int (cfg['MonteCarloCase']['NumCases'])
	config['MonteCarloCase']['NumCases'] = numCases
	ent = f7.children['rows']
	ent.delete (0, tk.END)
	ent.insert (0, str(numCases))

	var1 = cfg['MonteCarloCase']['Variable1']
	config['MonteCarloCase']['Variable1'] = var1
	f7.children['cb1'].set(var1)

	var2 = cfg['MonteCarloCase']['Variable2']
	config['MonteCarloCase']['Variable2'] = var2
	f7.children['cb2'].set(var2)

	var3 = cfg['MonteCarloCase']['Variable3']
	config['MonteCarloCase']['Variable3'] = var3
	f7.children['cb3'].set(var3)

	config['MonteCarloCase']['Band1'] = cfg['MonteCarloCase']['Band1']
	config['MonteCarloCase']['Band2'] = cfg['MonteCarloCase']['Band2']
	config['MonteCarloCase']['Band3'] = cfg['MonteCarloCase']['Band3']

	config['MonteCarloCase']['Samples1'] = [0] * numCases
	config['MonteCarloCase']['Samples2'] = [0] * numCases
	config['MonteCarloCase']['Samples3'] = [0] * numCases

	for i in range(numCases):
		config['MonteCarloCase']['Samples1'][i] = cfg['MonteCarloCase']['Samples1'][i]
		config['MonteCarloCase']['Samples2'][i] = cfg['MonteCarloCase']['Samples2'][i]
		config['MonteCarloCase']['Samples3'][i] = cfg['MonteCarloCase']['Samples3'][i]

	SizeMonteCarloFrame (f7)

#ttk.Style().configure('TButton', background='blue')
ttk.Style().configure('TButton', foreground='blue')
btn = ttk.Button(f1, text='Generate Case Files', command=GenerateFiles)
btn.grid(row=len(varsTM) + 1, column=1, sticky=tk.NSEW)
btn = ttk.Button(f1, text='Save Config...', command=SaveConfig)
btn.grid(row=len(varsTM) + 2, column=1, sticky=tk.NSEW)
btn = ttk.Button(f1, text='Open Config...', command=OpenConfig)
btn.grid(row=len(varsTM) + 3, column=1, sticky=tk.NSEW)

def UpdateMonteCarloFrame():
	numCases = int (f7.children['rows'].get())
	SizeMonteCarlo (numCases)
	SizeMonteCarloFrame (f7)

print('TkInter Version', tk.TkVersion)

lab = ttk.Label(f7, text='Columns', relief=tk.RIDGE)
lab.grid(row=0, column=0, sticky=tk.NSEW)
cb = ttk.Combobox(f7, values=monteCarloChoices, name='cb1')
cb.set(monteCarloChoices[1])
cb.grid(row=0, column=1, sticky=tk.NSEW)
cb = ttk.Combobox(f7, values=monteCarloChoices, name='cb2')
cb.set(monteCarloChoices[2])
cb.grid(row=0, column=2, sticky=tk.NSEW)
cb = ttk.Combobox(f7, values=monteCarloChoices, name='cb3')
cb.set(monteCarloChoices[3])
cb.grid(row=0, column=3, sticky=tk.NSEW)

InitializeMonteCarlo (7)
lab = ttk.Label(f7, text='Rows', relief=tk.RIDGE)
lab.grid(row=1, column=0, sticky=tk.NSEW)
ent = ttk.Entry(f7, name='rows')
ent.insert(0, config['MonteCarloCase']['NumCases'])
ent.grid(row=1, column=1, sticky=tk.NSEW)
btn = ttk.Button (f7, text='Update', command=UpdateMonteCarloFrame)
btn.grid(row=1, column=3, sticky=tk.NSEW)
SizeMonteCarlo (config['MonteCarloCase']['NumCases'])
SizeMonteCarloFrame (f7)

nb.add(f1, text='Main', underline=0, padding=2)
nb.add(f2, text='Feeder', underline=0, padding=2)
nb.add(f3, text='PYPOWER', underline=0, padding=2)
nb.add(f4, text='Energy+', underline=0, padding=2)
nb.add(f5, text='Auction', underline=0, padding=2)
nb.add(f6, text='Thermostats', underline=0, padding=2)
nb.add(f7, text='Sampling', underline=0, padding=2)

while True:
	try:
		root.mainloop()
		break
	except UnicodeDecodeError:
		pass
