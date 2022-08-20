DSOT_residential_hvac_setpt metadata contains setpoint distributions for resdiential hvac population
The metadata is based on RECS microdata analysis from the excel file 'Resdential Thermostat Schedules CBECS'.

********************************************
Definitions:

cooling setpoints distribution
occ_cool: distribution of temperatures when someone is at home during daytime i.e. after wake-up
unocc_cool: distribution of temperatures when no one is at home during daytime i.e. during office time
night_cool: distribution of temperatures during sleeping time

heataing setpoints distribution
occ_heat: distribution of temperatures when someone is at home during daytime i.e. after wake-up
unocc_heat: distribution of temperatures when no one is at home during daytime i.e. during office time
night_heat: distribution of temperatures during sleeping time

Other notes on how to use this data:
To utilize the microdata, the follow process is proposed.  The format of the data for space heating and space cooling is identical, so the procedure is identical for both datasets.
•	Take a random draw from the distribution of temperature values for when someone is home during the day.  This value is taken to be the ideal temperature.
•	Then a random draw is taken from the daytime when no one is home temperatures, which has been partitioned into subset distributions.  The subsets were created to track behaviors of individual respondents.  For each temperature reported in the daytime when someone is home category, there is a corresponding distribution for the daytime when no one is home data.  For example, if there were 23 temperatures reported in the daytime when someone is home microdata for space heating, so 23 distributions were generated for the daytime when no one is home category (i.e., if the random draw from temperature when someone is home produces the value 70, there is a distribution of daytime when no one is home temperatures generated just from respondents who had selected 70 as their daytime when someone is home temperature).
•	Then a random draw is taken from the nighttime temperatures, which has been partitioned into subset distributions.  The subsets were created to track behaviors of individual respondents.  For each temperature combination possible for the daytime when someone is home and daytime when no one is home, there is a corresponding distribution for the nighttime data.  For example, if there were 55 unique combinations of daytime when someone is home and daytime when no one is home temperatures, there would be 55 nighttime distributions (i.e., if the random draw from temperature when someone is home produces the value 70 and the random draw from daytime when no one is home is 75, there is a distribution of nighttime temperatures generated just from respondents who had selected 70 as their daytime when someone is home temperature and 75 as their daytime when no one is home temperature).
