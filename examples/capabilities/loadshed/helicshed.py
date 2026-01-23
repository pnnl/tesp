# Copyright (c) 2021-2025 Battelle Memorial Institute
# file: helicsshed.py

import helics as h
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())

helicsversion = h.helicsGetVersion()
log.info("Loadshed Federate: HELICS version = {}".format(helicsversion))


def create_federate(deltat=1.0, fedinitstring="--federates=1"):
    fed = h.helicsCreateCombinationFederateFromConfig("loadshedConfig.json")
    return fed


def destroy_federate(fed, broker=None):
    h.helicsFederateDestroy(fed)


def show_helics_query(fed, qstr):
    hq = h.helicsCreateQuery("mainbroker", qstr)
    qret = h.helicsQueryExecute(hq, fed)
    try:
        log.info(qstr + "=" + ",".join(qret))
    except:
        log.info(qstr + "=")
        log.info(qret)
        pass
    h.helicsQueryFree(hq)


def main():
    fed = create_federate()
    fedName = h.helicsFederateGetName(fed)
    log.info("The name of the federate is: {0}.".format(fedName))
    endpoint_count = h.helicsFederateGetEndpointCount(fed)
    log.info("Number of {0} endpoints.".format(endpoint_count))
    log.info("########################   Entering Execution Mode  ##########################################")
    h.helicsFederateEnterExecutingMode(fed)

    swStatusEpName = fedName + "/sw_status"
    swStatusEp = h.helicsFederateGetEndpoint(fed, swStatusEpName)
    h.helicsFederateEnterExecutingMode(fed)

    for qstr in ["federates", "endpoints", "publications", "filters", "dependencies", "dependents", "isinit"]:
        show_helics_query(fed, qstr)

    switchings = [[0, 1], [1800, 0], [5400, 1], [16200, 0], [19800, 1]]
    hours = 6
    seconds = int(60 * 60 * hours)
    currTime = h.helicsFederateGetCurrentTime(fed)

    while currTime < seconds:
        currTime = h.helicsFederateGetCurrentTime(fed)
        grantedtime = h.helicsFederateRequestNextStep(fed)
        if (currTime * 100) % 100 == 0:
            log.debug("Current time: {0}, Granted time: {1}".format(currTime, grantedtime))
        end_name = h.helicsEndpointGetName(swStatusEp)
        for swt in switchings:
            t = swt[0]
            val = swt[1]
            if int(currTime) == t:
                if val == 1:
                    log.info("Switching " + end_name + " to CLOSED at second " + str(t))
                    h.helicsEndpointSendBytesTo(swStatusEp, "CLOSED".encode(), "")
                elif val == 0:
                    log.info("Switching " + end_name + " to OPEN at second " + str(t))
                    h.helicsEndpointSendBytesTo(swStatusEp, "OPEN".encode(), "")
                else:
                    log.info("!!!!!!! Signals should only be 0 or 1 !!!!!!!")
    log.info("Destroying federate")
    destroy_federate(fed)


if __name__ == "__main__":
    main()
    log.info("Done!")
