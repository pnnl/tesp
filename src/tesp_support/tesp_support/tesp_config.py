# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: tesp_config.py
"""Presents a GUI to configure and package TESP cases

Public Functions:
  :show_tesp_config: Initializes and runs the GUI

References:
  `Graphical User Interfaces with Tk <https://docs.python.org/3/library/tk.html>`_
"""
import csv
import json
import os

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox

import numpy as np

from .data import tesp_share, weather_path

config = {'BackboneFiles': {},
          'FeederGenerator': {},
          'EplusConfiguration': {},
          'PYPOWERConfiguration': {},
          'AgentPrep': {},
          'ThermostatSchedule': {},
          'WeatherPrep': {},
          'SimulationConfig': {},
          'MonteCarloCase': {}}

StartTime = "2013-07-01 00:00:00"
EndTime = "2013-07-03 00:00:00"

taxonomyChoices = ['TE_Base',
                   'GC-12.47-1',
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
                   ]

buildingChoices = ['FullServiceRestaurant',
                   'Hospital',
                   'LargeHotel',
                   'LargeOffice',
                   'MediumOffice',
                   'MidriseApartment',
                   'OutPatient',
                   'PrimarySchool',
                   'QuickServiceRestaurant',
                   'SchoolDualController',
                   'SecondarySchool',
                   'SmallHotel',
                   'SmallOffice',
                   'StandaloneRetail',
                   'StripMall',
                   'SuperMarket',
                   'Warehouse'
                   ]

inverterModesBattery = ['GROUP_LOAD_FOLLOWING', 'LOAD_FOLLOWING', 'VOLT_VAR_FREQ_PWR', 'VOLT_WATT', 'VOLT_VAR',
                        'CONSTANT_PF', 'CONSTANT_PQ', 'NONE']
inverterModesPV = ['VOLT_VAR_FREQ_PWR', 'VOLT_WATT', 'VOLT_VAR', 'CONSTANT_PF', 'CONSTANT_PQ', 'NONE']

billingModes = ['TIERED_TOU', 'TIERED_RTP', 'HOURLY', 'TIERED', 'UNIFORM', 'NONE']

eplusVoltageChoices = ['208', '480']

powerFlowChoices = ['AC', 'DC']
optimalPowerFlowChoices = ['AC', 'DC']

# if one of these ends in 'Mid' we need to supply a 'Band' input
monteCarloChoices = ['None', 'ElectricCoolingParticipation', 'ThermostatRampMid', 'ThermostatOffsetLimitMid',
                     'WeekdayEveningStartMid', 'WeekdayEveningSetMid']

weatherChoices = ['TMY3']  # ,'CSV','WeatherBug']

# var columns are label, value, hint, JSON class, JSON attribute
# if there is a sixth column, that will be the name of a Choices tuple, to be edited via Combobox
# if there is not a sixth column, that indicates a single value to be edited via Entry
varsTM = [['Start Time', StartTime, 'GLD Date/Time', 'SimulationConfig', 'StartTime'],
          ['End Time', EndTime, 'GLD Date/Time', 'SimulationConfig', 'EndTime'],
          ['Market Clearing Period', 300, 's', 'AgentPrep', 'MarketClearingPeriod'],
          ['GridLAB-D Time Step', 15, 's', 'FeederGenerator', 'MinimumStep'],
          ['Metrics Time Step', 300, 's', 'FeederGenerator', 'MetricsInterval'],
          ['Power Flow Time Step', 15, 's', 'PYPOWERConfiguration', 'PFStep'],
          ['Agent Time Step', 15, 's', 'AgentPrep', 'TimeStepGldAgents'],
          ['GridLAB-D Taxonomy Choice', 'TE_Base', '', 'BackboneFiles', 'TaxonomyChoice', 'taxonomyChoices'],
          ['Feeder Name Prefix', 'Fdr1_', 'Prepend to Taxonomy Names', 'BackboneFiles', 'NamePrefix'],
          ['PYPOWER Base File', 'ppbasefile.py', '', 'BackboneFiles', 'PYPOWERFile'],
          ['Weather Type', 'TMY3', '', 'WeatherPrep', 'WeatherChoice', 'weatherChoices'],
          ['Weather Source', 'WA-Yakima_Air_Terminal.tmy3', 'File or URL', 'WeatherPrep', 'DataSource'],
          ['Latitude (N > 0)', 32.133, 'deg', 'WeatherPrep', 'Latitude'],
          ['Longitude (E > 0)', -110.95, 'deg', 'WeatherPrep', 'Longitude'],
          ['Altitude (not used yet)', 777.0, 'm', 'WeatherPrep', 'Altitude'],
          ['TZmeridian (E > 0)', -105.00, 'deg', 'WeatherPrep', 'TZmeridian'],
          ['Support Directory', '$TESPDIR', 'Directory of TESP', 'SimulationConfig', 'SourceDirectory'],
          ['Working Directory', './test', '', 'SimulationConfig', 'WorkingDirectory'],
          ['Case Name', 'test', '', 'SimulationConfig', 'CaseName']
          ]
