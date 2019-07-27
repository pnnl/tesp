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

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'

def idf_int(val):
    """Helper function to format integers for the EnergyPlus IDF input data file

    Args:
        val (int): the integer to format

    Returns:
        str: the integer in string format, padded with a comma and zero or one blanks, in order to fill three spaces
    """
    sval = str(val)
    if len(sval) < 2:
        return sval + ', '
    return sval + ','

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

        * Tmy3toTMY2_ansi, which converts the user-selected TMY3 file to TMY2
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
        * clean.bat: Windows helper to clean up simulation outputs
        * clean.sh: Linux/Mac OS X helper to clean up simulation outputs
        * commercial_schedules.glm: non-responsive non-responsive time schedules for GridLAB-D, invariant
        * eplus.yaml: FNCS subscriptions and time step for EnergyPlus
        * eplus_json.yaml: FNCS subscriptions and time step for the EnergyPlus agent
        * gui.py: helper to launch the GUI solution monitor (FNCS_CONFIG_FILE envar must be set for this process, see gui.bat and gui.sh under examples/te30)
        * kill5570.bat: Windows helper to kill one of the federates listening on port 5570
        * kill5570.sh: Linux/Mac OS X helper to kill all federates listening on port 5570
        * launch_auction.py: helper script for the GUI solution monitor to launch the substation federate
        * launch_pp.py: helper script for the GUI solution monitor to launch the PYPOWER federate
        * list5570.bat: Windows helper to list all federates listening on port 5570
        * monitor.py: duplicate of gui.py, should remove
        * plots.py: helper script that will plot a selection of case outputs
        * pypower.yaml: FNCS subscriptions and time step for PYPOWER
        * run.bat: Windows helper to launch the TESP simulation
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
        * Write gui.bat and gui.sh, per the te30 examples
        * do not write monitor.py
    """
    tespdir = config['SimulationConfig']['SourceDirectory']
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

    ep_dow_names = ['Monday,   ', 'Tuesday,  ', 'Wednesday,', 'Thursday, ', 'Friday,   ', 'Saturday, ', 'Sunday,   ']
    dow = dt1.weekday()
    begin_month = dt1.month
    begin_day = dt1.day
    end_month = dt2.month
    end_day = dt2.day
    if dt2.hour == 0 and dt2.minute == 0 and dt2.second == 0:
        end_day -= 1

    (rootweather, weatherext) = os.path.splitext(config['WeatherPrep']['DataSource'])
    EpRef = config['EplusConfiguration']['ReferencePrice']
    EpRamp = config['EplusConfiguration']['Slope']
    EpLimHi = config['EplusConfiguration']['OffsetLimitHi']
    EpLimLo = config['EplusConfiguration']['OffsetLimitLo']
    EpWeather = rootweather + '.epw' # config['EplusConfiguration']['EnergyPlusWeather']
    EpStep = config['EplusConfiguration']['TimeStep'] # minutes
    EpFile = config['BackboneFiles']['EnergyPlusFile']
    EpMetricsKey = os.path.splitext (EpFile)[0]
    EpAgentStop = str (seconds) + 's'
    EpAgentStep = str (config['FeederGenerator']['MetricsInterval']) + 's'
    EpMetricsFile = 'eplus_' + casename + '_metrics.json'
    GldFile = casename + '.glm'
    GldMetricsFile = casename + '_metrics.json'
    AgentDictFile = casename + '_agent_dict.json'
    PPJsonFile = casename + '_pp.json'
    SubstationYamlFile = casename + '_substation.yaml'
    WeatherConfigFile = casename + '_Weather_Config.json'

    weatherfile = weatherdir + rootweather + '.tmy3'
    eplusfile = eplusdir + EpFile
    eplusout = casedir + '/' + EpFile
    ppfile = ppdir + config['BackboneFiles']['PYPOWERFile']
    ppcsv = ppdir + config['PYPOWERConfiguration']['CSVLoadFile']

    # copy some boilerplate files
    if freshdir == True:
        shutil.copy (miscdir + 'clean.sh', casedir)
        shutil.copy (miscdir + 'clean.bat', casedir)
        shutil.copy (miscdir + 'kill5570.sh', casedir)
        shutil.copy (miscdir + 'kill5570.bat', casedir)
        shutil.copy (miscdir + 'killold.bat', casedir)
        shutil.copy (miscdir + 'list5570.bat', casedir)
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
    if len(EpFile) > 0:
        bUseEplus = True
        # set the RunPeriod for EnergyPlus
        ip = open (eplusfile, 'r', encoding='latin-1')
        op = open (eplusout, 'w', encoding='latin-1')
        print ('filtering', eplusfile, 'to', eplusout)
        for ln in ip:
            line = ln.rstrip('\n')
            if '!- Begin Month' in line:
                print ('    %s                      !- Begin Month' % idf_int(begin_month), file=op)
            elif '!- Begin Day of Month' in line:
                print ('    %s                      !- Begin Day of Month' % idf_int(begin_day), file=op)
            elif '!- End Month' in line:
                print ('    %s                      !- End Month' % idf_int(end_month), file=op)
            elif '!- End Day of Month' in line:
                print ('    %s                      !- End Day of Month' % idf_int(end_day), file=op)
            elif '!- Day of Week for Start Day' in line:
                print ('    %s               !- Day of Week for Start Day' % ep_dow_names[dow], file=op)
            else:
                print (line, file=op)
        ip.close()
        op.close()

        # process TMY3 ==> TMY2 ==> EPW
        pw1 = subprocess.Popen ('Tmy3toTMY2_ansi ' + casedir + '/' + rootweather + '.tmy3 > '
                                + casedir + '/' + rootweather + '.tmy2', shell=True)
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
        print ('        topic: eplus_json/cooling_setpoint_delta', file=op)
        print ('        default: 0', file=op)
        print ('    HEAT_SETP_DELTA:', file=op)
        print ('        topic: eplus_json/heating_setpoint_delta', file=op)
        print ('        default: 0', file=op)
        op.close()

        epjyamlstr = """name: eplus_json
