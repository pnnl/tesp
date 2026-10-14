# Transactive Simulation Entities and Concepts

Over the years that PNNL has been researching transactive systems in general and growing it's imulation capability of said systems, we have reached some conclusions about the nature of the various entities in a transactive system and what defines their roles in the transactive system. This document will illuminate and define these roles, particularly with respect to the Transactive Energy Simulation Platform (TESP).

## Customers

The customer is the individual or organization that is being provided electricity by the utility and is legally responsible for the costs of their consumption. In transactive systems, the customer is assumed to have preferences around the costs of their electricity and how they choose to use it. For example, they may own an electrically heated hot tub and are willing to pay the costs associated with running it or they may prefer to have indoor heating via natural gas due to it's lower cost, for example. The preferences of the customers are assumed to be quantifiable in some manner such that they are able to particpate in a transactive system.

## Agents

All customers are assumed to interact in a transactive system through an agent. Agents take on the responsibility of taking the implicit or explicit preferences of the customers and be their proxy in the transactive system. They have the responsibility of creating market signals (_e.g._ bids, price estimates) as part of the transactive system and correspondingly responding to market signals they receive (_e.g._ market clearing price for energy). The agent relieves the customer of what could be frequent market interacts by using the customer's prefences and through an algorithm, convert them into the necessary market signals.

In TESP, any energy consuming or generating device has the potential to be a participant in a transactive system. Generally, these devices are controllable in some way (_e.g._ HVAC thermostat setpoints, EV charging power, battery charging or discharging power) but in some cases it is desirable to have uncontrollable energy consumers or producers participate in the market as a means of correctly understanding the demands on the electrical system. For example, rather than having the utility estimate the rooftop solar energy production for all customers on a particular circuit, the transactive system may require that this production be provided by the customer itself. In this case, each rooftop solar installation would have a corresponding agent so that it could generate this production estimate as its market signal in the transactive system.

The nature of the market signals depends on the nature of the transactive system. Most of the work PNNL has done to date has used a double-auction mechanism in which both suppliers and demanders submit bids to a central market that clears and uses the equilibrium (clearing) price as the cost of electricity during that market period. There are other transactive mechanisms in TESP, though, such as a consensus mechanism in which a community of participants exchange a price signal with a few neighbors in the system and each runs an optimization to produce a new price estimate, eventually with the group reaching a broad consensus on the price of electricity. 

## Utility or Distribution System Operator (DSO)

The utility is the entity responsible for running the portion of the power system to which most of the customers connect. In TESP we call this the "Distribution System Operator" or "DSO". There are a few distinct sub-entities within the DSO that TESP explicitely models each with their own roles and responsibilities.

### Distribution System Operator/Owner (DO or DOO)
The DO is responsible for maintaining the physical infrastructure of the distribution system; they are the "wires" company. They have the repair crews that perform repairs and maintenance, they are responsible for building new substations and circuits or upgrading existing ones, and since they own the meters and the infrastructure to read them, they are responsible for collecting customer meter data. 

Historically, TESP has not had much functionality that would be handled by a DO due to the nature of the research topics and analysis undertaken. The closest we have come is the consideration (but eventual removal) of a market to manage the voltage in the distribution system. Since the DO is ultimately responsible for maintaining voltage compliance and is likely to have the best powerflow model of the distribution system, it would be expected that it would be heavily involved in such a market. 

Another example of a possible role for the DO in PNNL's transactive studies: validating the viability of the bids. In the DSO+T study, all bids by the customer's agents were assuemd to not cause problems with voltage or power capacity in the distribution system. The DO could have been involved in taking the bids collected from the retail market operation and using them to solve a powerflow model to ensure that they did not cause physical problems in the distribution circuits.

### Market Operator (MO)

The market operator is responsible for implementing and running the retail market for all participating customers in the distribution system being managed by the DSO. The nature of this work depends on the transactive system itself but generally includes sending and receiving market signals with all retail market participants. The MO is responsible for providing an estimated load quantity and expressing any price-sensitivity in that load (_e.g._ a demand curve) for use in the wholesale market. The market is thus also responsible for maintaining a list of who are it's participants.

In TESP, every different tarriff structure would have a market operator to manage it. In the case of non-interactive rates where customers don't provide load estimates or price-responsiveness directly through a market mechanism, the MO is responsible for estimating the load quantity and providing this as a market signal to the wholesale market.

### Load-Serving Entity (LSE)

The LSE is the energy retailer and responsible for procuring the necessary energy to serve the customers in the distribution system. Generally in TESP this means interacting with the MO to determine the quantity and price of energy needed and interacting with the wholesale market to make that procurement. As is the case with the MO, each tarriff being used in the distribution system in question will have a corresponding LSE that makes the procurement for it's customers.

## Markets

Though we've already used the term "market" in the context of what a market operator does, markets are so central to TESP and transactive energy that they bear further exposition. So, starting at the beginning, economic theory is all about finding a way to allocate scarce resources that provides the most benefit. Markets are one such mechanism and the one implemented in TESP. In this case, the good whose allocation is being managed is often energy (though there can be and are markets for other related goods). Thus a "retail energy market" as is often implemented in TESP is concerned with allocating the available energy to a set of local (retail) customers. Generally, the price of energy is used as a market signal to which customers can respond by by adjusting their consumption.

In terms of the management of the electrical system, a market is used to manage a constraint (that is, the scarce resource). Thinking more generally, then, a market can be used to manage other constraints in the electrical system, with power capacity through a component being a very common one. If a component, such as a substation transformer, only has so much power transfer capacity, then a transactive means of managing the loading on the transformer could be to establish a market for the capacity of said transformer. This market would use some mechanism to allocate it's power transfer capacity to any interested party in getting electricity through that transformer (all the customers in the corresponding distribution system).

## Transactions or Value Exchanges

A transaction is created when two or more actors in a system reach an agreement on an exchange of goods or services. In the world of PNNL's Transactive System's Program (which TESP is a part of), these are also sometimes called "value exchanges". In TESP, each transaction in the transactive system specifies a price and quantity. 

## Curves

In TESP, a "curve" is a generic term for an expression of supply or demand that is usually thought of as a bid or offer. Curves can take the form of a collection of block bids or as a polynomial expression.