varsTMSupportDirIndex = 16

varsFD = [['Electric Cooling Penetration', 90, '%', 'FeederGenerator', 'ElectricCoolingPercentage'],
          ['Electric Cooling Participation', 50, '%', 'FeederGenerator', 'ElectricCoolingParticipation'],
          ['Water Heater Penetration', 75, '%', 'FeederGenerator', 'WaterHeaterPercentage'],
          ['Water Heater Participation', 25, '%', 'FeederGenerator', 'WaterHeaterParticipation'],
          ['Solar Penetration', 0, '%', 'FeederGenerator', 'SolarPercentage'],
          ['Storage Penetration', 0, '%', 'FeederGenerator', 'StoragePercentage'],
          ['Solar Inverter Mode', 'CONSTANT_PF', '', 'FeederGenerator', 'SolarInverterMode', 'inverterModesPV'],
          ['Storage Inverter Mode', 'CONSTANT_PF', '', 'FeederGenerator', 'StorageInverterMode',
           'inverterModesBattery'],
          ['Billing Mode', 'TIERED', '', 'FeederGenerator', 'BillingMode', 'billingModes'],
          ['Monthly Fee', 13.0, '$', 'FeederGenerator', 'MonthlyFee'],
          ['Price', 0.102013, '$/kwh', 'FeederGenerator', 'Price'],
          ['Tier 1 Energy', 500.0, 'kwh', 'FeederGenerator', 'Tier1Energy'],
          ['Tier 1 Price', 0.117013, '$/kwh', 'FeederGenerator', 'Tier1Price'],
          ['Tier 2 Energy', 1000.0, 'kwh', 'FeederGenerator', 'Tier2Energy'],
          ['Tier 2 Price', 0.122513, '$/kwh', 'FeederGenerator', 'Tier2Price'],
          ['Tier 3 Energy', 0.0, 'kwh', 'FeederGenerator', 'Tier3Energy'],
          ['Tier 3 Price', 0.0, '$/kwh', 'FeederGenerator', 'Tier3Price']
          ]
varsPP = [['OPF Type', 'DC', 'for dispatch and price', 'PYPOWERConfiguration', 'ACOPF', 'optimalPowerFlowChoices'],
          ['PF Type', 'DC', 'for voltage', 'PYPOWERConfiguration', 'ACPF', 'powerFlowChoices'],
          ['Substation Voltage', 230.0, 'kV', 'PYPOWERConfiguration', 'TransmissionVoltage'],
          ['Substation Base', 12.0, 'MVA', 'PYPOWERConfiguration', 'TransformerBase'],
          ['GLD Bus Number', 7, '', 'PYPOWERConfiguration', 'GLDBus'],
          ['GLD Load Scale', 20, '', 'PYPOWERConfiguration', 'GLDScale'],
          ['Non-responsive Loads', 'NonGLDLoad.txt', 'CSV File', 'PYPOWERConfiguration', 'CSVLoadFile'],
          ['Unit Out', 2, '', 'PYPOWERConfiguration', 'UnitOut'],
          ['Unit Outage Start', '2013-07-02 07:00:00', 'GLD Date/Time', 'PYPOWERConfiguration', 'UnitOutStart'],
          ['Unit Outage End', '2013-07-02 19:00:00', 'GLD Date/Time', 'PYPOWERConfiguration', 'UnitOutEnd'],
          ['Branch Out', 3, '', 'PYPOWERConfiguration', 'BranchOut'],
          ['Branch Outage Start', '', 'GLD Date/Time', 'PYPOWERConfiguration', 'BranchOutStart'],
          ['Branch Outage End', '', 'GLD Date/Time', 'PYPOWERConfiguration', 'BranchOutEnd']
          ]
