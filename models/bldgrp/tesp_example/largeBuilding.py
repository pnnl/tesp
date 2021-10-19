from __future__ import print_function

from datetime import datetime, timedelta

import os
import json
from LargeOffice import LargeOffice
import sys
import math

try:
    import fncs
except:
    print('fncs problem')
    pass
from metrics_collector import MetricsCollector, MetricsStore


# def startLOSimulation(startDay, duration, timeStep=60, metricsRecordInterval=86400):
def startLOSimulation(configFile):
    # startDay        = 1  # day of year --> 1=Jan; 32=Feb; 60=Mar; 91=Apr; 121=May; 152=Jun; 182=Jul; 213=Aug; 244=Sep; 274=Oct; 305=Nov; 335=Dec;
    # duration        = 2   # number of days
    if os.path.isfile(configFile):
        with open(configFile, 'r') as stream:
            try:
                conf = json.load(stream)
                name = str(conf['name'])
                duration = conf['duration']
                StartTime = conf['StartTime']
                timeFormat = '%Y-%m-%d %H:%M:%S'
                dtStart = datetime.strptime(StartTime, timeFormat)
                timeDeltaStr = conf['time_delta']
                metricsRecordInterval = conf['metricsRecordInterval']
                metricsWriteOutInterval = conf['metricsWriteOutInterval']
            except ValueError as ex:
                print(ex)
    else:
        print('could not open CONFIG FILE for largeBuilding.')
        sys.exit()

    startDay = dtStart.timetuple().tm_yday
    duration = int(filter(lambda x: x.isdigit(), duration))
    timeStep = convertTimeToSeconds(timeDeltaStr)
    metricsAddInterval = convertTimeToSeconds(metricsRecordInterval)
    metricsWriteOutInterval = convertTimeToSeconds(metricsWriteOutInterval)
    startTime = (int(startDay) - 1) * 86400
    print("start time: ", startTime)
    stopTime = (int(startDay) - 1 + int(duration)) * 86400
    print("stop time: ", stopTime)
    timeElapsed = 0
    print("current time: ", timeElapsed)
    tnext_write_metrics = metricsWriteOutInterval
    print("metrics record interval: ", tnext_write_metrics)
    tnext_add_metrics = metricsAddInterval

    # ------temporary read in from CSVs, eventually read in from FNCS---------------------
    # TO = np.genfromtxt('./core/_temp/TO.csv', delimiter=',',max_rows=(startDay - 1 + duration)*1440+1)[(startDay-1)*1440+1:,1]

    # weather_current = {"TO":0,"windSpeed":0}
    # initialize a large office model

    TO_current = None
    windSpeed = None
    voltageAB = 0
    voltageBC = 0
    voltageCA = 0
    # weather_current = {}
    fncs.initialize()
    print('FNCS initialized')

    while timeElapsed < stopTime - startTime:
        events = fncs.get_events()
        for topic in events:
            value = fncs.get_value(topic)
            if topic == 'temperature':
                TO_current = float(value)
            if topic == 'wind_speed':
                windSpeed = float(value)
            if topic == 'voltageAB':
                p, q = parse_complex(value)
                voltageAB = math.sqrt(p ** 2 + q ** 2)
            if topic == 'voltageBC':
                p, q = parse_complex(value)
                voltageBC = math.sqrt(p ** 2 + q ** 2)
            if topic == 'voltageCA':
                p, q = parse_complex(value)
                voltageCA = math.sqrt(p ** 2 + q ** 2)
            print(topic)
            print(value)
        if TO_current is None:
            print("TO_current is None")
        if windSpeed is None:
            print("windSpeed is None")
        if TO_current is not None and windSpeed is not None:
            break
        print("current time: ", timeElapsed)
        timeElapsed = timeElapsed + timeStep
        nextFNCSTime = min(timeElapsed, stopTime)
        print('nextFNCSTime: ', nextFNCSTime)
        time_granted = fncs.time_request(nextFNCSTime)
        print('time granted: ', time_granted)
        timeElapsed = time_granted
        print("current time after time granted: ", timeElapsed)

    print("weather info found!")
    weather_current = {"TO": TO_current, "windSpeed": windSpeed}
    voltage = {"voltage_AB": voltageAB, "voltage_BC": voltageBC, "voltage_CA": voltageCA}

    # adding the metrics collector object
    metrics_collector_obj = MetricsCollector.factory(start_time=StartTime, write_hdf5=False)

    # interval for metrics recording
    metrics_interval_cnt = 1
    tnext_write_metrics += timeElapsed
    tnext_add_metrics += timeElapsed

    # define metadata for metric files
    metrics_collector = MetricsStore(
        name_units_pairs= [
            ('total_power', ['kW']),
            # ('room_temperature', [u"\u2103".encode('utf-8')] * 19)
            ('room_temperature', ['degF'] * 19)
            # ('room_temperature', [u'\N{DEGREE SIGN}'.encode('utf-8') + 'C'] * 19)
        ],
        file_string='large_office_{}_interval'.format(metricsRecordInterval),
        collector=metrics_collector_obj,
    )
    # print(u"\u2103")u"\u00B0"
    # lo_metrics_meta = {'total_power': {'units': str(['kW']), 'index': 0},
    #                    'room_temperature': {'units': str(['c'] * 19), 'index': 1}}

    # add metric data to collector
    # metrics_collector_obj.add_metric('large_office_' + str(metricsRecordInterval) + '_interval_', 'large_office_' + str(metricsRecordInterval) + '_interval_', lo_metrics_meta)

    LO1 = LargeOffice(int(startDay), int(duration), weather_current)
    # LO2 = LargeOffice(startDay, duration,initation2)

    # start simulation
    model_time = LO1.startTime + timeElapsed
    print('model_time: ', model_time)
    time_stop = LO1.stopTime

    control_inputs = {}  # use default control inputs, or define dynamic values here
    if weather_current:  # ['TO'] and weather_current['windSpeed']:
        P_total, T_room = LO1.step(model_time, weather_current, control_inputs, voltage)
        # print(P_total)
        fncs.publish('room_temps', T_room)
        fncs.publish('total_power', str(list(P_total)))
        if time_granted >= tnext_add_metrics or time_granted >= stopTime - startTime:
            metrics_collector.append_data(
                time_granted,
                name,
                P_total.tolist(),
                [convertTemperatureFromFtoC(t) for t in T_room]
            )
            tnext_add_metrics+=metricsAddInterval
        # metrics_collector_obj.add_data('large_office_' + str(metricsRecordInterval) + '_interval_', time_granted, {'total_power': [P_total.tolist()], 'room temperature': [T_room.tolist()]})
        # metrics_collector_obj.add_data('large_office_' + str(metricsRecordInterval) + '_interval_', time_granted, {'name': [P_total.tolist(), T_room.tolist()]})
        # metrics_collector_obj.add_data('large_office_' + str(metricsRecordInterval) + '_interval_', time_granted, {'name': [P_total.tolist() + T_room.tolist()]})
        print('P_total: ', P_total, ', T_room: ', T_room)
    # model_time = model_time + timeStep
    # nextFNCSTime = min(model_time, time_stop)
    # print('nextFNCSTime: ', nextFNCSTime)
    # time_granted = fncs.time_request(nextFNCSTime)
    # print('time granted: ', time_granted)
    # model_time = time_granted

    print("current time: ", timeElapsed)
    timeElapsed = timeElapsed + timeStep
    nextFNCSTime = min(timeElapsed, stopTime - startTime)
    print('nextFNCSTime: ', nextFNCSTime)
    time_granted = fncs.time_request(nextFNCSTime)
    print('time granted: ', time_granted)
    timeElapsed = time_granted
    print("current time after time granted: ", timeElapsed)
    model_time = LO1.startTime + timeElapsed
    print('model_time: ', model_time)

    while (timeElapsed < stopTime - startTime):  # fmu uses second of year as model_time
        # currentDay = int(model_time/86400)
        # currentHour = int((model_time-currentDay*86400)%86400/3600)
        # currentMin = int((model_time-(currentDay*86400+currentHour*3600))/60)
        # currentSec = int((model_time-(currentDay*86400+currentHour*3600))%60)

        events = fncs.get_events()
        for topic in events:
            value = fncs.get_value(topic)
            if topic == 'temperature':
                weather_current['TO'] = float(value)
            if topic == 'wind_speed':
                weather_current['windSpeed'] = float(value)
            if topic == 'voltageAB':
                p, q = parse_complex(value)
                voltage['voltage_AB'] = math.sqrt(p ** 2 + q ** 2)
            if topic == 'voltageBC':
                p, q = parse_complex(value)
                voltage['voltage_BC'] = math.sqrt(p ** 2 + q ** 2)
            if topic == 'voltageCA':
                p, q = parse_complex(value)
                voltage['voltage_CA'] = math.sqrt(p ** 2 + q ** 2)
            print(topic)
            print(value)
        # weather_current={'TO':TO_current,'windSpeed':windSpeed}
        control_inputs = {}  # use default control inputs, or define dynamic values here
        if weather_current:  # ['TO'] and weather_current['windSpeed']:
            P_total, T_room = LO1.step(model_time, weather_current, control_inputs, voltage)
            # print(P_total)
            fncs.publish('room_temps', T_room)
            fncs.publish('total_power', str(list(P_total)))
            if time_granted >= tnext_add_metrics or time_granted >= stopTime - startTime:
                metrics_collector.append_data(
                    time_granted,
                    name,
                    P_total.tolist(),
                    [convertTemperatureFromFtoC(t) for t in T_room]
                )
                tnext_add_metrics+=metricsAddInterval
            # metrics_collector_obj.add_data('large_office_' + str(metricsRecordInterval) + '_interval_', time_granted, {'total_power': [P_total.tolist()], 'room temperature': [T_room.tolist()]})
            # metrics_collector_obj.add_data('large_office_' + str(metricsRecordInterval) + '_interval_', time_granted, {'name': [P_total.tolist(), T_room.tolist()]})
            # metrics_collector_obj.add_data('large_office_' + str(metricsRecordInterval) + '_interval_', time_granted, {'name': [P_total.tolist() + T_room.tolist()]})
            print('P_total: ', P_total, ', T_room: ', T_room)
        print("current time: ", timeElapsed)
        timeElapsed = timeElapsed + timeStep
        nextFNCSTime = min(timeElapsed, stopTime - startTime)
        print('nextFNCSTime: ', nextFNCSTime)
        time_granted = fncs.time_request(nextFNCSTime)
        print('time granted: ', time_granted)
        timeElapsed = time_granted
        print("current time after time granted: ", timeElapsed)
        model_time = LO1.startTime + timeElapsed
        print('model_time: ', model_time)

        # ----------------------------------------------------------------------------------------------------
        # ------------------------------------ Write metrics -------------------------------------------------
        # ----------------------------------------------------------------------------------------------------
        if time_granted >= tnext_write_metrics or time_granted >= stopTime - startTime:
            print("-- writing metrics --")
            # write all known metrics to disk
            # metrics_collector_obj.write_metrics(metrics_interval_cnt)
            metrics_collector_obj.write_metrics()
            tnext_write_metrics += metricsWriteOutInterval
            # metrics_interval_cnt += 1

    LO1.terminate()
    print("=======================Simulation Done=======================")
    print('finalizing FNCS')
    fncs.finalize()


