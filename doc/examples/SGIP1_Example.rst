SGIP1 Analysis Example
======================

Problem Description and Analysis Goals
--------------------------------------

The Smart Grid Interoperability Panel (SGIP), as a part of its work, defined a number of scenarios for use in understanding ways in which transactive energy can be applicable. The first of these (hereafter referred to as "SGIP1") is a classic use case for transactive energy :cite:`15`:

   The weather has been hot for an extended period, and it has now reached an afternoon extreme temperature peak. Electricity, bulk-generation resources have all been tapped and first-tier DER resources have already been called. The grid operator still has back-up DER resources, including curtailing large customers on interruptible contracts. The goal is to use TE designs to incentivize more DER to participate in lowering the demand on the grid.

To flesh out this example the following additions and/or assumptions were made:

     - The scenario will take place in Tucson Arizona where hot weather events that stress the grid are common.
     - The scenario will span two days with similar weather but the second day will include a bulk power system generator outage that will drive real-time prices high enough to incentivize participation by transactively enabled DERs.
     - Only HVACs will be used to respond to transactive signals
     - Roughly 50% of the HVACs on one particular feeder will participate in the transactive system. All other feeders will be modeled by a loadshape that is not price-responsive.
     

The goal of this analysis are as follows:

    - Evaluate the effectiveness of using transactively enabled DERs for reducing peak load.
    - Evaluate the value exchange for residential customers in terms of comfort lost and monetary compensation.
    - Evaluate the impacts of increasing rooftop solar PV penetration and energy storage on the transactive system performance.
    - Demonstrate the capabilities of TESP to perform transactive system co-simulations.


Valuation Model
---------------



Use Case Diagram
................
A Use Case Diagram is helpful in providing a broad overview of the activities taking place in the system being modeled. It shows the external actors and the specific use cases in which each participates as well as any sequencing between specific use cases.

.. figure:: ../media/SGIP1/ValueModel-SGIP1UseCase.png
	:name: fig_value_model_use_case

	Definition of the use cases being modeled in the system under analysis.


Value Flow Diagram
..................
Value flows define the exchanges between actors in the system. For transactive systems, these value exchanges are essential in defining and enabling the transactive system to operate effectively. These value exchanges are often used when defining the key valuation metrics used to evaluate the performance of the system. The diagrams below show the key value exchanges modeled in this system.


.. figure:: ../media/SGIP1/ValueModel-WholesaleElectricityServiceValue.png
	:name: fig_value_model_wholesale

	Value exchanges modeled in the wholesale market
	

.. figure:: ../media/SGIP1/ValueModel-RetailElectricityServiceValue.png
	:name: fig_value_model_retail

	Value exchanges modeled in the retail market
	
.. figure:: ../media/SGIP1/ValueModel-ModifyResourceAndDemandUsingTES.png
	:name: fig_value_model_transactive




Metrics Identification
......................
To guide the development of the analysis, it is important that key metrics are identified in the value model. The diagram below shows the specific metrics identified as sub-elements of the Accounting Table object. Though this diagram does not define the means by which these metrics are calculated, it does define the need for such a defintion, leading to a data requirement from the analysis process.

	Value exchanges modeled during the transactive system operation
.. figure:: ../media/SGIP1/ValueModelMetrics.png
	:name: fig_value_model_metrics

	Identification of the specific metrics to be included in the Accounting Table.


Transactive Mechanism Flowchart (Sequence Diagram)
..................................................

.. figure:: ../media/SGIP1/ClearingSequence2.png
	:name: fig_value_model_clearing_sequence

	Transactive mechanism sequence diagram showing the data exchange between participants


Key Performance Metrics Definitions
...................................

Some (but not all) of the key performance metrics used in this analysis are as follows. A list of the final metrics collected can be found in tabular form in Appendix C of :cite:`Hammerstrom:2017ta`.

Social Welfare:

    .. math::

    SW = \sum_{i=1}^{N_L}U_i(p_i^L) - \sum_{j=1}^{N_G}C_j(p_j^G)
 
     where 
    * :math:`U_i()` are the utility functions of the individual loads
    * :math:`C_j()` are the utility functions of the individual generators 
    * :math:`p_i^L` is the power consumption of the individual loads
    * :math:`p_j^G` is the power generation of the individual generators
    * :math:`N_L` is the total number of loads
    * :math:`N_G` is the total number of generators
    
