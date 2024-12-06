# -*- coding: utf-8 -*-
"""
Created on Thursday, April 21, 2022
@author: Laurentiu Marinovici
"""

import getopt
import json
import logging
import time as tm

import helics as h

helicsversion = h.helicsGetVersion()

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)
logger.info('Federated Learning Federate - Test. HELICS version = {}'.format(helicsversion))


def start_loadshed(argv):
    # SETUP SIMULATION
    # ---------------
    # total simulation time for fed
    simTime = int(3)
    grantedTime = 0
    try:
        opts, args = getopt.getopt(argv, 'hc:t:', ['help', 'config=', 'simTime='])
        if not opts:
            logger.info('ERROR: need options and arguments to run.')
            logger.info('Usage: python FedLearning.py -c <HELICS configuration file in JSON format> -t <simulation duration in seconds>')
            sys.exit()
    except getopt.GetoptError:
        logger.info('Wrong option or no input argument! Usage: python FedLearning.py -c <HELICS configuration file in JSON format> -t <simulation duration in seconds>')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            logger.info('Help prompt. Usage: python FedLearning.py -c <HELICS configuration file in JSON format> -t <simulation duration in seconds>')
            sys.exit()
        # Set HELICS configuration file for the Python federate
        elif opt in ('-c', '--config'):
            configFileName = arg
        elif opt in ('-t', '--simTime'):
            simTime = float(arg)

    #  Registering  federate info from json
    fed = h.helicsCreateCombinationFederateFromConfig(configFileName)
    fedName = h.helicsFederateGetName(fed)
    logger.info('Federate name: {}'.format(fedName))
    endpoint_count = h.helicsFederateGetEndpointCount(fed)
    logger.info('Number of endpoints: {}'.format(endpoint_count))
    logger.info('######################## Entering Execution Mode ########################')
    #   Entering Execution Mode
    execStartTime = tm.time()
    h.helicsFederateEnterExecutingMode(fed)
    currTime = h.helicsFederateGetCurrentTime(fed)
    deltaTime = h.helicsFederateGetTimeProperty(fed, 140)  # helics_property_time_period = 140, in the C API
    logger.info('START: Current time: {0}. Delta time: {1}. Granted time: {2}.'.format(currTime, deltaTime, grantedTime))

    with open('loadshedScenario.json', 'r') as loadshedFile:
        loadshedScenario = json.load(loadshedFile)
    logger.info(loadshedScenario)
    # {
    #   45:
    #   {
    #     'R1_12_47_1_tn_1_mhse_1': 'OUT_OF_SERVICE',
    #     'R1_12_47_1_tn_2_mhse_1': 'OUT_OF_SERVICE',
    #     'R1_12_47_1_tn_2_mhse_2': 'OUT_OF_SERVICE'
    #   },
    #   135:
    #   {
    #     'R1_12_47_1_tn_2_mhse_1': 'IN_SERVICE'
    #   },
    #   255:
    #   {
    #     'R1_12_47_1_tn_2_mhse_2': 'IN_SERVICE'
    #   }
    # }
    # loadshedScenario = {
    #   120:
    #   {
    #     'R1_12_47_1_tn_1_mtr_1': 'OUT_OF_SERVICE',
    #     'R1_12_47_1_tn_2_mtr_1': 'OUT_OF_SERVICE',
    #     'R1_12_47_1_tn_2_mtr_2': 'OUT_OF_SERVICE'
    #   },
    #   240:
    #   {
    #     'R1_12_47_1_tn_1_mtr_1': 'OUT_OF_SERVICE',
    #     'R1_12_47_1_tn_2_mtr_1': 'IN_SERVICE',
    #     'R1_12_47_1_tn_2_mtr_2': 'OUT_OF_SERVICE'
    #   },
    #   300:
    #   {
    #     'R1_12_47_1_tn_1_mtr_1': 'OUT_OF_SERVICE',
    #     'R1_12_47_1_tn_2_mtr_1': 'IN_SERVICE',
    #     'R1_12_47_1_tn_2_mtr_2': 'IN_SERVICE'
    #   }
    # }

    while grantedTime <= simTime:
        totalBillMtrLoad = 0
        currTime = h.helicsFederateGetCurrentTime(fed)
        logger.info('\n========================================================')
        logger.info('Current time: {0}. Delta time: {1}. Granted time: {2}.'.format(currTime, deltaTime, grantedTime))
        iterStartTime = tm.time()
        for ind in range(0, endpoint_count):
            fedEP = h.helicsFederateGetEndpointByIndex(fed, ind)
            epName = h.helicsEndpointGetName(fedEP)
            # Checking for new messages destined to the particular monitor EP in this federate
            if epName.split('/')[0] == fedName and 'substation' in epName.split('/')[1]:
                logger.info(
                    '<<<<< time: {0}; federate: {1}; endpoint: {2}; message? {3}  >>>>>'.
                    format(grantedTime, fedName, epName,
                           h.helicsEndpointHasMessage(fedEP) and 'YES' or 'NO'))
                epMessages = dict({})
                while h.helicsEndpointHasMessage(fedEP):
                    message = h.helicsFederateGetMessage(fed)
                    messageDetails = {
                        'time received': h.helicsMessageGetTime(message),
                        'data': h.helicsMessageGetString(message),
                        'original source': h.helicsMessageGetOriginalSource(message),
                        'source': h.helicsMessageGetSource(message),
                        'original destination': h.helicsMessageGetOriginalDestination(message),
                        'destination': h.helicsMessageGetDestination(message)
                    }
                    # logger.info(messageDetails)
                    # If there are multiple messages from different previous time instances
                    # the following line would overwrite them
                    # allowing access to the latest ones through epMessages structure
                    epMessages[messageDetails['source']] = messageDetails
                for epKey in epMessages.keys():
                    logger.info(
                        f'\toriginal source: {epMessages[epKey]["original source"]}, source: {epMessages[epKey]["source"]}, data: {epMessages[epKey]["data"]}, time received: {epMessages[epKey]["time received"]}')
                    # if 'mhse' in epMessages[epKey]['source']:
                    totalBillMtrLoad += float(epMessages[epKey]["data"].split(" ")[0])
            if int(currTime) in [int(x) for x in list(loadshedScenario.keys())]:
                for key in loadshedScenario[str(int(currTime))]:
                    destination = f'R1-12.47-1/{key}'
                    # destination = f'R1-12.47-1/R1_12_47_1_switch_1'
                    messg = loadshedScenario[str(int(currTime))][key]
                    if messg == 'OUT_OF_SERVICE':
                        h.helicsEndpointSendBytesTo(fedEP, "0", destination)
                    elif messg == 'IN_SERVICE':
                        h.helicsEndpointSendBytesTo(fedEP, "1", destination)
                    logger.info(f'\tPutting {key} {messg} ({destination})')

        iterStopTime = tm.time()
        logger.info(f'Processing data at time {currTime} took {iterStopTime - iterStartTime} sec.')
        logger.info(f'\tCurrent total house load: {totalBillMtrLoad} W')
        nextTime = currTime + deltaTime
        if nextTime > simTime:
            break
        grantedTime = h.helicsFederateRequestTime(fed, nextTime)
    # Destroying federate
    # logger.info(f'It took {ccTime - eventAckTime} sec from when the event has been acknowledged for ADMS and the co-sim is done. Deltatime for CC is {deltaTime} sec.')
    h.helicsFederateDisconnect(fed)
    execStopTime = tm.time()
    logger.info(f'It took {execStopTime - execStartTime} sec from entering execution mode until exit.')


if __name__ == "__main__":
    import sys

    start_loadshed(sys.argv[1:])