def parse_complex(arg):
    """ Helper function to parse P+jQ from a FNCS value

    Args:
      arg (str): FNCS value in rectangular format

    Returns:
      float, float: P [MW] and Q [MVAR]
    """
    tok = arg.strip('; MWVAKdrij')
    bLastDigit = False
    bParsed = False
    vals = [0.0, 0.0]
    for i in xrange(len(tok)):
        if tok[i] == '+' or tok[i] == '-':
            if bLastDigit:
                vals[0] = float(tok[: i])
                vals[1] = float(tok[i:])
                bParsed = True
                break
        bLastDigit = tok[i].isdigit()
    if not bParsed:
        vals[0] = float(tok)

    if 'd' in arg:
        vals[1] *= (math.pi / 180.0)
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    elif 'r' in arg:
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    else:
        p = vals[0]
        q = vals[1]

    if 'KVA' in arg:
        p /= 1000.0
        q /= 1000.0
    elif 'MVA' in arg:
        p *= 1.0
        q *= 1.0
    else:  # VA
        p /= 1000000.0
        q /= 1000000.0
    return p, q


def usage():
    # print(        "usage: python largeBuilding.py <startDay of year> <duration by day> <time step by seconds(optional, default to 60 seconds)> <metrics record interval by seconds(optional, default to 300 seconds)>")
    print(
        "usage: python largeBuilding.py <configFile>")