Electrical energy per day
,,,,,,,,,,,,,,,,,,,,,,,,
    
.. math::
    
    EE_{day} = \sum_{t=0}^{t_{day}} P_{sub}
    
where

    :math:`t` is simulation time
    
    :math:`t_{day}` is the last simulated time for each day
    
    :math:`P_{sub}` is the real power for the feeder as measured at the substation
    
    

Electrical energy per day per customer:
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
 
.. math::
 
    EE_{cust \cdot day} = EE_{day} / N_c

where

    :math:`N_c` is the number of customers
    
    
    
Electrical energy fee per day:
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. math::

    EF_{day} =  \sum_{t=0}^{t_{day}} LMP_{sub}
    
where

    :math:`t` is simulation time
    
    :math:`t_{day}` is the last simulated time for each day
    
    :math:`LMP_{sub}` is the real power for the feeder as measured at the substation
    
    
    
Electrical energy per day per customer:
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
 
.. math::
 
    EF_{cust \cdot day} = EF_{day} / N_c

where

    :math:`N_c` is the number of customers



Analysis Design Model
---------------------

The analysis design model is a description of the planned analysis process showing how all the various analysis steps lead towards the computation of the key performance metrics. The data requirements of the valuation and validation metrics drive the definition of the various analysis steps that must take place in order to be able to calculate these metrics.

The level of detail is in this model is somewhat subjective and up to those leading the analysis. There must be sufficient detail to avoid the biggest surprises when planning the execution of the analysis but a highly detailed plan is likely to be more effort than it is worth. The analysis design model supports varying levels of fidelity by allowing any individual activity block to be defined in further detail through the definition of subactivities

Top Level
.........

The top level analysis diagram (shown in :numref:`fig_AD_top_level`) is the least detailed model and shows the analysis process at the coarsest level. On the left-hand side of the diagram is the source data (which includes assumptions) and is the only analysis activity with no inputs. The analysis activity blocks in the middle of the diagram show the creation of various outputs from previously created inputs with the terminal activities being the presentation of the final data in the form of tables, graphs, and charts.


.. figure:: ../media/SGIP1/AD_Top_Level.png
	:name: fig_AD_top_level

	Top level view of the analysis design model
	
Source Data
...........

The green source data block in the top level diagram (see :numref:`fig_AD_top_level`) is defined in further detail in a sub-diagram shown in :numref:`fig_AD_data_sources`. Many of these items are more than single values and are more complex data structures themselves. 

.. figure:: ../media/SGIP1/AD_data_sources.png
	:name: fig_AD_data_sources

	Detailed view of the data sources necessary to the SGIP1 analysis.


Develop Transmission and Generation Model
.........................................
The "Develop T+G model" activity block in the top level diagram (see :numref:`fig_AD_top_level`) is defined in further detail in a sub-diagram shown in :numref:`fig_AD_develop_tg_model`. The diagram shows that both generation and transmission network information is used to create a PYPOWER model.

.. figure:: ../media/SGIP1/AD_develop_tg_model.png
	:name: fig_AD_develop_tg_model

	Detailed model of the development process of the transmission and generation system model.
	
	
Develop Distribution Model
..........................
The "Develop dist. model" activity block in the top level diagram (see :numref:`fig_AD_top_level`) is defined in further detail in a sub-diagram shown in :numref:`fig_AD_develop_distribution_model`. The distribution model uses assumptions and information from the Residential Energy Consumer Survey (RECS) to define the properties of the modeled houses as well as the inclusion of rooftop solar PV and the participation in the transactive system. These inputs are used to generate a GridLAB-D model.

.. figure:: ../media/SGIP1/AD_develop_distribution_model.png
	:name: fig_AD_develop_distribution_model
	
	Detailed model of the development process of the distribution system model.



Develop Commercial Building Model
.................................
The "Develop commercial building model" activity block in the top level diagram (see :numref:`fig_AD_top_level`) is defined in further detail in a sub-diagram shown in :numref:`fig_AD_develop_commercial_building_model`. The commercial building model is a predefined Energy+ model paired with a particular TMY3 weather file (converted to EPW for use in Energy+).

.. figure:: ../media/SGIP1/AD_develop_commercial_building_model.png
	:name: fig_AD_develop_commercial_building_model
	
	Detailed model of the development process of the commercial building.
	
	
