'''
main file of the controller object, mainly used for assigning data read from input
'''

# import from library or functions
import numpy as np
import csv
import fncs
import sys
import json

from ramp_controller_object import ramp_controller_object

# ==================Generate agent registration information ==================================
# This is similar to a zpl file, for assigning initial values to the agent
# If it is ramp controller:
# Read in json file with the controller registration data
filename = sys.argv[1]
lp = open(filename).read()
controllerDict = json.loads(lp)

# ====================Initialize simulation time step and duration===============   
tf = 48 # simulation time in hours
deltaT = 60  # simulation time interval in seconds, which usually the same as controller period 
     
# ====================Obtain controller bid====================================

#print ("Running for %d hours with %d-minute interval, starting at 0 min:" % (tf, deltaT/60))       

# Create controller object:
controller_obj =  ramp_controller_object(controllerDict)

time_granted = 0 # time variable for checking the retuned time from FNCS
timeSim= 0

# Start simulation for each time step:     
# for timeSim in np.arange(0, tf*3600, deltaT):
while (time_granted < tf*3600):
    # =================Simulation for each time step ============================================ 
    # Initialization when time = 0
    if time_granted == 0:
        controller_obj.initController()
    
    # Subscrib values from FNCS broker (or csv file here)
    if time_granted != 0:
        fncs_sub_value_String = ''
        fncs_sub_value_unicode = (fncs.agentGetEvents()).decode()
        if fncs_sub_value_unicode != '':
            fncs_sub_value_String = json.loads(fncs_sub_value_unicode)
            controller_obj.subscribeVal(fncs_sub_value_String)
    
    # Process presync, sync and postsync part for each time step:
    
    # Presync process
    presyncReturn = controller_obj.presync()
    
    # Sync process
    syncReturn = controller_obj.sync(time_granted)
    
    # Postsync process
    postsyncReturn = controller_obj.postsync()
    
    # Update controller t2 data
    if presyncReturn < 0 or syncReturn < 0 or postsyncReturn < 0:
        # Stop running the simulation if returned invalid time t2
        break
    
    controller_obj.controller['t2'] = min(presyncReturn, syncReturn, postsyncReturn)
    
    if (time_granted < (timeSim + deltaT)) :
        time_granted = fncs.time_request(timeSim + deltaT)
    else:
        timeSim = timeSim + deltaT
        time_granted = fncs.time_request(timeSim + deltaT)
        
# finalize fncs
fncs.finalize()
    


        
        
        
        
        