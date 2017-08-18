.. role:: math(raw)
   :format: html latex
..

Transactive Energy Simulation Platform
======================================

.. sidebar:: Transactive Systems Program

  |logo|

Pacific Northwest National Laboratory has been working on a multi-year
transactive systems program (TSP) funded by the United States Department
of Energy (DOE). The 2016-2017 work included a separate task on
simulation of transactive systems approaches. Previous transactive
simulation work has been closely linked to demonstration projects, and
often not easily repeatable by others. Building on GridLAB-D and other
software modules, we have produced a Transactive Energy Simulation
Platform (TESP) that addresses a wider variety of use cases and drivers
that were described earlier. Equally important, TESP has been designed
for easier customization and use by other researchers, so it can support
a greater variety of design, test and experimentation work in
transactive systems.

The source code, design documents and examples for TESP are being moved
from an internal PNNL repository onto a public site at
https://github.com/pnnl/tesp/, with minimally restrictive open-source
license terms. The main goal of this section is to summarize and explain
the design choices in TESP, in particular the message schemas and
metrics, so that other researchers may evaluate the costs and benefits
of using TESP. The public repository will have more detailed and
up-to-date information.

Goals
-----

Preliminary functional requirements were based on the valuation approach
developed last year [`1 <#_ENREF_1>`__], supplemented by additional
study of use cases and drivers to be published in a companion report. We
also considered the possibility of new transactive pilot projects, as
suggested by NIST’s TE Challenge [`2 <#_ENREF_2>`__]. This led to
adoption of the following objectives:

1. Integration of separate Transactive Energy Agents (TEAgents) that
   encapsulate behaviors of market mechanisms and participants.

2. Separation of the valuation function from simulation.

3. Implementation of an efficient and completely open-source platform
   for Windows, Mac OS X and Linux.

4. Definition of a growth model for multi-year TE simulations.

Objectives 1-3 specifically support use by others, while objective 4
ultimately extends the simulation time horizon up to 20 years.

Design Choices for Version 1
----------------------------

Figure 1 shows the simulation modules federated in Rev 1 of TESP.
GridLAB-D covers the electric power distribution system
[`3 <#_ENREF_3>`__], MATPOWER covers the bulk electric power system
[`4 <#_ENREF_4>`__], and EnergyPlus covers large commercial buildings
[`5 <#_ENREF_5>`__]. These three simulators have been previously
federated at PNNL, but only pairwise (i.e. GridLAB-D with MATPOWER, and
GridLAB-D with EnergyPlus). The use of all three together in a
transactive simulation is new this year. The integrating Framework for
Network Co-simulation (FNCS) manages the time step synchronization and
message exchange among all of the federated simulation modules
[`6 <#_ENREF_6>`__]. In this way, TESP builds mostly on proven
components, which helps mitigate risk in software development. Some of
these components may be upgraded or replaced in future versions, as
described later. However, the overall platform design in Figure 1 still
applies.

|image0|

Figure 1. TESP Rev 1 components federated through FNCS. New work in
green.

New work in Figure 1 has been highlighted in **green**. This primarily
represents custom code implemented in the Python programming language,
which was chosen because:

1. Python is now commonly used in colleges to teach new programmers

2. Python has many available add-on packages for numerics, graphics and
   data handling

3. Python bindings to FNCS already existed

Custom code for TESP can also be implemented in other languages like C++
and Java, and in fact, the “wrappers” or “agents” for MATPOWER and
EnergyPlus have been implemented as separate C++ programs. Our
experience has been that developers with experience in C++ or Java can
easily work in Python, while the converse is not always true. These
factors led to the choice of Python as a default language for
customizing TESP.

Initially, the TEAgents include a double-auction market mechanism, one
per substation, and a dual-ramp thermostat controller, one per house
[`7 <#_ENREF_7>`__]. These were previously hard-coded in GridLAB-D, and
those implementations remain in GridLAB-D, but the separate Python
versions allow others to study and modify just the transactive code
without having to rebuild all of GridLAB-D. Much of the future work
envisioned for TESP would focus on significantly expanding the numbers
and capabilities of TEAgents. Regarding the other new work highlighted
in Figure 1, section 1.3 (next) describes the Growth Model and section
1.5 describes the Valuation scripts.

Operational and Growth Models
-----------------------------

TESP adopts a time-stepping simulation that separates the operational
model, of a system with fixed infrastructure running for hours or days,
from the growth model, of a system with infrastructure that evolves over
months or years. Figure 2 shows these two models in a Unified Modeling
Language (UML) activity diagram [`8 <#_ENREF_8>`__]. After
configuration, the simulation begins with a system in the initial
year-zero state, i.e. with no growth included. The operational model
then begins to run with federated co-simulators in the form of
GridLAB-D, TEAgents, MATPOWER and EnergyPlus. The operational model has
two different time steps, which may vary with time and between
simulators under supervision by FNCS. These are:

1. The operational time step for power system load and resource
   variations, weather variations, and power system control actions,
   e.g. 1 to 60 seconds, although 15 seconds is recommended.

2. The market-clearing time step for transactive systems, e.g. 5, 15 or
   60 minutes.

Events like peak load days, power system faults, transmission line
outages, and bulk generator outages would occur within the operational
model. These involve no permanent changes to the system infrastructure,
and the power system is expected to respond autonomously to such events.
Events like new loads, new distributed energy resources (DER), and
capital investments would occur within the growth model because they
represent permanent changes to system infrastructure. Most of the time,
this will require stopping and re-starting the operational model and its
federated simulators. Future TESP versions will make these transitions
more efficiently. Growth model time steps would usually be monthly,
quarterly or yearly, but could also be as short as weekly. After the
last growth time step, the simulation ends for valuation by
post-processing.

|image1|

Figure 2. Interaction of growth model with operational model

Early versions of the growth model will only include:

1. Fixed growth factors for existing solar, storage and controllable
   loads; input as a schedule of %/year vs. time.

2. Pre-identified feasible sites for new capacitor banks, chosen from a
   list of fixed sizes.

3. Residential rooftop solar adoption models for existing houses
   [`9 <#_ENREF_9>`__, `10 <#_ENREF_10>`__], or a simpler one based
   on total energy use and floor area of the house.

4. Changing size of an existing substation or service transformer.

