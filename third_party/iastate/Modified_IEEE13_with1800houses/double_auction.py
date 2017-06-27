'''
main file of the auction object, mainly used for assigning data read from input
'''

# import from library or functions
import numpy as np
import csv
import math
import fncs
import sys
import json


from auction_object import auction_object

# ==================Generate agent registration information ==================================
# This is similar to a zpl file, for assigning initial values to the agent
# Read in json file with the controller registration data
filename = sys.argv[1]
lp = open(filename).read()
auctionDict = json.loads(lp)
# ================== capacity_reference_bid_price ==================================
# Read in buyer name
#filename = "capacity_reference_bid_price"
#with open("../data/" + filename + ".csv", 'r') as f:
#        reader = csv.reader(f)
#        capacity_reference_bid_price = list(map(tuple, reader))

# ====================Open and define metrics JSON files ========================
unit = auctionDict['initial_values']['market_information']['unit']
auction_op = open ("auction_" + sys.argv[2] + "_metrics.json", "w")
controller_op = open ("controller_" + sys.argv[2] + "_metrics.json", "w")
auction_meta = {'clearing_price':{'units':'USD','index':0},'clearing_type':{'units':'[0..5]=[Null,Fail,Price,Exact,Seller,Buyer]','index':1}}
controller_meta = {'bid_price':{'units':'USD','index':0},'bid_quantity':{'units':unit,'index':1}}
StartTime = "2012-01-01 00:00:00 PST"
auction_metrics = {'Metadata':auction_meta,'StartTime':StartTime}
controller_metrics = {'Metadata':controller_meta,'StartTime':StartTime}

# ====================Initialize simulation time step and duration===============

tf = 48 # simulation time in hours
deltaT = 300 # simulation time interval in seconds, which usually the same as auction period

# ====================Obtain market information====================================

# print ("Running for %d hours with %d-minute interval, starting at 0 min:" % (tf, deltaT/60))

# Create auction object:
aucObj = auction_object(auctionDict)

time_granted = 0 # time variable for checking the retuned time from FNCS
timeSim = 0
# Start simulation for each time step:
while (time_granted < tf*3600):
    # ============================ Value assigned to the auction object from csv files ============================
    # Obtain the step number for the capacity_reference_bid_price, for read in from csv file only, not for FNCS read in
    # Bidder prices are given with 5 minute interval: 
    bidderStepNum = int(math.floor(time_granted / 300))
    
    # =================Simulation for each time step ============================================================       
    # Initialization when time = 0
    if time_granted == 0:
        aucObj.initAuction()
        
    # Subscribe values from FNCS broker (or csv file here)
    if time_granted != 0:
        fncs_sub_value_String = ''
        fncs_sub_value_unicode = (fncs.agentGetEvents()).decode()
        if fncs_sub_value_unicode != '':
            fncs_sub_value_String = json.loads(fncs_sub_value_unicode)
            aucObj.subscribeVal(fncs_sub_value_String)
    
    # Process presync, sync and postsync part for each time step
    # Presync process
    aucObj.presync(time_granted) 

    # write metrics only at market clearings
    if len (aucObj.offers['name']) > 0:
        clearing_str = aucObj.market['cleared_frame']['clearing_type']
        clearing_type = 0
        if clearing_str == 'CT_FAILURE':
            clearing_type = 1
        elif clearing_str == 'CT_PRICE':
            clearing_type = 2
        elif clearing_str == 'CT_EXACT':
            clearing_type = 3
        elif clearing_str == 'CT_SELLER':
            clearing_type = 4
        elif clearing_str == 'CT_BUYER':
            clearing_type = 5
        auction_metrics[str(time_granted)] = {aucObj.market['name']:[aucObj.market_output['clear_price'],clearing_type]}
        controller_metrics[str(time_granted)] = {}
        for i in range(len(aucObj.offers['name'])):
            controller_metrics[str(time_granted)][aucObj.offers['name'][i]] = [aucObj.offers['price'][i], aucObj.offers['quantity'][i]]
    
    # Sync process
    # No sync process in this object
    
    # Postsync process
    # No postsync process in this object
    
    if (time_granted < (timeSim + deltaT)) :
#        print ('requesting the same', timeSim + deltaT, flush=True)
        time_granted = fncs.time_request(timeSim + deltaT)
    else:
        timeSim = timeSim + deltaT
#        print ('requesting new', timeSim + deltaT, flush=True)
        time_granted = fncs.time_request(timeSim + deltaT)


# ==================== Finalize the metrics output ===========================

print ('writing metrics', flush=True)
print (json.dumps(auction_metrics), file=auction_op)
print (json.dumps(controller_metrics), file=controller_op)

print ('closing files', flush=True)
auction_op.close()
controller_op.close()
        
print ('finalizing FNCS', flush=True)
fncs.finalize()

    

    
    
            
    



