time_delta: """ + EpAgentStep + """
broker: tcp://localhost:5570
values:
    kwhr_price:
        topic: auction/clear_price
        default: 0.10
    cooling_controlled_load:
        topic: eplus/EMS COOLING CONTROLLED LOAD
        default: 0
    cooling_desired_temperature:
        topic: eplus/EMS COOLING DESIRED TEMPERATURE
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
    heating_desired_temperature:
        topic: eplus/EMS HEATING DESIRED TEMPERATURE
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
    ashrae_uncomfortable_hours:
        topic: eplus/FACILITY FACILITY THERMAL COMFORT ASHRAE 55 SIMPLE MODEL SUMMER OR WINTER CLOTHES NOT COMFORTABLE TIME
        default: 0
    occupants_1:
        topic: eplus/BATH_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_2:
        topic: eplus/CAFETERIA_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_3:
        topic: eplus/COMPUTER_CLASS_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_4:
        topic: eplus/CORNER_CLASS_1_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_5:
        topic: eplus/CORNER_CLASS_1_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_6:
        topic: eplus/CORNER_CLASS_1_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_7:
        topic: eplus/CORNER_CLASS_2_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_8:
        topic: eplus/CORNER_CLASS_2_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_9:
        topic: eplus/CORNER_CLASS_2_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_10:
        topic: eplus/CORRIDOR_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_11:
        topic: eplus/CORRIDOR_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_12:
        topic: eplus/CORRIDOR_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_13:
        topic: eplus/GYM_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_14:
        topic: eplus/KITCHEN_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_15:
        topic: eplus/LIBRARY_MEDIA_CENTER_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_17:
        topic: eplus/MAIN_CORRIDOR_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_18:
        topic: eplus/MULT_CLASS_1_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_19:
        topic: eplus/MULT_CLASS_1_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_20:
        topic: eplus/MULT_CLASS_1_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_21:
        topic: eplus/MULT_CLASS_2_POD_1_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_22:
        topic: eplus/MULT_CLASS_2_POD_2_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_23:
        topic: eplus/MULT_CLASS_2_POD_3_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
    occupants_24:
        topic: eplus/OFFICES_ZN_1_FLR_1 PEOPLE PEOPLE OCCUPANT COUNT
        default: 0
