# jModelica large building example

Copyright (c) 2017-2022, Battelle Memorial Institute

This example has the jModelica large building model. 

The largeBulding.py file is the main script to run the simulations. Two parameters need to be supplied to the script: 
	
	- *start day of the simulation: it is the day of the year(1=Jan; 32=Feb; 60=Mar; 91=Apr; 121=May; 152=Jun; 182=Jul; 213=Aug; 244=Sep; 274=Oct; 305=Nov; 335=Dec). 

	- *duration of the simulation: it is the number of days the simulation needs to run.

	- *There is a 3rd optional parameter to this script, the time step, the default value is 60 in the unit of second.

The LargeOffice.py is the class where the actual FMU model is called and run, it is used in the largeBulding.py script. 

Currently, there are four inputs to the model:

	- *current time,
	- *temperature and wind speed from weather agent,
	- *control inputs, includes TSetHeating, TSetCooling and LightDimmer, using default value for now,
	- *voltage, three phase line to line voltages from gridlabd simulation as a dictionary.

The output from the model are:

	- *total power,
	- *temperature of the rooms as an array of double.
