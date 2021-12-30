============================================
TESP Design Philosophy and Development Plans
============================================

Introduction
------------
The Transactive Energy Simulation Platform (TESP) is a signature component of the Transactive Systems Program (TSP) funded by Chris Irwin in the Office of Electricity (OE) at the US Department of Energy (DOE). This simulation platform is an on-ramp into transactive energy simulations by providing an easy-to-install collection of simulators that have been pre-configured to exchange certain information via HELICS. In addition to the simulators several transactive agents have been developed by PNNL and included in TESP to allow for the simulation of, for example, residential HVAC systems participating in a transactive control scheme using an integrated wholesale-retail real-time energy market. In addition to the software proper, documention of the software is provided via a Read The Docs website. TESP has served as the foundation for a few studies studies including PNNL's Distribution System Operator + Transmission (DSO+T), and a transactive energy blockchain demonstration.

The key goal of TESP has been to provide a means of reducing the barrier to entry for evaluating transactive systems through time-series simulation. Transactive energy (TE), by its nature, tries to look more holistically at how systems operate (across traditional analysis and jurisdictional divides) and as a result tends to require information exchange across simulator domains. This creates several challenges for those new to TE.

* Knowledge of multiple analysis tools to replicate the behavior of the specific subsystems being connected is required
* Knowledge of how to connect multiple tools on the co-simulation platform of choice is required

For those with a TE mechanism they would like to evaluate in-hand, the barrier of learning and integrating new analysis tools can easily be overwhelming and result in the researcher in question either abandoning the idea or evaluating their mechanism by another method which may or may not be as comprehensive as would be possible with an integrated simulation and analysis environment.

In an ideal world, TESP would be able to directly and comprehensively address these challenges. It provides an integrated transmission, generation, and distribution power system simulation capability with sufficient detail to allow for simulation of classical transactive mechanisms (such as HVAC participation in an integrated wholesale-retail transactive real-time energy market). Using one of the built-in examples, it is easy to imagine a researcher with a similar transactive idea or wanting to evaluate the provided transactive system in a slightly different environment (say, one with high penetration of electric vehicles) being able to make relatively simple modifications to the provided models and scripts and perform the necessary analysis.

That's the dream: take all the simulation management complexity away from TE researchers and allow them to focus on the details of their unique ideas, evaluating them quickly and easily in TESP.


Challenges of a Generic TESP
----------------------------
Achieving the dream of a generic TESP where any transactive mechanism can be easily evaluated is not trivial.

TE can be Arbitrarily Specific
..............................
The world of TE is very large. At its core, it is a merger of economics and control theory and draws on the rich foundation from both. Development of TE mechanisms have the blessing of being able to utilize the theory of both of these domains to develop mechanisms that better capture value, better account for uncertainties, and are more easily implemented by practitioners. From a simulation environment, this blessing becomes a curse: any given transactive mechanism may require modeling new features and/or facilitating new information exchange between simulators to achieve a meaningful simulation test environment for said mechanism.

What is required to support a given transactive mechanism is arbitrarily complex and may or may not easily align with the existing software suite and its underlying architecture. TESP cannot both be both usable as a plug-and-play TE evaluation environment where users can expect to avoid the complexity of the underlying software and just use it out-of-the-box while simultaneously supporting arbitrarily general TE mechanisms. 


Modifying TESP can Quickly Become Non-Trivial
.............................................
Since TESP will never be able to provide the no-effort on-ramp to any generic TE mechanism, what can it do to allow users to customize it more easily? To some extent, this question is fighting against the goals of TESP, providing a no-hassle method of evaluating new TE mechanisms. Every line of code and configuration that a user has to modify is one more than we would ideally like. Given the reality of what TESP would ideally support, though, expecting a user to have no hand in the coding pie is unreasonable. So what challenges would a TESP user face in trying to customize TESP?

