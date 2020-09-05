# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: tesp_case.py
"""Creates and fills a subdirectory with files to run a TESP simulation

Use *tesp_config* to graphically edit the case configuration

Public Functions:
    :make_tesp_case: sets up for a single-shot TESP case
    :make_monte_carlo_cases: sets up for a Monte Carlo TESP case of up to 20 shots
    :first_tesp_feeder: customization of make_tesp_case that will accept more feeders
    :add_tesp_feeder: add another feeder to the case directory created by first_tesp_feeder
"""
import sys
import json
import subprocess
import os
import stat
import shutil
from datetime import datetime
import tesp_support.helpers as helpers
import tesp_support.make_ems as idf

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'

def write_tesp_case (config, cfgfile, freshdir = True):
    """Writes the TESP case from data structure to JSON file

    This function assumes one GridLAB-D, one EnergyPlus, one PYPOWER
    and one substation_loop federate will participate in the TESP simulation.
    See the DSO+T study functions, which are customized to ERCOT 8-bus and 
    200-bus models, for examples of other configurations.

    The TESP support directories, working directory and case name are all specified 
    in *config*. This function will create one directory as follows:

        * workdir = config['SimulationConfig']['WorkingDirectory']
        * casename = config['SimulationConfig']['CaseName']
        * new directory created will be *casedir* = workdir/casename

    This function will read or copy several files that are specified in the *config*.
    They should all exist. These include taxonomy feeders, GridLAB-D schedules, 
    weather files, a base EnergyPlus model, a base PYPOWER model, and supporting scripts
    for the end user to invoke from the *casedir*.  The user could add more base model files
    weather files or schedule files under the TESP support directory, where this *tesp_case*
    module will be able to find and use them.

    This function will launch and wait for 6 subprocesses to assist in the 
    case configuration. All must execute successfully:

        * TMY3toTMY2_ansi, which converts the user-selected TMY3 file to TMY2
        * tesp.convert_tmy2_to_epw, which converts the TMY2 file to EPW for EnergyPlus
        * tesp.TMY3toCSV, which converts the TMY3 file to CSV for the weather agent
        * tesp.populate_feeder, which populates the user-selected taxonomy feeder with houses and DER
        * tesp.glm_dict, which creates metadata for the populated feeder
        * tesp.prep_substation, which creates metadata and FNCS configurations for the substation agents

    As the configuration process finishes, several files are written to *casedir*:

        * Casename.glm: the GridLAB-D model, copied and modified from the TESP support directory
        * Casename_FNCS_Config.txt: FNCS subscriptions and publications, included by Casename.glm
        * Casename_agent_dict.json: metadata for the simple_auction and hvac agents
        * Casename_glm_dict.json: metadata for Casename.glm
        * Casename_pp.json: the PYPOWER model, copied and modified from the TESP support directory
        * Casename_substation.yaml: FNCS subscriptions and time step for the substation, which manages the simple_auction and hvac controllers
        * NonGLDLoad.txt: non-responsive load data for the PYPOWER model buses, currently hard-wired for the 9-bus model. See the ERCOT case files for examples of expanded options.
        * SchoolDualController.idf: the EnergyPlus model, copied and modified from the TESP support directory 
        * WA-Yakima_Air_Terminal.epw: the selected weather file for EnergyPlus, others can be selected
        * WA-Yakima_Air_Terminal.tmy3: the selected weather file for GridLAB-D, others can be selected
        * appliance_schedules.glm: time schedules for GridLAB-D
        * clean.sh: Linux/Mac OS X helper to clean up simulation outputs
        * commercial_schedules.glm: non-responsive non-responsive time schedules for GridLAB-D, invariant
        * eplus.yaml: FNCS subscriptions and time step for EnergyPlus
        * eplus_agent.yaml: FNCS subscriptions and time step for the EnergyPlus agent
        * kill5570.sh: Linux/Mac OS X helper to kill all federates listening on port 5570
        * launch_auction.py: helper script for the GUI solution monitor to launch the substation federate
        * launch_pp.py: helper script for the GUI solution monitor to launch the PYPOWER federate
        * monitor.py: helper to launch the GUI solution monitor (FNCS_CONFIG_FILE envar must be set for this process, see gui.sh under examples/te30)
        * plots.py: helper script that will plot a selection of case outputs
        * pypower.yaml: FNCS subscriptions and time step for PYPOWER
        * run.sh: Linux/Mac OS X helper to launch the TESP simulation
        * tesp_monitor.json: shell commands and other configuration data for the solution monitor GUI
        * tesp_monitor.yaml: FNCS subscriptions and time step for the solution monitor GUI
        * water_and_setpoint_schedule_v5.glm: non-responsive time schedules for GridLAB-D, invariant
        * weather.dat: CSV file of temperature, pressure, humidity, solar direct, solar diffuse and wind speed

    Args:
        config (dict): the complete case data structure
        cfgfile (str): the name of the JSON file that was read
        freshdir (boolean): flag to create the directory and base files anew

    Todo:
        * Write gui.sh, per the te30 examples
    """
    tespdir = os.path.expandvars (os.path.expanduser (config['SimulationConfig']['SourceDirectory']))
    feederdir = tespdir + '/feeders/'
    scheduledir = tespdir + '/schedules/'
    weatherdir = tespdir + '/weather/'
    eplusdir = tespdir + '/energyplus/'
    ppdir = tespdir + '/pypower/'
    miscdir = tespdir + '/misc/'
    print ('feeder backbone files from', feederdir)
    print ('schedule files from', scheduledir)
    print ('weather files from', weatherdir)
    print ('E+ files from', eplusdir)
    print ('pypower backbone files from', ppdir)

    casename = config['SimulationConfig']['CaseName']
    workdir = config['SimulationConfig']['WorkingDirectory']
    if len(workdir) > 2:
        casedir = workdir
    else:
        casedir = workdir + casename
    glmroot = config['BackboneFiles']['TaxonomyChoice']
    print ('case files written to', casedir)

    if freshdir == True:
        if os.path.exists(casedir):
            shutil.rmtree(casedir)
        os.makedirs(casedir)

    StartTime = config['SimulationConfig']['StartTime']
    EndTime = config['SimulationConfig']['EndTime']
    time_fmt = '%Y-%m-%d %H:%M:%S'
    dt1 = datetime.strptime (StartTime, time_fmt)
    dt2 = datetime.strptime (EndTime, time_fmt)
    seconds = int ((dt2 - dt1).total_seconds())
    days = seconds / 86400
    WeatherYear = dt1.year
    print ('run', days, 'days or', seconds, 'seconds in weather year', WeatherYear)

    (rootweather, weatherext) = os.path.splitext(config['WeatherPrep']['DataSource'])
    EpRef = config['EplusConfiguration']['ReferencePrice']
    EpRamp = config['EplusConfiguration']['Slope']
    EpLimHi = config['EplusConfiguration']['OffsetLimitHi']
    EpLimLo = config['EplusConfiguration']['OffsetLimitLo']
    EpWeather = rootweather + '.epw' # config['EplusConfiguration']['EnergyPlusWeather']
    EpStepsPerHour = int (config['EplusConfiguration']['StepsPerHour'])
    EpBuilding = config['EplusConfiguration']['BuildingChoice']
    EpEMS = config['EplusConfiguration']['EMSFile']
    EpXfmrKva = config['EplusConfiguration']['EnergyPlusXfmrKva']
    EpVolts = config['EplusConfiguration']['EnergyPlusServiceV']
    EpBus = config['EplusConfiguration']['EnergyPlusBus']
    EpMetricsKey = EpBuilding # os.path.splitext (EpFile)[0]
    EpAgentStop = str (seconds) + 's'
    EpStep = int (60 / EpStepsPerHour) # minutes
    EpAgentStep = str(int (60 / EpStepsPerHour)) + 'm'
    EpMetricsFile = 'eplus_' + casename + '_metrics.json'
    GldFile = casename + '.glm'
    GldMetricsFile = casename + '_metrics.json'
    AgentDictFile = casename + '_agent_dict.json'
    PPJsonFile = casename + '_pp.json'
    SubstationYamlFile = casename + '_substation.yaml'
    WeatherConfigFile = casename + '_FNCS_Weather_Config.json'

    weatherfile = weatherdir + rootweather + '.tmy3'
    eplusfile = eplusdir + EpBuilding + '.idf'
    emsfile = eplusdir + EpEMS + '.idf'
    eplusout = casedir + '/Merged.idf'
    eplusoutFNCS = casedir + '/MergedFNCS.idf'
    ppfile = ppdir + config['BackboneFiles']['PYPOWERFile']
    ppcsv = ppdir + config['PYPOWERConfiguration']['CSVLoadFile']

    # copy some boilerplate files
    if freshdir == True:
#        shutil.copy (miscdir + 'clean.bat', casedir)
#        shutil.copy (miscdir + 'kill5570.bat', casedir)
#        shutil.copy (miscdir + 'killold.bat', casedir)
#        shutil.copy (miscdir + 'list5570.bat', casedir)
        shutil.copy (miscdir + 'clean.sh', casedir)
        shutil.copy (miscdir + 'kill5570.sh', casedir)
        shutil.copy (miscdir + 'kill23404.sh', casedir)
        shutil.copy (miscdir + 'killboth.sh', casedir)
        shutil.copy (miscdir + 'monitor.py', casedir)
        shutil.copy (miscdir + 'plots.py', casedir)
        shutil.copy (scheduledir + 'appliance_schedules.glm', casedir)
        shutil.copy (scheduledir + 'commercial_schedules.glm', casedir)
        shutil.copy (scheduledir + 'water_and_setpoint_schedule_v5.glm', casedir)
    #    shutil.copy (weatherfile, casedir)
        # process TMY3 ==> weather.dat
        cmdline = pycall + """ -c "import tesp_support.api as tesp;tesp.weathercsv('""" + weatherfile + """','""" + casedir + '/weather.dat' + """','""" + StartTime + """','""" + EndTime + """',""" + str(WeatherYear) + """)" """
        print (cmdline)
    #    quit()
        pw0 = subprocess.Popen (cmdline, shell=True)
        pw0.wait()

    #########################################
    # set up EnergyPlus, if the user wants it
    bUseEplus = False
    if len(EpBus) > 0:
        bUseEplus = True
        idf.merge_idf (eplusfile, emsfile, StartTime, EndTime, eplusout, EpStepsPerHour)
        if 'emsHELICS' in emsfile: # legacy support of FNCS for the built-in EMS library
          emsfileFNCS = emsfile.replace ('emsHELICS', 'emsFNCS')
          idf.merge_idf (eplusfile, emsfileFNCS, StartTime, EndTime, eplusoutFNCS, EpStepsPerHour)

        # process TMY3 ==> TMY2 ==> EPW
        cmdline = 'TMY3toTMY2_ansi ' + weatherfile + ' > ' + casedir + '/' + rootweather + '.tmy2'
        print (cmdline)
        pw1 = subprocess.Popen (cmdline, shell=True)
        pw1.wait()
        cmdline = pycall + """ -c "import tesp_support.api as tesp;tesp.convert_tmy2_to_epw('""" + casedir + '/' + rootweather + """')" """
        print (cmdline)
        pw2 = subprocess.Popen (cmdline, shell=True)
        pw2.wait()
        os.remove (casedir + '/' + rootweather + '.tmy2')

        # write the EnergyPlus YAML files 
        op = open (casedir + '/eplus.yaml', 'w')
        print ('name: eplus', file=op)
        print ('time_delta:', str (EpStep) + 'm', file=op)
        print ('broker: tcp://localhost:5570', file=op)
        print ('values:', file=op)
        print ('    COOL_SETP_DELTA:', file=op)
        print ('        topic: eplus_agent/cooling_setpoint_delta', file=op)
        print ('        default: 0', file=op)
        print ('    HEAT_SETP_DELTA:', file=op)
        print ('        topic: eplus_agent/heating_setpoint_delta', file=op)
        print ('        default: 0', file=op)
        op.close()

        epjyamlstr = """name: eplus_agent
time_delta: """ + str(EpAgentStep) + """
broker: tcp://localhost:5570
values:
    kwhr_price:
        topic: sub1/clear_price
        default: 0.10
    indoor_air:
        topic: eplus/EMS INDOOR AIR TEMPERATURE
        default: 0
    outdoor_air:
        topic: eplus/ENVIRONMENT SITE OUTDOOR AIR DRYBULB TEMPERATURE
        default: 0
    cooling_volume:
        topic: eplus/EMS COOLING VOLUME
        default: 0
    heating_volume:
        topic: eplus/EMS HEATING VOLUME
        default: 0
    cooling_controlled_load:
        topic: eplus/EMS COOLING CONTROLLED LOAD
        default: 0
    cooling_schedule_temperature:
        topic: eplus/EMS COOLING SCHEDULE TEMPERATURE
        default: 0
    cooling_setpoint_temperature:
        topic: eplus/EMS COOLING SETPOINT TEMPERATURE
        default: 0
    cooling_current_temperature:
        topic: eplus/EMS COOLING CURRENT TEMPERATURE
        default: 0
    cooling_power_state:
        topic: eplus/EMS COOLING POWER STATE
        default: 0
    heating_controlled_load:
        topic: eplus/EMS HEATING CONTROLLED LOAD
        default: 0
    heating_schedule_temperature:
        topic: eplus/EMS HEATING SCHEDULE TEMPERATURE
        default: 0
    heating_setpoint_temperature:
        topic: eplus/EMS HEATING SETPOINT TEMPERATURE
        default: 0
    heating_current_temperature:
        topic: eplus/EMS HEATING CURRENT TEMPERATURE
        default: 0
    heating_power_state:
        topic: eplus/EMS HEATING POWER STATE
        default: 0
    electric_demand_power:
        topic: eplus/WHOLE BUILDING FACILITY TOTAL ELECTRIC DEMAND POWER
        default: 0
    hvac_demand_power:
        topic: eplus/WHOLE BUILDING FACILITY TOTAL HVAC ELECTRIC DEMAND POWER
        default: 0
    ashrae_uncomfortable_hours:
        topic: eplus/FACILITY FACILITY THERMAL COMFORT ASHRAE 55 SIMPLE MODEL SUMMER OR WINTER CLOTHES NOT COMFORTABLE TIME
        default: 0
    occupants_total:
        topic: eplus/EMS OCCUPANT COUNT
        default: 0
"""
        op = open (casedir + '/eplus_agent.yaml', 'w')
        print (epjyamlstr, file=op)
        op.close()

        epSubs = []
        epSubs.append ({"key": "eplus_agent/cooling_setpoint_delta","type": "double","required":True})
        epSubs.append ({"key": "eplus_agent/heating_setpoint_delta","type": "double","required":True})
        epPubs = []
        epPubs.append ({"global":False, "key":"EMS Cooling Controlled Load", "type":"double", "unit":"kWh"})
        epPubs.append ({"global":False, "key":"EMS Heating Controlled Load", "type":"double", "unit":"kWh"})
        epPubs.append ({"global":False, "key":"EMS Cooling Schedule Temperature", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS Heating Schedule Temperature", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS Cooling Setpoint Temperature", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS Heating Setpoint Temperature", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS Cooling Current Temperature", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS Heating Current Temperature", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS Cooling Power State", "type":"string"})
        epPubs.append ({"global":False, "key":"EMS Heating Power State", "type":"string"})
        epPubs.append ({"global":False, "key":"EMS Cooling Volume", "type":"double", "unit":"stere"})
        epPubs.append ({"global":False, "key":"EMS Heating Volume", "type":"double", "unit":"stere"})
        epPubs.append ({"global":False, "key":"EMS Occupant Count", "type":"int", "unit":"count"})
        epPubs.append ({"global":False, "key":"EMS Indoor Air Temperature", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"WHOLE BUILDING Facility Total Electric Demand Power", "type":"double", "unit":"W"})
        epPubs.append ({"global":False, "key":"WHOLE BUILDING Facility Total HVAC Electric Demand Power", "type":"double", "unit":"W"})
        epPubs.append ({"global":False, "key":"FACILITY Facility Thermal Comfort ASHRAE 55 Simple Model Summer or Winter Clothes Not Comfortable Time", "type":"double", "unit":"hour"})
        epPubs.append ({"global":False, "key":"Environment Site Outdoor Air Drybulb Temperature", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS HEATING SETPOINT", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS HEATING CURRENT", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS COOLING SETPOINT", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"EMS COOLING CURRENT", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"H2_NOM SCHEDULE_VALUE", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"H1_NOM SCHEDULE_VALUE", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"C2_NOM SCHEDULE_VALUE", "type":"double", "unit":"degC"})
        epPubs.append ({"global":False, "key":"C1_NOM SCHEDULE_VALUE", "type":"double", "unit":"degC"})
        epConfig = {}
        epConfig["name"] = "energyPlus"
        epConfig["period"] = 60 * EpStep
        epConfig["loglevel"] = 4
        epConfig["publications"] = epPubs
        epConfig["subscriptions"] = epSubs
        op = open (casedir + '/eplus.json', 'w', encoding='utf-8')
        json.dump (epConfig, op, ensure_ascii=False, indent=2)
        op.close()

        epaSubs = []
        epaSubs.append ({"key": "sub1/clear_price","type": "double","required":True,"info":"kwhr_price"})
        epaSubs.append ({"key": "energyPlus/EMS Heating Controlled Load","type": "double","required":True,"info":"heating_controlled_load"})
        epaSubs.append ({"key": "energyPlus/EMS Cooling Controlled Load","type": "double","required":True,"info":"cooling_controlled_load"})
        epaSubs.append ({"key": "energyPlus/EMS Cooling Schedule Temperature","type": "double","required":True,"info":"cooling_schedule_temperature"})
        epaSubs.append ({"key": "energyPlus/EMS Heating Schedule Temperature","type": "double","required":True,"info":"heating_schedule_temperature"})
        epaSubs.append ({"key": "energyPlus/EMS Cooling Setpoint Temperature","type": "double","required":True,"info":"cooling_setpoint_temperature"})
        epaSubs.append ({"key": "energyPlus/EMS Heating Setpoint Temperature","type": "double","required":True,"info":"heating_setpoint_temperature"})
        epaSubs.append ({"key": "energyPlus/EMS Cooling Current Temperature","type": "double","required":True,"info":"cooling_current_temperature"})
        epaSubs.append ({"key": "energyPlus/EMS Heating Current Temperature","type": "double","required":True,"info":"heating_current_temperature"})
        epaSubs.append ({"key": "energyPlus/EMS Cooling Power State","type": "string","required":True,"info":"cooling_power_state"})
        epaSubs.append ({"key": "energyPlus/EMS Heating Power State","type": "string","required":True,"info":"heating_power_state"})
        epaSubs.append ({"key": "energyPlus/EMS Cooling Volume","type": "double","required":True,"info":"cooling_volume"})
        epaSubs.append ({"key": "energyPlus/EMS Heating Volume","type": "double","required":True,"info":"heating_volume"})
        epaSubs.append ({"key": "energyPlus/EMS Occupant Count","type": "int","required":True,"info":"occupants_total"})
        epaSubs.append ({"key": "energyPlus/EMS Indoor Air Temperature","type": "double","required":True,"info":"indoor_air"})
        epaSubs.append ({"key": "energyPlus/WHOLE BUILDING Facility Total Electric Demand Power","type": "double","required":True,"info":"electric_demand_power"})
        epaSubs.append ({"key": "energyPlus/WHOLE BUILDING Facility Total HVAC Electric Demand Power","type": "double","required":True,"info":"hvac_demand_power"})
        epaSubs.append ({"key": "energyPlus/FACILITY Facility Thermal Comfort ASHRAE 55 Simple Model Summer or Winter Clothes Not Comfortable Time","type": "double","required":True,"info":"ashrae_uncomfortable_hours"})
        epaSubs.append ({"key": "energyPlus/Environment Site Outdoor Air Drybulb Temperature","type": "double","required":True,"info":"outdoor_air"})
        epaPubs = []
        epaPubs.append ({"global":False, "key":"power_A", "type":"double", "unit":"W"})
        epaPubs.append ({"global":False, "key":"power_B", "type":"double", "unit":"W"})
        epaPubs.append ({"global":False, "key":"power_C", "type":"double", "unit":"W"})
        epaPubs.append ({"global":False, "key":"bill_mode", "type":"string"})
        epaPubs.append ({"global":False, "key":"price", "type":"double", "unit":"$/kwh"})
        epaPubs.append ({"global":False, "key":"monthly_fee", "type":"double", "unit":"$"})
        epaPubs.append ({"global":False, "key":"cooling_setpoint_delta", "type":"double", "unit":"degC"})
        epaPubs.append ({"global":False, "key":"heating_setpoint_delta", "type":"double", "unit":"degC"})
        epaConfig = {}
        epaConfig["name"] = "eplus_agent"
        epaConfig["period"] = 60 * EpStep
        epaConfig["loglevel"] = 4
        epaConfig["time_delta"] = 1
        epaConfig["uninterruptible"] = False
        epaConfig["subscriptions"] = epaSubs
        epaConfig["publications"] = epaPubs
        op = open (casedir + '/eplus_agent.json', 'w', encoding='utf-8')
        json.dump (epaConfig, op, ensure_ascii=False, indent=2)
        op.close()

    ###################################
    # dynamically import the base PYPOWER case
    import importlib.util
    spec = importlib.util.spec_from_file_location('ppbasecase', ppfile)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ppcase = mod.ppcasefile()
    #print (ppcase)

    # make ppcase JSON serializable
    ppcase['bus'] = ppcase['bus'].tolist()
    ppcase['gen'] = ppcase['gen'].tolist()
    ppcase['branch'] = ppcase['branch'].tolist()
    ppcase['areas'] = ppcase['areas'].tolist()
    ppcase['gencost'] = ppcase['gencost'].tolist()
    ppcase['DSO'] = ppcase['DSO'].tolist()
    ppcase['UnitsOut'] = ppcase['UnitsOut'].tolist()
    ppcase['BranchesOut'] = ppcase['BranchesOut'].tolist()

    # update the case from config JSON
    ppcase['StartTime'] = config['SimulationConfig']['StartTime']
    ppcase['Tmax'] = int(seconds)
    ppcase['Period'] = config['AgentPrep']['MarketClearingPeriod']
    ppcase['dt'] = config['PYPOWERConfiguration']['PFStep']
    ppcase['CSVFile'] = config['PYPOWERConfiguration']['CSVLoadFile']
    if config['PYPOWERConfiguration']['ACOPF'] == 'AC':
        ppcase['opf_dc'] = 0
    else:
        ppcase['opf_dc'] = 1
    if config['PYPOWERConfiguration']['ACPF'] == 'AC':
        ppcase['pf_dc'] = 0
    else:
        ppcase['pf_dc'] = 1
    fncsBus = int (config['PYPOWERConfiguration']['GLDBus'])
    fncsScale = float (config['PYPOWERConfiguration']['GLDScale'])
    ppcase['DSO'][0][0] = fncsBus
    ppcase['DSO'][0][2] = fncsScale
    baseKV = float(config['PYPOWERConfiguration']['TransmissionVoltage'])
    for row in ppcase['bus']:
        if row[0] == fncsBus:
            row[9] = baseKV

    if len(config['PYPOWERConfiguration']['UnitOutStart']) > 0 and len(config['PYPOWERConfiguration']['UnitOutEnd']) > 0:
        dt3 = datetime.strptime (config['PYPOWERConfiguration']['UnitOutStart'], time_fmt)
        tout_start = int ((dt3 - dt1).total_seconds())
        dt3 = datetime.strptime (config['PYPOWERConfiguration']['UnitOutEnd'], time_fmt)
        tout_end = int ((dt3 - dt1).total_seconds())
        ppcase['UnitsOut'][0] = [int(config['PYPOWERConfiguration']['UnitOut']), tout_start, tout_end]
    else:
        ppcase['UnitsOut'] = []

    if len(config['PYPOWERConfiguration']['BranchOutStart']) > 0 and len(config['PYPOWERConfiguration']['BranchOutEnd']) > 0:
        dt3 = datetime.strptime (config['PYPOWERConfiguration']['BranchOutStart'], time_fmt)
        tout_start = int ((dt3 - dt1).total_seconds())
        dt3 = datetime.strptime (config['PYPOWERConfiguration']['BranchOutEnd'], time_fmt)
        tout_end = int ((dt3 - dt1).total_seconds())
        ppcase['BranchesOut'][0] = [int(config['PYPOWERConfiguration']['BranchOut']), tout_start, tout_end]
    else:
        ppcase['BranchesOut'] = []

    fp = open (casedir + '/' + casename + '_pp.json', 'w')
    json.dump (ppcase, fp, indent=2)
    fp.close ()

    ppyamlstr = """name: pypower
time_delta: """ + str(config['PYPOWERConfiguration']['PFStep']) + """s
broker: tcp://localhost:5570
values:
    SUBSTATION7:
        topic: gld1/distribution_load
        default: 0
    UNRESPONSIVE_MW:
        topic: sub1/unresponsive_mw
        default: 0
    RESPONSIVE_MAX_MW:
        topic: sub1/responsive_max_mw
        default: 0
    RESPONSIVE_C2:
        topic: sub1/responsive_c2
        default: 0
    RESPONSIVE_C1:
        topic: sub1/responsive_c1
        default: 0
    RESPONSIVE_DEG:
        topic: sub1/responsive_deg
        default: 0
"""
    if freshdir == True:
        shutil.copy (ppcsv, casedir)
        op = open (casedir + '/pypower.yaml', 'w')
        print (ppyamlstr, file=op)
        op.close()
        ppSubs = []
        ppSubs.append ({"name": "SUBSTATION7","key": "gld1/distribution_load","type": "complex"})
        ppSubs.append ({"name": "UNRESPONSIVE_MW","key": "sub1/unresponsive_mw","type": "double"})
        ppSubs.append ({"name": "RESPONSIVE_MAX_MW","key": "sub1/responsive_max_mw","type": "double"})
        ppSubs.append ({"name": "RESPONSIVE_C1","key": "sub1/responsive_c1","type": "double"})
        ppSubs.append ({"name": "RESPONSIVE_C2","key": "sub1/responsive_c2","type": "double"})
        ppSubs.append ({"name": "RESPONSIVE_DEG","key": "sub1/responsive_deg","type": "integer"})
        ppPubs = []
        ppPubs.append ({"global":False, "key":"three_phase_voltage_B7", "type":"double"})
        ppPubs.append ({"global":False, "key":"LMP_B7", "type":"double"})
        ppConfig = {}
        ppConfig["name"] = "pypower"
        ppConfig["log_level"] = 4
        ppConfig["period"] = int (config['PYPOWERConfiguration']['PFStep'])
        ppConfig["subscriptions"] = ppSubs
        ppConfig["publications"] = ppPubs
        op = open (casedir + '/pypowerConfig.json', 'w', encoding='utf-8')
        json.dump (ppConfig, op, ensure_ascii=False, indent=2)
        op.close()

    # write a YAML for the solution monitor
    tespyamlstr = """name = tesp_monitor
time_delta = """ + str(int(config['AgentPrep']['MarketClearingPeriod'])) + """s
broker: tcp://localhost:5570
aggregate_sub: true
values:
  vpos7:
    topic: pypower/three_phase_voltage_B7
    default: 0
    type: double
    list: false
  LMP7:
    topic: pypower/LMP_B7
    default: 0
    type: double
    list: false
  clear_price:
    topic: sub1/clear_price
    default: 0
    type: double
    list: false
  distribution_load:
    topic: gld1/distribution_load
    default: 0
    type: complex
    list: false
  power_A:
    topic: eplus_agent/power_A
    default: 0
    type: double
    list: false
  electric_demand_power:
    topic: eplus/WHOLE BUILDING FACILITY TOTAL ELECTRIC DEMAND POWER
    default: 0
    type: double
    list: false
"""
    if freshdir == True:
        op = open (casedir + '/tesp_monitor.yaml', 'w')
        print (tespyamlstr, file=op)
        op.close()

    cmdline = pycall + """ -c "import tesp_support.api as tesp;tesp.populate_feeder('""" + cfgfile + """')" """
    print (cmdline)
    p1 = subprocess.Popen (cmdline, shell=True)
    p1.wait()
    glmfile = casedir + '/' + casename

    cmdline = pycall + """ -c "import tesp_support.api as tesp;tesp.glm_dict('""" + glmfile + """')" """
    print (cmdline)
    p2 = subprocess.Popen (cmdline, shell=True)
    p2.wait()

    cmdline = pycall + """ -c "import tesp_support.api as tesp;tesp.prep_substation('""" + glmfile + """','""" + cfgfile + """')" """
    print (cmdline)
    p3 = subprocess.Popen (cmdline, shell=True)
    p3.wait()

    if freshdir == False:
        return

    # FNCS shell scripts and chmod for Mac/Linux - need to specify python3
    aucline = """python3 -c "import tesp_support.api as tesp;tesp.substation_loop('""" + AgentDictFile + """','""" + casename + """')" """
    ppline = """python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('""" + PPJsonFile + """','""" + casename + """')" """
    weatherline = """python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" """

    shfile = casedir + '/run.sh'
    op = open (shfile, 'w')
    if bUseEplus:
        print ('(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 6 &> fncs_broker.log &)', file=op)
        print ('(export FNCS_CONFIG_FILE=eplus.yaml && export FNCS_FATAL=YES && exec energyplus -w ' 
               + EpWeather + ' -d output -r MergedFNCS.idf &> fncs_eplus.log &)', file=op)
        print ('(export FNCS_CONFIG_FILE=eplus_agent.yaml && export FNCS_FATAL=YES && exec eplus_agent', EpAgentStop, EpAgentStep, 
               EpMetricsKey, EpMetricsFile, EpRef, EpRamp, EpLimHi, EpLimLo, '&> fncs_eplus_agent.log &)', file=op)
    else:
        print ('(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 4 &> fncs_broker.log &)', file=op)
    print ('(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS -D METRICS_FILE='
           + GldMetricsFile + ' ' + GldFile + ' &> fncs_gld1.log &)', file=op)
    print ('(export FNCS_CONFIG_FILE=' + SubstationYamlFile + ' && export FNCS_FATAL=YES && exec ' + aucline + ' &> fncs_sub1.log &)', file=op)
    print ('(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec ' + ppline + ' &> fncs_pypower.log &)', file=op)
    print ('(export WEATHER_CONFIG=' + WeatherConfigFile + ' && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec ' + weatherline + ' &> fncs_weather.log &)', file=op)
    op.close()
    st = os.stat (shfile)
    os.chmod (shfile, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shfile = casedir + '/kill5570.sh'
    os.chmod (shfile, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shfile = casedir + '/clean.sh'
    os.chmod (shfile, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # HELICS shell scripts and chmod for Mac/Linux - need to specify python3
    PypowerConfigFile = 'pypowerConfig.json'
    SubstationConfigFile = casename + '_HELICS_substation.json'
    WeatherConfigFile = casename + '_HELICS_Weather_Config.json'
    aucline = """python3 -c "import tesp_support.api as tesp;tesp.substation_loop('""" + AgentDictFile + """','""" + casename + """',helicsConfig='""" + SubstationConfigFile + """')" """
    ppline = """python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('""" + PPJsonFile + """','""" + casename + """',helicsConfig='""" + PypowerConfigFile + """')" """

    shfile = casedir + '/runh.sh'
    op = open (shfile, 'w')
    if bUseEplus:
#      print ('# FNCS federation is energyplus with agent', file=op)
#      print ('#(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 2 &> fncs_broker.log &)', file=op)
#      print ('#(export FNCS_CONFIG_FILE=eplus.yaml && export FNCS_FATAL=YES && exec energyplus -w ' 
#             + EpWeather + ' -d output -r MergedFNCS.idf &> fncs_eplus.log &)', file=op)
#      print ('#(export FNCS_CONFIG_FILE=eplus_agent.yaml && export FNCS_FATAL=YES && exec eplus_agent', EpAgentStop, EpAgentStep, 
#             EpMetricsKey, EpMetricsFile, EpRef, EpRamp, EpLimHi, EpLimLo, 'helics_eplus_agent.json &> dual_eplus_agent.log &)', file=op)
#      print ('# HELICS federation is GridLAB-D, PYPOWER, substation, weather, E+ and E+ agent', file=op)
      print ('(exec helics_broker -f 6 --loglevel=4 --name=mainbroker &> broker.log &)', file=op)
      print ('(export HELICS_CONFIG_FILE=eplus.json && exec energyplus -w ' + EpWeather + ' -d output -r Merged.idf &> eplus.log &)', file=op)
      print ('(exec eplus_agent_helics', EpAgentStop, EpAgentStep, EpMetricsKey, EpMetricsFile, EpRef, EpRamp, EpLimHi, EpLimLo,
             'eplus_agent.json &> eplus_agent.log &)', file=op)
    else:
      print ('(exec helics_broker -f 4 --loglevel=4 --name=mainbroker &> broker.log &)', file=op)
    print ('(exec gridlabd -D USE_HELICS -D METRICS_FILE='+ GldMetricsFile + ' ' + GldFile + ' &> gld1.log &)', file=op)
    print ('(exec ' + aucline + ' &> sub1.log &)', file=op)
    print ('(exec ' + ppline + ' &> pypower.log &)', file=op)
    print ('(export WEATHER_CONFIG=' + WeatherConfigFile + ' && exec ' + weatherline + ' &> weather.log &)', file=op)
    op.close()
    st = os.stat (shfile)
    os.chmod (shfile, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # commands for launching Python federates
    op = open (casedir + '/launch_auction.py', 'w')
    print ('import tesp_support.api as tesp', file=op)
    print ('tesp.substation_loop(\'' + AgentDictFile + '\',\'' + casename + '\')', file=op)
    op.close()
    op = open (casedir + '/launch_pp.py', 'w')
    print ('import tesp_support.api as tesp', file=op)
    print ('tesp.pypower_loop(\'' + PPJsonFile + '\',\'' + casename + '\')', file=op)
    op.close()
    op = open (casedir + '/tesp_monitor.json', 'w')
    cmds = {'time_stop':seconds, 
            'yaml_delta':int(config['AgentPrep']['MarketClearingPeriod']), 
            'commands':[]}
    if bUseEplus:
        cmds['commands'].append({'args':['fncs_broker', '6'], 
                           'env':[['FNCS_BROKER', 'tcp://*:5570'],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                           'log':'broker.log'})
        cmds['commands'].append({'args':['EnergyPlus', '-w', EpWeather, '-d', 'output', '-r', 'MergedFNCS.idf'], 
                           'env':[['FNCS_CONFIG_FILE', 'eplus.yaml'],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                           'log':'eplus.log'})
        cmds['commands'].append({'args':['eplus_agent', EpAgentStop, EpAgentStep, EpMetricsKey, EpMetricsFile, EpRef, EpRamp, EpLimHi, EpLimLo], 
                           'env':[['FNCS_CONFIG_FILE', 'eplus_agent.yaml'],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                           'log':'eplus_agent.log'})
    else:
        cmds['commands'].append({'args':['fncs_broker', '6'], 
                           'env':[['FNCS_BROKER', 'tcp://*:5570'],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                           'log':'broker.log'})
    cmds['commands'].append({'args':['gridlabd', '-D', 'USE_FNCS', '-D', 'METRICS_FILE=' + GldMetricsFile, GldFile], 
                       'env':[['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                       'log':'gld1.log'})
    cmds['commands'].append({'args':[pycall, 'launch_auction.py'], 
                       'env':[['FNCS_CONFIG_FILE', SubstationYamlFile],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                       'log':'sub1.log'})
    cmds['commands'].append({'args':[pycall, 'launch_pp.py'], 
                       'env':[['FNCS_CONFIG_FILE', 'pypower.yaml'],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                       'log':'pypower.log'})
    json.dump (cmds, op, indent=2)
    op.close()

def make_tesp_case (cfgfile = 'test.json'):
    """Wrapper function for a single TESP case configuration.

    This function opens the JSON file, and calls *write_tesp_case*

    Args:
        cfgfile (str): JSON file containing the TESP case configuration
    """
    lp = open (cfgfile).read()
    config = json.loads(lp)
    write_tesp_case (config, cfgfile)

def modify_mc_config (config, mcvar, band, sample):
    """Helper function that modifies the Monte Carlo configuration for a specific sample, i.e., shot

    For variables that have a band associated, the agent preparation code will apply
    additional randomization. This applies to thermostat ramps, offset limits, and
    period starting or ending times. For those variables, the Monte Carlo sample
    value is a mean, and the agent preparation code will apply a uniform distribution
    to obtain the actual value for each house.
    """
    if mcvar == 'ElectricCoolingParticipation':
        config['FeederGenerator'][mcvar] = sample
    elif mcvar == 'ThermostatRampMid':
        config['AgentPrep']['ThermostatRampLo'] = sample - 0.5 * band
        config['AgentPrep']['ThermostatRampHi'] = sample + 0.5 * band
    elif mcvar == 'ThermostatOffsetLimit':
        config['AgentPrep']['ThermostatOffsetLimitLo'] = sample - 0.5 * band
        config['AgentPrep']['ThermostatOffsetLimitHi'] = sample + 0.5 * band
    elif mcvar == 'WeekdayEveningStartMid':
        config['ThermostatSchedule']['WeekdayEveningStartLo'] = sample - 0.5 * band
        config['ThermostatSchedule']['WeekdayEveningStartHi'] = sample + 0.5 * band
    elif mcvar == 'WeekdayEveningSetMid':
        config['ThermostatSchedule']['WeekdayEveningSetLo'] = sample - 0.5 * band
        config['ThermostatSchedule']['WeekdayEveningSetHi'] = sample + 0.5 * band

def make_monte_carlo_cases (cfgfile = 'test.json'):
    """Writes up to 20 TESP simulation case setups to a directory for Monte Carlo simulations

    Latin hypercube sampling is recommended; sample values may be specified via *tesp_config*

    Args:
        cfgfile (str): JSON file containing the TESP case configuration
    """
    lp = open (cfgfile).read()
    config = json.loads(lp)
    mc_cfg = 'monte_carlo_sample_' + cfgfile
    basecase = config['SimulationConfig']['CaseName']

    mc = config['MonteCarloCase']
    n = mc['NumCases']
    var1 = mc['Variable1']
    var2 = mc['Variable2']
    var3 = mc['Variable3']
    band1 = mc['Band1']
    band2 = mc['Band2']
    band3 = mc['Band3']
    samples1 = mc['Samples1']
    samples2 = mc['Samples2']
    samples3 = mc['Samples3']
#    print (var1, var2, var3, n)
    for i in range(n):
        mc_case = basecase + '_' + str(i+1)
        config['SimulationConfig']['CaseName'] = mc_case
        modify_mc_config (config, var1, band1, samples1[i])
        modify_mc_config (config, var2, band2, samples2[i])
        modify_mc_config (config, var3, band3, samples3[i])
        op = open (mc_cfg, 'w')
        print (json.dumps(config), file=op)
        op.close()
#        print (mc_case, mc['Samples1'][i], mc['Samples2'][i], mc['Samples3'][i])
        write_tesp_case (config, mc_cfg)

def add_tesp_feeder (cfgfile):
    """Wrapper function to start a single TESP case configuration.

    This function opens the JSON file, and calls *write_tesp_case* for just the
    GridLAB-D files. The subdirectory *targetdir* doesn't have to match the 
    case name in *cfgfile*, and it should be created first with *make_tesp_case*

    Args:
        cfgfile (str): JSON file containing the TESP case configuration
        targetdir (str): directory, based on cwd, to receive the TESP case files
    """
    print ('additional TESP feeder from', cfgfile)
    lp = open (cfgfile).read()
    config = json.loads(lp)
    write_tesp_case (config, cfgfile, freshdir = False)