varsEP = [['Energy+ Base File', 'SchoolDualController', '', 'EplusConfiguration', 'BuildingChoice', 'buildingChoices'],
          ['Energy+ EMS File', 'emsFNCS/emsSchoolDualController', '', 'EplusConfiguration', 'EMSFile'],
          ['Time Steps per Hour', 12, '', 'EplusConfiguration', 'StepsPerHour'],
          ['Eplus Bus', 'Feeder_head', '', 'EplusConfiguration', 'EnergyPlusBus'],
          ['Eplus Service Voltage', 480.0, 'V', 'EplusConfiguration', 'EnergyPlusServiceV', 'eplusVoltageChoices'],
          ['Eplus Transformer Size', 150.0, 'kVA', 'EplusConfiguration', 'EnergyPlusXfmrKva'],
          ['Reference Price', 0.02, '$', 'EplusConfiguration', 'ReferencePrice'],
          ['Ramp', 25.0, 'degF/$', 'EplusConfiguration', 'Slope'],
          ['Delta Limit Hi', 4.0, 'degF', 'EplusConfiguration', 'OffsetLimitHi'],
          ['Delta Limit Lo', 4.0, 'degF', 'EplusConfiguration', 'OffsetLimitLo']
          ]
varsAC = [['Initial Price', 0.02078, '$', 'AgentPrep', 'InitialPriceMean'],
          ['Std Dev Price', 0.00361, '$', 'AgentPrep', 'InitialPriceStdDev'],
          ['Ramp Lo', 0.5, '$(std dev)/degF', 'AgentPrep', 'ThermostatRampLo'],
          ['Ramp Hi', 3.0, '$(std dev)/degF', 'AgentPrep', 'ThermostatRampHi'],
          ['Band Lo', 1.0, 'degF', 'AgentPrep', 'ThermostatBandLo'],
          ['Band Hi', 3.0, 'degF', 'AgentPrep', 'ThermostatBandHi'],
          ['Offset Limit Lo', 2.0, 'degF', 'AgentPrep', 'ThermostatOffsetLimitLo'],
          ['Offset Limit Hi', 6.0, 'degF', 'AgentPrep', 'ThermostatOffsetLimitHi'],
          ['Price Cap Lo', 1.00, '$', 'AgentPrep', 'PriceCapLo'],
          ['Price Cap Hi', 3.00, '$', 'AgentPrep', 'PriceCapHi']
          ]