Later versions are planned to have heuristics that utility system
planners and other agents would use in making investment decisions.
These heuristics will execute between growth model time steps, using
only information available at that point in the simulation.

Messages between Simulators and Agents
--------------------------------------

In Rev 1, TESP simulators exchange a minimal set of messages shown in
Figure 3 and Figure 4.

|image2|

Figure 3. Message Schemas

These messages route through FNCS in a format like
“topic/keyword=value”. In Figure 3, the “id” would refer to a specific
feeder, house, market, or building, and it would be the message topic.
Once published via FNCS, any other FNCS simulator can access the value
by subscription. For example, MATPOWER publishes two values, the
locational marginal price (LMP) at a substation bus and the positive
sequence three-phase voltage at the bus. GridLAB-D subscribes to the
voltage, using it to update the power flow solution. The double-auction
for that substation subscribes to the LMP, using it to represent a
seller in the next market clearing interval. In turn, GridLAB-D
publishes a distribution load value at the substation following each
significantly different power flow solution; MATPOWER subscribes to that
value for its next optimal power flow solution.

|image3|

Figure 4. Message Flows

EnergyPlus publishes three phase power values after each of its
solutions (currently on five-minute intervals). These are all
numerically equal, at one third of the total building power that
includes lights, office equipment, refrigeration and HVAC loads.
GridLAB-D subscribes in order to update its power flow model at the
point of interconnection for the building, which is typically at a 480-V
or 208-V three-phase transformer. EnergyPlus also subscribes to the
double-auction market’s published clearing price, using that value for a
real-time price (RTP) response of its HVAC load.

Message flows involving the thermostat controller, at the center of
Figure 4, are a little more involved. From the associated house within
GridLAB-D, it subscribes to the air temperature, HVAC power state, and
the HVAC power if turned on. The controller uses this information to
help formulate a bid for electric power at the next market clearing,
primarily the price and quantity. Note that each market clearing
interval will have its own market id, and that re-bidding may be allowed
until that particular market id closes. When bidding closes for a market
interval, the double-auction market will settle all bids and publish
several values, primarily the clearing price. The house thermostat
controllers use that clearing price subscription, compared to their bid
price, to adjust the HVAC thermostat setpoint. As noted above, the
EnergyPlus building also uses the clearing price to determine how much
to adjust its thermostat setting. Figure 3 shows several other keyword
values published by the double-auction market and thermostat
controllers; these are mainly used to define “ramps” for the controller
bidding strategies. See the GridLAB-D documentation, or TESP design
documentation, for more details.

These message schemas are limited to the minimum necessary to operate
Version 1, and it’s expected that the schema will expand as new TEAgents
are added. Beyond that, note that any of the simulators may subscribe to
any values that it “knows about”, i.e., there are no security and access
control emulations. This may be a layer outside the scope of TESP.
However, there is also no provision for enforcement of bid compliance,
i.e. perfect compliance is built into the code. That’s clearly not a
realistic assumption, and is within the scope for future versions as
described in Section 3.

Output Metrics to Support Evaluation
------------------------------------

TESP will produce various outputs that support comparative evaluation of
different scenarios. Many of these outputs are non-monetary, so a user
will have to apply different weighting and aggregation methods to
complete the evaluations. This is done in the Evaluation Script, which
is written in Python. These TESP outputs all come from the Operational
Model, or from the Growth Model applied to the Operational Model. For
efficiency, each simulator writes intermediate metrics to Javascript
Object Notation (JSON) files during the simulation, as shown in Figure
5. For example, if GridLAB-D simulates a three-phase commercial load at
10-second time steps, the voltage metrics output would only include the
minimum, maximum, mean and median voltage over all three phases, and
over a metrics aggregation interval of 5 to 60 minutes. This saves
considerable disk space and processing time over the handling of
multiple CSV files. Python, and other languages, have library functions
optimized to quickly load JSON files.

|image4|

Figure 5. Partitioning the valuation metrics between simulation and
post-processing

To support these intermediate metrics, two new classes were added to the
“tape” module of GridLAB-D, as shown in Figure 6. The volume and variety
of metrics generated from GridLAB-D is currently the highest among
simulators within TESP, so it was especially important here to provide
outputs that take less time and space than CSV files. Most of the
outputs come from billing meters, either single-phase triplex meters
that serve houses, or three-phase meters that serve commercial loads.
The power, voltage and billing revenue outputs are linked to these
meters, of which there may be several thousand on a feeder. Houses,
which always connect to triplex meters, provide the air temperature and
setpoint deviation outputs for evaluating occupant comfort. Inverters,
which always connect to meters, provide real and reactive power flow
outputs for connected solar panels, battery storage, and future DER like
vehicle chargers. Note that inverters may be separately metered from a
house or commercial building, or combined on the same meter as in net
metering. Feeder-level metrics, primarily the real and reactive losses,
are also collected by a fourth class that iterates over all transformers
and lines in the model; this substation-level class has just one
instance not shown in Figure 6. An hourly metrics output interval is
shown, but this is adjustable.

|image5|

Figure 6. New metrics collection classes for GridLAB-D

The initial GridLAB-D metrics are detailed in five UML diagrams, so we
begin the UML metric descriptions with MATPOWER, which is much simpler.
During each simulation, MATPOWER will produce two JSON files, one for
all of the generators and another for all of the FNCS interface buses to
GridLAB-D. A third JSON file, called the dictionary, is produced before
the simulation starts from the MATPOWER case input file. The dictionary
serves as an aid to post-processing. Figure 7 shows the schema for all
three MATPOWER metrics files.

The MATPOWER dictionary (top of Figure 7) includes the system MVA base
(typically 100) and GridLAB-D feeder amplification factor. The
amplification factor is used to scale up the load from one simulated
GridLAB-D feeder to represent many similar feeders connected to the same
MATPOWER bus. Each generator has a bus number (more than one generator
can be at a bus), power rating, cost function
f(P) = c :sub:`0` + c :sub:`1` P + c :sub:`2` P :sup:`2`, startup cost, shutdown cost, and
other descriptive information. Each FNCSBus has nominal P and Q that
MATPOWER can vary outside of GridLAB-D, plus the name of a GridLAB-D
substation that provides additional load at the bus. (All GridLAB-D
loads are currently scaled by the same *ampFactor* in MATPOWER, but the
released version of TESP will have separate *ampFactor* for each
FNCSBus). In total, the MATPOWER dictionary contains four JSON objects;
the *ampFactor*, the *baseMVA*, a dictionary (map) of Generators keyed
on the generator id, and a dictionary (map) of FNCSBuses keyed on the
bus id. In MATPOWER, all id values are integers, but the other
simulators use string ids.

