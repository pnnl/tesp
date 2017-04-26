import numpy as np

def writeRegistration (filename):
    import json
    import re
    import os
    import shutil
    
    folderName = "input"
    ip = open (filename + ".glm", "r")
    if not os.path.exists("input"):
        os.makedirs(folderName)
    else:
        shutil.rmtree("input") # delete the existing input folder in case there are data not needed
        os.makedirs(folderName)
    op_auction = open (folderName + "/auction_registration.json", "w")
     
    # parameters to be written (in case it is not assigned in glm file)
    # controller data:
    periodController = 300
    control_mode = "CN_RAMP"
    min_ramp_high = 1.5
    max_ramp_high = 2.5
    min_range_high = 1.5
    max_range_high = 2.5
    # used with np.random.uniform below
    min_ramp_low = 1.5
    max_ramp_low = 2.5
    min_range_low = -3.0
    max_range_low = -2.0
    min_base_setpoint = 76.0
    max_base_setpoint = 80.0
    bid_delay = 60
    use_predictive_bidding = 0
    use_override = "OFF"
    
    # market data:
    marketName = "Market_1"
    unit = "kW"
    periodMarket = 300
    initial_price = 0.02078
    std_dev = 0.01 # 0.00361
    price_cap = 3.78
    special_mode = "MD_NONE" #"MD_BUYERS"
    use_future_mean_price = 0
    clearing_scalar = 0.0
    latency = 0
    ignore_pricecap = 0
    ignore_failedmarket = 0
    statistic_mode = 1
    stat_mode =  ["ST_CURR", "ST_CURR"]
    interval = [86400, 86400]
    stat_type = ["SY_MEAN", "SY_STDEV"]
    value = [0.02078, 0.01] # 0.00361]
    capacity_reference_object = 'substation_transformer'
    max_capacity_reference_bid_quantity = 5000
    
    # house data:
    air_temperature = 78.0 # 0.0
    
    # Assign empty dictionary
    controllers = {}
    auctions = {}
     
    ip.seek(0,0)
    inFNCSmsg = False
    inHouses = False
    endedHouse = False
    isELECTRIC = False
    
    houseName = ""
    FNCSmsgName = ""
    # Obtain controller dictionary based on house numbers
    for line in ip:
        lst = line.split()
        if len(lst) > 1:
            if lst[1] == "house":
                inHouses = True
            # Check fncs_msg object:
            if lst[1] == "fncs_msg":
                inFNCSmsg = True
            # Check for ANY object within the house, and don't use its name:
            if inHouses == True and lst[0] == "object" and lst[1] != "house":
                endedHouse = True
#                print('  ended on', line)
            # Check FNCS_msg object name
            if inFNCSmsg == True:
                if lst[0] == "name":
                    FNCSmsgName = lst[1].strip(";")
                    inFNCSmsg = False
            # Check house object with controller inside
            if inHouses == True:
                if lst[0] == "name" and endedHouse == False:
                    houseName = lst[1].strip(";")
                if lst[0] == "air_temperature":
                    air_temperature = lst[1].strip(";")
                if lst[0] == "cooling_system_type":
                    if (lst[1].strip(";") == "ELECTRIC"):
                        isELECTRIC = True
#                        print('ELECTRIC parsed',houseName,air_temperature)
        elif len(lst) == 1:
            if inHouses == True: 
                inHouses = False
                endedHouse = False
                if isELECTRIC == True:
#                    print('  ELECTRIC writing',houseName,air_temperature,'on',line)
                    controller_name = houseName + "_thermostat_controller"
                    controllers[controller_name] = {}
                    ramp_low = np.random.uniform (min_ramp_low, max_ramp_low)
                    range_low = np.random.uniform (min_range_low, max_range_low)
                    ramp_high = np.random.uniform (min_ramp_high, max_ramp_high)
                    range_high = np.random.uniform (min_range_high, max_range_high)
                    base_setpoint = np.random.uniform (min_base_setpoint, max_base_setpoint)
                    controllers[controller_name]['controller_information'] = {'control_mode': control_mode, 'marketName': marketName, 'houseName': houseName, 'bid_id': controller_name, 'period': periodController, \
                               'ramp_low': ramp_low, 'ramp_high': ramp_high, 'range_low': range_low, 'range_high': range_high, 'base_setpoint': base_setpoint, \
                               'bid_delay': bid_delay, 'use_predictive_bidding': use_predictive_bidding, 'use_override': use_override}
                    controllers[controller_name]['market_information'] = {'market_id': 0, 'market_unit': unit, 'initial_price': initial_price, 'average_price': initial_price, 'std_dev': std_dev, 'clear_price': initial_price, 'price_cap': price_cap, 'period': periodMarket}
