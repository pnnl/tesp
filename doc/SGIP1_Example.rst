SGIP Analysis Example
======================

Problem Description and Analysis Goals
--------------------------------------

The Smart Grid Interoperability Panel (SGIP), as a part of its work, defined a number of scenarios for use in understanding ways in which transactive energy can be applicable. The first of these (hereafter referred to as "SGIP1") is a classic use case for transactive energy :cite:`15`:

   The weather has been hot for an extended period, and it has now reached an afternoon extreme temperature peak. Electricity, bulk-generation resources have all been tapped and first-tier DER resources have already been called. The grid operator still has back-up DER resources, including curtailing large customers on interruptible contracts. The goal is to use TE designs to incentivize more DER to participate in lowering the demand on the grid.

To flesh out this example the following additions and/or assumptions were made:

     - The scenario will take place in Tucson Arizona where hot weather events that stress the grid are common.
     - The scenario will span two days with similar weather but the second day will include a bulk power system generator outage that will drive real-time prices high enough to incentivize participation by transactively enabled DERs.
     - Only HVACs will be used to respond to transactive signals
     - Roughly 50% of the HVACs on one particular feeder will participate in the transactive system. All other feeders will be modeled by a loadshape that is not price-responsive. **TODO: Determine how much of the total system load is price-responsive.**
     

The goal of this analysis are as follows:

    - Evaluate the effectiveness of using transactively enabled DERs for reducing peak load.
    - Evaluate the value exchange for residential customers in terms of comfort lost and monetary compensation.
    - Demonstrate the capabilities of TESP to perform transactive system co-simulations.


Valuation Model
---------------

Value Flow Diagram
..................


Transactive Mechanism Flowchart (Sequence Diagram)
..................................................


Key Performance Metrics Definitions
...................................

Some (but not all) of the key performance metrics used in this analysis are as follows. The entire metric list can be found in :cite:`Hammerstrom:2017ta`

.. Social Welfare:

    .. math::

    SW = \sum_{i=1}^{N_L}U_i(p_i^L) - \sum_{j=1}^{N_G}C_j(p_j^G)
 
     where 
    :math: `U_i()` are the utility functions of the individual loads
    :math: `C_j()` are the utility functions of the individual generators 
    :math: `p_i^L` is the power consumption of the individual loads
    :math: `p_j^G` is the power generation of the individual generators
    :math: `N_L` is the total number of loads
    :math: `N_G` is the total number of generators
    
Electrical energy per day
    
.. math::
    
    EE_{day} = \sum_{t=0}^t_{day} P_{sub}
    
where
    :math: `t` is simulation time
    :math: `t_{day}` is the last simulated time for each day
    :math: `P_{sub}` is the real power for the feeder as measured at the substation
    
Electrical energy per day per customer:
 
.. math::
 
    EE_{day * cust} = EE_{day} / N_c

where
    :math: `N_c` is the number of customers
    
Electrical energy fee per day:

.. math::

    EF_{day} =  \sum_{t=0}^t_{day} LMP_{sub}
    
where
    :math: `t` is simulation time
    :math: `t_{day}` is the last simulated time for each day
    :math: `LMP_{sub}` is the real power for the feeder as measured at the substation
    
Electrical energy per day per customer:
 
.. math::
 
    EF_{day * cust} = EF_{day} / N_c

where
    :math: `N_c` is the number of customers


SGIP 1 Model Overview
---------------------

:numref:`fig_sgip1` shows the types of assets and stakeholders considered for the
use cases in this version. The active market participants include a
double-auction market at the substation level, the bulk transmission and
generation system, a large commercial building with one-way responsive HVAC
thermostat, and single-family residences that have a two-way responsive HVAC
thermostat. Transactive message flows and key attributes are indicated
in **orange**.

In addition, the model includes PV and storage resources at some of the
houses, and waterheaters at many houses. These resources can be
transactive, but are not in this version because the corresponding
separate TEAgents have not been implemented yet. Likewise, the planned
new TEAgent that implements load shedding from the substation has not
yet been implemented.

.. figure:: ./media/SGIP1system.png
	:name: fig_sgip1

	SGIP-1 system configuration with partial PV and storage adoption

The Circuit Model
-----------------

:numref:`fig_pp_sgip1` shows the bulk system model in PYPOWER. It is a small system
with three generating units and three load buses that comes with
PYPOWER, to which we added a high-cost peaking unit to assure
convergence of the optimal power flow in all cases. In SGIP-1
simulations, generating unit 2 was taken offline on the second day to
simulate a contingency. The GridLAB-D model was connected to Bus 7, and
scaled up to represent multiple feeders. In this way, prices, loads and
resources on transmission and distribution systems can impact each
other.

.. figure:: ./media/PYPOWERsystem.png
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

.. figure:: ./media/FeederR1_1.png
	:name: fig_taxonomy

	Distribution Feeder Model (http://emac.berkeley.edu/gridlabd/taxonomy\_graphs/)

.. figure:: ./media/School.png
	:name: fig_school

	Elementary School Model

The Growth Model
----------------

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
  | No TE         | 1594         | 1                      | 1151               | 0                | 0                     |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  | Year 0        | 1594         | 755                    | 1151               | 0                | 0                     |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  | Year 1        | 1594         | 755                    | 1151               | 159              | 82                    |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  | Year 2        | 1594         | 755                    | 1151               | 311              | 170                   |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+
  | Year 3        | 1594         | 755                    | 1151               | 464              | 253                   |
  +---------------+--------------+------------------------+--------------------+------------------+-----------------------+

Insights and Lessons Learned
----------------------------

A public demonstration and rollout of TESP was included in a workshop on
April 27, 2017, in Northern Virginia. That workshop marked the end of
TESP’s first six-month release cycle. The main accomplishment, under our
simulation task, is that all of the essential TESP components are
working over the FNCS framework and on multiple operating systems. This
has established the foundation for adding many more features and use
case simulations over the next couple of release cycles, as described in
Section 3. Many of these developments will be incremental, while others
are more forward-looking.

Two significant lessons have been learned in this release cycle, meaning 
those two things need to be done differently going forward.  The first 
lesson relates to MATPOWER.  It has been difficult to deploy compiled 
versions of MATPOWER on all three operating systems, and it will be 
inconvenient for users to manage different versions of the required MATLAB 
runtime.  This is true even for users who might already have a full 
version of MATLAB.  Furthermore, we would need to modify MATPOWER source 
code in order to detect non-convergence and summarize transmission system 
losses.  This led us to replace MATPOWER with PYPOWER :cite:`17` for 
the public releases of TESP.  During 2019, TESP will be able to use 
AMES for day-ahead markets and unit commitment :cite:`18`.  

The second lesson relates to EnergyPlus modeling, which is a completely
different domain than power system modeling. We were able to get help
from other PNNL staff to make small corrections in the EnergyPlus model
depicted in :numref:`fig_school`, but it’s clear we will need more building model
experts on the team going forward. This will be especially true as we
integrate VOLTTRON-based agents into TESP.

