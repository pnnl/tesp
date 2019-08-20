# Communication Network Example

This example will compare a transactive case with and without an external
communication network. To run and plot the base case without comms on Mac/Linux:

1. python3 make_comm_base.py
2. cd Nocomm_Base
3. chmod +x *.sh
4. ./run.sh
5. python3 plots.py Nocomm_Base & # use pythonw on Mac

On Windows:

1. python make_comm_base.py
2. cd Nocomm_Base
3. run
4. python plots.py Nocomm_Base

# Combined Feeder Example

This example combines three populated GridLAB-D taxonomy feeders to run as one federate
with one substation transformer. 

First, configure each feeder separately to have the house,
storage, solar and other populations as if they were part of a standalone TESP case. There 
will be a case configuration JSON file for each feeder. It's important that each JSON file
have a unique CaseName, e.g., *Feeder1*, but a common WorkingDirectory, e.g., *./CombinedCase*

Second, run the Python script that combines all feeders into a single TESP case. Following
the example provided in *combine_feeders.py*, notice that the substation transformer size
has been set at 20 MVA to serve all three feeders, compared to the original 12 MVA size in
each separate JSON file. Your own example may need a different substation transformer size, but
otherwise, the modifications to *combine_feeders.py* should be straightforward.

Third, you have to change run.bat or run.sh to run the combined case, because the *combine_feeders.py*
script leaves them set up to run just the first feeder.  There are two example modified files provided,
with the changes marked in ***bold italic***.

Fourth, you might need to hand-edit the PYPOWER JSON file, e.g., *Feeder1_pp.json*, with adjustments to the GridLAB-D/FNCS
load scaling factor.

## runcombined.sh

(export FNCS_BROKER="tcp://*:5570" && export FNCS_FATAL=YES && exec fncs_broker 4 &> broker.log &)

(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS -D METRICS_FILE=***CombinedCase***_metrics.json ***CombinedCase***.glm &> gridlabd.log &)

(export FNCS_CONFIG_FILE=***CombinedCase***_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('***CombinedCase***_agent_dict.json','***CombinedCase***')"  &> substation.log &)

(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('Feeder1_pp.json','***CombinedCase***')"  &> pypower.log &)

(export WEATHER_CONFIG=Feeder1_Weather_Config.json && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')"  &> weather.log &)

## runcombined.bat

set FNCS_FATAL=yes

set FNCS_TIME_DELTA=

set FNCS_CONFIG_FILE=

start /b cmd /c fncs_broker 4 ^>broker.log 2^>^&1

set FNCS_CONFIG_FILE=

start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=***CombinedCase***_metrics.json ***CombinedCase***.glm ^>gridlabd.log 2^>^&1

set FNCS_CONFIG_FILE=***CombinedCase***_substation.yaml

start /b cmd /c python -c "import tesp_support.api as tesp;tesp.substation_loop('***CombinedCase***_agent_dict.json','***CombinedCase***')" ^>substation.log 2^>^&1

set FNCS_CONFIG_FILE=pypower.yaml

start /b cmd /c python -c "import tesp_support.api as tesp;tesp.pypower_loop('Feeder1_pp.json','***CombinedCase***')" ^>pypower.log 2^>^&1

set FNCS_CONFIG_FILE=

set WEATHER_CONFIG=Feeder1_Weather_Config.json

start /b cmd /c python -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" ^>weather.log 2^>^&1

## Running CombinedCase

To set up and run CombinedCase on Mac/Linux:

1. python3 combine_feeders.py
2. cd CombinedCase
3. cp ../runcombined.sh .
4. chmod +x *.sh
5. ./runcombined.sh

To set up and run CombinedCase on Windows:

1. python combine_feeders.py
2. cd CombinedCase
3. copy ..\runcombined.bat
4. runcombined.bat

### File Directory

- *clean.bat*; removes the CombinedCase and Nocomm_Base working directories on Windows
- *combine_feeders.py*; script that combines three taxonomy feeders into a self-contained TESP case in the CombinedCase subdirectory (creates and/or overwrites the subdirectory as needed)
- *Feeder1.json*; feeder configuration to use R3-12.47-2 in CombinedCase
- *Feeder2.json*; feeder configuration to use GC-12.47-1 in CombinedCase (this is a commercial feeder with three 2.5-MVA load connection points for large buildings in EnergyPlus/Modelica, or industrial loads defined in player files)
- *Feeder3.json*; feeder configuration to use R1-12.47-3 in CombinedCase
- *Nocomm_Base.json*; case configuration for the R5-12.47-5 feeder with no large building and no communications network
- *make_comm_base.py*; script that reads Nocomm_Base.json and creates a self-contained TESP case in the Nocomm_Base subdirectory (creates and/or overwrites the subdirectory as needed)
- *Nocomm_Base.json*; case configuration for the R5-12.47-5 feeder with no large building and no communications network
- *runcombined.bat*; example hand-edited batch file to run CombinedCase on Windows
- *runcombined.sh*; example hand-edited script file to run CombinedCase on Mac/Linux
- *show_config.py*; script that shows the case configuration GUI; use to open, edit and save Nocomm_Base.json

Copyright (c) 2017-2019, Battelle Memorial Institute

License: https://github.com/pnnl/tesp/blob/master/LICENSE
