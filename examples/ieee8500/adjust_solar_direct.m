function [ cloudy_direct ] = adjust_solar_direct( sunny_direct )
% ramps direct solar from 100% down to 10% between 1430 and 1440
% then back up to 100% from 1600 to 1630
    start_down = 60 * 14.5;
    stop_down = start_down + 10;
    start_up = 60 * 16.0;
    stop_up = start_up + 30;
    cloudy_direct = sunny_direct;
    slope_down = (0.1*cloudy_direct(stop_down) - cloudy_direct(start_down)) / 10;
    org_up = 0.1*cloudy_direct(start_up);
    slope_up = (cloudy_direct(stop_up) - org_up) / 30;
    for i=1:1440
        if (i >= start_down) && (i <= stop_down)
            cloudy_direct(i) = cloudy_direct(start_down) + slope_down*(i-start_down);
        elseif (i > stop_down) && (i < start_up)
            cloudy_direct(i) = 0.1*cloudy_direct(i);
        elseif (i >= start_up) && (i <= stop_up)
            cloudy_direct(i) = org_up + slope_up*(i-start_up);
        end
    end
end

