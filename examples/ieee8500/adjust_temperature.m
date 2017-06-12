function [ cloudy_temp ] = adjust_temperature( temp )
% ramps temperature offset from 0 to -5 between 1200 and 1210
% then back up to 0 from 1330 to 1400
% in minutes (index value) ramp down 720 to 730 and up 810 to 840
    cloudy_temp = temp;
    slope_down = -5 / 10;
    slope_up = 5 / 30;
    for i=1:1440
        if (i >= 720) && (i <= 730)
            cloudy_temp(i) = cloudy_temp(i) + slope_down*(i-720);
        elseif (i > 730) && (i < 810)
            cloudy_temp(i) = cloudy_temp(i) - 5;
        elseif (i >= 810) && (i <= 840)
            cloudy_temp(i) = cloudy_temp(i) - 5 + slope_up*(i-810);
        end
    end
end