|image6|

Figure 7. MATPOWER dictionary with generator and FNCS bus metrics

The GenMetrics file (center of Figure 7) includes the simulation
starting date, time and time zone as *StartTime*, which should be the
same in all metrics output files from that simulation. It also contains
a dictionary (map) of three MetadataRecords, which define the array
index and units for each of the three generator metric output values.
These are the real power *LMP*, along with the actual real and reactive
power outputs, *Pgen* and *Qgen*. At each time for metrics output, a
GenTime dictionary (map) object will be written with key equal to the
time in seconds from the simulation *StartTime*, and the value being a
dictionary (map) of GenRecords.

The GenRecord keys are generator numbers, which will match the
dictionary. The GenRecord values are arrays of three indexed output
values, with indices and units matching the Metadata. This structure
minimizes nesting in the JSON file, and facilitates quick loading in a
Python post-processor program. Valuation may require the use of both
metrics and the dictionary. For example, suppose we need the profit
earned by a generator at a time 300 seconds after the simulation
starting time. The revenue comes from the metrics as *LMP\_P \* Pgen*.
In order to find the cost, one would start with cost function
coefficients obtained from the dictionary for that generator, and
substitute *Pgen* into that cost function. In addition, the post
processing script should add startup and shutdown costs based on *Pgen*
transitions between zero and non-zero values; MATPOWER itself does not
handle startup and shutdown costs. Furthermore, aggregating across
generators and times would have to be done in post-processing, using
built-in functions from Python’s NumPy package. The repository includes
an example of how to do this.

Turning to more complicated GridLAB-D metrics, Figure 8 provides the
dictionary. At the top level, it includes the substation transformer
size and the MATPOWER substation name for FNCS connection. There are
four dictionaries (maps) of component types, namely houses, inverters,
billing meters and feeders. While real substations often have more than
one feeder, in this model only one feeder dictionary will exist,
comprising all GridLAB-D components in that model. The reason is that
feeders are actually distinguished by their different circuit breakers
or reclosers at the feeder head, and GridLAB-D does not currently
associate components to switches that way. In other words, there is one
feeder and one substation per GridLAB-D file in this version of TESP.
When this restriction is lifted in a future version, attributes like
*feeder\_id*, *house\_count* and *inverter\_count* will become helpful.
At present, all *feeder\_id* attributes will have the same value, while
*house\_count* and *inverter\_count* will simply be the length of their
corresponding JSON dictionary objects. Figure 8 shows that a
BillingMeter must have at least one House or Inverter with no upper
limit, otherwise it would not appear in the dictionary. The
*wh\_gallons* attribute can be used to flag a thermostat-controlled
electric waterheater, but these are not yet treated as responsive loads
in Version 1. Other attributes like the inverter’s *rated\_W* and the
house’s *sqft* could be useful in weighting some of the metric outputs.

Figure 9 shows the structure of substation metrics output from
GridLAB-D, consisting of real power and energy, reactive power and
energy, and losses from all distribution components in that model. As
with MATPOWER metrics files, the substation metrics JSON file contains
the *StartTime* of the simulation, Metadata with array index and units
for each metric value, and a dictionary (map) of time records, keyed on
the simulation time in seconds from *StartTime*. Each time record
contains a dictionary (map) of SubstationRecords, each of which contains
an array of 18 values. This structure, with minimal nesting of JSON
objects, was designed to facilitate fast loading and navigation of
arrays in Python. The TESP code repository includes examples of working
with metrics output in Python.

Figure 10 shows the structure of billing meter metrics, which is very
similar to that of substation metrics, except that each array contains
30 values. The billing meter metrics aggregate real and reactive power
for any houses and inverters connected to the meter, with several
voltage magnitude and unbalance metrics. The interval bill is also
included, based on metered consumption and the tariff that was input to
GridLAB-D. In some cases, revenues may be recalculated in
post-processing to explore different tariff designs. It’s also possible
to re-calculate the billing determinants from metrics that have been
defined.

|image7|

Figure 8. GridLAB-D dictionary

The Range A and Range B metrics in Figure 10 refer to ANSI C84.1
[`11 <#_ENREF_11>`__]. For service voltages less than 600 V, Range A is
+/- 5% of nominal voltage for normal operation. Range B is -8.33% to
+5.83% of nominal voltage for limited-extent operation. Voltage
unbalance is defined as the maximum deviation from average voltage,
divided by average voltage, among all phases present. For three-phase
meters, the unbalance is based on line-to-line voltages, because that is
how motor voltage unbalance is evaluated. For triplex meters, unbalance
is based on line-to-neutral voltages, because there is only one
line-to-line voltage. In Figure 10, *voltage\_* refers to the
line-to-neutral voltage, while *voltage12\_* refers to the line-to-line
voltage. The *below\_10\_percent* voltage duration and count metrics
indicate when the billing meter has no voltage. That information would
be used to calculate reliability indices in post-processing, with
flexible weighting and aggregation options by customer, owner, circuit,
etc. These include the System Average Interruption Frequency Index
(SAIFI) and System Average Interruption Duration Index (SAIDI)
[`12 <#_ENREF_12>`__, `13 <#_ENREF_13>`__]. This voltage-based approach
to reliability indices works whether the outage resulted from a
distribution, transmission, or bulk generation event. The voltage-based
metrics also support Momentary Average Interruption Frequency Index
(MAIFI) for shorter duration outages.

|image8|

Figure 9. GridLAB-D substation metrics

|image9|

Figure 10. GridLAB-D billing meter metrics

The house metric JSON file structure is shown in Figure 11, following
the same structure as the other GridLAB-D metrics files, with 18 values
in each array. These relate to the breakdown of total house load into
HVAC and waterheater components, which are both thermostat controlled.
The house air temperature, and its deviation from the thermostat
setpoint, are also included. Note that the house bill would be included
in billing meter metrics, not the house metrics. Inverter metrics in
Figure 12 include 8 real and reactive power values in the array, so the
connected resource outputs can be disaggregated from the billing meter
outputs, which always net the connected houses and inverters. In Version
1, the inverters will be net metered, or have their own meter, but they
don’t have transactive agents yet.

