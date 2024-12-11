# Agent Software Architecture

This documen provides a prose-style description of the software architecture. More formal definitions of this architecture can be found in the UML diagrams and this document is intended to provide additional background and detail that is not easily expressed in those digrams. 

## Agent Functions
The following is a list of the functionality an agent needs to perform to do it's job in a transactive system.

### Device System Model
Every agent manages a devices and the process of creating a bid requires the agent to be able to estimate the devices autonomous behavior given static inputs. For examples, an HVAC system with a static thermostat setpoint will consume more or less energy depending on a number factors such as the outside air temperature and the occupancy of the house. Given a set of conditions, an agent needs to be able to estimate the energy consumption of the device so that it can know how much energy the device will consume and can bid into the energy market appropriately. In some markets, it will be required that the agent bid for multiple consecutive market periods at once and thus the device model must also support making such estimates.

### Bidding Strategy
Defines relationship between device amenity and willingness-to-pay for one or more market periods. This generally takes the form of a demand curve where the  quantity axis has units in terms of amenity rather than in terms of what the market operates in. Generally, devices turn energy into amenity and thus when a user (agent) is figuring out how to use a device it begins with thinking in terms of amenity. For example, the bidding strategy for an EV charger would be denominated in miles of range and would likely show a very high willingness-to-pay for enough charging to support the daily commute of the owner but perhaps a much lower willingness to pay for the last ten miles of range as they are generally not utilized or needed by the owner.

### Bid Formation
The agent is responsible for converting the bidding strategy (which is likely invariant in time) into bids which generally do vary in time. The variation of the bids in time is caused by changes in the environment in which the device is operating (weather, user needs). For example, though the bidding strategy is constant, changes in outdoor air temperature will generally change the bids that are submitted to the market. Similarly, if an EV owner suddenly becomes aware that the next drive time is not the daily commute of ten miles the following morning but is a 100 mile trip in three hours, the bids the EV charger will be submitting to the market will also change.

### Market Interaction Management
Each market has a specific way in which participants interact with it. Generally these can be thought of as timing requirments and format requirements. The agent is responsible for managing itself to ensure that the appropriate signals are submitted to the market at the correct time and in the correct manner and also to respond to any market signals it may receive in an appropriate manner.

### Device Interation Management
The agent is responsible for being able to interact with the device model in an appropriate manner to understand its current state and potentially (re-)estimate device parameters to use in its internal model of the device system.

## Data Collection and Reporting
The agent is repsonsible for collecting and reporting appropriate data for use in post-processing and analysis. Some of the data reported may values for existing internal variables or data that was submitted to the device under management or the market(s) in which it is participating. The agent may also be responsible for calculating some reported values such as the measured elasticity of the bids.

## Agent Operation
