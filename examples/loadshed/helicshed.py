import time
import helics as h
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
#logger.setLevel(logging.DEBUG)

helicsversion = h.helicsGetVersion()
logger.info('Loadshed Federate: HELICS version = {}'.format(helicsversion))

def create_federate(deltat=1.0, fedinitstring='--federates=1'):
    fed = h.helicsCreateCombinationFederateFromConfig('loadshedConfig.json')
    return fed

def destroy_federate(fed, broker=None):
    h.helicsFederateDestroy(fed)
#   status = h.helicsFederateFinalize(fed)
#   state = h.helicsFederateGetState(fed)
#   assert state == 3
#   while (h.helicsBrokerIsConnected(broker)):
#       time.sleep(1)
#   h.helicsFederateFree(fed)
#   h.helicsCloseLibrary()

def show_helics_query (fed, qstr):
  hq = h.helicsCreateQuery ('mainbroker', qstr)
  qret = h.helicsQueryExecute (hq, fed)
  logger.info (qstr + '=' + qret)
  h.helicsQueryFree (hq)

def main():
    fed = create_federate()
    fedName = h.helicsFederateGetName(fed)
    logger.info('The name of the federate is: {0}.'.format(fedName))
    endpoint_count = h.helicsFederateGetEndpointCount(fed)
    logger.info('I have counted a number of {0} endpoints.'.format(endpoint_count))
    logger.info( '########################   Entering Execution Mode  ##########################################')
    h.helicsFederateEnterExecutingMode(fed)

    swStatusEpName = fedName + '/sw_status'
    swStatusEp = h.helicsFederateGetEndpoint(fed, swStatusEpName)
    h.helicsFederateEnterExecutingMode(fed)
    
    for qstr in ['federates', 'endpoints', 'publications', 'filters', 'dependencies', 'dependents', 'isinit']:
      show_helics_query (fed, qstr)

    switchings = [[0,1],[1800,0],[5400,1],[16200,0],[19800,1]]
    hours = 6
    seconds = int(60 * 60 * hours)
    grantedtime = 0
    currTime = h.helicsFederateGetCurrentTime(fed)
    grantedtime = h.helicsFederateRequestNextStep(fed)

    while currTime < seconds:
      currTime = h.helicsFederateGetCurrentTime(fed)
      grantedtime = h.helicsFederateRequestNextStep(fed)
      if (currTime * 100) % 100 == 0:
        logger.info('Current time: {0}, Granted time: {1}'.format(currTime, grantedtime))
      end_name = h.helicsEndpointGetName(swStatusEp)
      for swt in switchings:
        t = swt[0]
        val = swt[1]
        if int(currTime) == t:
          if val == 1:
            logger.info('Switching ' + end_name + ' to CLOSED at second ' + str(t))
            h.helicsEndpointSendMessageRaw(swStatusEp, '', 'CLOSED'.encode())
          elif val == 0:
            logger.info('Switching ' + end_name + ' to OPEN at second ' + str(t))
            h.helicsEndpointSendMessageRaw(swStatusEp, '', 'OPEN'.encode())
          else:
            logger.info('!!!!!!! Signals should only be 0 or 1 !!!!!!!')
    """
    for swt in switchings:
        logger.info('1. Current time: {0}'.format(h.helicsFederateGetCurrentTime(fed)))
        logger.info('1. Next step request: {0}'.format(h.helicsFederateRequestNextStep(fed)))
        t = swt[0]
        val = str(swt[1])
        while grantedtime < t:
            logger.info('Loadshed current time: ' + str(grantedtime))
            logger.info('Loadshed requesting time: ' + str(t))
            grantedtime = h.helicsFederateRequestTime(fed, t)
            logger.info('Loadshed granted time: ' + str(grantedtime))
            logger.info('2. Current time: {0}'.format(h.helicsFederateGetCurrentTime(fed)))
            logger.info('2. Next step request: {0}'.format(h.helicsFederateRequestNextStep(fed)))
        if grantedtime == t:
            logger.info(' ** ' + swStatusEpName + '=' + str(val) + ' at ' + str(t))
            h.helicsEndpointSendMessageRaw(swStatusEp, '', val)
      """
    logger.info('Destroying federate')
    destroy_federate(fed)

if __name__ == '__main__':
    main()
    logger.info('Done!')
