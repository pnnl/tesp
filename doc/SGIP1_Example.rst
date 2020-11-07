SGIP and TE30 Examples
======================

TE30 Example
------------

:numref:`fig_te30` shows a reduced-order demonstration model that
incorporates all three federated co-simulators; GridLAB-D simulating 30
houses, EnergyPlus simulating one large building, and PYPOWER or
MATPOWER simulating the bulk system. This model can simulate two days of
real time in several minutes of computer time, which is an advantage for
demonstrations and early testing of new code. There aren’t enough market
participants or diverse loads to produce realistic results at scale.
Even so, this model is the recommended starting point for TESP.

.. figure:: ./media/TE30system.png
	:name: fig_te30

	Demonstration model with 30 houses and a school

The three-phase unresponsive load comes from a GridLAB-D player file on
each phase, connected to the feeder primary. The EnergyPlus load
connects through a three-phase padmount transformer, while the houses
connect through single-phase transformers, ten per phase. Except for
transformers, all of the line impedances in this model are negligible.
One of the house loads has been shown in more detail. It includes a
responsive electric cooling load, lights, and several non-responsive
appliances. In addition, each house has a solar panel connected through
an inverter to the same meter, which might or might not implement net
metering. Storage, vehicle chargers and other appliances (e.g. electric
water heater) could be added. For now, each house is assumed to have gas
heat and gas water heater.

SGIP Use Cases
--------------

TESP will initially respond to four of the Smart Grid Interoperability
Panel (SGIP) use cases :cite:`15` and an additional use case
to illustrate the growth model.

*SGIP-1 and SGIP-6*. “The grid is severely strained in capacity and
requires additional load shedding/shifting or storage resources”
:cite:`15`. The details confirm that this use case addresses
only generation capacity constraints of the type that might be needed
after existing demand-response resources become exhausted.

This use case clearly takes place on a day that available resources are
inadequate in a warm location like California or Arizona. In the
base-case scenario, the system anticipates the event that morning or
even earlier. Contracted demand-response resources—predominantly
distributed generator sets―are scheduled to actuate during the day at
the predicted time of the peak load. While helpful, the demand response
proves inadequate. Therefore, each distribution utility must also
conduct emergency curtailment, meaning that entire distribution circuits
must be intentionally de-energized to reduce system demand. Each utility
is allocated a fraction of the total shortfall to correct.

In the test scenario, nearly everything remains the same, except a
double-auction transactive market is coordinating battery energy storage
and residential space conditioning and electric water heaters. These
controllable assets are presumed to not be contracted by and to not
participate in conventional demand-response. As the last available
resources become dispatched, the costly final resources elevate the
transactive price signal, thus causing transactive assets to respond.
The demand-response resources are dispatched as for the base case,
presuming they were scheduled that morning without consideration of the
transactive system’s response. As the peak demand nears, the need for
emergency curtailment might be reduced or fully avoided by the actions
of the transactive system.

The principal valuation metrics for this use case address the costs and
inconvenience of the emergency curtailment. Interesting impacts include
changes in the numbers of customers curtailed, the durations of the
emergency curtailment, and unserved load.

*SGIP-2*. “DER are engaged based on economics and location to balance
wind resources” :cite:`15`. The scenario narrative states
that ramping, not balancing or fast regulation, should be the target
grid service for this use case.

This use case requires that bulk wind resources are a substantial
fraction (40%) of the region’s bulk resource mix. Wind resources are
highly correlated across the region. If the wind resource disappears
rapidly, then other resources must be rapidly dispatched to replace the
wind energy. This challenge is exacerbated if it occurs while other
demand is increasing. If, however, wind resource materializes rapidly,
other resources must ramp down, and this challenge is amplified if it
occurs while other demand is decreasing. The ideal test day includes
both the rapid ramping up and down of wind resource.

In the base case, supply is scheduled every hour or half-hour. The
system must always allow a margin—ramping reserves―both up and down
should these ramping services be needed. The system counteracts rapid
changes in wind, both up and down, by controlling hydropower generation
and spinning reserves :cite:`15`. The cost of doing this is
often modest, given that hydropower generation might not even be the
marginal resource. But the costs might understate the fact that more
expensive resources might be used to provide this margin, and provision
of ramping might impact hydropower generation maintenance costs. The
cost of reserving resources is incurred regardless whether the system is
ramping up or down. These reserves, as well as the costs of providing
them, are addressed centrally by the system. The provision of ramping
services is not isolated in that the quality of response might excite
balancing and regulation services to become engaged.

In the test case, a transactive system is in operation, but the system
otherwise operates the same.

We do not expect the double-auction transactive system to be
particularly helpful for this use case. The dispatch algorithm generates
the equivalent of a locational marginal price, which is responsive to
the locational cost of marginal resource, efficiency, and transport
constraints. While there will be some benefit caused by the transactive
period being shorter than the scheduling interval, the transactive
system here will respond to the marginal cost, which does not reflect
ramping service costs. So, as wind ramps up and down, there will be a
corresponding helpful reduction and increase in the transactive price
signal. However, the transactive signal is not designed to align with
the scheduling intervals and the corresponding needs for ramping
services that result within each scheduling interval.

Primary impacts will address ramping reserves and their costs under the
alternative scenarios.

*SGIP-3*. “High-penetration of rooftop solar PV causes swings in voltage
on distribution grid” :cite:`15`. Solar generation capacity
is stated to be up to 120% of load. Reversals of power flow can occur.
Solar power intermittency creates corresponding voltage power quality
issues. We choose to focus on the voltage management challenge, given
that flow reversal is not itself a problem if it makes sense for system
economics.

In the base case, this condition might today be disallowed at the
planning stage because of the challenges that reversed power flow might
induce in protection schemes. Presuming such high penetration and
reversed flows are allowed, the distribution feeder must use its
existing resources—capacitors, reactors, regulating transformers—to keep
voltage in its acceptable range. Solar power inverters mostly correct to
unity power factor today. Voltage tends to increase, if uncorrected, at
times that solar power is injected into the distribution system. It is
likely that this feeder will encounter voltage violations and flicker
because of the high penetration and intermittency of the PV generation.

In the test case, the double-auction transactive system is operating on
the high-solar-penetration feeder. Voltage management is not directly
targeted by transactive mechanisms today, but the behaviors of the
mechanisms can affect voltage management.

The primary impacts will be changes in the occurrences of voltage range
violations, power quality events, and operations of voltage controls
(e.g., tap changes) on the feeder.

*SGIP-6*. “A sudden transmission system constraint results in emergency
load reductions” :cite:`15`. A distribution system network
operator with a system having 150 MW peak winter load is given
15-minutes advance notice by his transmission supplier to curtail 40 MW.
The curtailment is to last 2 hours. The distribution system network
operator has no generation resources of his own to use. Business as
usual mitigation is to conduct rolling blackouts. Alternatives exist if
some or all of the emergency curtailment can be satisfied by DER
:cite:`15`. Alternatively, the event might be naturally
exercised by emulating contingency and maintenance outages. These events
would then be stochastic in their occurrences.

SGIP-6 is very similar to SGIP-1, but it is caused by a system
constraint rather than inadequate supply resources. It can be emulated
by reducing the capacity of transmission or distribution that supply the
test feeders. Refer to our discussion of SGIP-1 for the remedial
actions, including conventional demand response, emergency curtailment,
and double-auction transactive system that will be used in the base case
and test scenarios. The valuation metrics and impacts are expected to be
the same.

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