def convertTimeToSeconds(time):
    """Convert time string with unit to integer in seconds

    It only parse unit in day, hour, minute and second.
    It will not recognize week, month, year, millisecond, microsecond or nanosecond, they can be added if needed.

    :param time: str
        time with unit
    :return: int
        represent the input time in second
    """
    unit = filter(lambda x: x.isalpha(), time)
    timeNum = int(filter(lambda x: x.isdigit(), time))
    if "d" == unit or "day" == unit or "days" == unit:
        return 24 * 60 * 60 * timeNum
    elif "h" == unit or "hour" == unit or "hours" == unit:
        return 60 * 60 * timeNum
    elif "m" == unit or "min" == unit or "minute" == unit or "minutes" == unit:
        return 60 * timeNum
    elif 's' == unit or "sec" == unit or "second" == unit or "seconds" == unit:
        return timeNum
    else:
        raise Exception("unrecognized time unit '" + unit + "'.")


def convertTemperatureFromFtoC(t):
    return t * 9.0 / 5.0 + 32.0

if __name__ == '__main__':
    # argLength = len(sys.argv)
    # if argLength == 3:
    #     startDay = sys.argv[1]
    #     duration = sys.argv[2]
    #     startLOSimulation(startDay, duration)
    # elif argLength == 4:
    #     startDay = sys.argv[1]
    #     duration = sys.argv[2]
    #     timeStep = int(sys.argv[3])
    #     startLOSimulation(startDay, duration, timeStep)
    # elif argLength == 5:
    #     startDay = sys.argv[1]
    #     duration = sys.argv[2]
    #     timeStep = int(sys.argv[3])
    #     metricsRecordInterval = int(sys.argv[4])
    #     startLOSimulation(startDay, duration, timeStep, metricsRecordInterval)
    # else:
    #     usage()
    #     sys.exit()
    argLength = len(sys.argv)
    if argLength == 2:
        configFile = sys.argv[1]
        startLOSimulation(configFile)
    else:
        usage()
        sys.exit()