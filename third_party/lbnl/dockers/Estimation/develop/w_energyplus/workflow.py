# Requirements -- gitpython, subprocess
try:
    import git
except ImportError:
    print("gitpython needs to be installed.")

try:
    import subprocess
except ImportError:
    print("subprocess needs to be installed.")

#############################################
# Flag to enable batch mode for matplotlib
RUN_DOCKER=True
#IF RUN_DOCKER=False then the path to the IDD
# needs to be specified in export_idf_as_fmu
# as it currently assumes the path to be in
# a specfic location which is defined in the docker.
#############################################
# The flag UNIT_EP_TZONE must be set to True to add units to E+ output variables.
# Currently, temperatures are supported. That's, if the output of E+
# is the temperature, then the unit degC will be added to the output variable
ADD_UNIT_EP_TZONE=True

#############################################
# Specified the number of R and C.
# The library TestModels.mo which is in the Estimation/develop/w_energyplus/models
# assume the same number of R and C. The library has been developed for R &C up to the order 3.
# This can be included in model_param which is in the main script below
NUM_RC=1

#############################################
# ***model_param*** which is in the main function is the json which 
# specifies the simulation parameters
# This can be provided as a file.

import os
##########################################
# DO NOT MODIFY THE NEXT two lines for matplotlib
# when running the code in a docker container.
# THIS MAKE SURE THAT MPCPy _plots
# results in the backend without
# requiring an X-window. Otherwise the mpcpy
# will fail when trying to validate the estimation.
# An alternative will be to start the container with the
# the option which enables support for GUIs
if RUN_DOCKER:
  import matplotlib
  matplotlib.use('Agg')
###########################################

import numpy as N
from datetime import datetime
from mpcpy import variables
from mpcpy import units
from mpcpy import exodata
import time

#========================================================
#==== Clone EnergyPlusToFMU repository ====
def get_energyplustofmu():
    from git import Repo
    import os
    import shutil
    if not os.path.exists(os.path.join(os.getcwd(),"eplustofmu")):
        print ("=========Cloning the EnergyPlusToFMU repository.\n")
        clo_dir = os.path.join(os.getcwd(), "eplustofmu")
        Repo.clone_from("https://github.com/lbl-srg/EnergyPlusToFMU.git", \
                            clo_dir, branch = "master", depth=1)

#========================================================
#==== Export the IDF file as an FMU ====
def export_idf_as_fmu(pat_eplustofmu, pat_idf, pat_idd, pat_wea ):
    import subprocess as sp
    eplus_main=os.path.join(pat_eplustofmu, "Scripts", "EnergyPlusToFMU.py")
    try:
        print("=========IDF path={!s}".format(pat_idf))
        #print("=========IDD path={!s}".format(pat_idd))
        print("=========Weather path={!s}".format(pat_wea))
        sp.check_output(['python', eplus_main, "-i", pat_idd, "-w", pat_wea, pat_idf])
    except sp.CalledProcessError as e:
        print e.output
        if e.output.startswith('error: {'):
            error = json.loads(e.output[7:]) # Skip "error: "
            print error['code']

#========================================================
#==== Estimate parameters of the model ====
def param_estimation(model_param, ADD_UNIT_EP_TZONE):

    # Simulation settings
    estimation_start_time = model_param['estimation_start_time']
    estimation_stop_time =model_param['estimation_stop_time']
    validation_start_time=model_param['validation_start_time']
    validation_stop_time=model_param['validation_stop_time']

    pat_wea=model_param['wea']
    variable_map=eval(model_param['var_map'])
    con_fil=model_param['con_fil']
    obs_var=model_param['obs_var']
    step_size=model_param['emulator_step_size']
    fmu_path=model_param['fmu_path']
    param_fil=model_param['param_fil']
    moinfo=model_param['rc_param']

    # Setup for running the weather FMU
    weather = exodata.WeatherFromEPW(pat_wea)

    control = exodata.ControlFromCSV(con_fil,
    variable_map,tz_name = weather.tz_name)

    # Running the weather data FMU
    weather.collect_data(estimation_start_time, estimation_stop_time)

    # Collecting the data from the CSV file
    control.collect_data(estimation_start_time, estimation_stop_time)

    # Setting up parameters for emulator model (EnergyPlusFMU)
    from mpcpy import systems
    measurements = {obs_var : {}}
    measurements[obs_var]['Sample'] = variables.Static('sample_rate_Tzone',
    step_size,units.s)
    fmupath=fmu_path

    print("=========Run emulation model with FMU={!s}".format(fmu_path))
    emulation = systems.EmulationFromFMU(measurements,fmupath=fmu_path,
    control_data = control.data, tz_name = weather.tz_name)

    # Running the emulator EnergyPlus FMU
    emulation.collect_measurements(estimation_start_time, estimation_stop_time)

    # Add units to EnergyPlus output variables
    if((ADD_UNIT_EP_TZONE==True) and obs_var=='Tzone'):
        print("==========WARNING: When using E+FMU, if the output of E+ is the "
        "zone temperature, then the next lines will add the unit degC to the "
        "output results. This is only valid for E+ and an output which is Tzone.")
        data = measurements[obs_var]["Measured"].display_data()
        name = measurements[obs_var]["Measured"].name

    # Set new variable with same data and name and units degC
    measurements[obs_var]["Measured"] = variables.Timeseries(name, data, units.degC)

    from mpcpy import models
    parameters = exodata.ParameterFromCSV(param_fil)
    parameters.collect_data()
    parameters.display_data()

    # Defning model to be use for parameter estimation
    model = models.Modelica(models.JModelica,models.RMSE,
                            emulation.measurements,
                            moinfo = moinfo,
                            parameter_data = parameters.data,
                            weather_data = weather.data,
                            control_data = control.data,
                            tz_name = weather.tz_name)

    #print("=========Simulate model with default parameters={!s}".format(moinfo))
    #model.simulate('1/1/2017', '1/2/2017')
    #model.parameter_data['zone.T0']['Value'].set_data(model.get_base_measurements('Measured')['Tzone'].loc[start_time_est_utc])

    #model.display_measurements('Simulated')
    print("=========Run parameter estimation for model={!s}".format(moinfo))
    print("=========Start time={!s}, Stop time={!s}, Observed variable={!s}".format(
      estimation_start_time, estimation_stop_time, obs_var))
    model.estimate(estimation_start_time, estimation_stop_time, [obs_var])

    # Validate the estimation model by comparing measured vs. simulated data
    # IMPORTANT: The accuracy of the validation depends on the initial temperature set
    # in the Modelica models. A parameter T0 is defined to set the initial
    # temperatures of the room air or internal mass. this should be set to
    # to the initial temperatures measured from the emulator.
    model.validate(validation_start_time, validation_stop_time, 'validate_tra', plot=1)
    print("The Root Mean Square Error={!s}".format(model.RMSE['Tzone'].display_data()))

    # Printing simulation results
    for key in model.parameter_data.keys():
        print(key, model.parameter_data[key]['Value'].display_data())