|image10|

Figure 11. GridLAB-D house metrics

|image11|

Figure 12. GridLAB-D inverter metrics

Figure 13 shows the transactive agent dictionary and metrics file
structures. Currently, these include one double-auction market per
substation and one double-ramp controller per HVAC. Each dictionary
(map) is keyed to the controller or market id. The Controller dictionary
(top left) has a *houseName* for linkage to a specific house within the
GridLAB-D model. In Version 1, there can be only one Market instance per
GridLAB-D model, but this will expand in future versions. See the
GridLAB-D market module documentation for information about the other
dictionary attributes.

There will be two JSON metrics output files for TEAgents during a
simulation, one for markets and one for controllers, which are
structured as shown at the bottom of Figure 13. The use of *StartTime*
and Metadata is the same as for MATPOWER and GridLAB-D metrics. For
controllers, the bid price and quantity (kw, not kwh) is recorded for
each market clearing interval’s id. For auctions, the actual clearing
price and type are recorded for each market clearing interval’s id. That
clearing price applies throughout the feeder, so it can be used for
supplemental revenue calculations until more agents are developed.

|image12|

Figure 13. TEAgent dictionary and metrics

The EnergyPlus dictionary and metrics structure in Figure 14 follows
the same pattern as MATPOWER, GridLAB-D and TEAgent metrics. There are
42 metric values in the array, most of them pertaining to heating and
cooling system temperatures and states. Each EnergyPlus model is
custom-built for a specific commercial building, with detailed models of
the HVAC equipment and zones, along with a customized Energy Management
System (EMS) program to manage the HVAC. Many of the metrics are
specified to track the EMS program performance during simulation. In
addition, the occupants metric can be used for weighting the comfort
measures; EnergyPlus estimates the number of occupants per zone based on
hour of day and type of day, then TESP aggregates for the whole
building. The *electric\_demand\_power* metric is the total three-phase
power published to GridLAB-D, including HVAC and variable loads from
lights, refrigeration, office equipment, etc. The *kwhr\_price* will
correspond to the market clearing price from Figure 13. Finally, the
*ashrae\_uncomfortable\_hours* is based on a simple standardized model,
aggregated for all zones [`14 <#_ENREF_14>`__].

|image13|

\ Figure 14. EnergyPlus dictionary and metrics

GridLAB-D Enhancements
----------------------

The TSP simulation task includes maintenance and updates to GridLAB-D in
support of TESP. This past year, the GridLAB-D enhancements done for
TESP have included:

1. Extraction of the double-auction market and double-ramp controller
   into separate modules, with communication links to the internal
   GridLAB-D houses. This pattern can be reused to open up other
   GridLAB-D controller designs to a broader community of
   developers.

2. Porting the FNCS-enabled version of GridLAB-D to Microsoft Windows.
   This had not been working with the MinGW compiler that was
   recently adopted for GridLAB-D on Windows, and it will be
   important for other projects.

3. Implementing the JSON metrics collector and writer classes in the
   tape module. This should provide efficiency and space benefits to
   other users who need to post-process GridLAB-D outputs.

4. Implementing a JSON-based message format for agents running under
   FNCS. Again, this should provide efficiency benefits for other
   projects that need more complicated FNCS message structures.

Using and Customizing the TESP
==============================

TESP runs on Linux (Ubuntu tested), Mac OS X, and Microsoft Windows.
Installers, source code, examples and documentation are available at
https://github.com/pnnl/tesp/, and the TESP also runs under
Linux at PNNL’s Electricity Infrastructure Operations Center (EIOC) in
Richland, WA. However, we expect that most users would wish to run TESP
on their own computers, which offers the possibility of customization
and also helps to preserve proprietary information that might be
developed or incorporated with TESP. There are two basic levels of
customization, depending whether the user chooses to install or build
TESP:

-  Install TESP: this may require administrator privileges on the target
   computer and supplemental downloads. It will be possible to
   develop new TEAgents and valuation scripts by modifying or
   developing Python, Java or C++ code.

-  Build TESP: in addition to the skill set for installing TESP, users
   should be familiar with configuring environments and using C/C++
   compilers on the target computer. This approach will enable the
   user to develop new TEAgents in C/C++, and to replace or upgrade
   co-simulators (i.e. GridLAB-D, MATPOWER, EnergyPlus) within TESP.

TESP has been designed to build and run with free compilers, including
MinGW but not Microsoft Visual C++ (MSVC) on Windows. The Python code
has been developed and tested with Python 3, including the NumPy, SciPy,
Matplotlib and Pandas packages. There are several suitable and free
Python distributions that will install these packages. MATPOWER has been
compiled into a shared object library with wrapper application, which
requires the MATLAB runtime to execute. This is a free download, but
it’s very large and the version must exactly match the MATLAB version
that TESP used in building the library and wrapper. This is true even if
you have a full version of MATLAB installed, so better solutions are
under investigation. At this time, we expect to support MATPOWER only
for Linux, with the alternative PYPOWER [`17 <#_ENREF_17>`__] supported
on Windows, Linux and Mac OS X. The code repository should always have
the most up-to-date information.

.. include:: ../install/Windows/Windows_install.rst

.. include:: ../install/Linux/Ubuntu_build.rst

.. include:: ../install/MacOSX/MacOSX_build.rst

.. include:: ../install/Windows/Windows_build.rst

.. include:: ../examples/Running_Examples.rst

Developing Valuation Scripts and Agents
---------------------------------------

In order to provide new or customized valuation scripts in Python, the
user should first study the provided examples. These illustrate how to
load the JSON dictionaries and metrics described in Section 1.5,
aggregate and post-process the values, make plots, etc. Coupled with
some experience or learning in Python, this constitutes the easiest
route to customizing TESP.

The next level of complexity would involve customizing or developing new
TEAgents in Python. The existing auction and controller agents provide
examples on how to configure the message subscriptions, publish values,
and link with FNCS at runtime. Section 1.4 describes the existing
messages, but these constitute a minimal set for Version 1. It’s
possible to define your own messages between your own TEAgents, with
significant freedom. It’s also possible to publish and subscribe, or
“peek and poke”, any named object / attribute in the GridLAB-D model,
even those not called out in Section 1.4. For example, if writing a
waterheater controller, you should be able to read its outlet
temperature and write its tank setpoint via FNCS messages, without
modifying GridLAB-D code. You probably also want to define metrics for
your TEAgent, as in Section 1.5. Your TEAgent will run under supervision
of a FNCS broker program. This means you can request time steps, but not
dictate them. The overall pattern of a FNCS-compliant program will be:

