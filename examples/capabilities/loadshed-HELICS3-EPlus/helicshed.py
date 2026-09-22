import logging

import helics as h

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())

helicsversion = h.helicsGetVersion()
log.info(f'Loadshed Federate: HELICS version = {helicsversion}')


def create_federate(deltat=1.0, fedinitstring='--federates=1'):
    fed = h.helicsCreateCombinationFederateFromConfig('loadshedConfig.json')
    return fed


def destroy_federate(fed, broker=None):
    h.helicsFederateDestroy(fed)
    h.helicsFederateFree(fed)
    h.helicsCloseLibrary()


def show_helics_query(fed, qstr):
    hq = h.helicsCreateQuery('mainbroker', qstr)
    qret = h.helicsQueryExecute(hq, fed)
    # log.info (qstr + '=' + qret)
    h.helicsQueryFree(hq)


def main():
    fed = create_federate()
    fedName = h.helicsFederateGetName(fed)
    log.info(f'The name of the federate is: {fedName}.')
    endpoint_count = h.helicsFederateGetEndpointCount(fed)
    log.info(f'I have counted a number of {endpoint_count} endpoints.')
    log.info('########################   Entering Execution Mode  ##########################################')
    h.helicsFederateEnterExecutingMode(fed)

    swStatusEpName = fedName + '/sw_status'
    swStatusEp = h.helicsFederateGetEndpoint(fed, swStatusEpName)
    h.helicsFederateEnterExecutingMode(fed)
    log.info(h.helicsEndpointGetDefaultDestination(swStatusEp))

    for qstr in ['federates', 'endpoints', 'publications', 'filters', 'dependencies', 'dependents', 'isinit']:
        show_helics_query(fed, qstr)

    switchings = [[120, 0], [1800, 1], [5400, 0], [16200, 1], [19800, 0]]
    # switchings = [[1800,0],[5400,1],[16200,0],[19800,1]]
    hours = 6
    seconds = int(60 * 60 * hours)
    grantedTime = 0
    currTime = h.helicsFederateGetCurrentTime(fed)
    log.info(f'Current time: {currTime}, Granted time: {grantedTime}')
    log.info('====================================================================')

    while grantedTime < seconds:
        currTime = h.helicsFederateGetCurrentTime(fed)
        log.debug(f'Granted time: {grantedTime}, Current time: {currTime}')
        end_name = h.helicsEndpointGetName(swStatusEp)
        for swt in switchings:
            t = swt[0]
            val = swt[1]
            if int(currTime) == t:
                if val == 1:
                    log.info(f'Switching {end_name} to CLOSED at second {int(currTime)} ({t})')
                    h.helicsEndpointSendBytes(swStatusEp, b'CLOSED')
                elif val == 0:
                    log.info(f'Switching {end_name} to OPEN at second {int(currTime)} ({t})')
                    h.helicsEndpointSendBytes(swStatusEp, b'OPEN')
                else:
                    log.info('!!!!!!! Signals should only be 0 or 1 !!!!!!!')
        grantedTime = h.helicsFederateRequestNextStep(fed)
    log.info('Destroying federate')
    destroy_federate(fed)


if __name__ == '__main__':
    main()
    log.info('Done!')
