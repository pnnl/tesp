function [ cloudy_direct ] = adjust_solar_direct( sunny_direct )
% ramps direct solar from 100% down to 10% between 1200 and 1210
% then back up to 100% from 1330 to 1400
% in minutes (index value) ramp down 720 to 730 and up 810 to 840
    cloudy_direct = sunny_direct;
    slope_down = (0.1*cloudy_direct(730) - cloudy_direct(720)) / 10;
    org_up = 0.1*cloudy_direct(810);
    slope_up = (cloudy_direct(840) - org_up) / 30;
    for i=1:1440
        if (i >= 720) && (i <= 730)
            cloudy_direct(i) = cloudy_direct(720) + slope_down*(i-720);
        elseif (i > 730) && (i < 810)
            cloudy_direct(i) = 0.1*cloudy_direct(i);
        elseif (i >= 810) && (i <= 840)
            cloudy_direct(i) = org_up + slope_up*(i-810);
        end
    end
end

