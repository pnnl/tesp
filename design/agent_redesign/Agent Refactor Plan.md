# Agent Design Guidance

## Motivation
There are multiple purposes of this deep dive into the DSO+T agents we are undertaking:

* There is limited understanding in the Transactive team as a whole about the particulars of the agents as most of the original developers have left PNNL since the completion of DSO+T. This expertise needs to be rebuilt as the agents (and the DSO+T framework as a whole) continues to be a cornerstone of our on-going work in the Transactive program.
* The existing code was written by engineers with limited experience designing software and under a time crunch. It shows.
* The agents have more in common than may be obvious at first glance and would benefit from making those commonalities more explicit. Let's call this a need for "good software architecture".
* Good software architecture will also allow the modification of the existing agents along with using the architecture to extend to new loads and market mechanisms.
* Non-Simulation folks want to be able to understand and adjust the behavior of the agents in new ways that are not currently easily supported by the parameterization.


## Strategy
The existing DSO+T study has four agents. Each of us on the development team will take one agent and focus our efforts into understanding it well enough to explain it to the team. After each person has presented, we will discuss the commonalities we see between the agents and work together to form a software architecture to apply to the existing agents. This will consist of a [class diagram](https://www.visual-paradigm.com/guide/uml-unified-modeling-language/uml-class-diagram-tutorial/) (showing the relationship between the classes in the architecture and the attributes and methods of each) as well as some form of [sequence diagram](https://www.visual-paradigm.com/guide/uml-unified-modeling-language/what-is-sequence-diagram/) (showing the interaction between instantiated agents.) The architecture that is defined will then be implemented by the team and each developer will re-implement their agent using the new architecture. Lastly these revised agents will be used to re-run the DSO+T case with the outputs compared; it is expected that the results between the two will be identical (barring the discovery of any bugs in the existing agents).

To generally improve the code quality and ensure continuity of performance from the old DSO+T agents and the new ones going forward (as well as any future agent development), the implementation of more formal develop operations ("devops") proceedures will be implemented. These will largely consist of:
* Implementation of a coding style guide and an automated means of enforcing it.
* Automated testing as we determine is appropriate
  * Ability to confirm old agents and new agents produce the same output given the same input
  * Unit testing
  * Functional testing
  * Integration testing
* Code and documentation reviews from the agent refactor team
* Develop release process for the new agents
* Issue tracking, task management, etc

## Requirements for Refactored Agents (evolving list)
1. Modularity between the device the agent is controlling and the market in which the agent is participating. Both should be interchangeable to support extension to new devices and new market/transactive mechanisms.
2. The agent should maintain some form of device model to use in estimating future device behavior. In DSO+T this was a physics-based model but other forms (_e.g._ machine-learning models) need to be supported.
3. Implemented in the context of a larger software architecture (class-based). We need to balance the complexity of the software architecture and class hiearchy with creating code that is usable by those new to TESP agents.
4. Ability to support use interchangeable bidding strategies.
5. Documentation of the software architecture and refactored classes, both of the APIs and in prose.
6. (Maybe?) Provide an interactive model of the device for use in understanding it's behavior and validating the design.

## Requirements for Agent Testbed
Agent developers (both those of us refactoring the existing agents as well as those developing new agents) need a computationally light way of evaluating the functionality and performance of their code. To that end, it will be important to provide one or more test harnesses where developers can insert their code and see how it performs. It is likely there will need to be at least two testbeds:
1. Single-agent evaluation - using a single agent instance and can be used to evaulate:
   - Impacts on market input signals (_e.g._ bidding) due to agent control parameters and other exongenous inputs
   - Impacts on device control signals due to market output (_e.g._ clearing) signals
   - Data exchanges with the device model class
   - Data exchanges with the market model class 
2. Multi-agent evaulation - implementing a group of agents acting in a small-scale or mock system to identify emergent behaviors/performance. The use of this testbed will evaluate broader system-level effects such as
   - Appropriate aggregated bid curves 
   - Appropriate aggregate response to market clearing signals
   - Ability to produce intended effects of the transctive system under evaluation

The single-agent testbed is (ideally) interactive and allows exploration and validation that the agent code is working as intended and able to handle edge cases in the inputs. This could be implemented in a manner similar to what Trevor did to show the sensitivity of the HVAC agent to a number of parameters via sliders in a matplotlib notebook. This is a sandbox with focussed application during the earlier part of the development of the agent. Consideration needs to be made for how multi-period behavior could be evaulated; maybe a separate testbed?

Once the agent has demonstrated appropriate behavior in the single-agent testbed, a multi-agent testbed can be used to evaulate the performance of a non-trivial number of agents (100?). This testing will necessarily be more computationally expensive with an effort to continue to minimize the computational load. For example, the wholesale market could be represented by a static supply curve (for a double-auction market). The testbed may choose to not utilize co-simulation and instead pass data via memory to speed up simulation time. The physics of the electrical system may be removed for similar reasons.

Consideration will need to be made about how to generalize the components of the testbed so they can be most easily adapted to differing devices and transactive/market mechanisms. The ability to be general may need to be balanced with making the testbed more easily usable.


## Workplan

## Minimum Viable Product Definition (MVP)
TBD but these are Trevor's suggestions
* Agent test harness
* Device models
* Double-auction market mechanism
* Agents that use all of the above
* In-line API documentation
* Draft RTD for all appropriate refactored code

### Work Assignments
* Trevor: [HVAC](https://github.com/pnnl/tesp/blob/62779f0ccaa38a7ec205d2a1a2c8748c5996a7be/src/tesp_support/tesp_support/dsot/hvac_agent.py)
* Mitch: [Water Heater](https://github.com/pnnl/tesp/blob/62779f0ccaa38a7ec205d2a1a2c8748c5996a7be/src/tesp_support/tesp_support/dsot/water_heater_agent.py)
* Fred: [Battery](https://github.com/pnnl/tesp/blob/62779f0ccaa38a7ec205d2a1a2c8748c5996a7be/src/tesp_support/tesp_support/dsot/battery_agent.py)
* Jessica: [EV](https://github.com/pnnl/tesp/blob/62779f0ccaa38a7ec205d2a1a2c8748c5996a7be/src/tesp_support/tesp_support/dsot/ev_agent.py)
* Nathan: Devops/technical manager

### Working Directory
All work for this should take place in the "agent_design" branch. The repo has a top level folder called "design" and a sub-folder called "agent_redesign" that should be used for storing notes, code, diagrams, etc. This is also the location we'll keep our notes as a team when developing the new software architecture.

### Agent evaulation guidelines
All existing agents are designed to participate in the DSO+T market protocol and perform some or all of the following functions. This list is intended to assist us all in better understanding the behavior of the agents by providing context.

#### Bid "object" structure
The bid object (not a class instance but a Python list of lists) consists of four price-quantity points; in DSO+T this is called a "four-point bid". The bid is arranged in increasing quantity with the first index defining which point (0 to 3) and the second defining whether the value is for quantity (index2 = 0) or price (index2 = 1).

#### Real-time market bidding
Each agent is responsible for forming a real-time market bid which consists of a single bid object. These values are communicated to the DSO which aggregates them before interacting with the wholesale market. Once the wholesale market clears, the DSO communicates a clearing price to the agent.

#### Load control
Each agent controls a single load for a customer and is responsible for sending it control signals based on any amentity it needs to provide (_e.g._ heating, cooling, water heating) as well as the clearing price from the market.

#### Load modeling (at least sometimes)
For some of the agent operations, a model of the load being controlled is maintained as a part of the agent. This model is useful for predicting behavior of the load for bidding into the day-ahed market.

#### Day-ahead market bidding
Each agent is responsible for forming a bid for the day-ahead market. This bid is a collection of at least one or more bid objects, one for each hour in between the time of bidding and the hour of operation. As a part of forming this bid many agents receive forecasts for some data (_e.g._ weather) and/or use an internal model of the load with an optimization model to make a best estimate of the optimal future energy needs of the load. Though the interaction with the day-ahead market only occurs once a day, the DSO+T day-ahead protocol had all the agents updating their bids every hour (all the way up to the hour of operation?). This iteration of the day-ahead market was necessary so that loads in general (and batteries in particular) didn't simply chase low-price periods _en masse_ and therefore turn them into high-price periods. Iteration allowed agents to spread their operation out in time as much as possible and form a stable estimate of the upcoming load profile and price forecast.

### Scope Management
The agents are necessarily interacting with devices and transactive mechanisms/markets that we intend to be interchangable. Thus, it is reasonable to tackle defining supporting classes the are generally useful by span of the agents, devices, and/or market mechanisms. In order to manage schedule and budget, we will have to be judicious about how much of these kinds of development activities we put in scope and how much we defer with the understanding the future refactoring may be necessary due to a lack of generality in the implementations we create now.

### Refactor Guidelines
Still have to figure out we need to do here. In addition to using the new software architecture, we'll need to implement the devops tasks.

### Deliverables for Richland meeting
* Class definition for your agent 
  * Methods will be more important than attributes
  * As necessary or helpful, a workflow or sequence diagram to show how the agent will use it's methods
  * Any supporting classes that are particular to your agent. 
* Comments on the prematurely-defined agent class diagram Trevor put together.
* Thoughts on common classes that all the agents will need
  * Bid class
  * Device model class (provide the agent with some kind of model for the device it is controlling)


### Schedule
This work will be started in FY25 and will almost certainly not be completed that fiscal uyear. The following is a preliminary schedule of deliverables:

* July 23, 2024 - Meeting in Richland. Completion of assessment of agents and beginning development of new software architecture.
* Sept 27, 2024 - Completion of new software architecture design with sufficient documenation (class sequence diagrams).
* Jan 2, 2025 - Completion of re-implementation of agents using new software architecture and beginning of validation testing, testing suite, and documentation.
* Mar 7, 2025 - Completion of validation testing, testing suite and documentation.

## References

The following documents might be useful through this agent redesign process.

* DSO+T: Transactive Energy Coordination Framework - https://www.osti.gov/biblio/1842489
* Classification of load types for transactive systems - https://ieeexplore.ieee.org/document/8791602