varsTS = [['Weekday Wakeup Start Lo', 5.0, 'hour of day', 'ThermostatSchedule', 'WeekdayWakeStartLo'],
          ['Weekday Wakeup Start Hi', 6.5, 'hour of day', 'ThermostatSchedule', 'WeekdayWakeStartHi'],
          ['Weekday Wakeup Set Lo', 78.0, 'degF', 'ThermostatSchedule', 'WeekdayWakeSetLo'],
          ['Weekday Wakeup Set Hi', 80.0, 'degF', 'ThermostatSchedule', 'WeekdayWakeSetHi'],
          ['Weekday Daylight Start Lo', 8.0, 'hour of day', 'ThermostatSchedule', 'WeekdayDaylightStartLo'],
          ['Weekday Daylight Start Hi', 9.0, 'hour of day', 'ThermostatSchedule', 'WeekdayDaylightStartHi'],
          ['Weekday Daylight Set Lo', 84.0, 'degF', 'ThermostatSchedule', 'WeekdayDaylightSetLo'],
          ['Weekday Daylight Set Hi', 86.0, 'degF', 'ThermostatSchedule', 'WeekdayDaylightSetHi'],
          ['Weekday Evening Start Lo', 17.0, 'hour of day', 'ThermostatSchedule', 'WeekdayEveningStartLo'],
          ['Weekday Evening Start Hi', 18.5, 'hour of day', 'ThermostatSchedule', 'WeekdayEveningStartHi'],
          ['Weekday Evening Set Lo', 78.0, 'degF', 'ThermostatSchedule', 'WeekdayEveningSetLo'],
          ['Weekday Evening Set Hi', 80.0, 'degF', 'ThermostatSchedule', 'WeekdayEveningSetHi'],
          ['Weekday Night Start Lo', 22.0, 'hour of day', 'ThermostatSchedule', 'WeekdayNightStartLo'],
          ['Weekday Night Start Hi', 23.5, 'hour of day', 'ThermostatSchedule', 'WeekdayNightStartHi'],
          ['Weekday Night Set Lo', 72.0, 'degF', 'ThermostatSchedule', 'WeekdayNightSetLo'],
          ['Weekday Night Set Hi', 74.0, 'degF', 'ThermostatSchedule', 'WeekdayNightSetHi'],
          ['Weekend Daylight Start Lo', 8.0, 'hour of day', 'ThermostatSchedule', 'WeekendDaylightStartLo'],
          ['Weekend Daylight Start Hi', 9.0, 'hour of day', 'ThermostatSchedule', 'WeekendDaylightStartHi'],
          ['Weekend Daylight Set Lo', 76.0, 'degF', 'ThermostatSchedule', 'WeekendDaylightSetLo'],
          ['Weekend Daylight Set Hi', 84.0, 'degF', 'ThermostatSchedule', 'WeekendDaylightSetHi'],
          ['Weekend Night Start Lo', 22.0, 'hour of day', 'ThermostatSchedule', 'WeekendNightStartLo'],
          ['Weekend Night Start Hi', 24.0, 'hour of day', 'ThermostatSchedule', 'WeekendNightStartHi'],
          ['Weekend Night Set Lo', 72.0, 'degF', 'ThermostatSchedule', 'WeekendNightSetLo'],
          ['Weekend Night Set Hi', 74.0, 'degF', 'ThermostatSchedule', 'WeekendNightSetHi']
          ]


