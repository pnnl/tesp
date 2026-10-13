# FY27 Development Plan

In FY27 TESP is continuing to extend the new architecture begun in FY26 to make improvements in the following ways:

- Architect, design, and implement a so-called "stub" version of a transmission system operator (TSO) which implements a real-time energy market.
- Architect, design, and implement a so-called "stub" version of a distribution system operator (DSO) which implements a real-time energy market.
- Using the agent architecture completed in FY26, implement appropriate agents to represent load and generation in a computationally light manner for participation in the wholesale market.
- Develop and improve the execution framework including upgrades to CoSim Toolbox (CST)
- Demonstrate this year's work by running an annual, hourly or finer simulation using the TSO stub and DSO stub along with the asset/device agents to build the supply and demand curves used in the market operation. 

The remainder of this document describes the expected work in greater detail. There are other minor tasks to be completed this year that are not discussed in this document.

## Demonstration of Capabilities

### Simple Stubs and Agents for Short Runtimes
Though this is the last task that we will perform in FY27, it is also the culmination of our efforts this year and thus serves to make the end goal clear and will provide context for the rest of the efforts.

The purpose of the DSO stub and TSO stub is to provide a representation of these power system entities in a manner that is minimal computation load. This allows them to execute quickly with a "good enough" fidelity for purposes of developing other parts of the system. For example, if developing a new market optimization formulation, instead of using GridLAB-D and bunch of device agents, you could use the DSO stub and aggregated device agents. This reduces the fidelity of the DSO bids into market BUT, particularly for early development, this is likely to be perfectly reasonable. We are expecting to use PySO as the foundation for both the TSO and DSO.

An important part of achieving this reduction in computation load is similarly reducing the fidelity of the device or asset agents that are participating in the market. In DSO+T, these agents had real device models and, particularly for the day-ahead market, ran optimization problems themselves to determine what their bids would be. Simplified models, aggregation, and other data-oriented techniques (rather than physics-oriented models) can be used with the stub operator models, though, to reduce the computation load and achieve faster execution. 

The philosophy of the TESP v2 architecture calls for an agent to act as a proxy for every controllable asset in the system. The physics of the device are generally represented by other simulators and while the agents do interact with these models in other simulations (e.g. getting the state of the device, sending control signals to the device) the role of the agent is to be the point of interaction across the broader control or coordination scheme. In the DSO+T study we implemented agents for all the customer-owned assets and, as an experiment, we plan on extending this to transmission assets in FY27 as well. Though having generation assets represents in the market as an agent is largely about software architecture consistently, it does provide some advantages for helping users of TESP to understand the roles and responsibilities of agents and structure their software more cleanly along these lines. 

For the demonstration at the end of FY27, we plan on pairing the DSO stub and the TSO stub and unconventionally have them run against each other. Additionally, all represented assets in the system will use an agent that uses a simplified, computationally light method of representation. The simulation will run for a full year with time steps of no longer than one hour. This will allow us to both validate the performance of the stubs and agents as well as confirm the short run times possible with these simplified models.

The system under study will be the DSO+T 8-node ERCOT model which will allow us to represent multiple DSOs with varying characteristics and one TSO. We will use the asset composition used in the DSO+T (e.g. DSO load composition, generator technology) to define the the assets being modeled in FY27. Given that this will be a physics-free representation, direct comparison to results in the DSO+T model will not be possible. 

### Execution Framework Improvements and LLM Configuration
Co-simulation is an essential part of building models that span multiple domains. For several years, TESP has used HELICS and will continue to do so. In FY27, we are also planning on testing adoption of CoSim Toolbox (CST) as the foundation for all the co-simulated components. CST allows faster federate development and more centralized data management. We expect to need to make improvements to CST as it is relatively new software and has had limited use thus far. 

We are also interested in seeing if existing LLMs can be configured in such a way that allows users to more quickly define scenarios, validate the scenario definitions or in other ways remove the time and effort it takes to configure a given scenario. This could include the creation of co-simulation configuration files, agent configuration files, or other more general configuration files. We know from previous work on DSO+T this is an activity that commonly takes more effort than it seems it should warrant.

### System Components Not Modeled
Interestingly, the scope of the work in FY27 does not include any explicit requirement to model the physics of the power system. In past studies such as DSO+T GridLAB-D solved the power flow of the distribution systems that were modeled and PyPOWER did the same for the transmission system. As the stub operations focus on market behavior of the systems, there will be no need in FY27 to solve the powerflows. Similarly, in the DSO+T study a significant portion of the computation time was modeling the physics of the devices being controlled (e.g. HVACs, solar PV, EVs). These devices will not be modeled to provide a real-world, ground truth reference but may be modeled in some way by the agent as its own device model.



## Execution Framework and CoSim Toolbox (Mitch)

### CST Data Collection
Much of the recent work on CST has focused on the poor performance of the database-centric data collection operation. Despite non-trivial effort, we have not been able to understand the cause of the poor performance and thus have not been able to improve it. The temporary work-around has been to support writing to local files as needed. Using experience gained since the original CST development, it seems clear that the particular use of the PostGres database is likely not a good fit for our purposes as it is designed as a transactional database and our use is data collection.

As an alternative approach, based on our experience with writing local files, in FY27 we are going to shift entirely to having federates collect data locally but do so using the Parquet format, a format that is well-suited for time-series data collection. Since one of the advertized advantages of CST is centralized data collection, we will likely want to create CST APIs that can move the locally collected data to a central location at the completion of the co-simulation.

