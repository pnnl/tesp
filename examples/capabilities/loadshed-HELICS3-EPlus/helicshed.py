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
  h.helicsFederateDestroy(fed)
  h.helicsFederateFree(fed)
  h.helicsCloseLibrary()

def show_helics_query (fed, qstr):
  hq = h.helicsCreateQuery ('mainbroker', qstr)
  qret = h.helicsQueryExecute (hq, fed)
  # logger.info (qstr + '=' + qret)
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
  logger.info(h.helicsEndpointGetDefaultDestination(swStatusEp))
    
  for qstr in ['federates', 'endpoints', 'publications', 'filters', 'dependencies', 'dependents', 'isinit']:
      show_helics_query (fed, qstr)

  switchings = [[120,0],[1800,1],[5400,0],[16200,1],[19800,0]]
  # switchings = [[1800,0],[5400,1],[16200,0],[19800,1]]
  hours = 6
  seconds = int(60 * 60 * hours)
  grantedTime = 0
  currTime = h.helicsFederateGetCurrentTime(fed)
  logger.info('Current time: {0}, Granted time: {1}'.format(currTime, grantedTime))
  logger.info('====================================================================')

  while grantedTime < seconds:
    currTime = h.helicsFederateGetCurrentTime(fed)
    logger.info(f'Granted time: {grantedTime}, Current time: {currTime}')
    end_name = h.helicsEndpointGetName(swStatusEp)
    for swt in switchings:
      t = swt[0]
      val = swt[1]
      if int(currTime) == t:
        if val == 1:
          logger.info(f'Switching {end_name} to CLOSED at second {int(currTime)} ({t})')
          h.helicsEndpointSendBytes(swStatusEp, 'CLOSED'.encode())
        elif val == 0:
          logger.info(f'Switching {end_name} to OPEN at second {int(currTime)} ({t})')
          h.helicsEndpointSendBytes(swStatusEp, 'OPEN'.encode())
        else:
          logger.info('!!!!!!! Signals should only be 0 or 1 !!!!!!!')
    grantedTime = h.helicsFederateRequestNextStep(fed)
  logger.info('Destroying federate')
  destroy_federate(fed)

if __name__ == '__main__':
    main()
    logger.info('Done!')