Prepare co-simulation
.....................
The "Prepare co-simulation" activity block in the top level diagram (see :numref:`fig_AD_top_level`) is defined in further detail in a sub-diagram shown in :numref:`fig_AD_prepare_co-simulation`. The core activity is the "Create co-sim config files" which are used by their respective simulation tools. Additionally, a special metadata file is created from the GridLAB-D model and is used by several of the metrics calculations directly.

.. figure:: ../media/SGIP1/AD_prepare_co-simulation.png
	:name: fig_AD_prepare_co-simulation
	
	Detailed model of the co-simulation configuration file creation.
	

Co-simulation
..............
The "Co-simulation" activity block in the top level diagram (see :numref:`fig_AD_top_level`) is defined in further detail in a sub-diagram shown in :numref:`fig_AD_co-simulation`. The GridLAB-D model plays a central role as a significant portion of the modeling effort is centered around enabling loads (specifically HVACs) to participate in the transactive system. In addition to the previously shown information flows between the activities the dynamic data exchange that takes place during the co-simulation run; this is shown by the "<<flow>>" arrows. 

.. figure:: ../media/SGIP1/AD_co-simulation.png
	:name: fig_AD_prepare_co-simulation
	
	Detailed model of the co-simulation process showing the dynamic data exchanges with "<<flow>>" arrows.
	

Accounting table
................
The "Accounting table" presentation block in the top level diagram (see :numref:`fig_AD_top_level`) is defined in further detail in a series of sub-diagrams shown below. Each line of the accounting table shown in :numref:`fig_value_model_metrics` is represented by a gray "presentation" block, showing the required inputs to produce that metric.

.. figure:: ../media/SGIP1/AT_Average_ASHRAE_Discomfort_Hours.png
	:name: fig_AT_avg_ASHRAE_discomfort_hours
	
	Average ASHRAE discomfort hours metric data flow
	
	
.. figure:: ../media/SGIP1/AT_Bulk_Power_System.png
	:name: fig_AT_bulk_power_system
	
	Bulk power system (T+G) metrics data flows
	
	
.. figure:: ../media/SGIP1/AT_DERs.png
	:name: fig_AT_DERs
	
	Distributed energy resources (DERs) metrics data flows
	
	
.. figure:: ../media/SGIP1/AT_Transactive_Feeder.png
	:name: fig_AT_transactive_feeder
	
	Transactive feeder metric data flows
	
	
.. figure:: ../media/SGIP1/AT_T_and_D_Losses.png
	:name: fig_AT_t_and_d_losses
	
	Transmission and distribution network losses metric data flows
	

Analysis Validation
...................
The "Analysis validation" presentation block in the top level diagram (see :numref:`fig_AD_top_level`) is defined in further detail in a series of sub-diagrams shown below. These are metrics similar to those in the :ref:`Accounting Table` section but they are not necessarily defined by the value exchanges and thus fall outside the value model. These metrics are identified by the analysis designer in cooperation with analysis team as a whole and are used to validate the correct execution of the analysis.


.. figure:: ../media/SGIP1/AV_Bulk_Power_System.png
	:name: fig_AV_bulk_power_system
	
	Bulk power system metrics data flows
	

.. figure:: ../media/SGIP1/AV_Average_Residential_Indoor_Air_Temperature.png
	:name: fig_AV_avg_indoor_air_temp
	
	Residential indoor air temperature metric data flows


.. figure:: ../media/SGIP1/AV_Commercial_Building.png
	:name: fig_AV_commercial_building
	
	Commercial indoor air temperature metric data flows	
	
	
.. figure:: ../media/SGIP1/AV_Residential_PV_and_ES_Impacts.png
	:name: fig_AV_pv_es_impacts
	
	Residential rooftop solar PV and energy storage metrics data flows


	

Simulated System Model
----------------------

:numref:`fig_sgip1` shows the types of assets and stakeholders considered for the use cases in this version. The active market participants include a double-auction market at the substation level, the bulk transmission and generation system, a large commercial building with one-way (price-responsive only) HVAC thermostat, and single-family residences that have a two-way (fully transactive) HVAC thermostat. Transactive message flows and key attributes are indicated in **orange**.

