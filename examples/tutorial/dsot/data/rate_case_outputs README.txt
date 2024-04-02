rate_case_ouputs.json is the file produced by the script DSO_rate_making.py. This script is run at the completion of the simulation and is used to calculate the flat rate (for all customers in the base case and non-participating customers in the transactive case).

rate_case_inputs.json is a nearly identical file which is used as the input for DSO_rate_making.py and can be considered the initial guess for the flat_rate value.

Generally, the rate case output defines prices for the different customer classes (residential, commercial, industrial) at various consumption tiers. This allows a rate case to be defined where low levels of consumption are more affordable while very high levels of consumption are expensive. Within each consumption tier the price of energy is constant and not a function of time. Even for a consumer with very high levels of consumption, the first kWh of energy used during a billing period is billed based on the price at the lowest tier.

Each DSO will run its own rate case and will produce different rate case outputs. 

The outputs of the rate case analysis will be written to this file in the the shown format. These values will then be used when calculating the balance sheets for the various entities in the system.


********************************************
Definitions:

flate rate ($/kWh): flat rate for each DSO that is applied to each customer regardless of class (e.g. residential, commercial, industrial)

connection_charge ($): constant monthly connection fee which is the same for all customers.

max_quantity (kWh): Defines the upper limit of the tier. For the highest tier, the value in the .json is an arbitrarily large number used to approximate infinity.

price ($/kWh): Defines the constant price of energy consumed in the given tier.

demand_charge ($/kW): Defines the cost of each kW of power consumption during the peak 15 minute period per month for each customer.