#======================================================
# rc_param: [Path to RC model file, RC class name, Modelica libraries needed]
# param_fil: Path to the parameters file which specifies parameters to be identified
# con_fil: Path to file with input variable values for emulator and RC model
# estimation_start_time: Estimation start time
# estimation_stop_time: Estimation stop time
# validation_start_time: Validation start time
# validation_stop_time: Validation stop time
# emulator_step_size: Time step of the emulator (E+ zone time step)
# obs_var: Measured variable
# idf: Path to the IDF
# wea: Path to weather file
# var_map: Variable map to match inputs of emulator and RC model to variables in con_fil

#========================================================
if __name__=="__main__":
    import shutil
    # Get the Modelicapath if Buildings library is used
    mo_libs=os.environ.get('MODELICAPATH')
    # The following models parameters can be written in a JSON file and parse so they can be used by the script.
    model_param={
        "rc_param": ["/mnt/shared/develop/w_energyplus/models/TestModels.mo", "TestModels.MPC.R"+str(NUM_RC)+"C"+str(NUM_RC)+"HeatCool", {mo_libs}],
        "param_fil": "/mnt/shared/develop/w_energyplus/parameters/R"+str(NUM_RC)+"C"+str(NUM_RC)+"HeatCool/Parameters.csv",
        "con_fil": "/mnt/shared/develop/w_energyplus/parameters/R"+str(NUM_RC)+"C"+str(NUM_RC)+"HeatCool/ControlSignal.csv",
    	"estimation_start_time": "1/1/2017",
        "estimation_stop_time": "1/2/2017",
        "validation_start_time":"1/1/2017",
        "validation_stop_time":"1/2/2017",
    	"emulator_step_size": 900,
    	"obs_var": "Tzone",
    	"idf": "/mnt/shared/develop/w_energyplus/models/_fmu_export_schedule.idf",
        "wea": "/mnt/shared/develop/w_energyplus/resources/weather/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
    	"var_map": "{'Qflow_csv' : ('QHeaCoo', units.W)}"
    }

    # Get EnergyPlusToFMU branch
    get_energyplustofmu()

    # This is valid when run in the docker as at installation,
    # a symbolink link is made to the installed version of E+
    model_param['idd']='/usr/local/Energy+.idd'

    # Resolve path to EnergyPlusToFMU
    pat_eplustofmu = os.path.join(os.getcwd(),"eplustofmu")
    print("=========Path to EnergyPlusToFMU={!s}".format(pat_eplustofmu))

    # Create working directory with name being rc model name + idf_file_name
    idf_base = os.path.splitext(os.path.basename(model_param['idf']))[0]
    work_dir=model_param['rc_param'][1] +"_" + idf_base
    pat_work_dir=os.path.join(os.getcwd(), work_dir)

    # Create working directory
    if not (os.path.exists(pat_work_dir)):
        os.mkdir(pat_work_dir)

    # Change to working directory
    os.chdir(pat_work_dir)

    # Export IDF as an FMU
    print ("=========Export IDF={!s} as an FMU for co-simulation 1.0.".format(
        model_param['idf']))
    export_idf_as_fmu(pat_eplustofmu, model_param['idf'],
            model_param['idd'], model_param['wea'])
    print("=========IDF={!s} is exported as an FMU for co-simulation 1.0"
      " in folder={!s}.".format(model_param['idf'], os.getcwd()))

    # Run parameter estimation with MPCPy
    model_param['fmu_path']=os.path.join(pat_work_dir, idf_base) +'.fmu'
    print("=========Path to the FMU={!s}.".format(model_param['fmu_path']))

    # Construct the moinfo for parameter estimation
    print("=========Starting parameter estimation for RC-model={!s}.".format(
        model_param['rc_param'][1]))

    start = time.time()
    # Running parameter estimation
    param_estimation(model_param, ADD_UNIT_EP_TZONE)
    end = time.time()
    print("Parameters estimation took {!s} seconds to run.".format(end - start))

#========================================================