The software toolset that TESP traditionally uses to implement TE mechanisms is specific. We use PyPower to model and solve transmission system power flows (and perform economic dispatch, if necessary), AMES/PSST to perform wholesale market operations, GridLAB-D to model distribution systems, solve their powerflows, and model residential customers and limited number of commercial customers, Energy+ to model a broader set of commercial customers (though not as well as we'd like), custom Python TE agents to perform the transactive control, HELICS to provide the integration between all these simulators and Python scripts to build the simulation cases of interest. Depending on the transactive mechanism, a TESP user may require modification in all of these tools and scripts (adding the DSO+T DA energy functionality did).


Analysis Needs Vary
...................
Under the best case scenario, a TESP user may desire to perform an analysis that TESP was specifically designed to support. It could easily be, though, that the user has different analysis needs than that originally imagined when the TESP example was built. Take, for example, a user that wants to evaluate the impacts of rooftop solar PV on the efficiency of real-time transactive energy markets, *the* classic transactive mechanism. It could be that this analyst wants to evaluate hundreds or even thousands of specific scenarios and is willing to given up some degree of modeling fidelity to crank through the simulations faster. Ideally TESP would be able to take an existing example with high fidelity and provide a way to quickly simplify it to speed up the simulation time.

TESP, though, does not support aribtrary levels of modeling fidelity. Even if the TE mechanism is well supported, to perform specific analysis significantly different models and simulation case constructions scripts may be required. This, again, requires the users to get their hands dirty to customize TESP to suit their analysis needs and likely requires a greater-than-cursory understanding of the software suite.




Addressing Challenges: The Design Philosophy of TESP
----------------------------------------------------
Given these challenges, the only way for TESP to be successful is to carefully define "success" in a way that makes the scope and scale of the software's goals clear. To that end, a few guiding principles have been defined to articulate the design philosophy of TESP.

TESP Targets Expert Users
.........................
Given the generic nature of how TESP is expected to be used and the level of expertise in designing and implementing transactive systems, TESP expects a high degree of skill from its users. Ideally users (or teams of users) would have sufficient experience with simulation tools deployed in TESP that constructing an configuring an appropriate set of tools for a given analysis would be a tractable task. To learn to use TESP well will likely require a commitment on the part of a new user that is measured in weeks or months rather than days. 

Though this is not desirable, there are many other complex software analysis packages (*e.g.* DOE's NEMS, Seimen's PSS/E, Energy Exemplar's PLEXOS) that require similar or greater levels of time and effort investment to learn to use well. For analysis that are very similar to those distributed with TESP, the barrier to entry is much lower as much of the analysis design and construction is baked into that example.

TESP Requires Excellent Documentation
.....................................
Because of the complexity of the simulation and analysis toolset, if TESP is to have any hope of being used (even by those that are implementing it), the documentation of the capabilities, the examples, demonstrations, and models that are distributed with it, and the code itself all need to be first-class.  If we expect users to use TESP knowing that they will have to modify existing code and craft new ones to achieve new analysis goals, we need to enable them to do so. How the TESP API is used, what assumptions went into certain models, how the simulators were tied together in co-simulation for a certain example, all of this needs to be clearly spelled out. Expecting users to become proficient through reading source code is not realistic if we expect the adoption of TESP to grow.

Built-In Examples Show How Things Could Be Done
...............................................
To help bridge the gap between an analysis goal and the user's unfamiliarity with the TESP toolset, a broad suite of capability demonstrations and example analysis need to be included with TESP. Capability demonstrations show how to user specific simulation tools, APIs, or models so that new users can understand the capabilities of TESP and how to use specific features. Example analysis are implementations in TESP of analysis that have been done with TESP. Often these analysis will have publications and a simplified version of the analysis will be implemented in TESP. The examples differ from the demonstrations in that they are analysis that are intended to produce meaningful results whereas the demonstrations are more about showing how to use a specific part of TESP. Being legitimate analysis, the examples will generally have a broader set of documentation that shows how the analysis as a whole was conducted and not just, say, how the co-simulation was configured.


Building Common Functions into the TESP API
...........................................
TESP provides the greatest value to users when it provides easier ways of doing hard things. Some of this comes through the built-in tool integration with HELICS but much of it is realized through the careful definition of the TESP API. Though the possible transactive systems analysis space is very large, there are common functions or standard practices that can be implemented through the TESP API that will standardize TESP in ways that will increase understanding and portability across specific analysis. Examples of such common functions could be data collection, post-processing to produce common metrics, standardize models and scripts to manipulate them. Some of these API calls may be specific to some common analysis.



The Path Forward for TESP
-------------------------
The foundation of TESP has been laid in that there are a working set of simulation tools that have been tied together in a co-simulation platform and a few full-scale, publishable analysis have been conducted using it. This said, for TESP to realize its potential as an evaluation platform of transactive systems significant development is still required will take many years at the current funding rate. Below are some of the major development efforts planned for TESP in the coming years:

TESP API
........
As was previously discussed, despite the general TE system analysis TESP desires to support, there are general functionalities that would allow TESP users to more efficiently build the simulation and conduct the analysis. Defining the contents of this API and developing it are a significant undertaking as will be the conversion of the existing TESP codebase to use the new API. The definition of the new API is expected to begin in FY22. Some preliminary thinking has identified the following areas as candidates for inclusion in the TESP API:

* Standardized, database-oriented data collection for time series inputs to and outputs from the co-simulation. helics_cli already uses a sqlite database that for data collection and this database could be co-opted for TESP as a whole.
* Definition of a standardized GridLAB-D model structure that would allow feeder_generator.py to easily add supported object values as well as edit models that have already contain some of these objects
* Definition and implementation of common metrics calculated from standard data collected from the co-simulation. Examples include total energy consumption, total energy cost, total economic surplus, bulk power system generator revenue, and indoor comfort
* Standard DER device agents that provide estimated energy consumption for arbitrary periods into the future. This information can be used by a HEMS to interact with the TE system to acquire the appropriate energy (or curtail the DER operation)
* Forecasters for common signals used by DER agents to create their forecasted device loads
* Standardized double-auction implementation


Reference Implementations of Common TE Systems
..............................................
Where TESP capability demonstrations are intended to be small in scale and show off specific TESP features and the example analysis are versions of actual studies done using TESP (and likely not maintained with API updates), there could be space for a middle-ground: reference implementations of common TE systems. These would be maintained as TESP evolves and would serve as starting points for users who want to do more specific studies. Candidates for reference implementations include integrated wholesale-retail real-time energy markets, and integrated wholesale-retail real-time and day-ahead energy markets. These reference implementations could also include reference implementations of specific components such as a HEMS, a double-auction market operator, prepare_case scripts that build the co-simulation and perform the analysis.

Full adoption of HELICS v3
..........................
HELICS v3 provides a wide variety of features and tools that would simplify many of the co-simulation mechanics in TESP. Using helics_cli to launch our co-simulations (instead of more complicated shell scripts), using message handles where appropriate rather than just value handles to support easy inclusion of communication system effects, and possibly using the helics_cli database for general TESP data collection.

Improved Commercial and Industrial Models
.........................................
The residential modeling provided by GridLAB-D has been used for many years of transactive studies and shown to be relatively effective. There's always ways in which the models and typical parameter values can be improved and updated but generally speaking, the modeling is good enough. The commercial building modeling has been difficult as the go-to simulation tool, EnergyPlus, does not handle the fast (minute-scale) dynamics that transactive systems typically operate under. GridLAB-D has a very limited set of commercial structures it models but these do not represent the diversity seen in the real-world. And the industrial load modeling is non-existent and much more complex. There is a lot of work to be done if TESP is going to reflect the broad load landscape.

Communication System Modeling
.............................
Transactive systems (and the smart grid in general) rely on communication systems to operate but the modeling of these communication systems is challenging. A generic transactive system protocol stack does not exist and the most common modeling tools (*e.g.* ns-3, Omnet++) are more appropriate for protocol development than full system performance modeling (the models are generally much more detailed than required for transactive system analysis). A clear understanding of the goal of including a communication system model in a transactive system analysis needs to be articulated and appropriate protocols and simulation tools need to be identified or developed.

Standardize Capacity Expansion Modeling
.......................................
Often, the biggest cost savings transactive energy provides is in capital cost savings, that is, in the power plants and transmission lines that don't need to get built (or are built much later) because transactive energy has been able to effectively manage the load. For analysis that want to capture these effects in simulation, a means of evolving the bulk power system under a given management philosophy (business as usual, time-of-use tarifs, transactive real-time tarifs) is an important part of creating a comprehensive apples-to-apples comparison. There are no tools in TESP to allow the run-time evolution of the power system and no direct integration with any of the popular capacity expansion tools to allow their outputs to easily fit into the TESP bulk power system modeling. This capability is an important missing piece for high-quality TE system evaluations.



