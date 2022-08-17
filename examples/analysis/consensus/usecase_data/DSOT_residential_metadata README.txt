DSOT_residential_metadata contains parameters necessary to instantiate the residential building population for the DSOT study. These models are single-zone HVAC and will be instantiated in GLD using house a object.

Much of the metadata is classified by population density (Urban, Suburban, or Rural).

Much of this metadata is based on analysis done of the RECS survey results.

There are some parameters in some models that have no value defined. Rather than remove the parameter from the list, the parameter is listed with a value of "null".

********************************************
Definitions:

housing_type - By population density the fraction of residences of a given type.

housing_vintage - By population density and housing type, the fraction of residences of a given vintage. Note that these fraction values are fractions of the indicated population density. That is, the sum of all Urban houses across housing type and vintage will equal 1 (100%).

floor area (sq. ft.) - By population density and housing type, the average, minimum, maximum, and standard deviation of the housing floor area.

num_stories - By population density, the fraction of houses of the indicated number of stories.

aspect_ratio - By housing type, the minimum, maximum, average, and standard deviation of the aspect ratio (length to width) of the housing population.

mobile_home - By vintage, the fraction of houses that are mobile homes

window_wall_ratio - By housing type, the minimum, maximum, average, and standard deviation of the window-wall ratio of the population.

air_conditioning - The fraction of residences that have air-conditioning equipment

gas_heating - By population density, the fraction of residences with gas heating.

heat_pump - By population density, the fraction of residences with heat pumps.

water_heater_tank_size - There are two pieces of metadata that need to be correlated to determine the water heater tank size for a given residence. The floor_area entry defines the minimum and maximum floor areas for a given number of residents. With that, the tank_size lists a minimum and maximum water heater tanks size in gallons for a house with the indicated number of residents.

hvac_oversize - The minimum, maximum, average, and standard deviation of the oversizing factor for the HVAC systems installed in the residences.

window_shading - The minimum, maximum, average, and standard deviation of the fraction of windows shaded in the residences.

COP_average - The average COP of the air-conditioners by vintage.

GLD_residential_house_classes - A list (array) of the structure types that GridLAB-D instantiates when building a model of a neighborhood.

