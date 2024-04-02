8-node-metadata.json contains parameters necessary to instantiate the 8-node transmission system model and the associated DSOs as well as parameters needed for performing the economics analysis of the associated system (primarily for the DSOs). The metadata is divided into two general sections: parameters that are general across all DSOs and DSO-specific parameters.

There are some parameters in some models that have no value defined. Rather than remove the parameter from the list, the parameter is listed with a value of "null".

********************************************
Definitions:

general:

    hours_per_year (hrs): For analysis purposes, the number of hours in a year.

    salary_to_total_compensation_ratio: The average value of ratio of the average worker's total compensation (salary, benefits, bonuses, etc) to their salary.

    customers_per_FTE: The ratio of customers per full-time-equivalent worker in a DSO. Used to estimate the number of workers required to run a DSO.

    transmission_access_fee_per_MWh: Fee payed by the DSO to the owner of the transmission system to cover operation of the transmission system ($/MW-hr)

    iso_fee_per_MWh: Stampage fee paid by the DSO to the ISO to cover its operating expenses ($/MW-hr)
    
    generation_capacity_fee_per_MW:  Cost paid by DSO based on its annual peak load to cover generator capacity payments ($/MW)
    
    comm_customers_per_bldg: The ratio of commercial customers per commercial building in a DSO. This uses ratios of CBECs and RECs building counts and ERCOT commercial and residential customer ratios to estimate this ratio.

    *** annual_materials_cost_per_customer ($): ????

    distribution_automation_network_costs_per_customer ($/customer): By population density, the average cost of distribution automation communications network cost normalized by customer.

    market_operations_cost ($): Costs associated with operating the DSO retail market broken down as a flat cost, cost per customer, and cost per substation.

    field_crew_hourly_rate ($/hr): By population density, the hourly unburdened labor cost of DSO field crews. (Salary?)

    operation_center_hourly_rate ($/hr): By population density, the hourly unburdened labor cost of DSO field crews. (Salary?)

    customer_service_agent_hourly rate ($/hr): By population density, the hourly unburdened labor cost of customer service agent. (Salary?)

    DER_recruiter_hourly_rate ($/hr): By population density, the hourly unburdened labor cost of a recruiter of DER assets for participation. (Salary?)

    billing_representative_hourly_rate ($/hr): By population density, the hourly unburdened labor cost of a billing representative for the DSO. 

    market_operations_labor_hourly_rate ($/hr): By population density, the hourly unburdened labor cost of the DSO's market operations. 

    feeder_capital_cost_rate ($/MVA) - By population density, the capital cost of a distribution system feeder

    retail_operations_costs ($, $/customer) - Cost of DSO retail operations broken down by flat costs ($) and per-customer cost ($/customer).

    substation_cost - Metadata associated with calculating the substation costs

        transformer_capital_costs ($/MVA) - Capital costs of substation transformers.

        substation_size (acre/MVA) - Size of land needed for substation

        balance_of_substation-costs ($/MVA) - Total of non-transformer substation equipment costs.

        land_cost ($/acre) - By population density, the cost of the land required for the substation.

        transformer_maintenance_costs ($/transformer) - Annual maintenance costs associated with the substation transformer

        transformer_lifetime (yrs) - Rated lifetime of the substation transformer.

    customer_transformer_rating ($) - By customer type, the rating of the customer (secondary) transformers.

    meter_cost ($) - Cost of customer meters.

    RCI_customer_growth_rates - By customer types, the customer growth rate.

    transmission_charge_rate ($/MWh) - Wholesale cost of energy delivery collected by DSO on behalf of the transmission system owners and paid by the DSO in question.

   market_ops_hardware_software ($, $/customer) - The cost of the DSO retail market operations hardware and software broken down by flat cost ($) and per-customer cost ($/customer).

    workspace_costs ($) - By population density, the total annual lease or mortgage cost of the DSO workplace.

DSO-specific

    bus_number - Numerical index of the transmission bus the DSO is associated with.

    name - Name of DSO (unique across all DSOs)

    climate_zone - Climate zone number associated with the location of the DSO (transmission node location). This number directly relates to which GridLAB-D prototypical feeders are used in populating the DSO.

    utility_type - Population density of the DSO

    peak_season - Season (winter, summer, or dual) during which the peak loads occurs.

    RCI_energy_mix - The fraction of the total load for the given DSO associated with each customer class

    number_of_customers - Total number of customers for the DSO
    
    number_of_gld_homes - Total number of Gridlab-D residential houses for all feeders in the simulation for the DSO

    number_of_substations - The number of substations in the DSO

    MVA_growth_rate - The growth rate of the total load of the DSO

    weather_file - The weather file used when simulating the given DSO

    RCI_customer_count_mix - The fraction of the total number of customers for the given DSO associated with each customer class

    average_load_MW (MW) - The average load of the DSO

    total_load_time_series_file - When simulating the base case (non-transactive, moderate renewables), the total load of the system is pre-defined from historical data. This total load, by definition, is what the DSO must bid into the market and is also used to define, through a separate analysis, the industrial load for the DSO. This parameter indicates the file that contains the time-series data that defines the total load.

    total_load_time_series_file - The name of the time-series industrial load profile, generated by a separate analysis based on the simulated R+C load and the total load profile.

    winter_peak_MW (MW) - The peak load of the DSO during the winter season.

    summer_peak_MW (MW) - The peak load of the DSO during the summer season.

    **** capacity_limit_MW (MW) - ???

    scaling_factor - In order to avoid simulating every actual customer in Texas, we simulate a representative subset (using the prototypical GridLAB-D feeders) and scale up the load (as defined by this parameter) roughly match the load that the given DSO should have. 

    substation_upgrade -  Results from an offline analysis that defines the size of each greenfield and brownfield substation, given simply as a vector in the JSON. These values have the scaling factor for the DSO built into them. That is, this is not necessarily the size of the simulated substation transformer but rather all the "real-world" transformers being represented by the much smaller number of simulated transformers.

    substation_transformer_count - Number of actual substation transformers in the real-world system that are being modeled by a much smaller number in the simulated system. 

    wholesale_demand_charge_rate ($/MW) - The demand charge rate for the DSO in question that is paid to the system operator.

    bilaterals - To replicate the effect of bilateral energy trading between the DSO and the generators, the wholesale market will still dispatch 100% of the generation but a certain fraction of that will be considered to be under a bilateral contract. These values define the price the DSO has contracted that energy at ($/MWh) and the the fraction of their total load under bilateral contract.

    DSO_system_energy_fraction - Fraction of total energy served by the system, used to calculate the fraction of the ISO reserve costs and wholesale losses that the DSO in question must cover.
