DSOT_ev_driving_metadata contains driving data from NHTS 2017 (National Household Travel Survey) from
https://nhts.ornl.gov/
---------------------------------------------
HOUSEID: house identifier
VEHID: vehicle identifier
STRTTIME: trip start time in HHMM format: we use this to estimate home leaving time
ENDTIME: trip end time in HHMM format: : we use this to estimate home arrival time
TRPMILES: miles driven on this particular trip
WHYFROM: trip origin (1 - home): we only care about home
WHYTO: trip destination (1 - home)
TRAVDAY: 1 - 7 : Sunday - Saturday
