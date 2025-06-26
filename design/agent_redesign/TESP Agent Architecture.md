# TESP Agent Architecture

## Introduction

The Transactive Energy Simulation Platform (TESP) is the primary tool used by the Transactive Systems Program (TSP) at the Pacific Northwest National Lab (PNNL) for evaluating transactive systems. TESP is a collection of tools that allow for the time-series simulation of large electrical power systems, from individual loads to bulk power system generation, and their corresponding market mechanisms. Recently, PNNL conducted a large-scale study evaluating the impacts of integrated wholesale and retail real-time and day-ahead energy markets using a Texas power grid. As part of this work, software transactive agents (hereafter referred to as "agents") were written for each of the customer loads participating the in the transactive system: heating, ventilation and air-conditioning (HVAC) systems, electric resistance water heaters, batteries, and electric vehicles (EVs). These software agents were sufficient for the purposes of this study but were developed in an ad-hoc manner with limited planning and coordination between the individual authors. In the years since that study, it has become apparent that more generalized versions of these agents would allow be useful in that they would allow faster implementation of various transactive systems and development of software agents applicable for other types of devices participating in a transactive system. 

This began a significant effort to evaluate the existing software agents and implement a software architecture to bring about these improvements. This effort is not complete but has reached a significant milestone in that a single agent, the HVAC agent has been used to motivate the re-architecture and has itself been re-implemented using a prototype version of the architecture. This report describes the architecture itself, the state of the development, and expected future improvements. This document will be periodically updated as the development and implementation of the architecture continue.

### Architecture as a TESP Capability
Though these agents were created under a TESP use case, the DSO+T study, the architecture being developed here based on their behavior is expected to be 

