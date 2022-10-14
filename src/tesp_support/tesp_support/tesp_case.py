# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: tesp_case.py
"""Creates and fills a subdirectory with files to run a TESP simulation

Use *tesp_config* to graphically edit the case configuration

Public Functions:
    :make_tesp_case: sets up for a single-shot TESP case
    :make_monte_carlo_cases: sets up for a Monte Carlo TESP case of up to 20 shots
    :first_tesp_feeder: customization of make_tesp_case that will accept more feeders
    :add_tesp_feeder: add another feeder to the case directory created by first_tesp_feeder
"""
import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime

from .TMYtoEPW import convert_tmy2_to_epw
from .data import feeders_path, scheduled_path, weather_path, energyplus_path, pypower_path
from .feederGenerator import populate_feeder
from .glm_dict import glm_dict
from .helpers import HelicsMsg
from .make_ems import merge_idf
from .prep_substation import prep_substation

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def write_tesp_case(config, cfgfile, freshdir=True):
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

        * casename.glm: the GridLAB-D model, copied and modified from the TESP support directory
        * casename_gridlabd.txt: FNCS subscriptions and publications, included by casename.glm
        * casename_agent_dict.json: metadata for the simple_auction and hvac agents
        * casename_glm_dict.json: metadata for casename.glm
        * casename_pp.json: the PYPOWER model, copied and modified from the TESP support directory
        * casename_substation.yaml: FNCS subscriptions and time step for the substation, which manages the simple_auction and hvac controllers
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
        * monitor.json: shell commands and other configuration data for the solution monitor GUI
        * tesp_monitor.json: HELICS subscriptions and time step for the solution monitor GUI
        * tesp_monitor.yaml: FNCS subscriptions and time step for the solution monitor GUI
        * water_and_setpoint_schedule_v5.glm: non-responsive time schedules for GridLAB-D, invariant
        * weather.dat: CSV file of temperature, pressure, humidity, solar direct, solar diffuse and wind speed

        * casename_gridlabd.txt: HELICS subscriptions and publications, included by casename.glm
        * casename_substation.json: HELICS subscriptions and time step for the substation, which manages the simple_auction and hvac controllers
        * eplus.json: HELICS subscriptions and time step for EnergyPlus
        * eplus_agent.json: HELICS subscriptions and time step for the EnergyPlus agent
        * pypower.json: HELICS subscriptions and time step for PYPOWER

    Args:
        config (dict): the complete case data structure
        cfgfile (str): the name of the JSON file that was read
        freshdir (boolean): flag to create the directory and base files anew

    """
    print('feeder backbone files from', feeders_path)
    print('schedule files from', scheduled_path)
    print('weather files from', weather_path)
    print('E+ files from', energyplus_path)
    print('pypower backbone files from', pypower_path)

    casename = config['SimulationConfig']['CaseName']
    workdir = config['SimulationConfig']['WorkingDirectory']
    if len(workdir) > 2:
        casedir = workdir
    else:
        casedir = workdir + casename
    print('case files written to', casedir)

    if freshdir:
        if os.path.exists(casedir):
            shutil.rmtree(casedir)
        os.makedirs(casedir)

    StartTime = config['SimulationConfig']['StartTime']
    EndTime = config['SimulationConfig']['EndTime']
    time_fmt = '%Y-%m-%d %H:%M:%S'
    dt1 = datetime.strptime(StartTime, time_fmt)
    dt2 = datetime.strptime(EndTime, time_fmt)
    seconds = int((dt2 - dt1).total_seconds())
    days = seconds / 86400
    WeatherYear = dt1.year
    print('run', days, 'days or', seconds, 'seconds in weather year', WeatherYear)

    (rootweather, weatherext) = os.path.splitext(config['WeatherPrep']['DataSource'])
    EpRef = config['EplusConfiguration']['ReferencePrice']
    EpRamp = config['EplusConfiguration']['Slope']
    EpLimHi = config['EplusConfiguration']['OffsetLimitHi']
    EpLimLo = config['EplusConfiguration']['OffsetLimitLo']
    EpWeather = rootweather + '.epw'  # config['EplusConfiguration']['EnergyPlusWeather']
    EpStepsPerHour = int(config['EplusConfiguration']['StepsPerHour'])
    EpBuilding = config['EplusConfiguration']['BuildingChoice']
    EpEMS = config['EplusConfiguration']['EMSFile']
    EpBus = config['EplusConfiguration']['EnergyPlusBus']
    EpMetricsKey = EpBuilding  # os.path.splitext (EpFile)[0]
    EpAgentStop = str(seconds) + 's'
    EpStep = int(60 / EpStepsPerHour)  # minutes
    EpAgentStep = str(int(60 / EpStepsPerHour)) + 'm'
    EpMetricsFile = 'eplus_' + casename + '_metrics.json'
    GldFile = casename + '.glm'
    GldMetricsFile = casename + '_metrics.json'
    AgentDictFile = casename + '_agent_dict.json'
    PPJsonFile = casename + '_pp.json'
    SubstationYamlFile = casename + '_substation.yaml'
    WeatherConfigFile = casename + '_weather_f.json'

    weatherfile = weather_path + rootweather + '.tmy3'
    eplusfile = energyplus_path + EpBuilding + '.idf'

    # Want both files to be created
    emsfile = energyplus_path + EpEMS + '.idf'
    if 'emsHELICS' in emsfile:
        emsfileFNCS = emsfile.replace('emsHELICS', 'emsFNCS')
    if 'emsFNCS' in emsfile:
        emsfileFNCS = emsfile
        emsfile = emsfile.replace('emsFNCS', 'emsHELICS')

    eplusout = casedir + '/Merged.idf'
    eplusoutFNCS = casedir + '/Merged_f.idf'

    ppfile = pypower_path + config['BackboneFiles']['PYPOWERFile']
    ppcsv = pypower_path + config['PYPOWERConfiguration']['CSVLoadFile']
    dso_substation_bus_id = int(config['PYPOWERConfiguration']['GLDBus'])

    gld_federate = "gld_" + str(dso_substation_bus_id)
    sub_federate = "sub_" + str(dso_substation_bus_id)
    tso_federate = "pypower"
    eplus_federate = "eplus"
    agent_federate = "eplus_agent"
    mtr_federate = "monitor"

    if freshdir:
        # process TMY3 ==> weather.dat
        cmdline = pycall + ' -c "import tesp_support.TMY3toCSV as tesp; tesp.weathercsv(' + "'" + \
                  weatherfile + "','" + casedir + '/weather.dat' + "','" + \
                  StartTime + "','" + EndTime + "'," + str(WeatherYear) + ')"'
        print(cmdline)
        #    quit()
        pw0 = subprocess.Popen(cmdline, shell=True)
        pw0.wait()

    #########################################
    # set up EnergyPlus, if the user wants it.
    # Only works for TE_Base.glm
    bUseEplus = False
    if len(EpBus) > 0:
        bUseEplus = True

        merge_idf(eplusfile, emsfile, StartTime, EndTime, eplusout, EpStepsPerHour)
        merge_idf(eplusfile, emsfileFNCS, StartTime, EndTime, eplusoutFNCS, EpStepsPerHour)

        # process TMY3 ==> TMY2 ==> EPW
        cmdline = 'TMY3toTMY2_ansi ' + weatherfile + ' > ' + casedir + '/' + rootweather + '.tmy2'
        print("Converting " + cmdline)
        pw1 = subprocess.Popen(cmdline, shell=True)
        pw1.wait()

        print("Converting " + casedir + '/' + rootweather)
        convert_tmy2_to_epw(casedir + '/' + rootweather)

        # write the EnergyPlus YAML files, only subscriptions for FNCS
        op = open(casedir + '/' + eplus_federate + '.yaml', 'w')
        print('name:', eplus_federate, file=op)
        print('time_delta:', str(EpStep) + 'm', file=op)
        print('broker: tcp://localhost:5570', file=op)
        print('values:', file=op)
        print('    COOL_SETP_DELTA:', file=op)
        print('        topic:', agent_federate + '/cooling_setpoint_delta', file=op)
        print('        default: 0', file=op)
        print('    HEAT_SETP_DELTA:', file=op)
        print('        topic:', agent_federate + '/heating_setpoint_delta', file=op)
        print('        default: 0', file=op)
        op.close()

        yamlstr = """name: """ + agent_federate + """
