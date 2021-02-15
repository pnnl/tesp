.. role:: math(raw)
   :format: html latex
..


##################
Heading 1 - Parts
#################

*****************
Heading 2 - Chapters
*****************

Heading 3 - Sections
========================

Heading 4 - Subsections
-------------------------

Heading 5 - Subsubsections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Heading 6 - Paragraphs
""""""""""""""""""""""""

Heading 7 - Trevor made up
...............................

Heading 8 - Does this really work?
//////////////////////////////////////





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
developed last year :cite:`1`, supplemented by additional
study of use cases and drivers to be published in a companion report. We
also considered the possibility of new transactive pilot projects, as
suggested by NIST’s TE Challenge :cite:`2`. This led to
adoption of the following objectives:

1. Integration of separate Transactive Energy Agents (TEAgents) that
   encapsulate behaviors of market mechanisms and participants.

2. Separation of the valuation function from simulation.

3. Implementation of an efficient and completely open-source platform
   for Windows, Mac OS X and Linux.

4. Definition of a growth model for multi-year TE simulations.

Objectives 1-3 specifically support use by others, while objective 4
ultimately extends the simulation time horizon up to 20 years.

Design Overview
---------------

:numref:`fig_federates` shows the simulation modules federated in TESP.  
GridLAB-D covers the electric power distribution system :cite:`3` and residential
buildings. 
PYPOWER, MATPOWER/MOST or AMES covers the Transmission System Operator (TSO). 
:cite:`4,17`. OpenDSS is an alternative distribution power flow program.
EnergyPlus covers large commercial buildings :cite:`5`. ns-3 is a communication
system simulator that can also host software agents. The integrating Message
Bus, using either the Hierarchical Engine for Large-scale Infrastructure Co-Simulation 
(HELICS) or Framework 
for Network Co-simulation (FNCS), manages the time step synchronization and 
message exchange among all of the federated simulation modules :cite:`Ciraci:2014ud`.  
In this way, TESP builds mostly on proven components, 
which helps mitigate risk in software development.  Some of these 
components may be upgraded or replaced in future versions, as described 
later.  However, the overall platform design in :numref:`fig_federates` still applies.  

.. figure:: ./media/Federates.png
	:name: fig_federates

	TESP Rev 1 components federated through FNCS and/or HELICS.

The user interacts with TESP by configuring simulation cases (magenta) and 
then running them.  Simulation federates or Agents write intermediate outputs
and metadata (green), which the user plots, post-processes and analyzes to
reach conclusions. In order to implement new functionality, the user would
write new TESP Developer Agents (orange), starting from one of the examples provided.

(Some of of the simulators and agents in :numref:`fig_federates` have to be configured
by hand. OpenDSS writes output in its native, non-TESP format, and EnergyPlus writes
output only through the Buildings agent; these are indicated with dashed green lines.
The ns-3 simulator doesn't write output; it's presently used in just one example, for
which the GridLAB-D outputs are adequate.)

Most of the new Agents in :numref:`fig_federates` were implemented in the Python 
programming language, which was chosen because: 

1. Python is now commonly used in colleges to teach new programmers

2. Python has many available add-on packages for numerics, graphics and
   data handling

3. Python bindings to FNCS already existed

Custom code for TESP can also be implemented in other languages like C++
and Java. To demonstrate, the Buildings agent was implemented in C++ and
one version of the simple Load Shed agent was written in Java. Our
experience has been that developers with experience in C++ or Java can
easily work in Python, while the converse is not always true. These
factors led to the choice of Python as a default language for
customizing TESP.

Initially, the TEAgents include a double-auction market mechanism, one
per substation, and a dual-ramp thermostat controller, one per house
:cite:`7`. These were previously hard-coded in GridLAB-D, and
those implementations remain in GridLAB-D, but the separate Python
versions allow others to study and modify just the transactive code
without having to rebuild all of GridLAB-D. Much of the future work
envisioned for TESP would focus on significantly expanding the numbers
and capabilities of TEAgents. Regarding the other new work highlighted
in :numref:`fig_federates`, section 1.3 (next) describes the Growth Model and section
1.5 describes the Valuation scripts.

Operational and Growth Models
-----------------------------

TESP adopts a time-stepping simulation that separates the operational
model, of a system with fixed infrastructure running for hours or days,
from the growth model, of a system with infrastructure that evolves over
months or years. :numref:`fig_growth_op` shows these two models in a Unified Modeling
Language (UML) activity diagram :cite:`8`. After
configuration, the simulation begins with a system in the initial
year-zero state, i.e. with no growth included. The operational model
then begins to run with federated co-simulators in the form of
GridLAB-D, TEAgents, PYPOWER and EnergyPlus. The operational model has
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

.. figure:: ./media/GrowthOpModel.png
	:name: fig_growth_op

	Interaction of growth model with operational model

Early versions of the growth model will only include:

1. Fixed growth factors for existing solar, storage and controllable
   loads; input as a schedule of %/year vs. time.

2. Pre-identified feasible sites for new capacitor banks, chosen from a
   list of fixed sizes.

3. Residential rooftop solar adoption models for existing houses
   :cite:`9,10`, or a simpler one based
   on total energy use and floor area of the house.

4. Changing size of an existing substation or service transformer.

Later versions are planned to have heuristics that utility system
planners and other agents would use in making investment decisions.
These heuristics will execute between growth model time steps, using
only information available at that point in the simulation.

.. |logo| image:: ./media/Transactive.png

