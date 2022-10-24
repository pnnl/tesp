DSOT_commercial_metadata contains parameters necessary to instantiate the commercial building population for the DSOT study. Most of these models are single-zone HVAC and  will be instantiated in GLD using house object though a few are multi-zone and will be initiated using a jModelica FMU model.

The parameters are divided into two categories: those that are common to all models and those that are model-specifics. In almost all model cases, all the values found in the "general" section are applicable. In a few cases (e.g. large_office, hospital/inpatient) there are unique values for a given parameter that supersede the value in the "general" section (e.g. HVAC COP).

There are some parameters in some models that have no value defined. Rather than remove the parameter from the list, the parameter is listed with a value of "null".

********************************************
Definitions:

general:

    thermal_integrity: the average U values for commercial building components in the indicated zones by vintage, climate zone, and construction type. Also includes the solar heat gain coefficient (SGHC) by vintage
    
    interior_mass (BTU/(F - sq. ft.)): amount of interior mass by the indicated average qualitative amount of furniture
    
    wall_thermal_mass (BTU/(F - sq. ft.)): amount of interior mass by vintage
    
    building_type: fraction by model type for buildings in the indicated population density
    
    HVAC: Roof-top unit details:
        COP by building vintage
        mean, standard deviation and upper and lower bounds for RTU over-sizing factor

building_model_specifics:

    building_model_type: single-zone or multi-zone building and HVAC model

    building_scorecard: Associated DOE Reference Building Scorecard used for key parameters (e.g. aspect ratio)

    vintage: fraction of population of the indicated age

    total_area (thousands of sq ft.): fraction of population within the indicated range

    ceiling_height (ft): self-explanatory

    number of stories - self-explanatory

    aspect_ratio: ratio of the width to length of the building floor plan

    window-wall_ratio: ratio of windows to walls in terms of area.

    Hm (BTU/(hr - F - sq. ft.)): surface co-efficient

    wall_construction: fraction of the population with wall materials of the indicated type

    roof_construction_insulation: fraction of the population with the indicated roof insulation type

    ventalation_requirements - self-explanatory

    fraction_awning: fraction of buildings with awnings providing additional shade to windows

    primary_electric_heating: fraction of population with electric heating (total) also broken down by population density (Urban, Suburban, Rural).

    electric_heating_system_type: fraction of those buildings with electric heating with the indicated type of electric heating
    
    occupancy: Fraction of hours in which the building is occupied by the indicated hour bin. Average hours and fraction of population are also explicitly called out.  Typical occupancy start time and duration are provide by day of the week.

    internal_heat_gains: the power of the listed sources providing internal heating during occupied times (need to be scaled down for unoccupied times).  Lighting, refrigeration, and MEL are in units of (W/sq. ft). Occupancy is number of occupants per sq.ft.



