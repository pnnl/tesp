8-Bus and 200-Bus ERCOT Bulk System Models
------------------------------------------

Copyright (c) 2018, Battelle Memorial Institute

Directory of input and script files:

- *200NodesData.json*; clustered load, generation and bus coordinates
- *Buses.csv*; defines buses for the 200-bus model, but not all retained
- *Buses8.csv*; defines buses for the 8-bus model
- *Lines.csv*; defines lines for the 200-bus model, but not all retained
- *Lines8.csv*; defines lines for the 8-bus model
- *RetainedBuses.csv*; edited Buses.csv
- *RetainedLines.csv*; edited Lines.csv
- *RetainedTransformers.csv*; transformers and tap ratios for 200-bus model, originally created manually
- *Units.csv*; defines generators for the 200-bus model
- *Units8.csv*; defines generators for the 8-bus model
- *clean.bat*; removes temporary output files on Windows
- *clean.sh*; removes temporary output files on Linux or Mac OS X
- *ercot_200.json*; 200-bus model for PYPOWER
- *ercot_8.json*; 8-bus model for PYPOWER
- *loopERCOT.py*; runs a daily simulation of the 8-bus model with varying load and wind
- *make_case.py*; makes ercot_200.json from RetainedBuses.csv, RetainedLines.csv, RetainedTransformers.csv and Units.csv
- *make_case8.py*; makes ercot_8.json from Buses8.csv, Lines8.csv and Units8.csv
- *make_lines.py*; produce Lines.csv from 200NodesData.json
- *make_units.py*; produce Units.csv from 200NodesData.json
- *process_pypower.py*; plots the metrics from loopERCOT solution
- *run_ercot.py*; spot-check the regular or optimal power flow solution at peak load for either the 8-bus or 200-bus model
- *test_wind.py*; runs a yearly wind plant simulation; edit this file to change the plant size
- *wind_plants.py*; runs a two-day output simulation of wind plants in the 8-bus model

To regenerate the 8-Bus Model:

    a. Edit Buses8.csv, Lines8.csv and Units8.csv. No transformers are included.
    b. Run 'python make_case8.py'

To regenerate the 200-Bus Model:

    a. Edit RetainedBuses.csv, RetainedLines.csv, RetainedTransformers.csv and Units.csv.
	b. Run 'python make_case.py'

To run the 8-bus Model:

	a. edit run_ercot.py to make sure it runs ercot_8.json
    b. Run 'python run_ercot.py' to spot check the PF and OPF solutions at peak load.
    c. Run 'python loopERCOT.py' to run a time-stepping check with varying load.
    d. Run 'python process_pypower.py' to plot the results of loopERCOT.py

To run the 200-bus Model:

	a. edit run_ercot.py to make sure it runs ercot_200.json
	b. Run 'python run_ercot.py' to spot check the PF and OPF solutions at peak load.

loopERCOT.py and process_pypower.py have not been tested yet with the 200-bus model.