class TespConfigGUI:
    """Manages a seven-page GUI for case configuration

    The GUI opens and saves a JSON file in the format used by *tesp.tesp_config*

    Todo:
      * Possible data loss if the user updated the number of Monte Carlo cases, but didn't click the Update button before saving the case configuration.

    Attributes:
      nb (Notebook): the top-level GUI with tabbed pages
      f1 (Frame): the page for date/time setup, along with T&D files, weather files and file paths
      f2 (Frame): the page for feeder generator setup
      f3 (Frame): the page for PYPOWER setup
      f4 (Frame): the page for EnergyPlus setup
      f5 (Frame): the page for simple_auction and hvac agent setup
      f6 (Frame): the page for time-scheduled thermostat settings
      f7 (Frame): the page for Monte Carlo setup
    """

    def __init__(self, master):
        self.nb = ttk.Notebook(master)
        self.nb.pack(fill='both', expand='yes')

        self.f1 = self.AttachFrame('varsTM', varsTM)
        self.f2 = self.AttachFrame('varsFD', varsFD)
        self.f3 = self.AttachFrame('varsPP', varsPP)
        self.f4 = self.AttachFrame('varsEP', varsEP)
        self.f5 = self.AttachFrame('varsAC', varsAC)
        self.f6 = self.AttachFrame('varsTS', varsTS)
        self.f7 = ttk.Frame(self.nb, name='varsMC')

        self.bldg_ems = self.f4.children['eplusconfiguration#emsfile']
        self.bldg_cb = self.f4.children['eplusconfiguration#buildingchoice']
        self.path_ent = self.f1.children['simulationconfig#sourcedirectory']
        self.tmy3_ent = self.f1.children['weatherprep#datasource']
        self.tz_ent = self.f1.children['weatherprep#tzmeridian']
        self.lat_ent = self.f1.children['weatherprep#latitude']
        self.long_ent = self.f1.children['weatherprep#longitude']
        self.alt_ent = self.f1.children['weatherprep#altitude']

        self.bldg_cb.bind("<<ComboboxSelected>>", self.UpdateEMS)

        # ttk.Style().configure('TButton', background='blue')
        ttk.Style().configure('TButton', foreground='blue')
        btn = ttk.Button(self.f1, text='Lat/Long/Alt/TZ from TMY3', command=self.ReadLatLong)
        btn.grid(row=len(varsTM) + 2, column=1, sticky=tk.NSEW)
        btn = ttk.Button(self.f1, text='Save Config...', command=self.SaveConfig)
        btn.grid(row=len(varsTM) + 3, column=1, sticky=tk.NSEW)
        btn = ttk.Button(self.f1, text='Open Config...', command=self.OpenConfig)
        btn.grid(row=len(varsTM) + 4, column=1, sticky=tk.NSEW)

        lab = ttk.Label(self.f7, text='Columns', relief=tk.RIDGE)
        lab.grid(row=0, column=0, sticky=tk.NSEW)
        cb = ttk.Combobox(self.f7, values=monteCarloChoices, name='cb1')
        cb.set(monteCarloChoices[1])
        cb.grid(row=0, column=1, sticky=tk.NSEW)
        cb = ttk.Combobox(self.f7, values=monteCarloChoices, name='cb2')
        cb.set(monteCarloChoices[2])
        cb.grid(row=0, column=2, sticky=tk.NSEW)
        cb = ttk.Combobox(self.f7, values=monteCarloChoices, name='cb3')
        cb.set(monteCarloChoices[3])
        cb.grid(row=0, column=3, sticky=tk.NSEW)

        self.InitializeMonteCarlo(7)
        lab = ttk.Label(self.f7, text='Rows', relief=tk.RIDGE)
        lab.grid(row=1, column=0, sticky=tk.NSEW)
        ent = ttk.Entry(self.f7, name='rows')
        ent.insert(0, config['MonteCarloCase']['NumCases'])
        ent.grid(row=1, column=1, sticky=tk.NSEW)
        btn = ttk.Button(self.f7, text='Update', command=self.UpdateMonteCarloFrame)
        btn.grid(row=1, column=3, sticky=tk.NSEW)
        self.SizeMonteCarlo(config['MonteCarloCase']['NumCases'])
        self.SizeMonteCarloFrame(self.f7)

        self.nb.add(self.f1, text='Main', underline=0, padding=2)
        self.nb.add(self.f2, text='Feeder', underline=0, padding=2)
        self.nb.add(self.f3, text='PYPOWER', underline=0, padding=2)
        self.nb.add(self.f4, text='Energy+', underline=0, padding=2)
        self.nb.add(self.f5, text='Auction', underline=0, padding=2)
        self.nb.add(self.f6, text='Thermostats', underline=0, padding=2)
        self.nb.add(self.f7, text='Sampling', underline=0, padding=2)

    def AttachFrame(self, tag, vars):
        """Creates a GUI page and loads it with data

        Label, Combobox and Entry (i.e. edit) controls are automatically created for each row of data

        Args:
          tag (str): the name of the Frame, i.e., GUI page
          vars (dict): the section of case configuration data to be loaded onto this new GUI page
        """
        f = ttk.Frame(self.nb, name=tag)
        lab = ttk.Label(f, text='Parameter', relief=tk.RIDGE)
        lab.grid(row=0, column=0, sticky=tk.NSEW)
        lab = ttk.Label(f, text='Value', relief=tk.RIDGE)
        lab.grid(row=0, column=1, sticky=tk.NSEW)
        lab = ttk.Label(f, text='Units/Notes', relief=tk.RIDGE)
        lab.grid(row=0, column=2, sticky=tk.NSEW)
        for i in range(len(vars)):
            lab = ttk.Label(f, text=vars[i][0], relief=tk.RIDGE)
            lab.grid(row=i + 1, column=0, sticky=tk.NSEW)
            varName = (vars[i][3] + '#' + vars[i][4]).lower()
            if len(vars[i]) > 5:
                cb = ttk.Combobox(f, values=globals()[vars[i][5]], name=varName)
                cb.set(vars[i][1])
                cb.grid(row=i + 1, column=1, sticky=tk.NSEW)
            else:
                ent = ttk.Entry(f, name=varName)
                ent.insert(0, vars[i][1])
                ent.grid(row=i + 1, column=1, sticky=tk.NSEW)
            lab = ttk.Label(f, text=vars[i][2], relief=tk.RIDGE)
            lab.grid(row=i + 1, column=2, sticky=tk.NSEW)
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=2)
        f.columnconfigure(2, weight=1)
        return f

    def ReloadFrame(self, f, vars):
        """Helper function to recreate the GUI page controls and load them with values

        Args:
          f (Frame): the GUI page to reload
          vars (dict): the section of case configuration with values to be loaded
        """
        for i in range(len(vars)):
            ent = f.grid_slaves(row=i + 1, column=1)[0]
            ent.delete(0, tk.END)
            ent.insert(0, vars[i][1])

    def mcSample(self, var):
        """Return an appropriate random value for each Monte Carlo variable choice

        Args:
          var (str): one of ElectricCoolingParticipation, ThermostatRampMid, ThermostatOffsetLimitMid, WeekdayEveningStartMid or WeekdayEveningSetMid
        """
        if var == 'ElectricCoolingParticipation':
            return '{:.3f}'.format(np.random.uniform(0, 100))
        elif var == 'ThermostatRampMid':
            return '{:.3f}'.format(np.random.uniform(1.0, 4.0))
        elif var == 'ThermostatOffsetLimitMid':
            return '{:.3f}'.format(np.random.uniform(0, 6.0))
        elif var == 'WeekdayEveningStartMid':
            return '{:.3f}'.format(np.random.uniform(16.5, 18.0))
        elif var == 'WeekdayEveningSetMid':
            return '{:.3f}'.format(np.random.uniform(68.0, 74.0))
        else:
            return '{:.3f}'.format(np.random.uniform(0, 1))

    def mcBand(self, var):
        """Find the band size corresponding to each Monte Carlo variable choice

        Args:
          var (str): one of ElectricCoolingParticipation, ThermostatRampMid, ThermostatOffsetLimitMid, WeekdayEveningStartMid or WeekdayEveningSetMid
        """
        if var == 'ElectricCoolingParticipation':
            return 10.0
        elif var == 'ThermostatRampMid':
            return 0.5
        elif var == 'ThermostatOffsetLimitMid':
            return 2.0
        elif var == 'WeekdayEveningStartMid':
            return 1.0
        elif var == 'WeekdayEveningSetMid':
            return 1.0
        else:
            return 0.0

    def SizeMonteCarlo(self, n):
        """Initializes the Monte Carlo data structures with variable choices and samples

        Args:
          n (int): the number of Monte Carlo shots
        """
        var1 = config['MonteCarloCase']['Variable1']
        var2 = config['MonteCarloCase']['Variable2']
        var3 = config['MonteCarloCase']['Variable3']
        config['MonteCarloCase']['NumCases'] = n
        config['MonteCarloCase']['Band1'] = self.mcBand(var1)
        config['MonteCarloCase']['Band2'] = self.mcBand(var2)
        config['MonteCarloCase']['Band3'] = self.mcBand(var3)
        config['MonteCarloCase']['Samples1'] = [0] * n
        config['MonteCarloCase']['Samples2'] = [0] * n
        config['MonteCarloCase']['Samples3'] = [0] * n
        for i in range(n):
            config['MonteCarloCase']['Samples1'][i] = self.mcSample(var1)
            config['MonteCarloCase']['Samples2'][i] = self.mcSample(var2)
            config['MonteCarloCase']['Samples3'][i] = self.mcSample(var3)

    def InitializeMonteCarlo(self, n):
        """Makes default variable choices and then initializes the Monte Carlo GUI page

        Args:
          n (int): the number of Monte Carlo shots
        """
        config['MonteCarloCase']['Variable1'] = monteCarloChoices[1]
        config['MonteCarloCase']['Variable2'] = monteCarloChoices[2]
        config['MonteCarloCase']['Variable3'] = monteCarloChoices[3]
        self.SizeMonteCarlo(n)

    # row 0 for dropdowns, 1 for update controls, 2 for column headers, 3 for range edits
    def SizeMonteCarloFrame(self, f):
        """Update the Monte Carlo page to match the number of shots and variables

        Args:
          f (Frame): the Monte Carlo GUI page
        """
        startRow = 3
        for w in f.grid_slaves():
            if int(w.grid_info()['row']) > 2:
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

        n = int(config['MonteCarloCase']['NumCases'])
        for i in range(n):
            lab = ttk.Label(f, text=str(i + 1), relief=tk.RIDGE)
            lab.grid(row=i + 2 + startRow, column=0, sticky=tk.NSEW)
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
            w1.grid(row=i + 2 + startRow, column=1, sticky=tk.NSEW)
            w2.grid(row=i + 2 + startRow, column=2, sticky=tk.NSEW)
            w3.grid(row=i + 2 + startRow, column=3, sticky=tk.NSEW)

    def ReadFrame(self, f, vars):
        """Helper function that reads values from gridded GUI controls into the local case configuration

        Args:
          f (Frame): the GUI page to read
          vars (dict): the local data structure to update
        """
        for w in f.grid_slaves():
            col = int(w.grid_info()['column'])
            row = int(w.grid_info()['row'])
            if col == 1 and row > 0 and row <= len(vars):
                val = w.get()
                try:
                    tmp = int(val)
                    val = tmp
                except:
                    try:
                        tmp = float(val)
                        val = tmp
                    except:
                        pass
                section = vars[row - 1][3]
                attribute = vars[row - 1][4]
                config[section][attribute] = val

    def UpdateEMS(self, event):
        emsFile = 'emsFNCS/ems' + self.bldg_cb.get()
        self.update_entry(self.bldg_ems, emsFile)

    def update_entry(self, ctl, val):
        ctl.delete(0, tk.END)
        ctl.insert(0, val)

    def ReadLatLong(self):
        """Updates the Latitude and Longitude from TMY3 file
        """
        weatherpath = self.path_ent.get()
        weatherfile = self.tmy3_ent.get()
        fname = weather_path + weatherfile
        if os.path.isfile(fname):
            fd = open(fname, 'r')
            rd = csv.reader(fd, delimiter=',', skipinitialspace=True)
            row = next(rd)
            tmy3source = row[0]
            tmy3station = row[1]
            tmy3state = row[2]
            tmy3tzoffset = float(row[3])
            tmy3latitude = float(row[4])
            tmy3longitude = float(row[5])
            tmy3altitude = float(row[6])
            self.update_entry(self.tz_ent, tmy3tzoffset)
            self.update_entry(self.lat_ent, tmy3latitude)
            self.update_entry(self.long_ent, tmy3longitude)
            self.update_entry(self.alt_ent, tmy3altitude)
            fd.close()
        else:
            print(fname, 'not found')

    def SaveConfig(self):
        """Updates the local case configuration from the GUI, queries user for a file name, and then saves case configuration to that file
        """
        self.ReadFrame(self.f1, varsTM)
        self.ReadFrame(self.f2, varsFD)
        self.ReadFrame(self.f3, varsPP)
        self.ReadFrame(self.f4, varsEP)
        self.ReadFrame(self.f5, varsAC)
        self.ReadFrame(self.f6, varsTS)

        col1 = self.f7.children['cb1'].get()
        col2 = self.f7.children['cb2'].get()
        col3 = self.f7.children['cb3'].get()
        config['MonteCarloCase']['Variable1'] = col1
        config['MonteCarloCase']['Variable2'] = col2
        config['MonteCarloCase']['Variable3'] = col3
        use1 = col1 != 'None'
        use2 = col2 != 'None'
        use3 = col3 != 'None'
        band1 = 'Mid' in col1
        band2 = 'Mid' in col2
        band3 = 'Mid' in col3
        numCases = int(
            self.f7.children['rows'].get())  # what if user changed entry and didn't click Update...global numCases?
        for w in self.f7.grid_slaves():
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
                    config['MonteCarloCase']['Samples1'][row - 5] = val
                if col == 2 and use2:
                    val = float(w.get())
                    config['MonteCarloCase']['Samples2'][row - 5] = val
                if col == 3 and use3:
                    val = float(w.get())
                    config['MonteCarloCase']['Samples3'][row - 5] = val
        if not os.path.exists(tesp_share):
            if not messagebox.askyesno('Continue to Save?', 'TESP Support Directory: ' + tesp_share + ' not found.'):
                return
        fname = filedialog.asksaveasfilename(initialdir='~/src/examples/te30',
                                             title='Save JSON Configuration to',
                                             defaultextension='json')
        if len(fname) > 0:
            op = open(fname, 'w')
            json.dump(config, op, ensure_ascii=False, indent=2)
            op.close()

    def JsonToSection(self, jsn, vars):
        """Helper function that transfers a JSON file segment into GUI data structures

        Args:
          jsn (dict): the loaded JSON file
          vars (dict): the local data structure
        """
        for i in range(len(vars)):
            section = vars[i][3]
            attribute = vars[i][4]
            vars[i][1] = jsn[section][attribute]
            config[section][attribute] = jsn[section][attribute]

    def OpenConfig(self):
        """Opens a JSON case configuration; transfers its data to the GUI
        """
        fname = filedialog.askopenfilename(initialdir='~/src/examples/te30',
                                           title='Open JSON Configuration',
                                           filetypes=(("JSON files", "*.json"), ("all files", "*.*")),
                                           defaultextension='json')
        lp = open(fname)
        cfg = json.loads(lp.read())
        lp.close()
        self.JsonToSection(cfg, varsTM)
        self.JsonToSection(cfg, varsFD)
        self.JsonToSection(cfg, varsPP)
        self.JsonToSection(cfg, varsEP)
        self.JsonToSection(cfg, varsAC)
        self.JsonToSection(cfg, varsTS)
        self.ReloadFrame(self.f1, varsTM)
        self.ReloadFrame(self.f2, varsFD)
        self.ReloadFrame(self.f3, varsPP)
        self.ReloadFrame(self.f4, varsEP)
        self.ReloadFrame(self.f5, varsAC)
        self.ReloadFrame(self.f6, varsTS)

        numCases = int(cfg['MonteCarloCase']['NumCases'])
        config['MonteCarloCase']['NumCases'] = numCases
        ent = self.f7.children['rows']
        ent.delete(0, tk.END)
        ent.insert(0, str(numCases))

        var1 = cfg['MonteCarloCase']['Variable1']
        config['MonteCarloCase']['Variable1'] = var1
        self.f7.children['cb1'].set(var1)

        var2 = cfg['MonteCarloCase']['Variable2']
        config['MonteCarloCase']['Variable2'] = var2
        self.f7.children['cb2'].set(var2)

        var3 = cfg['MonteCarloCase']['Variable3']
        config['MonteCarloCase']['Variable3'] = var3
        self.f7.children['cb3'].set(var3)

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

        self.SizeMonteCarloFrame(self.f7)

    def UpdateMonteCarloFrame(self):
        """Transfer data from the Monte Carlo page into the case configuration
        """
        numCases = int(self.f7.children['rows'].get())
        config['MonteCarloCase']['Variable1'] = self.f7.children['cb1'].get()
        config['MonteCarloCase']['Variable2'] = self.f7.children['cb2'].get()
        config['MonteCarloCase']['Variable3'] = self.f7.children['cb3'].get()
        self.SizeMonteCarlo(numCases)
        self.SizeMonteCarloFrame(self.f7)


def show_tesp_config():
    """Runs the GUI. Reads and writes JSON case configuration files.
    """
    root = tk.Tk()
    root.title('Transactive Energy Simulation Platform: Case Configuration')
    varsTM[varsTMSupportDirIndex][1] = tesp_share
    my_gui = TespConfigGUI(root)
    while True:
        try:
            root.mainloop()
            break
        except UnicodeDecodeError:
            pass


if __name__ == "__main__":
    show_tesp_config()
