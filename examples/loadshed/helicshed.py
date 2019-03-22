import time
import helics as h
import logging

helicsversion = h.helicsGetVersion()
print("Loadshed Federate: HELICS version = {}".format(helicsversion))

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

def create_federate(deltat=1.0, fedinitstring="--federates=1"):
    fedinfo = h.helicsCreateFederateInfo()
    h.helicsFederateInfoSetCoreName(fedinfo, "PythonLoadshedFederate")
    h.helicsFederateInfoSetCoreTypeFromString(fedinfo, "zmq")
    h.helicsFederateInfoSetCoreInitString(fedinfo, fedinitstring)
    h.helicsFederateInfoSetTimeProperty(fedinfo, h.helics_property_time_delta, deltat)
    fed = h.helicsCreateCombinationFederate("PythonLoadshedFederate", fedinfo)
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
    pubid = h.helicsFederateRegisterGlobalPublication(fed, "loadshed/sw_status", h.helics_data_type_int, "")
    subid = h.helicsFederateRegisterSubscription(fed, "gridlabdSimulator1/totalLoad", "")
    h.helicsFederateEnterExecutingMode(fed)
    
    switchings = [[0,1],[1800,0],[5400,1],[16200,0],[19800,1]]
    hours = 6
    seconds = int(60 * 60 * hours)
    grantedtime = -1
    for swt in switchings:
        t = swt[0]
        val = swt[1]
        while grantedtime < t:
            grantedtime = h.helicsFederateRequestTime(fed, t)
        logger.info('Switching to ' + str(val) + ' at ' + str(t))
        status = h.helicsPublicationPublishInteger(pubid, val)
    logger.info("Destroying federate")
    destroy_federate(fed)

if __name__ == "__main__":
    main()
    logger.info("Done!")
