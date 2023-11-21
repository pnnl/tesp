# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: helicsshed0.py

import helics as h
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

helicsversion = h.helicsGetVersion()
logger.info("Loadshed0 Federate: HELICS version = {}".format(helicsversion))


def create_federate(deltat=1.0, fedinitstring="--federates=1"):
    fedinfo = h.helicsCreateFederateInfo()
    h.helicsFederateInfoSetCoreName(fedinfo, "PythonLoadshedFederate")
    h.helicsFederateInfoSetCoreTypeFromString(fedinfo, "zmq")
    h.helicsFederateInfoSetCoreInitString(fedinfo, fedinitstring)
    h.helicsFederateInfoSetTimeProperty(fedinfo, h.helics_property_time_delta, deltat)
    fed = h.helicsCreateCombinationFederate("PythonLoadshedFederate", fedinfo)
    return fed


def destroy_federate(fed, broker=None):
    h.helicsFederateDestroy(fed)


def main():
    fed = create_federate()
    pubid = h.helicsFederateRegisterGlobalPublication(fed, "loadshed/sw_status", h.helics_data_type_string, "")
    #    subid = h.helicsFederateRegisterSubscription(fed, "gridlabdSimulator1/totalLoad", "")
    endpoint_count = h.helicsFederateGetEndpointCount(fed)
    logger.info("I have counted a number of {0} endpoints.".format(endpoint_count))
    logger.info("########################   Entering Execution Mode  ##########################################")
    h.helicsFederateEnterExecutingMode(fed)

    switchings = [[0, 1], [1800, 0], [5400, 1], [16200, 0], [19800, 1]]

    grantedtime = -1
    for swt in switchings:
        t = swt[0]
        val = swt[1]
        while grantedtime < t:
            grantedtime = h.helicsFederateRequestTime(fed, t)
        logger.info('Switching to ' + str(val) + ' at ' + str(t))
        status = h.helicsPublicationPublishString(pubid, str(val))
    logger.info("Destroying federate")
    destroy_federate(fed)


if __name__ == "__main__":
    main()
    logger.info("Done!")