time_delta: """ + str(EpAgentStep) + """
broker: tcp://localhost:5570
values:
    kwhr_price:
        topic: """ + sub_federate + """/clear_price
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
        op = open(casedir + '/' + agent_federate + '.yaml', 'w')
        print(yamlstr, file=op)
        op.close()

        eps = HelicsMsg(eplus_federate, 60 * EpStep)
        # Subs
        eps.subs_e(True, agent_federate + "/cooling_setpoint_delta", "double", "")
        eps.subs_e(True, agent_federate + "/heating_setpoint_delta", "double", "")
        # Pubs
        eps.pubs_e(False, "EMS Cooling Controlled Load", "double", "kWh")
        eps.pubs_e(False, "EMS Heating Controlled Load", "double", "kWh")
        eps.pubs_e(False, "EMS Cooling Schedule Temperature", "double", "degC")
        eps.pubs_e(False, "EMS Heating Schedule Temperature", "double", "degC")
        eps.pubs_e(False, "EMS Cooling Setpoint Temperature", "double", "degC")
        eps.pubs_e(False, "EMS Heating Setpoint Temperature", "double", "degC")
        eps.pubs_e(False, "EMS Cooling Current Temperature", "double", "degC")
        eps.pubs_e(False, "EMS Heating Current Temperature", "double", "degC")
        eps.pubs_e(False, "EMS Cooling Power State", "string", "")
        eps.pubs_e(False, "EMS Heating Power State", "string", "")
        eps.pubs_e(False, "EMS Cooling Volume", "double", "stere")
        eps.pubs_e(False, "EMS Heating Volume", "double", "stere")
        eps.pubs_e(False, "EMS Occupant Count", "int", "count")
        eps.pubs_e(False, "EMS Indoor Air Temperature", "double", "degC")
        eps.pubs_e(False, "WHOLE BUILDING Facility Total Electric Demand Power", "double", "W")
        eps.pubs_e(False, "WHOLE BUILDING Facility Total HVAC Electric Demand Power", "double", "W")
        eps.pubs_e(False, "FACILITY Facility Thermal Comfort ASHRAE 55 " +
                   "Simple Model Summer or Winter Clothes Not Comfortable Time", "double", "hour")
        eps.pubs_e(False, "Environment Site Outdoor Air Drybulb Temperature", "double", "degC")
        eps.pubs_e(False, "EMS HEATING SETPOINT", "double", "degC")
        eps.pubs_e(False, "EMS HEATING CURRENT", "double", "degC")
        eps.pubs_e(False, "EMS COOLING SETPOINT", "double", "degC")
        eps.pubs_e(False, "EMS COOLING CURRENT", "double", "degC")
        eps.pubs_e(False, "H2_NOM SCHEDULE VALUE", "double", "degC")
        eps.pubs_e(False, "H1_NOM SCHEDULE VALUE", "double", "degC")
        eps.pubs_e(False, "C2_NOM SCHEDULE VALUE", "double", "degC")
        eps.pubs_e(False, "C1_NOM SCHEDULE VALUE", "double", "degC")
        eps.write_file(casedir + '/eplus.json')

        epa = HelicsMsg(agent_federate, 60 * EpStep)
        epa.config("time_delta", 1)
        epa.config("uninterruptible", False)
        # Subs
        epa.subs_e(True, sub_federate + "/clear_price", "double", "kwhr_price")
        epa.subs_e(True, eplus_federate + "/EMS Cooling Controlled Load", "double", "cooling_controlled_load")
        epa.subs_e(True, eplus_federate + "/EMS Heating Controlled Load", "double", "heating_controlled_load")
        epa.subs_e(True, eplus_federate + "/EMS Cooling Schedule Temperature", "double", "cooling_schedule_temperature")
        epa.subs_e(True, eplus_federate + "/EMS Heating Schedule Temperature", "double", "heating_schedule_temperature")
        epa.subs_e(True, eplus_federate + "/EMS Cooling Setpoint Temperature", "double", "cooling_setpoint_temperature")
        epa.subs_e(True, eplus_federate + "/EMS Heating Setpoint Temperature", "double", "heating_setpoint_temperature")
        epa.subs_e(True, eplus_federate + "/EMS Cooling Current Temperature", "double", "cooling_current_temperature")
        epa.subs_e(True, eplus_federate + "/EMS Heating Current Temperature", "double", "heating_current_temperature")
        epa.subs_e(True, eplus_federate + "/EMS Cooling Power State", "string", "cooling_power_state")
        epa.subs_e(True, eplus_federate + "/EMS Heating Power State", "string", "heating_power_state")
        epa.subs_e(True, eplus_federate + "/EMS Cooling Volume", "double", "cooling_volume")
        epa.subs_e(True, eplus_federate + "/EMS Heating Volume", "double", "heating_volume")
        epa.subs_e(True, eplus_federate + "/EMS Occupant Count", "int", "occupants_total")
        epa.subs_e(True, eplus_federate + "/EMS Indoor Air Temperature", "double", "indoor_air")
        epa.subs_e(True, eplus_federate + "/WHOLE BUILDING Facility Total Electric Demand Power", "double",
                   "electric_demand_power")
        epa.subs_e(True, eplus_federate + "/WHOLE BUILDING Facility Total HVAC Electric Demand Power", "double",
                   "hvac_demand_power")
        epa.subs_e(True, eplus_federate + "/FACILITY Facility Thermal Comfort ASHRAE 55 Simple Model " +
                   "Summer or Winter Clothes Not Comfortable Time", "double", "ashrae_uncomfortable_hours")
        epa.subs_e(True, eplus_federate + "/Environment Site Outdoor Air Drybulb Temperature", "double", "outdoor_air")
        # Pubs
        epa.pubs_e(False, "power_A", "double", "W")
        epa.pubs_e(False, "power_B", "double", "W")
        epa.pubs_e(False, "power_C", "double", "W")
        epa.pubs_e(False, "bill_mode", "string", "")
        epa.pubs_e(False, "price", "double", "$/kwh")
        epa.pubs_e(False, "monthly_fee", "double", "$")
        epa.pubs_e(False, "cooling_setpoint_delta", "double", "degC")
        epa.pubs_e(False, "heating_setpoint_delta", "double", "degC")
        epa.write_file(casedir + '/eplus_agent.json')

    ###################################
    # dynamically import the base PYPOWER case
    import importlib.util
    spec = importlib.util.spec_from_file_location('ppbasecase', ppfile)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ppcase = mod.ppcasefile()
    # print (ppcase)

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
    ppcase['DSO'][0][0] = dso_substation_bus_id
    ppcase['DSO'][0][2] = float(config['PYPOWERConfiguration']['GLDScale'])
    baseKV = float(config['PYPOWERConfiguration']['TransmissionVoltage'])
    for row in ppcase['bus']:
        if row[0] == dso_substation_bus_id:
            row[9] = baseKV

    if len(config['PYPOWERConfiguration']['UnitOutStart']) > 0 and len(
            config['PYPOWERConfiguration']['UnitOutEnd']) > 0:
        dt3 = datetime.strptime(config['PYPOWERConfiguration']['UnitOutStart'], time_fmt)
        tout_start = int((dt3 - dt1).total_seconds())
        dt3 = datetime.strptime(config['PYPOWERConfiguration']['UnitOutEnd'], time_fmt)
        tout_end = int((dt3 - dt1).total_seconds())
        ppcase['UnitsOut'][0] = [int(config['PYPOWERConfiguration']['UnitOut']), tout_start, tout_end]
    else:
        ppcase['UnitsOut'] = []

    if len(config['PYPOWERConfiguration']['BranchOutStart']) > 0 and len(
            config['PYPOWERConfiguration']['BranchOutEnd']) > 0:
        dt3 = datetime.strptime(config['PYPOWERConfiguration']['BranchOutStart'], time_fmt)
        tout_start = int((dt3 - dt1).total_seconds())
        dt3 = datetime.strptime(config['PYPOWERConfiguration']['BranchOutEnd'], time_fmt)
        tout_end = int((dt3 - dt1).total_seconds())
        ppcase['BranchesOut'][0] = [int(config['PYPOWERConfiguration']['BranchOut']), tout_start, tout_end]
    else:
        ppcase['BranchesOut'] = []

    fp = open(casedir + '/' + casename + '_pp.json', 'w')
    json.dump(ppcase, fp, indent=2)
    fp.close()

    if freshdir:
        shutil.copy(ppcsv, casedir)

        # write tso Power
        yamlstr = """name: """ + tso_federate + """
time_delta: """ + str(config['PYPOWERConfiguration']['PFStep']) + """s
broker: tcp://localhost:5570
values:
    SUBSTATION""" + str(dso_substation_bus_id) + """:
        topic: """ + gld_federate + """/distribution_load
        default: 0
    UNRESPONSIVE_MW:
        topic: """ + sub_federate + """/unresponsive_mw
        default: 0
    RESPONSIVE_MAX_MW:
        topic: """ + sub_federate + """/responsive_max_mw
        default: 0
    RESPONSIVE_C2:
        topic: """ + sub_federate + """/responsive_c2
        default: 0
    RESPONSIVE_C1:
        topic: """ + sub_federate + """/responsive_c1
        default: 0
    RESPONSIVE_DEG:
        topic: """ + sub_federate + """/responsive_deg
        default: 0
"""
        op = open(casedir + '/pypower.yaml', 'w')
        print(yamlstr, file=op)
        op.close()

        ppc = HelicsMsg(tso_federate, int(config['PYPOWERConfiguration']['PFStep']))
        ppc.subs_n(gld_federate + "/distribution_load", "complex")
        ppc.subs_n(sub_federate + "/unresponsive_mw", "double")
        ppc.subs_n(sub_federate + "/responsive_max_mw", "double")
        ppc.subs_n(sub_federate + "/responsive_c1", "double")
        ppc.subs_n(sub_federate + "/responsive_c2", "double")
        ppc.subs_n(sub_federate + "/responsive_deg", "integer")
        ppc.pubs_n(False, "three_phase_voltage_" + str(dso_substation_bus_id), "double")
        ppc.pubs_n(False, "LMP_" + str(dso_substation_bus_id), "double")
        ppc.write_file(casedir + '/pypower.json')

        # write a YAML for the solution monitor
        yamlstr = """name: """ + mtr_federate + """
time_delta: """ + str(config['AgentPrep']['MarketClearingPeriod']) + """s
broker: tcp://localhost:5570
aggregate_sub: true
values:
  TPV_""" + str(dso_substation_bus_id) + """:
    topic: """ + tso_federate + """/three_phase_voltage_""" + str(dso_substation_bus_id) + """
    default: 0
    type: double
    list: false
  LMP_""" + str(dso_substation_bus_id) + """:
    topic: """ + tso_federate + """/LMP_""" + str(dso_substation_bus_id) + """
    default: 0
    type: double
    list: false
  clear_price:
    topic: """ + sub_federate + """/clear_price
    default: 0
    type: double
    list: false
  distribution_load:
    topic: """ + gld_federate + """/distribution_load
    default: 0
    type: complex
    list: false
"""

        if len(EpBus) > 0:
            yamlstr = yamlstr + """  power_A:
    topic: """ + agent_federate + """/power_A
    default: 0
    type: double
    list: false
  electric_demand_power:
    topic: """ + eplus_federate + """/WHOLE BUILDING Facility Total Electric Demand Power
    default: 0
    type: double
    list: false
"""
        op = open(casedir + '/' + casename + '_monitor.yaml', 'w')
        print(yamlstr, file=op)
        op.close()

        ppc = HelicsMsg(mtr_federate, config['AgentPrep']['MarketClearingPeriod'])
        ppc.subs_n(tso_federate + "/three_phase_voltage_" + str(dso_substation_bus_id), "double")
        ppc.subs_n(tso_federate + "/LMP_" + str(dso_substation_bus_id), "double")
        ppc.subs_n(sub_federate + "/clear_price", "double")
        ppc.subs_n(gld_federate + "/distribution_load", "complex")
        if len(EpBus) > 0:
            ppc.subs_n(agent_federate + "/power_A", "double")
            ppc.subs_n(eplus_federate + "/WHOLE BUILDING Facility Total Electric Demand Power", "double")
        ppc.write_file(casedir + '/' + casename + '_monitor.json')

    populate_feeder(cfgfile)
    # glm file name without a .glm extension
    glmfile = casedir + '/' + casename
    glm_dict(glmfile)
    prep_substation(glmfile, cfgfile)

    if not freshdir:
        return

    # ====================================================================
    # FNCS shell scripts and chmod for Mac/Linux - need to specify python3
    try:
        aucline = "import tesp_support.substation as tesp;tesp.substation_loop('" + AgentDictFile + "','" + casename + "')"
        ppline = "import tesp_support.tso_PYPOWER_f as tesp;tesp.tso_pypower_loop_f('" + PPJsonFile + "','" + casename + "')"
        weatherline = "import tesp_support.weatherAgent as tesp;tesp.startWeatherAgent('weather.dat')"

        shfile = casedir + '/run.sh'
        op = open(shfile, 'w')
        if bUseEplus:
            print(
                '(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 6 &> broker_f.log &)',
                file=op)
            print('(export FNCS_CONFIG_FILE=eplus.yaml && export FNCS_FATAL=YES && exec energyplus -w '
                  + EpWeather + ' -d output Merged_f.idf &> ' + eplus_federate + '_f.log &)', file=op)
            print('(export FNCS_CONFIG_FILE=eplus_agent.yaml && export FNCS_FATAL=YES && exec eplus_agent',
                  EpAgentStop, EpAgentStep, EpMetricsKey, EpMetricsFile, EpRef, EpRamp, EpLimHi, EpLimLo,
                  '&> ' + agent_federate + '_f.log &)', file=op)
        else:
            print('(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 4 &> broker_f.log &)',
                file=op)
        print('(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS -D METRICS_FILE=' + GldMetricsFile + ' ' + GldFile +
              ' &> ' + gld_federate + '_f.log &)', file=op)
        print('(export FNCS_CONFIG_FILE=' + SubstationYamlFile + ' && export FNCS_FATAL=YES && exec python3 -c "' + aucline +
              '" &> ' + sub_federate + '_f.log &)', file=op)
        print('(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && ' +
              'export FNCS_LOG_STDOUT=yes && exec python3 -c "' + ppline +
              '" &> ' + tso_federate + '_f.log &)', file=op)
        print('(export WEATHER_CONFIG=' + WeatherConfigFile +
              ' && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "' + weatherline +
              '" &> weather_f.log &)', file=op)
        op.close()
        st = os.stat(shfile)
        os.chmod(shfile, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        cmds = {'time_stop': seconds,
                'yaml_delta': int(config['AgentPrep']['MarketClearingPeriod']),
                'commands': [],
                'helics_config': casename + '_monitor.json',
                'commands_f': [],
                'fncs_config': casename + '_monitor.yaml'}

        cmd = cmds['commands_f']
        cmd.append({'args': ['fncs_broker', '5'],
                    'env': [['FNCS_BROKER', 'tcp://*:5570'],
                            ['FNCS_FATAL', 'YES']],
                    'log': 'broker_f.log'})
        if bUseEplus:
            cmd[0]['args'][1] = '7'
            cmd.append({'args': ['energyplus', '-w', EpWeather, '-d', 'output', 'Merged_f.idf'],
                        'env': [['FNCS_CONFIG_FILE', 'eplus.yaml'],
                                ['FNCS_FATAL', 'YES']],
                        'log': eplus_federate + '_f.log'})
            cmd.append({'args': ['eplus_agent', EpAgentStop, EpAgentStep,
                                 EpMetricsKey, EpMetricsFile, str(EpRef),
                                 str(EpRamp), str(EpLimHi), str(EpLimLo)],
                        'env': [['FNCS_CONFIG_FILE', 'eplus_agent.yaml'],
                                ['FNCS_FATAL', 'YES']],
                        'log': agent_federate + '_f.log'})

        cmd.append({'args': ['gridlabd', '-D', 'USE_FNCS', '-D', 'METRICS_FILE=' + GldMetricsFile, GldFile],
                    'env': [['FNCS_FATAL', 'YES']],
                    'log': gld_federate + '_f.log'})
        cmd.append({'args': [pycall, '-c', aucline],
                    'env': [['FNCS_CONFIG_FILE', SubstationYamlFile],
                            ['FNCS_FATAL', 'YES'],
                            ['FNCS_LOG_STDOUT', 'yes']],
                    'log': sub_federate + '_f.log'})
        cmd.append({'args': [pycall, '-c', ppline],
                    'env': [['FNCS_CONFIG_FILE', 'pypower.yaml'],
                            ['FNCS_FATAL', 'YES'],
                            ['FNCS_LOG_STDOUT', 'yes']],
                    'log': tso_federate + '_f.log'})
        cmd.append({'args': [pycall, '-c', weatherline],
                    'env': [['WEATHER_CONFIG', WeatherConfigFile],
                            ['FNCS_FATAL', 'YES']],
                    'log': 'weather_f.log'})
    finally:
        pass

    # ======================================================================
    # HELICS shell scripts and chmod for Mac/Linux - need to specify python3
    try:  # HELICS
        PypowerConfigFile = 'pypower.json'
        SubstationConfigFile = casename + '_substation.json'
        WeatherConfigFile = casename + '_weather.json'
        aucline = "import tesp_support.substation as tesp;tesp.substation_loop('" + AgentDictFile + "','" + casename + "',helicsConfig='" + SubstationConfigFile + "')"
        ppline = "import tesp_support.tso_PYPOWER as tesp;tesp.tso_pypower_loop('" + PPJsonFile + "','" + casename + "',helicsConfig='" + PypowerConfigFile + "')"

        shfile = casedir + '/runh.sh'
        op = open(shfile, 'w')
        if bUseEplus:
            print('(exec helics_broker -f 6 --loglevel=warning --name=mainbroker &> broker.log &)', file=op)
            print('(export HELICS_CONFIG_FILE=eplus.json && exec energyplus -w ' + EpWeather +
                  ' -d output Merged.idf &> ' + eplus_federate + '.log &)', file=op)
            # configure from the command line, but StartTime and load_scale not supported this way
            print('(exec eplus_agent_helics',
                  EpAgentStop, EpAgentStep, EpMetricsKey, EpMetricsFile, EpRef, EpRamp, EpLimHi, EpLimLo,
                  'eplus_agent.json &> ' + agent_federate + '.log &)', file=op)
        else:
            print('(exec helics_broker -f 4 --loglevel=warning --name=mainbroker &> broker.log &)', file=op)
        print('(exec gridlabd -D USE_HELICS -D METRICS_FILE=' + GldMetricsFile + ' ' + GldFile + ' &> ' +
              gld_federate + '.log &)', file=op)
        print('(exec python3 -c "' + aucline + '" &> ' + sub_federate + '.log &)', file=op)
        print('(exec python3 -c "' + ppline + '" &> ' + tso_federate + '.log &)', file=op)
        print('(export WEATHER_CONFIG=' + WeatherConfigFile + ' && exec python3 -c "' + weatherline +
              '" &> weather.log &)', file=op)
        op.close()
        st = os.stat(shfile)
        os.chmod(shfile, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        cmd = cmds['commands']
        cmd.append({'args': ['helics_broker', '-f', '5', '--loglevel=warning', '--name=mainbroker'],
                    'log': 'broker.log'})
        if bUseEplus:
            cmd[0]['args'][2] = '7'
            cmd.append({'args': ['energyplus', '-w', EpWeather, '-d', 'output', 'Merged.idf'],
                        'env': [['HELICS_CONFIG_FILE', 'eplus.json']],
                        'log': eplus_federate + '.log'})
            cmd.append({'args': ['eplus_agent_helics', EpAgentStop, EpAgentStep,
                                 EpMetricsKey, EpMetricsFile, str(EpRef),
                                 str(EpRamp), str(EpLimHi), str(EpLimLo), 'eplus_agent.json'],
                        'log': agent_federate + '.log'})

        cmd.append({'args': ['gridlabd', '-D', 'USE_HELICS', '-D', 'METRICS_FILE=' + GldMetricsFile, GldFile],
                    'log': gld_federate + '.log'})
        cmd.append({'args': [pycall, '-c', aucline],
                    'log': sub_federate + '.log'})
        cmd.append({'args': [pycall, '-c', ppline],
                    'log': tso_federate + '.log'})
        cmd.append({'args': [pycall, '-c', weatherline],
                    'env': [['WEATHER_CONFIG', WeatherConfigFile]],
                    'log': 'weather.log'})
        op = open(casedir + '/monitor.json', 'w')
        json.dump(cmds, op, indent=2)
        op.close()
    finally:
        pass


def make_tesp_case(cfgfile='test.json'):
    """Wrapper function for a single TESP case configuration.

    This function opens the JSON file, and calls *write_tesp_case*

    Args:
        cfgfile (str): JSON file containing the TESP case configuration
    """
    lp = open(cfgfile).read()
    config = json.loads(lp)
    write_tesp_case(config, cfgfile)


def modify_mc_config(config, mcvar, band, sample):
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


def make_monte_carlo_cases(cfgfile='test.json'):
    """Writes up to 20 TESP simulation case setups to a directory for Monte Carlo simulations

    Latin hypercube sampling is recommended; sample values may be specified via *tesp_config*

    Args:
        cfgfile (str): JSON file containing the TESP case configuration
    """
    lp = open(cfgfile).read()
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
        mc_case = basecase + '_' + str(i + 1)
        config['SimulationConfig']['CaseName'] = mc_case
        modify_mc_config(config, var1, band1, samples1[i])
        modify_mc_config(config, var2, band2, samples2[i])
        modify_mc_config(config, var3, band3, samples3[i])
        op = open(mc_cfg, 'w')
        print(json.dumps(config), file=op)
        op.close()
        #        print (mc_case, mc['Samples1'][i], mc['Samples2'][i], mc['Samples3'][i])
        write_tesp_case(config, mc_cfg)


def add_tesp_feeder(cfgfile):
    """Wrapper function to start a single TESP case configuration.

    This function opens the JSON file, and calls *write_tesp_case* for just the
    GridLAB-D files. The subdirectory *targetdir* doesn't have to match the 
    case name in *cfgfile*, and it should be created first with *make_tesp_case*

    Args:
        cfgfile (str): JSON file containing the TESP case configuration
    """
    print('additional TESP feeder from', cfgfile)
    lp = open(cfgfile).read()
    config = json.loads(lp)
    write_tesp_case(config, cfgfile, freshdir=False)


if __name__ == "__main__":
    make_tesp_case('~/tesp/repository/tesp/examples/capabilities/ttest/test.json')