### UML Diagram Note
All the UML diagrams referenced in this document were written using the PlantUML format. This is a text-based format that can easily rendedered to an image using a PlantUML renderer. IDEs such as Visual Studio code has extensions that can render files into images and there is an (online renderer)[https://www.plantuml.com/plantuml/uml/] where the PlantUML text can be pasted to produce an image. As some of these diagrams are relatively large, the image versions of these are not included in-line. This document will reference and link to the PlantUML documents themselves and leave the rendering of these images to be addressed by the reader.



## Architecture Requirements
To ensure that the new software architecture meets the needs of TESP developers and users, a list of software requirements were developed.

### Architecture Extensible to Many Future Use Cases
It almost goes without saying but to be clear, this architecture is intended to make it easier to understand how the current agents work and thus make it easier to modify or reimplement part of the agent. Thus, the architecture needs to not only work for the existing agents but also be able to work for future agents the TSP program might need. That is, we want the architecture to be general.

### Device Modeling as a Modular Part of the Agent
In DSOT, it was determined that supporting the day-ahead market operations required that the agent include a model of the device it was managing. This model needed to support the ability for estimating behavior an arbitrary amount of time into the future so as to inform the necessary market interactions. The agent's device model should be a distinct portion of the code that can be interchanged to suite the modeling fidelity of a given analysis.

### Market Interactions as Modular Part of the Agent
Similar to the device model, the interaction with the transactive system ("market") needs to be a modular portion of the the agent software architecture. This will make it easier to implement a variety of market mechanisms while keeping the remainder of the agent code intact.

### Bidding Strategy as a Modular Part of the Agent
Similarly to the device model, the bidding strategy of the agent needs to be a modular portion of the agent software architecture.

### Arbitrary Bid Curves
The Economics and Theory group in TSP has requested increased flexibility in how the devices bid into markets and to support this, the agents need to be able to create arbitrary bid curves. The current agents from DSOT use a four-point bid curve which provides a linear response to price with a deadband around a nominal price. In improving this from four points to an arbitrary number of points it will be essential that the software accepting these bid curves also be improved to support an arbitrary number.

### Software Testability
The agents need to have the ability to add in traditional software testing measures. This will allow the changes in the software architecture to be evaulated using automated testing mechanisms common in software today. These tests are largely absent from the existing agents and make it difficult to verify and validate the performance of the software agents after any changes are made without running a full-scale simulation. Implementation of these tests will allow for at least a preliminary evaluation of any changes to the agent at a much lower computation cost.

### Agent Testbeds
Developers of new agents or components of agents need a way to evaulate their changes from a validation stand-point ("Does it do what I want it to do?") without running a computationally expensive full-scale simulation. As part of the agent architecture, one or more agent testbeds need to be implemented to allow for this functional evaluation. The nature of these testbeds will need to be defined in the future and will likely involve an interactive elements. These testbeds should also support evaluation of single agents as well as an ensemble of agents.

### Identical Outputs
Once re-implemented in the new software architecture, the agent should produce identical outputs as the original agent. That is, the re-architecture must not change the behavior of the agent, just re-organize the code.

### Improved Documentation
Not only does the software architecture documentation need to be generated, but the documentation of the existing agent code needs to be written. Generally, there is limited to no documentation in the existing agent code.




## Abstract Class Architecture
With the above requirements in mind, the HVAC agent code was documented and evaluated. After this work, a proposed abstract class architecture was developed. These abstractions provide the fundamental classes that define the essential components of the agent while allowing the specialization necessary to reach what was implemented in the DSO+T study. The ["new_agent_abstract_cd.plantuml"](./new_agent_abstract_cd.plantuml) document contains the latest version of this class diagram.
 

As shown in the UML, the primary class is the _Agent_ class which is composed of two other classes: _Asset_ and _BiddingStrategy_. _Asset_ is in turn composed of an _AssetState_ class which holds the current state of the asset the agent is managing and a _AssetModel_ that holds the model of the asset used by the agent to make predictions about the state of the asset in the future. The _BiddingStrategy_ class holds the strategy itself as well as the _MarketInterface_, used for sending and receiving market signals. 

Also shown in the diagram are a few supporting classes:
- _Bid_ - A data structure for holding bid information. 
- _Metrics_ - A data structure for holding data to be written out and the methods to do so
- _Forecasts_ - A data structure for holding forecast information for use by the _AssetModel_

The diagram also shows the path through the class hierarchy to reach the actual concrete implemented classes in the prototype re-architecting of the HVAC agent. The details of the final concrete classes are not shown here to allow for a simpler diagram. Though the hierarchy of the classes is well-articulated, many of the attributes and methods of most of the abstract classes have not been defined yet.

As will be seen in the following sections, we know this architecture is sufficient to well-implement one agent (the HVAC agent) and we believe it will also serve the other DSOT agents well. 

## DSO+T HVAC Agent Prototype Class Diagram Under New Architecture
Working from the abstract classes, the functionality of the existing HVAC agent code was divided among the classes, defining new classes particular to the HVAC agent as necessary. This required defining all necessary parameters and methods to achieve the functionality that already existed in DSO+T HVAC agent. The file ["hvad_dsot_new_agent_cd.plantuml"](./hvac_dsot_new_agent_cd.plantuml) renders to the full digram but only contains the relationships between classes; the definitions of the classes themselves are found in ["hvac_dsot_class_definitions.plantuml"](./hvac_dsot_class_definitions.plantuml).

### DSO+T HVAC Agent Asset Model
One of the most significant changes as compared to the abstract class is the segmentation of the _AssetModel_ (realized as "HVACDSOTAssetModel") into three component classes: "HVACDSOTStructureModel", "HVACDSOTEnvironmentModel", "HVACDSOTSystemModel". These three components are highly related to each other and could easily be directly realized in "HVACDOSTAssetModel". The choice to split them out was largely motivated by the desire to make the code on the page more manageable though this segmentation does create greater cross-class interaction than is likely necessary. This segmentation may be at least partially reversed in future revisions.

"HVACDSOTStructureModel" holds the parameters for the physical structure for the building being heated and cooled by the HVAC system. Parameter include details such as the insulation levels of the exterior surfaces, the total floor area of the house, number of doors, area of windows, etc. These values are used to by the "calc_structure_ETP_parameters()" method of this class to calculate the parameters for the equivalent thermal parameter (ETP) model for a single-zone structure. Doing so is fundamental to calculating the thermodynamics of the stucture and is used by other classes.

"HVACDSOTEnvironmentModel" calculates the the heat flows within the single-zone house model, many of which are derived the from the heat flows into the house from the external environment. This class holds data related to the outside air temperature and solar radiation and uses them to calculate the thermal energy flows into and out of the structure represented by the ETP model.

"HVACDSOTSystemModel" manages all the modeling of the HVAC system components proper and the changes in their performance as a function of indoor and outdoor air temperature.  

These three component classes are integrated in the "HVACDSOTAssetModel" whose primary method is "simulate_time_step()". This method takes the current state of the asset and the necessary forecasts and simulates the evolution of the thermodyanmics of the structure to the provided future time. Doing so allows the electrical load produced by the HVAC system for all time-steps simulated to be known, allowing the agent to produce a reasonable estimate of the required power and energy under those conditions.

### DSO+T HVAC Agent Asset State Model
The "HVACDSOTAssetState" is a data class that holds the current state of the asset. In the DSOT analysis, what was considered the "true" state of the device was determined by a GridLAB-D simulation and at periodic intervals, the state of the HVACs being modeled there was communicated over to the agent, updating the attributes of this class. This class currently has no methods as the update process is managed outside this class.

### HVAC DSO+T Agent Day-Ahead and Real-Time Bidding Strategy
In the DSO+T study, the agents were responsible for participating in a day-ahead and real-time energy market. Under the new architecture, the generation of each of these market signals is realized in seperate classes, "HVACDSOTDABiddingStrategy" and "HVACDSOTRTBiddingStrategy". Both classes contain as attributes references to the Asset Model and its component classes for use when forming a bid.

The formation of the day-ahead market is relatively complex as it requires working across multiple hourly market periods. This requires collecting multiple vectors of forecast data (_e.g._ temperatures, price) and then using them in an optimization problem to determine the optimal operating strategy that respects the temperature limits defined by the customers preferences while minimizing the cost of the energy that must be purchased. In DSO+T the result of this optimization strategy was then put into a bid that was submitted to the retail day-ahead market, producing an updated price-forecast. The optimization problem was then resolved and this iteration cycle took place a number of times, producing a converged retail day-ahead price. This class holds the data and has the methods necessary to execute this operation. 

The formation of the retail real-time bid was much simpler as the time horizons were much shorter and no optimzation problem needed to be solved and, thus, a much simpler class overall. The agent simply needed to estimate how much energy it was going to use in the next five minutes. This class also has attributes holding instances of the Asset Model and used them to estimate the indoor air temperature for a few short time steps into the future, looking for when the HVAC system would turn on or off. This allowed for a very good estimate of the energy required over that time period and thus the bid that needed to be made.

### HVAC DSO+T Agent Market Interface
At this time, the concrete implementation of the _MarketInterface_ class has not been implemented. The nature of the relationships between it and the Bidding Strategy classes is unclear. It is expected that the definition of the generic function of this class in the abstract class will allow a meaningful implementation to be realized as part of this new software architecture. At this time, the operations of the Market Interface classes is being realized in the Biddging Strategy classes.


### Other Classes 
In addition to these main classes, a number of other classes where defined in re-architecting the HVAC DSO+T agent; these are described below. Not included are a number of enumeration classes.

- **HVACTemperatures** - Data class that holds (and validates) the large number of tempertaures needed to express customer preferences and is used in the day-ahead optimization process
- **HVACTSchedule** - Holds the thermostat schedule as well as numerous derived values that are needed to convert the "slider setting" (expression of customer preferences) into temperature limits. The methods of this class perform these operations.
- **DSOT4pointBid** - Holds the DSOT 4-point bid with a method to form the marginal prices curve from these points.


## DSO+T HVAC Agent Prototype Sequence Diagram Under New Architecture

### Role of "substation.py"

### DSO+T Interaction Between "substation.py" and Agents

### New Architecture Interaction Between "substation.py" and Agents


## State of Development
Currently, the DSOT HVAC agent has all of its code converted to this new architecture as it is currently defined. (As previously noted, the Market Interface classes are not well-defined and thus unimplemented). Furthermore, a basic functional teest was implemented to exercise that part of the code base (all but the "HVACDSOTRTBiddingStrategy") and the code is able to produce a bid without error. This functional test serves as a prototype for an integration test that could be a part of the final TESP automated test suite and also serves as a starting point for some of the testbeds that need to be developed to support development and testing of new agents.

We have also implemented some prototype testing using Python's "pytest" library. This testing largely serves to motivate the design of a more formal testing philosophy and has allowed the TESP development team to gain familiarity with the automated testing process, something has not existed in the TESP codebase to date.







## Expected Future Development Activity
The work to date is a good start in defining and implementing a new architecture for the agents in TESP, with the HVAC serving as the prototype. The further development activities detailed below are roughly in expected order of execution.

### Complete the Abstract Class Definitions
Admittedly, the current abstract classes are somewhat impoverished with many lacking any attribute or method definitions. In preparation for implementing the re-architecting for the other agents, these abstract classes should be more fully defined.

### Definition and Implementation of the Market Interface Class
As already mentioned, the Market Interface class is currently unimplemented as it lacks a clear abstract definition. After the completion of the abstract class definitions, the appropriate functionality that is in the Bidding Strategy classes needs to be pulled out, implemented in the Market Interface classes, and appropriate connected to the rest of the code base.

### Validation of Re-Architected Agent
Though the single testbed/integration test shows that the rearchitected code is able to execute without error, it has not been confirmed that the bid that is produced matches that of the original agent. Ideally, a similar function could be implemented in the original agent to facilitate this comparison. It is likely that multiple such tests would need to be implemented to evaluate the various portions of the two agents. Similarly, a variety of input test conditions would need to be defined to ensure the behavior was consistent across a sufficiently wide range of test conditions.

### Expanded Automated Testing
The automated testing that is currently supported is not comprehensive nor sufficient for the current needs of TESP. A more concrete testing philosophy needs to be defined and the implemented testing needs to be expanded. This activity could dove-tail well with the validation activity as it would define what portions of the new agent need to be tested to ensure expected behavior. 

### Testbed Devleopment
The existing integration test provides a hint at what kind of work needs to be done for implementing the appropriate testbeds for the agents. This test will serve as a starting point to define what kind of functionality the testbeds need to implement; that is, what functionality do agent developers need to help them most. 

An interactive bid curve viewer was previously implemented for the retail DA bid for the HVAC agent by copying-out and restructuring code. This stand-alone tool was never validated against the original agent but could serve as a prototype for at least one of the testbeds, showing how to implement interactive sliders to aid agent developers.

### Implementation of Arbitrary Bid Curves
A key to making the existing agents more generic is the implementation of a more generic bid curve. From the work done on the HVAC agent, implementing this in the agent code is not expected to be more complicated. It is unclear, though, what degree of effort is required to update all the other simulation components that interact with the bid curve handle these more expressive curves appropriately.

### Expansion to All DSO+T Agents
Given the experience gained through re-implementing the HVAC agent, the same architecture implementation, automated testing implementation, testbed implementation, and validation needs to be extended to the other DSO+T agents. If we've done our job well with the architecture definition and can leverage the lessons learned, this activity should be largely straight-foward, though not necessarily quick. The work we've done provides us a map for this activity and an estimate of the amount of activity but we still have to put in the time

### Comprehensive Evaluation of New Agents
With all new agents implemented, an end-to-end test of the entirely re-implemented system needs to be performed. This will compare the entire simulated system's behavior, both under the original implementation and under the new implmentation with the new architecture. Success is expected to show identical results when comparing the outputs of both systems.

Ideally, the changes to the architecture will not require significant re-work of code outside the agents themselves (_e.g._ "substation.py", "dso_agent") but intial evaluations are not promising in this regard. There is no desire for a "boil the ocean" strategy but it may not be possible to contain the knock-on impacts of creating this new agent architecture. Early work has been done to define a new architecture for these components but this architecture is not complete enough at this time to facilitate re-implementation of the necessary code under this architecture.

### Comprehensive Documentation
Much of the documentation of the new implementation of the agents under the new architecture will include extensive in-line documentation in form of sturctured (_e.g._ class method documentation) and unstructured documentation (_e.g._ single line or code block comments). There is likely to be a need for more general documentation to assist agent developers who are approaching this architecture 

### Stretch Goal:Unification of Day-Ahead and Real-Time Bidding Process
(This activity is not strictly required by the re-architecting activity but it may be easiest to make this change as a part of re-architecting process.) In the original DSO+T HVAC agent, the day-ahead and real-time bidding strategies followed a very different process, largely motivated by the need for the day-ahead bidding to perform an optimization. Conceptually, though, the need to estimate the future power and energy needs of the HVAC are similar and it is just the time horizon that differs. A more careful look at the two implemented bidding processes should be performed

