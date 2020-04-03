import time
import helics as h
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

helicsversion = h.helicsGetVersion()
logger.info('Loadshed Federate: HELICS version = {}'.format(helicsversion))

def create_federate(deltat=1.0, fedinitstring='--federates=1'):
    fed = h.helicsCreateCombinationFederateFromConfig('loadshedConfig.json')
    return fed

def destroy_federate(fed, broker=None):
    status = h.helicsFederateFinalize(fed)
    state = h.helicsFederateGetState(fed)
    assert state == 3
    while (h.helicsBrokerIsConnected(broker)):
        time.sleep(1)
    h.helicsFederateFree(fed)
    h.helicsCloseLibrary()

def show_helics_query (fed, qstr):
  hq = h.helicsCreateQuery ('mainbroker', qstr)
  qret = h.helicsQueryExecute (hq, fed)
  logger.info (qstr + '=' + qret)
  h.helicsQueryFree (hq)

def main():
    fed = create_federate()
    fedName = h.helicsFederateGetName(fed)
    swStatusEpName = fedName + '/sw_status'
    swStatusEp = h.helicsFederateGetEndpoint(fed, swStatusEpName)
    h.helicsFederateEnterExecutingMode(fed)
    
    for qstr in ['federates', 'endpoints', 'publications', 'filters', 'dependencies', 'dependents', 'isinit']:
      show_helics_query (fed, qstr)

    switchings = [[0,1],[1800,0],[5400,1],[16200,0],[19800,1]]
    hours = 6
    seconds = int(60 * 60 * hours)
    grantedtime = 0
    for swt in switchings:
        t = swt[0]
        val = str(swt[1])
        while grantedtime < t:
            logger.info('Loadshed current time: ' + str(grantedtime))
            logger.info('Loadshed requesting time: ' + str(t))
            grantedtime = h.helicsFederateRequestTime(fed, t)
            logger.info('Loadshed granted time: ' + str(grantedtime))
        if grantedtime == t:
            logger.info(' ** ' + swStatusEpName + '=' + str(val) + ' at ' + str(t))
            h.helicsEndpointSendMessageRaw(swStatusEp, '', val)
    logger.info('Destroying federate')
    destroy_federate(fed)

if __name__ == '__main__':
    main()
    logger.info('Done!')