"""
        op = open (casedir + '/eplus_json.yaml', 'w')
        print (epjyamlstr, file=op)
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
    ppcase['FNCS'] = ppcase['FNCS'].tolist()
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
    ppcase['FNCS'][0][0] = fncsBus
    ppcase['FNCS'][0][2] = fncsScale
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
        topic: gridlabdSimulator1/distribution_load
        default: 0
    UNRESPONSIVE_MW:
        topic: auction/unresponsive_mw
        default: 0
    RESPONSIVE_MAX_MW:
        topic: auction/responsive_max_mw
        default: 0
    RESPONSIVE_C2:
        topic: auction/responsive_c2
        default: 0
    RESPONSIVE_C1:
        topic: auction/responsive_c1
        default: 0
    RESPONSIVE_DEG:
        topic: auction/responsive_deg
        default: 0
"""
    if freshdir == True:
        shutil.copy (ppcsv, casedir)
        op = open (casedir + '/pypower.yaml', 'w')
        print (ppyamlstr, file=op)
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
    topic: substation/clear_price
    default: 0
    type: double
    list: false
  distribution_load:
    topic: gridlabdSimulator1/distribution_load
    default: 0
    type: complex
    list: false
  power_A:
    topic: eplus_json/power_A
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

    # write the command scripts for console and tesp_monitor execution
    aucline = """python -c "import tesp_support.api as tesp;tesp.substation_loop('""" + AgentDictFile + """','""" + casename + """')" """
    ppline = """python -c "import tesp_support.api as tesp;tesp.pypower_loop('""" + PPJsonFile + """','""" + casename + """')" """
    weatherline = """python -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" """

    # batch file for Windows
    batfile = casedir + '/run.bat'
    op = open (batfile, 'w')
    print ('set FNCS_FATAL=yes', file=op)
    print ('set FNCS_TIME_DELTA=', file=op)
    print ('set FNCS_CONFIG_FILE=', file=op)
    if bUseEplus:
        print ('start /b cmd /c fncs_broker 6 ^>broker.log 2^>^&1', file=op)
        print ('set FNCS_CONFIG_FILE=eplus.yaml', file=op)
        print ('start /b cmd /c energyplus -w ' + EpWeather + ' -d output -r ' + EpFile + ' ^>eplus.log 2^>^&1', file=op)
        print ('set FNCS_CONFIG_FILE=eplus_json.yaml', file=op)
        print ('start /b cmd /c eplus_json', EpAgentStop, EpAgentStep, EpMetricsKey, EpMetricsFile, EpRef, EpRamp, EpLimHi, EpLimLo, '^>eplus_json.log 2^>^&1', file=op)
    else:
        print ('start /b cmd /c fncs_broker 4 ^>broker.log 2^>^&1', file=op)
    print ('set FNCS_CONFIG_FILE=', file=op)
    print ('start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=' + GldMetricsFile + ' ' + GldFile + ' ^>gridlabd.log 2^>^&1', file=op)
    print ('set FNCS_CONFIG_FILE=' + SubstationYamlFile, file=op)
    print ('start /b cmd /c', aucline + '^>substation.log 2^>^&1', file=op)
    print ('set FNCS_CONFIG_FILE=pypower.yaml', file=op)
    print ('start /b cmd /c', ppline + '^>pypower.log 2^>^&1', file=op)
    print ('set FNCS_CONFIG_FILE=', file=op)
    print ('set WEATHER_CONFIG=' + WeatherConfigFile, file=op)
    print ('start /b cmd /c', weatherline + '^>weather.log 2^>^&1', file=op)
    op.close()
    
    # shell scripts and chmod for Mac/Linux - need to specify python3
    aucline = """python3 -c "import tesp_support.api as tesp;tesp.substation_loop('""" + AgentDictFile + """','""" + casename + """')" """
    ppline = """python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('""" + PPJsonFile + """','""" + casename + """')" """
    weatherline = """python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" """

    shfile = casedir + '/run.sh'
    op = open (shfile, 'w')
    if bUseEplus:
        print ('(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 6 &> broker.log &)', file=op)
        print ('(export FNCS_CONFIG_FILE=eplus.yaml && export FNCS_FATAL=YES && exec EnergyPlus -w ' 
               + EpWeather + ' -d output -r ' + EpFile + ' &> eplus.log &)', file=op)
        print ('(export FNCS_CONFIG_FILE=eplus_json.yaml && export FNCS_FATAL=YES && exec eplus_json', EpAgentStop, EpAgentStep, 
               EpMetricsKey, EpMetricsFile, EpRef, EpRamp, EpLimHi, EpLimLo, '&> eplus_json.log &)', file=op)
    else:
        print ('(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 4 &> broker.log &)', file=op)
    print ('(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS -D METRICS_FILE='
           + GldMetricsFile + ' ' + GldFile + ' &> gridlabd.log &)', file=op)
    print ('(export FNCS_CONFIG_FILE=' + SubstationYamlFile + ' && export FNCS_FATAL=YES && exec ' + aucline + ' &> substation.log &)', file=op)
    print ('(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec ' + ppline + ' &> pypower.log &)', file=op)
    print ('(export WEATHER_CONFIG=' + WeatherConfigFile + ' && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec ' + weatherline + ' &> weather.log &)', file=op)
    op.close()
    st = os.stat (shfile)
    os.chmod (shfile, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shfile = casedir + '/kill5570.sh'
    os.chmod (shfile, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shfile = casedir + '/clean.sh'
    os.chmod (shfile, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # commands for the GUI execution
    op = open (casedir + '/gui.py', 'w')
    print ('import tesp_support.tesp_monitor as tesp', file=op)
    print ('tesp.show_tesp_monitor()', file=op)
    op.close()
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
        cmds['commands'].append({'args':['EnergyPlus', '-w', EpWeather, '-d', 'output', '-r', EpFile], 
                           'env':[['FNCS_CONFIG_FILE', 'eplus.yaml'],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                           'log':'eplus.log'})
        cmds['commands'].append({'args':['eplus_json', EpAgentStop, EpAgentStep, EpMetricsKey, EpMetricsFile, EpRef, EpRamp, EpLimHi, EpLimLo], 
                           'env':[['FNCS_CONFIG_FILE', 'eplus_json.yaml'],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                           'log':'eplus_json.log'})
    else:
        cmds['commands'].append({'args':['fncs_broker', '6'], 
                           'env':[['FNCS_BROKER', 'tcp://*:5570'],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                           'log':'broker.log'})
    cmds['commands'].append({'args':['gridlabd', '-D', 'USE_FNCS', '-D', 'METRICS_FILE=' + GldMetricsFile, GldFile], 
                       'env':[['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                       'log':'gridlabd.log'})
    cmds['commands'].append({'args':[pycall, 'launch_auction.py'], 
                       'env':[['FNCS_CONFIG_FILE', SubstationYamlFile],['FNCS_FATAL', 'YES'],['FNCS_LOG_STDOUT', 'yes']], 
                       'log':'substation.log'})
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