In addition, the model includes residential rooftop solar PV and electrical energy storage resources at some of the houses, and waterheaters at many houses. These resources can be transactive, but are not in this version. The rooftop solar PV has a nameplate efficiency of 20% and inverters with 100% efficiency. inverters are set to operate at a constant power factor of 1.0. The rated power of the rooftop solar PV installations varies from house to house and ranges from roughly 2.7 kW to 4.5 kW.

The energy storage devices also have inverters with 100% efficiency and operate in an autonomous load-following mode that performs peak-shaving and valley-filling based on the total load of the customer's house to which it is attached. All energy storage devices are identical with a capacity of 13.5 kWh and a rated power of 5 kW (both charging and discharging). The batteries are modeled as lithium-ion batteries with a round-trip efficiency of 86%. Other details can be found in :numref:`tbl_sgip1`.


.. figure:: ../media/SGIP1/SGIP1system.png
	:name: fig_sgip1

	SGIP-1 system configuration with partial PV and storage adoption
	

The Circuit Model
.................

:numref:`fig_pp_sgip1` shows the bulk system model in PYPOWER. It is a small system with three generating units and three load buses that comes with
PYPOWER, to which we added a high-cost peaking unit to assure convergence of the optimal power flow in all cases. In SGIP-1 simulations, generating unit 2 was taken offline on the second day to simulate a contingency. The GridLAB-D model was connected to Bus 7, and scaled up to represent multiple feeders. In this way, prices, loads and resources on transmission and distribution systems can impact each other.

.. figure:: ../media/SGIP1/PYPOWERsystem.png
	:name: fig_pp_sgip1

	Bulk System Model with Maximum Generator Real Power Output Capacities

:numref:`fig_taxonomy` shows the topology of a 12.47-kV feeder based on the western
region of PNNL’s taxonomy of typical distribution feeders
:cite:`16`. We use a MATLAB feeder generator script that
produces these models from a typical feeder, including random placement
of houses and load appliances of different sizes appropriate to the
region. The model generator can also produce small commercial buildings,
but these were not used here in favor of a detailed large building
modeled in EnergyPlus. The resulting feeder model included 1594 houses,
755 of which had air conditioning, and approximately 4.8 MW peak load at
the substation. We used a typical weather file for Arizona, and ran the
simulation for two days, beginning midnight on July 1, 2013, which was a
weekday. A normal day was simulated in order for the auction market
history to stabilize, and on the second day, a bulk generation outage
was simulated. See the code repository for more details.

:numref:`fig_school` shows the building envelope for an elementary school model
that was connected to the GridLAB-D feeder model at a 480-volt,
three-phase transformer secondary. The total electric load varied from
48 kW to about 115 kW, depending on the hour of day. The EnergyPlus
agent program collected metrics from the building model, and adjusted
the thermostat setpoints based on real-time price, which is a form of
passive response.

