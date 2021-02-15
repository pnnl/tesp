function [ btuperhr kw ] = estimate_ac_size (floor_area, thermal_integrity)
% estimate_ac_size mimics the GridLAB-D design_cooling_capacity
%   floor_area is the total floor area of the house in square feet
%   thermal_integrity ranges from 0 (poor) to 6 (very good)
%   returns btu/hour rounded to the next highest 6000, and load kw (unadj)
    if thermal_integrity == 0
        Rroof = 11;
        Rwall = 4;
        Rfloor = 4;
        Rdoors = 3;
        Rwindows = 1 / 1.27;
        airchange_per_hour = 1.5;
    elseif thermal_integrity == 1
        Rroof = 19;
        Rwall = 11;
        Rfloor = 4;
        Rdoors = 3;
        Rwindows = 1 / 0.81;
        airchange_per_hour = 1.5;
    elseif thermal_integrity == 2
        Rroof = 19;
        Rwall = 11;
        Rfloor = 11;
        Rdoors = 3;
        Rwindows = 1 / 0.81;
        airchange_per_hour = 1.0;
    elseif thermal_integrity == 3
        Rroof = 30;
        Rwall = 11;
        Rfloor = 19;
        Rdoors = 3;
        Rwindows = 1 / 0.6;
        airchange_per_hour = 1.0;
    elseif thermal_integrity == 4
        Rroof = 30;
        Rwall = 19;
        Rfloor = 11;
        Rdoors = 3;
        Rwindows = 1 / 0.6;
        airchange_per_hour = 1.0;
    elseif thermal_integrity == 5
        Rroof = 30;
        Rwall = 19;
        Rfloor = 22;
        Rdoors = 5;
        Rwindows = 1 / 0.47;
        airchange_per_hour = 0.5;
    elseif thermal_integrity == 6
        Rroof = 48;
        Rwall = 22;
        Rfloor = 30;
        Rdoors = 11;
        Rwindows = 1 / 0.31;
        airchange_per_hour = 0.5;
    else % unknown, or default
        Rroof = 30;
        Rwall = 19;
        Rfloor = 22;
        Rdoors = 5;
        Rwindows = 1 / 0.47;
        airchange_per_hour = 0.5;
    end

    % other GridLAB-D defaults
    glazing_shgc = 0.67;
    window_exterior_transmission_coefficient = 0.6;
    over_sizing_factor = 0.0;
    latent_load_factor = 0.3;
    cooling_design_temperature = 95.0;
    cooling_design_setpoint = 75.0;
    air_density = 0.0735;
    air_heat_capacity = 0.2402;
    ceiling_height = 8.0;
    number_of_stories = 1.0;
    number_of_doors = 4.0;
    aspect_ratio = 1.5;
    window_wall_ratio = 0.15;
    exterior_wall_fraction = 1.0;
    exterior_ceiling_fraction = 1.0;
    exterior_floor_fraction = 1.0;
    design_peak_solar = 195.0;
    
    % estimate the default building dimensions
    gross_wall_area = 2.0 * number_of_stories * (aspect_ratio + 1.0) ...
        * ceiling_height * sqrt(floor_area / aspect_ratio / number_of_stories);
    door_area = number_of_doors * 3.0 * 78.0 / 12.0;
    window_area = gross_wall_area * window_wall_ratio * exterior_wall_fraction;
    exterior_ceiling_area = floor_area * exterior_ceiling_fraction / number_of_stories;
    exterior_floor_area = floor_area * exterior_floor_fraction / number_of_stories;
    net_exterior_wall_area = exterior_wall_fraction * gross_wall_area - window_area - door_area;
    volume = ceiling_height * floor_area;
    
    % GridLAB-D thermal calculations
    airchange_UA = airchange_per_hour * volume * air_density * air_heat_capacity;
    envelope_UA = exterior_ceiling_area / Rroof + exterior_floor_area / Rfloor ...
        + net_exterior_wall_area / Rwall + window_area / Rwindows + door_area / Rdoors;
    UA = airchange_UA + envelope_UA;
    design_internal_gains = 167.09 * floor_area^0.442;
    solar_heatgain_factor = window_area * glazing_shgc * window_exterior_transmission_coefficient;
    design_capacity = (1 + over_sizing_factor) * (1 + latent_load_factor) ...
        * (UA * (cooling_design_temperature - cooling_design_setpoint) + design_internal_gains + design_peak_solar * solar_heatgain_factor);
    
    % return values
    btuperhr = 6000 * ceil (design_capacity / 6000.0);
    kw = btuperhr * 0.001 / 3.412;
end

