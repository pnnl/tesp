% Copyright (C) 2021-2022 Battelle Memorial Institute
% file: adjust_temperature.m

function [ cloudy_temp ] = adjust_temperature( temp )
% ramps temperature offset from 0 to -5 between 1430 and 1440
% then back up to 0 from 1600 to 1630
    start_down = 60 * 14.5;
    stop_down = 60 * 14.6667;
    start_up = 60 * 16.0;
    stop_up = 60 * 16.5;
    cloudy_temp = temp;
    slope_down = -5 / 10;
    slope_up = 5 / 30;
    for i=1:1440
        if (i >= start_down) && (i <= stop_down)
            cloudy_temp(i) = cloudy_temp(i) + slope_down*(i-start_down);
        elseif (i > stop_down) && (i < start_up)
            cloudy_temp(i) = cloudy_temp(i) - 5;
        elseif (i >= start_up) && (i <= stop_up)
            cloudy_temp(i) = cloudy_temp(i) - 5 + slope_up*(i-start_up);
        end
    end
end