.. figure:: ../media/SGIP1/FeederR1_1.png
	:name: fig_taxonomy

	Distribution Feeder Model (http://emac.berkeley.edu/gridlabd/taxonomy\_graphs/)

.. figure:: ../media/SGIP1/School.png
	:name: fig_school

	Elementary School Model


The Growth Model
................

This version of the growth model has been implemented for yearly
increases in PV adoption, storage adoption, new (greenfield) houses, and
load growth in existing houses. For SGIP-1, only the PV and storage
growth has actually been used. A planned near-term extension will cover
automatic transformer upgrades, making use of load growth more robust
and practical.

:numref:`tbl_sgip1` summarizes the growth model used in this report for SGIP-1. In
row 1, with no (significant) transactive mechanism, one HVAC controller
and one auction market agent were still used to transmit PYPOWER’s LMP
down to the EnergyPlus model, which still responded to real-time prices.
In this version, only the HVAC controllers were transactive. PV systems
would operate autonomously at full output, and storage systems would
operate autonomously in load-following mode.

.. table:: Growth Model for SGIP-1 Simulations
  :name: tbl_sgip1

  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  | **Case**      | **Houses**   | **HVAC Controllers**   | **Waterheaters**   | **PV Systems**   | **Storage Systems**   |
  +===============+==============+========================+====================+==================+=======================+
  | (a) No TE     | 1594         | 1                      | 1151               | 0                | 0                     |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  | (b) Year 0    | 1594         | 755                    | 1151               | 0                | 0                     |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  | (c) Year 1    | 1594         | 755                    | 1151               | 159              | 82                    |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  | (d) Year 2    | 1594         | 755                    | 1151               | 311              | 170                   |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  | (e) Year 3    | 1594         | 755                    | 1151               | 464              | 253                   |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  
  


Simulation Architecture Model
-----------------------------

**TODO: Provides details into the design of the software to execute the analysis, leading to the ability to calculate the key performance and validation metrics.**

Simulated Functionalities
.........................

The functionalities shown in :numref:`fig_sgip1` are implemented in simulation through a collection of software entities. Some of these entities perform dual roles (such as PYPOWER), solving equations that define the physical state of the system (in this case by solving the powerflow problem) and in also performing market operations to define prices (in this case by solving the optimal power flow problem).

    -  **GridLAB-D**
        - Simulates the physics of the electrical distribution system by solving the power flow of the specified distribution feeder model. To accomplish this it must provide the total distribution feeder load to PYPOWER (bulk power system simulator) and receives from it the substation input voltage.
        - Simulates the thermodynamics and HVAC thermostat control for all residential buildings in the specified distribution feeder model. Provides thermodynamic state information to the Substation Agent to allow formation of real-time energy bids.
        - Simulates the production of the solar PV panels and their local controller (for the cases that include such devices).
        Simulates the physics of the energy storage devices and the behavior of their local controllers.
    - **Substation Agent**
        - Contains all the transactive agents for the residential customers. Using the current state of the individual customers' residences (*e.g.* indoor air temperature) These agents form real-time energy bids for their respective customers and adjust HVAC thermostat setpoints based on the cleared price.
        - Aggregates all individual HVAC agents' real-time energy bids to form a single bid to present to the wholesale real-time energy market.
    - **EnergyPlus**
        - Simulates the thermodynamics of a multi-zone structure (an elementary school in this case)
        - Simulates the integrated controller of said structure
        - Communicates electrical load of said structure to GridLAB-D for its use in solving the powerflow of the distribution feeder model.
    - **PYPOWER**
        - After collecting the load information from GridLAB-D (and scaling it up to a value representative of an entire node in the transmission model) solves the bulk power system power flow to define the nodal voltages, communicating the appropriate value to GridLAB-D.
        - Using the bid information from the generation natively represented in the bulk power system model and the price-responsive load bids provided by the Substation Agent, find the real-time energy price for each node the bulk power system (the LMP) by solving the optimal power flow problem to find the least-cost dispatch for generation and flexible load. Communicate the appropriate LMP to the Substation Agent.


.. figure:: ../media/SGIP1/ClearingSequence2.png
	:name: fig_clearing_sequence

	Sequence of operations to clear market operations
	
Figure :numref:`fig_clearing_sequence` is a sequence diagram showing the order of events and communication of information between the software entities. 

Due to limitations in the load modeling provided by Energy+, some expected interactions are not included in this system model. Specifically:

    - The loads modeled internally in Energy+ are not responsive to voltage and thus the interaction between it and GridLAB-D is only one way: Energy+ just provides a real power load; GridLAB-D does not assume a power factor and the the Energy Plus Agent (which is providing the value via FNCS) does not assume one either.
    - The Energy Plus agent is only price responsive and does not provide a bid for real-time energy.



Data Collection
...............
The data collection for TESP is handled in a largely standardized way. Each simulation tool produces an output dataset with key measurements. This data is typically stored in a JSON file (with an exception or two where the datasets are large and HDF5 is used). The specific data collected is defined in the :ref:`metrics section<design_reference_metrics>` of the TESP  :ref:`design_reference`.

The JSON data files are post-processed by Python scripts (one per simulation tool) to produce Python dictionaries that can then be queried to further post-process the data or used directly to create graphs, charts, tables or other presentations of the data from the analysis. Metadata files describing the models used in the analysis are also used when creating these presentations.
 

Running the Example
-------------------

As shown in :numref:`tbl_sgip1`, the SGIP1 example is actually a set of five separate co-simulation runs. Performing each run takes somewhere around two hours (depending on the hardware) though they are entirely independent and thus can be run in parallel if sufficient computation resources are available. To avoid slowdowns due to swapping, it is recommended that each run be allocated 16Gb of memory.

To launch one of these runs, only a few simple commands are needed::

    cd ~/tesp/examples/sgip1
    python3 prepare_cases.py # Prepares all SGIP1 cases
    # run and plot one of the cases
    ./runSGIP1b.sh
    
    
``./runSGIP1b.sh`` will return a command prompt with the co-simulation running in the background. To check how far along the co-simulation monitoring one of the output files is the most straight-forward way::

    tail -f SGIP1b.csv
    
The first entry in every line of the file is the number of seconds in the co-simulation that have been completed thus far. The co-simulation is finished at 172800 seconds. After that is complete, a set of summary plots can be created with the following command::

    python3 plots.py SGIP1b
    


Analysis Results - Model Validation
-----------------------------------
The graphs below were created by running ``validation_plots.py`` (**TODO: Update default path to match where the data will be) to validate the performance of the models in the co-simulation. Most of these plots involve comparisons across the cases evaluated in this study (see :numref:`tbl_sgip1`).


.. figure:: ../media/SGIP1/validation_generator_outputs.png
	:name: fig_validation_generator_outputs
	
	Generator outputs of bulk power system, showing the loss of Unit 3 on the second day.
	
	
.. figure:: ../media/SGIP1/validation_transactive_bus_prices.png
	:name: fig_validation_transactive_bus_prices
	
	Wholesale market prices (LMPs) for base and transactive cases, showing lower prices during the peak of the day as transactively participating loads respond.	
	
	
.. figure:: ../media/SGIP1/validation_transactive_bus_loads2.png
	:name: fig_validation_transactive_bus_loads4
	
	Total load for transactive feeder in base and transactive case. Should show peak-shaving, valley-filling, and snapback as prices come down off their peak.
	
	
.. figure:: ../media/SGIP1/validation_transactive_bus_loads4.png
	:name: fig_validation_transactive_bus_loads2
	
	Total load for transactive feeder in for four transactive cases with increasing levels of rooftop solar PV and energy storage penetration.


.. figure:: ../media/SGIP1/validation_residential_indoor_temperature.png
	:name: fig_validation_residential_indoor_temperature
	
	Average residential indoor air temperature for all houses in both base and transactive case. The effect of the transactive controller for the HVACS drives lower relatively lower temperatures during low price periods and relatively higher prices during higher periods.
	
	
.. figure:: ../media/SGIP1/validation_commercial_building_indoor_temperature.png
	:name: fig_validation_commercial_building_indoor_temperature
	
	Commercial building (as modeled in Energy+) indoor air temperature for the base and transactive case. Results should be similar to the residential indoor air temperature with lower temperatures during low-price periods and higher temperatures during high-price periods.
	
	
.. figure:: ../media/SGIP1/validation_solar_output.png
	:name: fig_validation_solar_output_output
	
	Total residential rooftop solar output on the transactive feeder across the four cases within increasing penetration. The rooftop solar is not price responsive. As expected, increasing PV penetration showing increased PV production.
	
	
.. figure:: ../media/SGIP1/validation_ES_output.png
	:name: fig_validation_ES_output_output
	
	Total residential energy storage output on the transactive feeder across the four cases within increasing penetration. The energy storage controller engages in peak-shaving and valley-filling based on the billing meter for the residential customer.
	
	
	
	


Analysis Results - Key Performance Metrics
------------------------------------------

Summary metrics results, likely in tabular form. May copy results from publications

Related Publications
--------------------

This use of TESP to perform the SGIP1 analysis resulted in the following related publications:

    S. E. Widergren, D. J. Hammerstrom, Q. Huang, K. Kalsi, J. Lian, A. Makhmalbaf, T. E. McDermott, D. Sivaraman, Y. Tang, A. Veeramany, and J. C. Woodward. Transactive Systems Simulation and Valuation Platform Trial Analysis. Technical Report PNNL-26409, Pacific Northwest National Laboratory (PNNL), Richland, WA (United States), Richland, WA, Apr. 2017. DOI: 10.2172/1379448. Available at: http://www.osti.gov/servlets/purl/1379448/
    
    Q. Huang, T. McDermott, Y. Tang, A. Makhmalbaf, D. Hammerstrom, A. Fisher, L. Marinovici, and T. D. Hardy. Simulation-Based Valuation of Transactive Energy Systems. Power Systems, IEEE Transactions on, May 2018. DOI: 10.1109/TPWRS.2018.2838111. Available at: https://ieeexplore.ieee.org/document/8360969/






