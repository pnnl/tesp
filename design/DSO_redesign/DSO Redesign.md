# DSO Redesign

**TODO: TDH:** I'm sure there's a paper out there that describes this better than I do which I should read, reference, and use to fill in any important gaps.

The DSO+T study originally conceived the DSO as the combination of three separate entities:

- Distribution System Owner/Operator (DO) - Responsible for the physical assets of the system and maintaining system reliability
- Distribution Market Operator (MO) - Responsible for running the retail market(s) for participating customers in the distribution system
- Load-Serving Entity (LSE) - Responsible for procurring energy from the wholesale market and retailing it to the retail customers in the distribution system.

The DSO implemented in the DSO+T study contained all three of these elements in one simulated legal entity and performed all of their corresponding functions. As part of a broader re-design effort, the TESP development team is planning on implementing a new DSO object that will contain these three sub-objects. We are doing this for the following reasons:

1. The functions performed in the DSO+T study (and many other functions envisioned but not implemented in TESP) are more easily designed and understood when placed in the appropriate part of the DSO.
2. Defining these functions allows variants of the existing study to be implemented more easily and with more clarity. For example, it is possible to model customers on various rate plans to be associated with separate LSEs and markets.
3. Updates, changes and implementation of new models will be more easily estimated and planned as it is clearer how the existing code works and what changes will be required.

This document provides serves as a planning document for the re-design of these higher-level DSO functionality. Under the current DSO+T study all of the DSO functionality is split between code found in "substation.py", "dso_market.py" and "retail_market.py". 

## DSO Components

In further detail, here are the components of the DSO as conceived for this redesign.

### Distribution System Owner/Operator (DO)

The DO is responsible for the maintenance and operation of the physical infrastructure of the distribution system; the DO can be thought of as the "wires company". They are responsible for respairs in cases of emergencies, regular maintenance and upgrades, and maintaining an electrical model of the system that accurately (enough) replicates the physics of its operation. Ideally, activities of the market operator (MO) and load-serving entity (LSE) would be validated by the DO to ensure that they are physically viable and do not compromise the safety of the distribution system. The DO also collects and maintains all the data on the physical state of the system (_e.g._  customer meter readings, voltage managment equipment state, substation equipment state.) 

The existing DSO+T software architecture implemented very few of the DO functionalities, the primary one being data collection on the state of the system. If implemented, it is likely the DO will need its own distribution system model that can be simulated with only GridLAB-D powerflow elements (_i.e._ no "house" or "solar" objects) to represent it's ability to estimate the physical flows and state of the system.

### Load-Serving Entity (LSE)

The primary role of the LSE is to procure energy to meet the demand of its enrolled customers. In the DSO+T study, all energy that was retailed was purchased from the wholesale market but you can imagine cases in which that energy could be purchased from distributed energy resources (DERs). The LSE also determines the tariff structure it uses with its customers which may or may not involve a market mechanism and a market operator (MO). When procurring energy from the wholesale market, it is responsible for interacting with said market in an appropriate manner which may involve estimating loads and forming bids. 

Generally the LSE needs to work with the DO to ensure there is sufficient capacity in the system to support the energy it intends to procure. Additionally, the DO may need more detailed information (per-customer procurement requests or estimates) to validate acceptable behavior of other aspects of the distribution system (_e.g._ voltage management, secondary transformer loading).

The LSE is also responsible for billing customers and will interact with the DO to get meter data necessary to calculate the cost of the procured energy for each customer.

The data collected by the LSE would consist of energy procurement requirements for the customers it serves (_e.g._ customer load estimates, customer bid information), wholesale market interactions (_e.g._ wholesale bids, wholesale clearing prices and quantities) and the price and quantity of the energy actually procured. This data would be collected on a per-customer basis where appropriate.

### Market Operator (MO)

The market operator is responsible for running the retail market, if present. Specifically, they are responsible for running the "utility" half of the market protocol which involves sending and receiving market signals with market participants. The output of the market operator is passed to the LSE for use in interacting with a wholesale market or other energy provider. The LSE is also repsonsible for passing information to the MO to allow it to communicate to market participants the results of their market interactions. The market signals sent to customers may also be validated by the MO through queries to the DO who has access to meter data.

The MO collects all the retail market related data including bids and retail clearing prices and quantities. 

Not all LSEs will require an MO. For example, if an LSE choose a flat-rate volumetric tariff, it would likely choose to estimate customers' load quantity (the amount of energy it needs to procure) without involving a market operation and use this to determine the quantity of energy it must procure.

## Software Implementation

### HELICS federate
The DSO is the only HELICS federate thought it models many entities (_e.g._ DO, LSE, MO, agents). It is arguable the that it is appropriate to represent the DSO and its consituent actors as a single federate and all of the analysis in the Transactive Systems Program has assumed this "total DSO" construct. 

Inclusion of the agents in the DSO federate, though, is much less justifiable. It was discovered in the process of the DSO+T study that each agent, when run by an individual Python interpreter, has a considerable memory footprint due to the necessity to load in the multiple libraries. Testing by Trevor in January 2025 showed that each interpretter loading in just a few libraries used about 30 MB of memory on his Mac. Multiplying this by thousandsa of agents produced a memory footprint that was and is generally untenable. To work around this, the agents are included as objects in the DSO with their HELICS communication managed by DSO itself. Through the use of parallelization libraries in Python ("joblib", in the case of DSO+T), the memory requirements become much more manageable.


### DSO State Machine
Borrow from some ideas from TENT

