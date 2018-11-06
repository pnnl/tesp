DSO+T Simulation Files
----------------------

Copyright (c) 2018, Battelle Memorial Institute

Directory of input and script files:

 - *clean.sh*; removes generated input and output files, EXCEPT Bus?.glm
 - *ercot_8.json*; bulk system model, copied from ../bulk_system and then edited
 - *fncsERCOT.py*; reads ercot_8.json and pypower8.yaml to run the bulk system simulation in PYPOWER, a customization of fncsPYPOWER in tesp_support
 - *kill5570.sh*; helper script to kill all FNCS processes
 - *plot_gld.py*; customization of process_gld for the ERCOT model
 - *plot_pp.py*; customization of process_pypower for the ERCOT model
 - *plots.py*; calls process_gld, process_houses and process_agents from tesp_support, for one bus
 - *prep_ercot_auction.py*; configures the transactive agent dictionary and FNCS subscriptions based on the GridLAB-D dictionary
 - *prepare_case.py*; writes the GridLAB-D dictionary for each bus, then calls prep_ercot_auction.py for each bus
 - *pypower8.yaml*; FNCS subscriptions for the bulk_system
 - *run.sh*; runs the bulk system and 8 feeders, but no transactive agents
 - *run_market.sh*; runs the bulk system and 8 feeders, with transactive agents
 - *run_market_debug.sh*; runs the transactive simulation with extra FNCS output

Directory of generated input files:

 - *Bus?.glm*; GridLAB-D inputs made from ../dist_system/populate_feeders.py
 - *Bus?_FNCS_Config.txt*; GridLAB-D publish and subscribe messages for FNCS, from prepare_case.py
 - *Bus?_agent_dict.json*, transactive thermostat metadata for post processing, from prepare_case.py
 - *Bus?_auction.yaml*; transactive thermostat configurations, from prepare_case.py
 - *Bus?_glm_dict.json*; GridLAB-D metadata for post processing, from prepare_case.py

Directory of generated output files (note: metadata is embedded in the json files):

 - *ercot_8_m_dict.json*; metadata for bulk system post processing, written by fncsERCOT.py
 - *Bus?.log*; GridLAB-D output log, includes resource usage
 - *auction?.log*; transactive agent output log, includes resource usage
 - *auction_Bus?_metrics.json*; intermediate auction metrics for transactive agents 
 - *billing_meter_Bus?_metrics.json*; intermediate metrics for GridLAB-D meters and triplex_meters 
 - *broker.log*; fncs_broker output log
 - *bulk.log*; PYPOWER output log, includes resource usage
 - *bus_ercot_8_metrics.json*; intermediate bulk system bus metrics, e.g. voltage and LMP
 - *capacitor_Bus?_metrics.json*; intermediate capacitor switching metrics for GridLAB-D
 - *controller_Bus?_metrics.json*; intermediate thermostat metrics for GridLAB-D
 - *ercot_8_opf.csv*; optimal power flow solution summary at the market clearing interval, plot in Excel
 - *ercot_8_pf.csv*; regular power flow solution summary at the simulation time step, plot in Excel
 - *gen_ercot_8_metrics.json*; intermediate bulk system generating unit metrics
 - *house_meter_Bus?_metrics.json*; intermediate house metrics for GridLAB-D
 - *inverter_Bus?_metrics.json*; intermediate PV and storage metrics for GridLAB-D
 - *regulator_Bus?_metrics.json*; intermediate tap changer metrics for GridLAB-D
 - *substation_Bus?_metrics.json*; intermediate feeder-level metrics for GridLAB-D
 - *sys_ercot_8_metrics.json*; intermediate bulk system-level metrics

To run the 8-bus simulations:

	 a. Make any feeder model updates using ../dist_system/populate_feeders.py
	 b. Make any bulk system model updates by editing ercot_8.json
	 c. If you changed the time step or time span in steps a and b, check lines 41-42 of prep_ercot_auction.py. Also check lines 11-18 of run.sh to make sure the number of hours (24 by default) matches the new time span.
	 d. "python3 prepare_case.py" generates all the input files from Bus?.glm
	 e. "run.sh" or "run_market.sh" to launch the simulations
	 f. "cat *.csv" to monitor progress from a terminal window

To plot the 8-bus simulations:

    a. "python plots.py Bus1" plots the feeder, house and auction results for Bus1, using variable selections built in to tesp_support
	b. "python plot_pp.py" plots the bulk system results
	c. "python plot_gld.py Bus1" plots the bill, meter voltages and house temperatures over all houses for Bus1