#                   controllers[controller_name]['house_information'] = {'target': 'air_temperature', 'deadband': 0, 'setpoint0': -1, 'currTemp': -1, 'controlled_load_all': 0, 'powerstate': 'ON'}
                    isELECTRIC = False
                       
    # Write market dictionary
    auctions[marketName] = {}
    auctions[marketName]['market_information'] = {'market_id': 1, 'unit': unit, 'special_mode': special_mode, 'use_future_mean_price': use_future_mean_price, 'pricecap': price_cap, 'clearing_scalar': clearing_scalar, \
                                                  'period': periodMarket, 'latency': latency, 'init_price': initial_price, 'init_stdev': std_dev, 'ignore_pricecap': ignore_pricecap, 'ignore_failedmarket': ignore_failedmarket, \
                                                  'statistic_mode': statistic_mode, 'capacity_reference_object': capacity_reference_object, 'max_capacity_reference_bid_quantity': max_capacity_reference_bid_quantity}
    auctions[marketName]['statistics_information'] = {'stat_mode': stat_mode, 'interval': interval, 'stat_type': stat_type, 'value': [0 for i in range(len(stat_mode))]}
    # obtain controller information for market:
    controllers_names = []
    for key, value in controllers.items(): # Add all controllers
        controllers_names.append(key)
    auctions[marketName]['controller_information'] = {'name': controllers_names, 'price': [0 for i in range(len(controllers))], 'quantity': [0.0 for i in range(len(controllers))], 'state': ["ON" for i in range(len(controllers))]}
    
    # Write file for controller registration
    for key, value in controllers.items(): # Process each controller
        controllerDict = {}
        houseName = controllers[key]['controller_information']['houseName']
        singleControllerReg = {}
        singleControllerReg['agentType'] = "controller"
        singleControllerReg['agentName'] = key
        singleControllerReg['timeDelta'] = 60 # Assum time step is always 60 sec for now
        singleControllerReg['broker'] = "tcp://localhost:5570"
        # publications
        publications = {}
        publications['market_id'] = {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 1}
        publications['bid_id'] = {'propertyType': 'string', 'propertyUnit': 'none', 'propertyValue': 'none'}
        publications['bid_name'] = {'propertyType': 'string', 'propertyUnit': 'none', 'propertyValue': 'none'}
        publications['price'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
        publications['quantity'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 1}
        publications['bid_accepted'] = {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 1}
        publications['state'] = {'propertyType': 'string', 'propertyUnit': 'none', 'propertyValue': 'BS_UNKNOWN'}
        publications['rebid'] = {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 0}
        publications['override_prop'] = {'propertyType': 'string', 'propertyUnit': 'none', 'propertyValue': 'none'}
        singleControllerReg['publications'] = publications
        # subscriptions
        subscriptions = {}
        auction = {}
        marketName = controllers[key]['controller_information']['marketName'] # Retrieve market name fro controller input information
        auction[marketName] = {}
        auction[marketName]['id'] = {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 1}
        auction[marketName]['initial_price'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
        auction[marketName]['average_price'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
        auction[marketName]['std_dev'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
        auction[marketName]['clear_price'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
        auction[marketName]['price_cap'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
        subscriptions['auction'] = auction
        singleControllerReg['subscriptions'] = subscriptions
        # Values recieved from house
        values = {}
        values['air_temperature'] = {'topic': FNCSmsgName + "/" + houseName + "/air_temperature", 'default': air_temperature, 'type': 'double', 'list': 'false'}
        values['power_state'] = {'topic': FNCSmsgName + "/" + houseName + "/power_state", 'default': 'ON', 'type': 'string', 'list': 'false'}
        values['hvac_load'] = {'topic': FNCSmsgName + "/" + houseName + "/hvac_load", 'default': 0, 'type': 'double', 'list': 'false'}
        singleControllerReg['values'] = values
        controllerDict['registration'] = singleControllerReg
        # Input data
        controllerDict['initial_values'] = controllers[key]
        # Write the controller into one json file:
        filename = folderName + "/controller_registration_" + key + ".json"
        op_controller = open(filename, "w")
        json.dump(controllerDict, op_controller)
        op_controller.close()
        
    # Write file for auction registration
    auctionReg = {}
    auctionReg['agentType'] = "auction"
    auctionReg['agentName'] = list(auctions.items())[0][0]
    auctionReg['timeDelta'] = 60 # Assum time step is always 60 sec for now
    auctionReg['broker'] = "tcp://localhost:5570"
    publications = {}
    publications['std_dev'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
    publications['average_price'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
    publications['clear_price'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
    publications['market_id'] = {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 1}
    publications['price_cap'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
    publications['period'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
    publications['initial_price'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
    auctionReg['publications'] = publications
    subscriptions = {}
    controller = {}
    auctionDict = {}
    marketName = auctionReg['agentName'] # Retrieve market name fro controller input information
    for key, value in controllers.items():
        if controllers[key]['controller_information']['marketName'] == marketName:
            singleControllerReg = {}
            singleControllerReg[key] = {}
            singleControllerReg[key]['price'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
            singleControllerReg[key]['quantity'] = {'propertyType': 'double', 'propertyUnit': 'none', 'propertyValue': 0.0}
            singleControllerReg[key]['bid_id'] = {'propertyType': 'string', 'propertyUnit': 'none', 'propertyValue': 0}
            singleControllerReg[key]['state'] = {'propertyType': 'string', 'propertyUnit': 'none', 'propertyValue': 'ON'}
            singleControllerReg[key]['rebid'] = {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 0}
            singleControllerReg[key]['market_id'] = {'propertyType': 'integer', 'propertyUnit': 'none', 'propertyValue': 0}
            controller[key] = singleControllerReg[key]
    subscriptions['controller'] = controller   
    auctionReg['subscriptions'] = subscriptions
    # Values received from MATPOWER and GridLAB-D
    values = {}
    values['LMP'] = {'topic': "pypower/LMP_B7", 'default': 0.1, 'type': 'double', 'list': 'false'}
    values['refload'] = {'topic': "gridlabdSimulator1/distribution_load", 'default': '0', 'type': 'complex', 'list': 'false'}
    auctionReg['values'] = values

    auctionDict['registration'] = auctionReg 
    # Input data
    auctionDict['initial_values'] = auctions[marketName]
    json.dump(auctionDict, op_auction) 
    
    # Close files
    ip.close()
    op_auction.close()

    return auctions, controllers