1. Initialize FNCS and subscribe to messages, i.e. notify the broker.

2. Determine the desired simulation *stop\_time*, and any time step size
   (*delta\_t*) preferences. For example, a transactive market mechanism
   on 5-minute clearing intervals would like *delta\_t* of 300 seconds.

3. Set *time\_granted* to zero; this will be under control of the FNCS
   broker.

4. Initialize *time\_request*; this is usually *0 + delta\_t*, but it
   could be *stop\_time* if you just wish to collect messages as they
   come in.

5. While *time\_granted* < *stop\_time*:

   a. Request the next *time\_request* from FNCS; your program then
      blocks.

   b. FNCS returns *time\_granted*, which may be less than your
      *time\_request.* For example, controllers might submit bids
      up to a second before the market interval closes, and you
      should keep track of these.

   c. Collect and process the messages you subscribed to. There may not be any if your time request has simply come up. On the other hand, you might receive bids or other information to store before  taking action on them.

   d. Perform any supplemental processing, including publication of values through FNCS. For example, suppose 300 seconds have elapsed since the last market clearing. Your agent should settle all the bids, publish the clearing price (and other values), and set up for the next market interval.

   e. Determine the next *time\_request*, usually by adding *delta\_t*
      to the last one. However, if *time\_granted* has been coming
      irregularly in 5b, you might need to adjust *delta\_t* so that
      you do land on the next market clearing interval. If your
      agent is modeling some type of dynamic process, you may also
      adapt *delta\_t* to the observed rates of change.

   f. Loop back to 5a, unless *time\_granted* ≥ *stop\_time*.

6. Write your JSON metrics file; Python has built-in support for this.

7. Finalize FNCS for an orderly shutdown, i.e. notify the broker that
   you’re done.

The main points are to realize that an overall “while loop” must be used
instead of a “for loop”, and that the *time\_granted* values don’t
necessarily match the *time\_requested* values.

Developers working with C/C++ will need much more familiarity with
compiling and linking to other libraries and applications, and much more
knowledge of any co-simulators they wish to replace. This development
process generally takes longer, which represents added cost. The
benefits could be faster execution times, more flexibility in
customization, code re-use, etc.

Example Models
==============

Figure 15 shows a reduced-order demonstration model that
incorporates all three federated co-simulators; GridLAB-D simulating 30
houses, EnergyPlus simulating one large building, and PYPOWER or
MATPOWER simulating the bulk system. This model can simulate two days of
real time in several minutes of computer time, which is an advantage for
demonstrations and early testing of new code. There aren’t enough market
participants or diverse loads to produce realistic results at scale.
Even so, this model is the recommended starting point for TESP.

|image14|

\ Figure 15. Demonstration model with 30 houses and a school

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
Panel (SGIP) use cases [`15 <#_ENREF_15>`__] and an additional use case
to illustrate the growth model.

*SGIP-1 and SGIP-6*. “The grid is severely strained in capacity and
requires additional load shedding/shifting or storage resources”
[`15 <#_ENREF_15>`__]. The details confirm that this use case addresses
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
wind resources” [`15 <#_ENREF_15>`__]. The scenario narrative states
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
and spinning reserves [`15 <#_ENREF_15>`__]. The cost of doing this is
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
on distribution grid” [`15 <#_ENREF_15>`__]. Solar generation capacity
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
load reductions” [`15 <#_ENREF_15>`__]. A distribution system network
operator with a system having 150 MW peak winter load is given
15-minutes advance notice by his transmission supplier to curtail 40 MW.
The curtailment is to last 2 hours. The distribution system network
operator has no generation resources of his own to use. Business as
usual mitigation is to conduct rolling blackouts. Alternatives exist if
some or all of the emergency curtailment can be satisfied by DER
[`15 <#_ENREF_15>`__]. Alternatively, the event might be naturally
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

Figure 16 shows the types of assets and stakeholders considered for the
use cases in this version. The active market participants include a
double-auction market at the substation level, the bulk transmission and
generation system, a large commercial building with responsive HVAC
thermostat, and single-family residences that have a responsive HVAC
thermostat. Transactive message flows and key attributes are indicated
in **orange**.

In addition, the model includes PV and storage resources at some of the
houses, and waterheaters at many houses. These resources can be
transactive, but are not in this version because the corresponding
separate TEAgents have not been implemented yet. Likewise, the planned
new TEAgent that implements load shedding from the substation has not
yet been implemented.

\ |image15|

Figure 16. SGIP-1 system configuration with partial PV and storage
adoption

The Circuit Model
-----------------

Figure 17 shows the bulk system model in MATPOWER. It is a small system
with three generating units and three load buses that comes with
MATPOWER, to which we added a high-cost peaking unit to assure
convergence of the optimal power flow in all cases. In SGIP-1
simulations, generating unit 2 was taken offline on the second day to
simulate a contingency. The GridLAB-D model was connected to Bus 7, and
scaled up to represent multiple feeders. In this way, prices, loads and
resources on transmission and distribution systems can impact each
other.

|image16|

Figure 17. Bulk System Model with Maximum Generator Real Power Output
Capacities

Figure 18 shows the topology of a 12.47-kV feeder based on the western
region of PNNL’s taxonomy of typical distribution feeders
[`16 <#_ENREF_16>`__]. We use a MATLAB feeder generator script that
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

Figure 19 shows the building envelope for an elementary school model
that was connected to the GridLAB-D feeder model at a 480-volt,
three-phase transformer secondary. The total electric load varied from
48 kW to about 115 kW, depending on the hour of day. The EnergyPlus
agent program collected metrics from the building model, and adjusted
the thermostat setpoints based on real-time price, which is a form of
passive response.

|image17|

