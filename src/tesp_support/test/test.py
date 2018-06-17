#import sys
#from datetime import datetime
#from datetime import timedelta
#StartTime = '2013-07-01 00:00:00 PST+8PDT'
#time_fmt = '%Y-%m-%d %H:%M:%S %Z'
#StartTime = '2013-07-01 00:00:00 -0800'
#time_fmt = '%Y-%m-%d %H:%M:%S %z'
#dt_now = datetime.strptime (StartTime, time_fmt)

# should not begin with a number, or contain '-' for FNCS
#def gld_strict_name(val):
#  if val[0].isdigit():
#    val = 'gld_' + val
#  return val.replace ('-', '_')

#oldname = '9R1-12-47-1_tn_1_hse_1'
#newname = gld_strict_name (oldname)
#print (oldname, newname)

# step 1
#import tesp_support.tesp_config as tesp
#tesp.show_tesp_config()

# step 2
import tesp_support.api as tesp
tesp.make_tesp_case ('Demo.json')

# step 3
#import tesp_support.api as tesp
#tesp.make_monte_carlo_cases ('Demo.json')

# step 4
#import tesp_support.tesp_monitor as tesp
#tesp.show_tesp_monitor()

