# Agent Design Guidance

## Motivation
There are multiple purposes of this deep dive into the DSO+T agents we are undertaking:

* There is limited understanding in the Transactive team as a whole about the particulars of the agents as most of the original developers have left PNNL since the completion of DSO+T. This expertise needs to be rebuilt as he agents (and the DSO+T framework as a whole) continues to be a cornerstone of our on-going work in the Transactive program.
* The existing code was written by engineers with limited experience designing software and under a time crunch. It shows.
* The agents have more in common than may be obvious at first glance and would benefit from making those commonalities more explicit. Let's call this a need for "good software architecture".
* Good software architecture will also allow the modification of the existing agents along with using the architecture to extend to new loads and market mechanisms.

## Strategy
The existing DSO+T study has four agents. Each of us on the development team will take one agent and focus our efforts into understanding it well enough to explain it to the team. After each person has presented, we will discuss the commonalities we see between the agents and work together to form a software architecture to apply to the existing agents. This will consist of a [class diagram](https://www.visual-paradigm.com/guide/uml-unified-modeling-language/uml-class-diagram-tutorial/) (showing the relationship between the classes in the architecture and the attributes and methods of each) as well as some form of [sequence diagram](https://www.visual-paradigm.com/guide/uml-unified-modeling-language/what-is-sequence-diagram/) (showing the interaction between instantiated agents.) The architecture that is defined will then be implemented by the team and each developer will re-implement their agent using the new architecture. Lastly these revised agents will be used to re-run the DSO+T case with the outputs compared; it is expected that the results between the two will be identical (barring the discovery of any bugs in the existing agents).

## Workplan

### Agent Assignments
* Trevor: [HVAC](https://github.com/pnnl/tesp/blob/62779f0ccaa38a7ec205d2a1a2c8748c5996a7be/src/tesp_support/tesp_support/dsot/hvac_agent.py)
* Mitch: [Water Heater](https://github.com/pnnl/tesp/blob/62779f0ccaa38a7ec205d2a1a2c8748c5996a7be/src/tesp_support/tesp_support/dsot/water_heater_agent.py)
* Fred: [Battery](https://github.com/pnnl/tesp/blob/62779f0ccaa38a7ec205d2a1a2c8748c5996a7be/src/tesp_support/tesp_support/dsot/battery_agent.py)
* Jessica: [EV](https://github.com/pnnl/tesp/blob/62779f0ccaa38a7ec205d2a1a2c8748c5996a7be/src/tesp_support/tesp_support/dsot/ev_agent.py)

### Working Directory
All work for this should take place in the "agent_design" branch. The repo has a top level folder called "design" and a sub-folder called "agent_redesign" that should be use for storing notes, code, diagrams, etc. This is also the location we'll keep our notes as a team when developing the new software architecture.


### Agent evaulation guidelines
All existing agents are designed to participate in the DSO+T market protocol and perform some or all of the following functions. This is intended to assist us all in better understanding the behavior of the agents by providing context.

#### Bid "object" structure
The bid object (not a class instance but a Python list of lists) consists of four price-quantity points; in DSO+T this is called a "four-point bid". The bid is arranged in increasing quantity with the first index defining which point (0 to 3) and the second defining whether the value is for quantity (index2 = 0) or price (index2 = 1).

#### Real-time market bidding
Each agent is responsible for forming a real-time market bid which consists of a single bid object. These values are communicated to the DSO which aggregates them before interacting with the wholesale market. Once the wholesale market clears, the DSO communicates a clearing price to the agent.

#### Load control
Each agent controls a single load for a customer and is responsible for sending it control signals based on any amentity it needs to provide (_e.g._ heating, cooling, water heating) as well as the clearing price from the market.

#### Load modeling (at least sometimes)
For some of the agent operations, a model of the load being controlled is maintained as a part of the agent. This model is useful for predicting behavior of the load for bidding into the day-ahed market.

#### Day-ahead market bidding
Each agent is responsible for forming a bid for the day-ahead market. This bid is a collection of at least 1 or more bid objects, one for each hour inbetween the time of bidding and the hour of operation. As a part of forming this bid many agents receive forecasts for some data (_e.g._ weather) and/or use an internal model of the load with an optimization model to make a best estimate of the optimal future energy needs of the load. Though the interaction with the day-ahead market only occurs once a day, the DSO+T day-ahead protocol had all the agents updating their bids every hour (all the way up to the hour of operation?). This iteration of the day-ahead market was necessary so that loads in general (and batteries in particular) didn't simply chase low-price periods _en masse_ and therefore turn them into high-price periods. Iteration allowed agents to spread their operation out in time as much as possible and form a stable estimate of the upcoming load profile and price forecast.


### Re-write guidelines
Still have to figure out we need to do here. In addition to using the new software architecture, we'll need to implement unit tests and potentially integration tests. 

### Deliverables for Seattle meeting
* Class definition for your agent 
  * Methods will be more important than attributes
  * As necessary or helpful, a workflow or sequence diagram to show how the agent will use it's methods
  * Any supporting classes that are particular to your agent. For example, the HVAC agent has a model of the house it is controlling that I'm thinking of spinning off into a separate class.
* Comments on the prematurely-defined agent class diagram Trevor put together.
* Thoughts on common classes that all the agents will need
  * Bid class
  * Device model class (provide the agent with some kind of model for the device it is controlling)


### Schedule
This work will be started in FY24 and continue into FY25. The following is a preliminary schedule of deliverables:

* July 23, 2024 - Meeting in Seattle. Completion of assessment of agents and beginning development of new software architecture.
* Sept 27, 2024 - Completion of new software architecture design with sufficient documenation (class sequence diagrams).
* Jan 2, 2025 - Completion of re-implementation of agents using new software architecture and beginning of validation testing, testing suite, and documentation.
* Mar 7, 2025 - Completion of validation testing, testing suite and documentation.

## References

The following documents might be useful through this agent redesign process.

* DSO+T: Transactive Energy Coordination Framework - https://www.osti.gov/biblio/1842489
* Classification of load types for transactive systems - https://ieeexplore.ieee.org/document/8791602