Figure 18. Distribution Feeder Model
(http://emac.berkeley.edu/gridlabd/taxonomy\_graphs/)

|image18|

Figure 19. Elementary School Model

The Growth Model
----------------

This version of the growth model has been implemented for yearly
increases in PV adoption, storage adoption, new (greenfield) houses, and
load growth in existing houses. For SGIP-1, only the PV and storage
growth has actually been used. A planned near-term extension will cover
automatic transformer upgrades, making use of load growth more robust
and practical.

Table 1 summarizes the growth model used in this report for SGIP-1. In
row 1, with no (significant) transactive mechanism, one HVAC controller
and one auction market agent were still used to transmit MATPOWER’s LMP
down to the EnergyPlus model, which still responded to real-time prices.
In this version, only the HVAC controllers were transactive. PV systems
would operate autonomously at full output, and storage systems would
operate autonomously in load-following mode.

Table 1. Growth Model for SGIP-1 Simulations

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

A public demonstration and rollout of TESP is planned for a workshop on
April 27, in Northern Virginia. That workshop will mark the end of
TESP’s first six-month release cycle. The main accomplishment, under our
simulation task, is that all of the essential TESP components are
working over the FNCS framework and on multiple operating systems. This
has established the foundation for adding many more features and use
case simulations over the next couple of release cycles, as described in
Section 3. Many of these developments will be incremental, while others
are more forward-looking.

Two significant lessons have been learned in this release cycle, meaning
those two things need to be done differently going forward. The first
lesson relates to MATPOWER. It has been difficult to deploy compiled
versions of MATPOWER on all three operating systems, and it will be
inconvenient for users to manage different versions of the required
MATLAB runtime. This is true even for users who might already have a
full version of MATLAB. Furthermore, we would need to modify MATPOWER
source code in order to detect non-convergence and summarize
transmission system losses. This leads us to seriously consider
alternatives, such as PyPower [`17 <#_ENREF_17>`__] or AMES
[`18 <#_ENREF_18>`__]; although both have their own limitations, they
are much easier to modify and deploy.

The second lesson relates to EnergyPlus modeling, which is a completely
different domain than power system modeling. We were able to get help
from other PNNL staff to make small corrections in the EnergyPlus model
depicted in Figure 19, but it’s clear we will need more building model
experts on the team going forward. This will be especially true as we
integrate VOLTTRON-based agents into TESP.

Planning for the Next TESP Version
==================================

At this stage, TESP comprises a basic framework to conduct design and
evaluation of transactive mechanisms, and it is open for use by others
on Windows, Linux and Mac OS X. The next version of TESP should rapidly
expand its capabilities, by building on the established framework.

New TEAgents
------------

These are arguably the most important, as they add key features that are
directly in TESP’s scope, and likely not available elsewhere integrated
into a single platform. The more examples we provide, the easier it
should be for others to write their own (better) TEAgents.

1. VOLTTRON is a standard for building automation and management
   systems, and it has been used to implement build-level transactive
   mechanisms for electricity, air and chilled water in co-simulation
   with EnergyPlus [`5 <#_ENREF_5>`__]. A TEAgent based on VOLTTRON
   could manage the building-level transactive system, and also
   participate in the feeder-level or substation-level electricity
   markets on behalf of the building loads and resources. The work
   involves porting the Python-based VOLTTRON program to interface with
   EnergyPlus via FNCS instead of EnergyPlus’s built-in Building Control
   Virtual Test Bed (BCVTB). Then, the VOLTTRON program will need to
   construct bid curves for the grid market.

2. PowerMatcher is a transactive mechanism implemented by the
   Netherlands Organisation for Applied Scientific Research (TNO)
   [`19 <#_ENREF_19>`__]. The existing code is in Java, with a custom
   API and message schema. TNO would have to undertake the work of
   interfacing PowerMatcher to the TESP, with technical support from
   PNNL.

3. TeMix is another transactive mechanism that has been implemented by a
   California-based company [`20 <#_ENREF_20>`__], and selected for some
   pilot projects. TeMix would have to undertake the work of interfacing
   its product to the TESP, with technical support from PNNL.

4. Passive Controller (Load Shedding) – GridLAB-D includes a built-in
   passive controller, and switches that can isolate sections of a
   circuit. This function would be extracted into a separate TEAgent
   that implements load shedding in response to a message from MATPOWER.
   If the bulk system capacity margin falls below minimum, or worse, if
   the optimal power flow fails to converge, the bulk system operator
   would have to invoke load shedding. In TESP, the MATPOWER simulator
   would initiate load shedding a few seconds prior to the market
   clearing time, which initiates a new GridLAB-D power flow and reduced
   substation load published to MATPOWER. Load shedding is a traditional
   approach that will reduce the system reliability indices, whereas
   transactive mechanisms could maintain resource margins without
   impacting the reliability indices.

5. Passive Controller (Demand Response) – the GridLAB-D passive
   controller already simulates various forms of price-responsive or
   directly-controlled loads. These would be extracted into a separate
   TEAgent for control of waterheaters and other loads, complementing
   the transactive dual ramp controller for HVAC.

6. Generator Controller – GridLAB-D has a built-in generator controller
   that is tailored for conventional (i.e. dispatchable) generators with
   operating, maintenance and capital recovery costs included. This has
   not been completely developed, but it would be useful in TESP as a
   separate TEAgent so that cogeneration may be included. For example,
   several teams are developing 1-kW generators for co-generation with
   residential gas furnaces (the ARPA-E GENSETS program).

7. Storage Controller – GridLAB-D’s built-in battery only implements a
   load-following mode with state-of-charge and charge/discharge
   thresholds. We expect to develop a more capable battery controller
   during 2017 as part of a Washington State Clean Energy Fund (CEF)
   project in collaboration with Avista Utilities and Washington State
   University. This new agent would be implemented and tested in TESP.

The enhancements 1, 2 and 3 are probably the most important. A VOLTTRON
agent is strategic because it enables intrabuilding-to-grid
transactions. It also fills a weakness in GridLAB-D’s own commercial
building models, which are adequate for small-box establishments and
strip malls, but not for larger buildings like the school in Section
2.3. The PowerMatcher and TeMix agents are strategic because they would
show usability of TESP by others, and facilitate cross-vendor
experiments.

Usability Enhancements
----------------------

These are also important for usability and widespread adoption of TESP.

1. Capacitor Switching and Tap Changer Metrics – GridLAB-D includes
   built-in counters for capacitor switching and tap changer operations,
   which reflect wear-and-tear on utility infrastructure. These should
   be added to the metrics described in Section 4.5, and this would
   likely complete the intermediate metrics output from GridLAB-D.

2. TE Challenge Message Schemas – NIST has defined several classes and
   message schemas for the TE Challenge project [`2 <#_ENREF_2>`__].
   Many of these tie directly to GridLAB-D, so they are already
   supported via FNCS. We will continue to review all of them to ensure
   that TESP remains compatible with TE Challenge to the extent
   possible.

3. Solution Monitor – at present, TESP is configured and launched via
   script-building utilities and console commands, which are adequate
   for developers. The two-day simulations described in this report
   finish within an hour or two, but that will increase as the time
   horizons and system sizes increase. We plan to provide a graphical
   user interface (GUI) with spreadsheet interfaces for configuring
   TESP, live strip charts to indicate solution progress, and more
   convenient methods to stop a simulation.

4. Valuation GUI – the post-processing scripts for valuation also run
   from the command line, which is adequate for developers. We plan to
   provide a GUI that presents results in formatted tables and lists,
   plots variables that are selected from lists, etc. Both the solution
   monitor and post-processing GUIs will be implemented in Python using
   the Tkinter package that comes with it. This makes the GUIs portable
   across operating systems, and allows for user customization, just as
   with the Python-based TEAgents.

5. IEEE 1516 [`21-23 <#_ENREF_21>`__] is a comprehensive family of
   standards for co-simulation, sometimes referred to as High-Level
   Architecture (HLA). As part of Grid Modernization Lab Consortium
   (GMLC) project 1.4.15, “Development of Integrated Transmission,
   Distribution and Communication (TDC) Models”, FNCS and other National
   Lab co-simulation frameworks are evolving toward greater compliance
   with IEEE 1516. We plan to adopt a reduced-profile, lightweight
   version of FNCS or some other framework in TESP, so that it will be
   fully compliant with IEEE 1516. This fosters interoperability among
   simulators and agents developed by others. However, compared to some
   other HLA frameworks that we have evaluated, FNCS is much more
   efficient, handling thousands of federated processes. For TESP, we’ll
   need to maintain that level of performance in the new
   standards-compliant framework.

6. Intermediate Time Aggregations – for a single feeder as described in
   Section 2.3, a two-day simulation produces about 1 GB in JSON metrics
   before compression. (CSV files would be even larger). To mitigate the
   growth of these files, we plan to implement aggregation in time for
   yearly and multi-year simulations, in which metrics are aggregated by
   hour of the day, season, weekday vs. weekend or holiday, and by year
   of the simulation. No accuracy would be lost in cumulative metrics,
   and it would still be possible to identify metrics for individual
   stakeholders.

The enhancements listed in sections 3.1 and 3.2 are of known complexity,
and could be implemented within the next year, subject to resource
availability (including external parties TNO and TeMix). We expect to do
some prioritization at a TESP pre-release workshop on April 27, and
implement the selected enhancements over a series of two six-month
release cycles.

Some important longer-term enhancements are described in the next four
subsections. Work on them will begin, but most likely not be completed
over the next year. We are also considering a faster building simulator
than EnergyPlus, and federating ns-3 to simulate communication networks.
For now, both of those appear to be less important than the enhancements
listed in sections 3.1 and 3.2.

Growth Model
------------

The growth model described in sections 1.3 and 2.4 follows a pre-defined
script, with some random variability. This is adequate for short
horizons, up to a few years. Over longer terms, we’ll need an
intelligent growth model that mimics the analytics and heuristics used
by various stakeholders to make investment decisions. For example, the
TESP user may wish to evaluate impacts from a policy initiative that
will have a ten-year lifetime. That policy initiative may influence
investments that have a twenty-year lifetime. It’s not possible to
realistically script that kind of growth model ahead of time. Instead,
we need growth model agents that will make investment decisions
appropriate to the system as it evolves.

Agent Learning Behaviors
------------------------

Participants in any market will naturally try to optimize their
outcomes, or “game the system” depending on the observer’s perspective.
In designing brand-new market mechanisms for transactive energy, it’s
critically important to account for this human behavior, otherwise
undesired and unanticipated outcomes will occur. It’s up to the
policymakers to design market rules so that, with enforcement of the
rules, undesired outcomes don’t occur. Currently, our agents take
algorithmic and sometimes probabilistic approaches to transactions, but
they aren’t smart enough to “game the system” as a human would. We have
teamed with Iowa State University to investigate these agent learning
behaviors beginning this year.

Stochastic Modeling
-------------------

TESP currently uses random input variables, but the simulations are
deterministic and in full detail (e.g. every house, every HVAC
thermostat, every waterheater, etc.) It would be more efficient, and
perhaps more realistic, to have stochastic simulations on reduced-order
models as an option. This opens the door to more use of sensitivity
analysis and automatic optimization routines than is currently
practical. We have teamed with University of Pittsburgh to investigate
the subject beginning this year, building on previous work in circuit
model order reduction and probabilistic modeling.

Testing and Validation
----------------------

Testing and validation will be a continuous process throughout the life
of TESP. Some opportunities will arise through past and future pilot
projects in transactive energy. Other test cases will have to be
created. We expect to team with Dartmouth College in formalizing this
process, and also to work with Case Western University in modeling their
transactive campus project with NASA.

References
==========

[1] D. J. Hammerstrom, C. D. Corbin, N. Fernandez, J. S. Homer, A.
Makhmalbaf, R. G. Pratt\ *, et al.* (2016). *Valuation of Transactive
Systems Final Report, PNNL-25323*. Available:
http://bgintegration.pnnl.gov/pdf/ValuationTransactiveFinalReportPNNL25323.pdf

[2] NIST. (2017). *NIST Transactive Energy Challenge*. Available:
https://pages.nist.gov/TEChallenge/

[3] D. P. Chassin, J. C. Fuller, and N. Djilali, "GridLAB-D: An
agent-based simulation framework for smart grids," *Journal of Applied
Mathematics,* vol. 2014, pp. 1-12, 2014.

[4] R. D. Zimmerman, C. E. Murillo-Sanchez, and R. J. Thomas, "MATPOWER:
Steady-State Operations, Planning, and Analysis Tools for Power Systems
Research and Education," *IEEE Transactions on Power Systems,* vol. 26,
pp. 12-19, 2011.

[5] H. Hao, C. D. Corbin, K. Kalsi, and R. G. Pratt, "Transactive
Control of Commercial Buildings for Demand Response," *IEEE Transactions
on Power Systems,* vol. PP, pp. 1-1, 2016.

[6] S. Ciraci, J. Daily, J. Fuller, A. Fisher, L. Marinovici, and K.
Agarwal, "FNCS: a framework for power system and communication networks
co-simulation," presented at the Proceedings of the Symposium on Theory
of Modeling & Simulation - DEVS Integrative, Tampa, Florida, 2014.

[7] J. C. Fuller, K. P. Schneider, and D. Chassin, "Analysis of
Residential Demand Response and double-auction markets," in *2011 IEEE
Power and Energy Society General Meeting*, 2011, pp. 1-7.

[8] J. Arlow and I. Neustadt, *UML 2.0 and the Unified Process:
Practical Object-Oriented Analysis and Design (2nd Edition)*:
Addison-Wesley Professional, 2005.

[9] H. Zhang, Y. Vorobeychik, J. Letchford, and K. Lakkaraju,
"Data-Driven Agent-Based Modeling, with Application to Rooftop Solar
Adoption," presented at the Proceedings of the 2015 International
Conference on Autonomous Agents and Multiagent Systems, Istanbul,
Turkey, 2015.

[10] V. Sultan, B. Alsamani, N. Alharbi, Y. Alsuhaibany, and M.
Alzahrani, "A predictive model to forecast customer adoption of rooftop
solar," in *2016 4th International Symposium on Computational and
Business Intelligence (ISCBI)*, 2016, pp. 33-44.

[11] ANSI, "ANSI C84.1-2016; American National Standard for Electric
Power Systems and Equipment—Voltage Ratings (60 Hz)," ed, 2016.

[12] IEEE, "IEEE Guide for Electric Power Distribution Reliability
Indices," *IEEE Std 1366-2012 (Revision of IEEE Std 1366-2003),* pp.
1-43, 2012.

[13] IEEE, "IEEE Guide for Collecting, Categorizing, and Utilizing
Information Related to Electric Power DistributionInterruption Events,"
*IEEE Std 1782-2014,* pp. 1-98, 2014.

[14] ASHRAE, "ANSI/ASHRAE standard 55-2010 : thermal environmental
conditions for human occupancy," 2010.

[15] D. G. Holmberg, D. Hardin, R. Melton, R. Cunningham, and S.
Widergren, "Transactive Energy Application Landscape Scenarios," Smart
Grid Interoperability Panel2016.

[16] K. P. Schneider, Y. Chen, D. Engle, and D. Chassin, "A Taxonomy of
North American radial distribution feeders," in *2009 IEEE Power &
Energy Society General Meeting*, 2009, pp. 1-6.

[17] R. Lincoln. (2017). *PYPOWER*. Available:
https://pypi.python.org/pypi/PYPOWER

[18] H. Li and L. Tesfatsion, "The AMES wholesale power market test bed:
A computational laboratory for research, teaching, and training," in
*2009 IEEE Power & Energy Society General Meeting*, 2009, pp. 1-8.

[19] J. K. Kok, C. J. Warmer, and I. G. Kamphuis, "PowerMatcher:
multiagent control in the electricity infrastructure," presented at the
Proceedings of the fourth international joint conference on Autonomous
agents and multiagent systems, The Netherlands, 2005.

[20] TeMix Inc. (2017). *TeMix*. Available: www.temix.net

[21] IEEE, "IEEE Standard for Modeling and Simulation (M&S) High Level
Architecture (HLA)-- Federate Interface Specification," *IEEE Std
1516.1-2010 (Revision of IEEE Std 1516.1-2000),* pp. 1-378, 2010.

[22] IEEE, "IEEE Standard for Modeling and Simulation (M&S) High Level
Architecture (HLA)-- Framework and Rules," *IEEE Std 1516-2010 (Revision
of IEEE Std 1516-2000),* pp. 1-38, 2010.