### Co-Simulation Monitoring
One of the other key advantages of centralized data collection in CST was to support monitoring of the co-simulation during its execution. This allows users to ensure the co-simulation is executing as expected and terminate it early if it is not. With the move away from a single database containing all data coming out of the co-simulation, the current implementation needs to be re-examined. Not only does there need to be a way to allow users to define data they want to collect for monitoring purposes, but the underlying database to store this monitoring data and the presentation of such data needs to be evaluated. InfluxDB and Grafana are commonly used for real-time data collection like this and may be good candidates for our needs.

### Data Service
There are some data values that multiple entities in the co-simulation need. Rather than relying on each entity reading in values from a file, DSO+T implemented a data server and in FY27, we will evaluate the server and determine what, if any changes or improvements should be made. Based on the needs of the agents, this server may or may not be used in the FY27 demonstration.

### LLM Configuration
As the size and complexity of the modeled system grows, the process of configuring the individual co-simulation components also becomes more complex, confusing, and error-prone. The growth of text-based LLMs is providing us an opportunity to see if they are the right tool for the job. We expect to need to develop a formal structure for the configuration process and the models being configured so that the LLM can reliably understand what parameters need to be adjusted to achieve the desired configuration. 

### Post-Processing
Working with the Valuation team, we will work on developing methods to make computation of standard metrics for analysis. Previous development in TESP and the DSO+T study can be leveraged for this. The goal of this task is to make it as easy as possible to consistently calculate metrics across multiple analysis, supporting more apples-to-apples comparisons.




## System Operator Class (Nathan)
Generally, there are many functions of system operators that could be a part of a software model for such entities. In FY27, we will focus our efforts on only the operations needed for the real-time energy market operation. It will be useful to develop the architecture of the system operator class to ensure that both these simple TSO and DSO stubs can be designed and implemented, but also more complex, full-features instances such as would be used in the DSO+T study or other cases where the operator offers multiple market products and performs other non-market activities such as reliability analysis or capacity expansion planning.

### PySO
The system operator class will be based on the PySO, a Python-based system operator library that uses Egret to perform the optimization calculations. It is expected that most of the functionality offered by PySO will not be utilized and it may be necessary to work with the PySO developers at PNNL to modify PySO to be more generic than they have originally expected. It is anticipated that PySO will be the preferred TSO simulation tool in coming years and this activity will allow us to get to know the tool even if we make very limited use of its functionality. Ideally, PySO will be used for both the TSO and DSO implementation in FY27.

An important part of PySO will be definition of a state machine to support the sequencing of the activities performed by the system operators and by their participants. A common definition of the state machines will need to be accessible to both the system operators as well as the participants to ensure the coordination of data exchange and proper operation of the market.

### TSO Market 
The primary (only?) functionality that will be performed by the TSO in FY27 is clearing a real-time energy market formulated as a double-auction. The Curve data objects used in FY26 will be used to hold the received supply curves from the generation agents and the demand curves from the DSOs. The TSO will clear the market and provide a clear price for real-time energy.

### DSO Aggregation
For FY27, we will not be operating a retail market so the primary function of the DSO is to aggregate device bids from the individual device agents. The device agents will be using Curve objects developed in FY26 to represent their demand and the DSO will be responsible for aggregating the supply and demand curves and submitting them to the TSO. Similarly, the DSO will be responsible for propagating the cleared price back down to the agents for their use in determining device set-points.

## Grid Asset Agents (Jessica)
Agents are software proxies for devices that are participating in management or coordination schemes for grid assets. This project's work in FY26 developed a new, more generic, flexible (and complex) agent architecture and in FY27 we will use this software architecture in this study. In addition to gaining general experience with it, due to the simplicity of the demonstration in FY27, we will be effectively evaluating the ability of the software architecture to support very simple use cases and bypass generic functionality that is not needed.

For the purposes of the FY27 study, to reduce the computation load of the demonstration, some kind of simplification of the agent's model of the grid asset will need to be made. This could be a physics model of a single device to represent all devices of that kind in the system. It could be historical data that is adjusted in some kind of way to reflect price sensitivity, it could be a statistical model using previous DSO+T and PAVER results to build an elasticity model (with respect to price). 

### Agents for Assets in the Distribution System
Just like in the DSO+T, each device located in the distribution system will have an agent. For the work in FY27, the responsibility of the agent is to estimate the devices ability to participate in a the real-time energy market, express this as a Curve object to the DSO, receive the cleared price from the DSO after the real-time energy market clears, and send a control signal to the device under management. Given that no physical devices will be modeled in FY27, the agent's model of the device will effectively be treated as a good-enough representation of the physical device. (_As Trevor is writing this, he is ambivalent about this choice. Maybe we do need a simple model of reality as well to more fully exercise the architecture? Would this be too much work?_)

The agent's model of the physical device can take on many forms. It could be recorded data, a simple physical model, a statistical model,etc. Whatever form the model, the agent needs to be able to estimate produce a demand or supply curve (energy consumed or produced as a function of price) for the upcoming market period (likely five minutes) and transmit it to the DSO. Conversely, when the DSO provides a market clearing prices, the agent needs to adjust a control signal to the device being managed by the agent.

### Agents for Assets in the Transmission System
Though not previously implemented in the DSO+T study, generators in the bulk power system are an asset and should be represented by an agent; this will be implemented in FY27. Just as in the agents for the distribution system assets, the agents will be responsible for estimating the price responsiveness of the generators as energy suppliers and any load not captured in another way.








Configuration this year needs to match expected configuration process we would use in, say, DSO+T. For example, the process by which we define the amount of rooftop solar in our stub simulation in FY27 would be the same as we would use for a fuller DSO+T or PAVER study.

