Feeder_Generator.m is a MATLAB script that takes power-flow only taxonomy feeders (distributed with GLD) and populates them with houses and accompanying real-life loads. This creates a feeder model that is much more dynamic and responsive, allowing for higher fidelity in the simulation.

The script is very lengthy but the most important user inputs are in the first hundred lines or so. For work with FNCS, the two most relavent are:

* `use_flags.fncs_powerflow`
* `use_flags.fncs_transactive`

These flags are indepent and setting either one to `1` will enable the appropriate parts of the feeder model and add the appropriate line to the FNCS GLD config file.

Other inputs of importance:

* `TechnologyToTest`  - Defines which combination of features to be be included when populating the feeder. The defaults are shown in "Feeder_Generator_TSP" while specific combinations are stored in "TechnologyParameters_TSP" for easily switching between options. None of the values in this file define the FNCS flags meaning that these flags must be set in the "Feeder_Generator_TSP" file.
* `taxonomy_files` -  Defines which base feeders will be populated.
* `taxonomy_directory` - Location of the base feeder models.
* `output_directory` - Location where populated feeders will be saved.
* `rng_seed` - There are various parameters of the houses that are added to the models that are randomized; this value defines the seed that is used to create those randomized values.

Running "Feeder_Generator_TSP" will take one instance each of the files listed in `taxonomy_files` and populate it with houses and other equipment as defined by the flags at the beginning of the files. To aid in the growth model implementation, all residences have batteries and solar PV (with corresponding inverters) included with their status set to `OFFLINE`. Simple changing that status will allow that equipment to begin operating.

Specifications of installed equipment:

* Solar panel 
  * Size: 10% of house square footage
  * Efficiency: 20%
  * Inverter: 90% of panel capacity
* Battery
  * Size: 13.5 kWh (Telsa Powerwall 2)
  * Efficiency:  86% (round trip)
  * Inverter power: 5kW
  * Operating mode: load-following on houses load, charging when house load goes less at least 0.1kW negative (overgenerating), discharging when house load is at least 3kW.