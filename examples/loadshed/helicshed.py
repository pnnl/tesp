import time
import helics as h
import logging

helicsversion = h.helicsGetVersion()
print("Loadshed Federate: HELICS version = {}".format(helicsversion))

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

def create_federate(deltat=1.0, fedinitstring="--federates=1"):
    fed = h.helicsCreateCombinationFederateFromConfig("loadshedConfig.json")
    return fed

def destroy_federate(fed, broker=None):
    status = h.helicsFederateFinalize(fed)
    state = h.helicsFederateGetState(fed)
    assert state == 3
    while (h.helicsBrokerIsConnected(broker)):
        time.sleep(1)
    h.helicsFederateFree(fed)
    h.helicsCloseLibrary()

def main():
    fed = create_federate()
    fedName = h.helicsFederateGetName(fed)
    swStatusEpName = fedName + "/sw_status"
    swStatusEp = h.helicsFederateGetEndpoint(fed, swStatusEpName)
    h.helicsFederateEnterExecutingMode(fed)
    
    switchings = [[0,1],[1800,0],[5400,1],[16200,0],[19800,1]]
    hours = 6
    seconds = int(60 * 60 * hours)
    mesg = h.helics_message()
    grantedtime = 0
    for swt in switchings:
        t = swt[0]
        val = swt[1]
        mesg.data= str(val)
        while grantedtime < t:
            print('Loadshed current time: ' + str(grantedtime))
            print('Loadshed requesting time: ' + str(t))
            grantedtime = h.helicsFederateRequestTime(fed, t)
            print('Loadshed granted time: ' + str(grantedtime))
        if grantedtime == t:
            logger.info('Switcht to ' + str(val) + ' at ' + str(t))
            h.helicsEndpointSendMessage(swStatusEp, mesg)
    logger.info("Destroying federate")
    destroy_federate(fed)

if __name__ == "__main__":
    main()
    logger.info("Done!")