[23] IEEE, "IEEE Standard for Modeling and Simulation (M&S) High Level
Architecture (HLA)-- Object Model Template (OMT) Specification," *IEEE
Std 1516.2-2010 (Revision of IEEE Std 1516.2-2000),* pp. 1-110, 2010.

.. |logo| image:: ./media/Transactive.png
   :width: 2.0in
   :height: 2.0in
.. |image0| image:: ./media/Federates.png
   :width: 6.16667in
   :height: 3.75000in
.. |image1| image:: ./media/GrowthOpModel.png
   :width: 6.50000in
   :height: 3.16667in
.. |image2| image:: ./media/MessageClasses.png
   :width: 6.00000in
   :height: 5.16667in
.. |image3| image:: ./media/MessageFlows.png
   :width: 6.00000in
   :height: 3.75000in
.. |image4| image:: ./media/IntermediateMetrics.png
   :width: 6.16667in
   :height: 3.33333in
.. |image5| image:: ./media/GLDMetricsClasses.png
   :width: 5.75000in
   :height: 2.83333in
.. |image6| image:: ./media/MATPOWERMetrics.png
   :width: 6.00000in
   :height: 6.33333in
.. |image7| image:: ./media/GLDDictionary.png
   :width: 6.00000in
   :height: 5.75000in
.. |image8| image:: ./media/SubstationMetrics.png
   :width: 6.00000in
   :height: 3.25000in
.. |image9| image:: ./media/BillingMeterMetrics.png
   :width: 6.00000in
   :height: 4.66667in
.. |image10| image:: ./media/HouseMetrics.png
   :width: 6.00000in
   :height: 3.25000in
.. |image11| image:: ./media/InverterMetrics.png
   :width: 6.00000in
   :height: 2.91667in
.. |image12| image:: ./media/AgentMetrics.png
   :width: 6.33333in
   :height: 5.33333in
.. |image13| image:: ./media/EplusMetrics.png
   :width: 6.00000in
   :height: 5.91667in
.. |image14| image:: ./media/TE30system.png
   :width: 6.50000in
   :height: 2.66866in
.. |image15| image:: ./media/SGIP1system.png
   :width: 6.50000in
   :height: 3.66667in
.. |image16| image:: ./media/MATPOWERsystem.png
   :width: 6.36111in
   :height: 3.81944in
.. |image17| image:: ./media/FeederR1_1.png
   :width: 6.50000in
   :height: 5.08333in
.. |image18| image:: ./media/School.png
   :width: 6.49167in
   :height: 2.66667in
