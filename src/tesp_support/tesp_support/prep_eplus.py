# Copyright (C) 2020-2022 Battelle Memorial Institute
# file: prep_eplus.py

import json
import os
import shutil
import stat
import math
import copy
import subprocess
from datetime import datetime

from .make_ems import merge_idf
from .helpers import HelicsMsg


def configure_eplus(caseConfig, template_dir):
    StartDate = caseConfig['StartDate']
    EndDate = caseConfig['EndDate']
    time_fmt = '%Y-%m-%d %H:%M:%S'
    dt1 = datetime.strptime(StartDate, time_fmt)
    dt2 = datetime.strptime(EndDate, time_fmt)
    seconds = int((dt2 - dt1).total_seconds())

    fp = open(template_dir + 'eplusH.json').read()
    eplusTemplate = json.loads(fp)

    fp = open(template_dir + 'eplus_agentH.json').read()
    agentTemplate = json.loads(fp)

    caseDir = caseConfig['CaseDir']
    caseName = caseConfig['CaseName']

    fedMeters = {}
    fedLoads = {}
    fedLoadNames = {}

    for bldg in caseConfig['Buildings']:
        if len(bldg['IDF']) > 0:
            fedRoot = '{:d}_{:s}'.format(bldg['ID'], bldg['Name'])
            fedMeters[fedRoot] = bldg['Meter']
            fedLoads[fedRoot] = bldg['Load']
            fedLoadNames[fedRoot] = bldg['Name']
            print('building configuration and merging IDF for', fedRoot)
            agName = 'agent' + fedRoot
            epName = 'eplus' + fedRoot

            eDict = copy.deepcopy(eplusTemplate)
            eDict['name'] = epName
            for sub in eDict['subscriptions']:
                sub['key'] = sub['key'].replace('eplus_agent', agName)
            oname = '{:s}/ep_{:s}_{:s}.json'.format(caseDir, caseName, fedRoot)
            op = open(oname, 'w')
            json.dump(eDict, op, ensure_ascii=False, indent=2)
            op.close()

            aDict = copy.deepcopy(agentTemplate)
            aDict['name'] = agName
            for sub in aDict['subscriptions']:
                sub['key'] = sub['key'].replace('energyPlus', epName)
            for otherBldg in caseConfig['Buildings']:
                if bldg['ID'] != otherBldg['ID']:
                    key = 'agent{:d}_{:s}/bid_curve'.format(otherBldg['ID'], otherBldg['Name'])
                    topic = 'bid_curve_{:d}'.format(otherBldg['ID'])
                    curveSub = {'key': key, 'type': 'vector', 'required': True, 'info': topic}
                    aDict['subscriptions'].append(curveSub)
            oname = '{:s}/ag_{:s}_{:s}.json'.format(caseDir, caseName, fedRoot)
            op = open(oname, 'w')
            json.dump(aDict, op, ensure_ascii=False, indent=2)
            op.close()

            oname = '{:s}/agj_{:s}_{:s}.json'.format(caseDir, caseName, fedRoot)
            op = open(oname, 'w')
            aDict = {'StartTime': caseConfig['StartDate'],
                     'LoadScale': bldg['EpScale'],
                     'BuildingID': fedRoot,
                     'MetricsFileName': 'eplus_{:s}_metrics.json'.format(fedRoot),
                     'HelicsConfigFile': 'ag_{:s}_{:s}.json'.format(caseName, fedRoot),
                     'StopSeconds': seconds,
                     'MetricsPeriod': caseConfig['MetricsPeriod'],
                     'BasePrice': caseConfig['BasePrice'],
                     'RampSlope': bldg['RampSlope'],
                     'MaxDeltaHeat': bldg['MaxDeltaHeat'],
                     'MaxDeltaCool': bldg['MaxDeltaCool'],
                     'UsePriceRamp': caseConfig['UsePriceRamp'],
                     'UseConsensus': caseConfig['UseConsensus'],
                     'dT': bldg['dT'],
                     'dP': bldg['dP']}
            json.dump(aDict, op, ensure_ascii=False, indent=2)
            op.close()

            oname = '{:s}/{:s}.idf'.format(caseDir, fedRoot)
            merge_idf(bldg['IDF'], bldg['EMS'], caseConfig['StartDate'], caseConfig['EndDate'],
                          oname, caseConfig['EpStepsPerHour'])
    return fedMeters, fedLoads, fedLoadNames


billingMeterLines = """  bill_mode UNIFORM;
  price {base_price};
  monthly_fee {monthly_fee};
  bill_day 1;
  object metrics_collector {{
    interval ${{METRICS_INTERVAL}};
  }};"""

gldLines = """#set relax_naming_rules=1
#set profiler=1
#set minimum_timestep={gld_step}
clock {{
  timezone PST+8PDT;
  starttime '{sdate}';
  stoptime '{edate}';
}};
module powerflow {{
  solver_method NR;
  line_capacitance TRUE;
}};
module generators;
module tape;
module climate;
module connection;

#define METRICS_INTERVAL={metrics_interval}
#define METRICS_FILE={root}_metrics.json
object metrics_collector_writer {{
  interval ${{METRICS_INTERVAL}};
  filename ${{METRICS_FILE}};
}};

object climate {{
  name localWeather;
  tmyfile "gldWeather.tmy3";
  interpolate QUADRATIC;
}};

#define VSOURCE={vsource:.2f}
#include "{root}_net.glm";
//#include "solar_pv.glm";
#ifdef USE_HELICS
object helics_msg {{
  configure gld_{root}.json;
}}
#endif
object recorder {{
  parent sourcebus;
  property distribution_power_A,distribution_power_B,distribution_power_C,distribution_load,positive_sequence_voltage;
  interval 60;
  file substation_load.csv;
}}
object recorder {{
  parent localWeather;
  property temperature,pressure,humidity,wind_speed,solar_direct,solar_diffuse;
  interval 60;
  file weather.csv;
}}"""

substationTemplate = """//////////////////////////////////////////
object transformer_configuration {{
  name substation_xfmr_config;
  connect_type WYE_WYE;
  install_type PADMOUNT;
  primary_voltage {primary_voltage};
  secondary_voltage {secondary_voltage};
  power_rating {transformer_kva};
  resistance 0.01;
  reactance 0.08;
  shunt_resistance 250.00;
  shunt_reactance 100.00;
}}
object transformer {{
  name substation_transformer;
  from sourcebus;
  to {swing_node};
  phases ABCN;
  configuration substation_xfmr_config;
}}
object substation {{
  name sourcebus;
  bustype SWING;
  nominal_voltage {nominal_voltage};
  positive_sequence_voltage ${{VSOURCE}};
  base_power {substation_watts};
  power_convergence_value 100.0;
  phases ABCN;
  object metrics_collector {{
    interval ${{METRICS_INTERVAL}};
  }};
}}
//////////////////////////////////////////////////////"""


def writeGlmClass(theseLines, thisClass, op):
    print('object', thisClass, '{', file=op)
    for i in range(1, len(theseLines)):
        print(theseLines[i], file=op)


# replace building node objects with a billing meter that collects metrics
# also make the substation collect metrics and configure itself to HELICS
def prepare_glm_file(caseConfig):
    iname = caseConfig['BaseGLMFile']
    oname = '{:s}/{:s}_net.glm'.format(caseConfig['CaseDir'], caseConfig['CaseName'])
    meters = []
    scale = caseConfig['LoadScale']
    xfmrLoadScales = {}
    newLoadNames = {}
    xfscale = 1.0
    bPower = False
    bCurrent = False  # TODO: not supported yet
    bImpedance = False
    if caseConfig['LoadType'] == 'ConstantPower':
        bPower = True
    elif caseConfig['LoadType'] == 'ConstantImpedance':
        bImpedance = True
    elif caseConfig['LoadType'] == 'ConstantCurrent':
        bCurrent = True

    for bldg in caseConfig['Buildings']:
        meters.append(bldg['Meter'])
        xfmrLoadScales[bldg['Load']] = bldg['XfScale']
        newLoadNames[bldg['Load']] = bldg['Name']
    print('filtering', len(meters), 'buildings', iname, 'to', oname, 'load scale =', scale)

    thisClass = ''
    thisName = ''
    theseLines = []
    nomkW = 0.0
    nomV = caseConfig['PrimaryVoltageLN']
    bStartWriting = False

    ip = open(iname, 'r')
    op = open(oname, 'w')
    for line in ip:
        if ('object' in line) and ('configuration' in line):
            bStartWriting = True
        if not bStartWriting:
            continue
        ln = line.rstrip()
        lst = ln.strip().split()
        if len(lst) > 0:
            if lst[0] == '}':
                theseLines.append(ln)
                writeGlmClass(theseLines, thisClass, op)
                thisClass = ''
                theseLines = []
                xfscale = 1.0
            else:
                if 'constant_power' in ln:  # scale the load values
                    scaledLoad = xfscale * scale * complex(lst[1].strip(';'))
                    nomkW += 0.001 * scaledLoad.real
                    if scaledLoad.imag < 0.0:
                        print('Reactive injection at', thisName)
                    if bPower:
                        theseLines.append('  {:s} {:.2f}+{:.2f}j;'.format(lst[0], scaledLoad.real, scaledLoad.imag))
                    elif bImpedance:
                        zLoad = nomV * nomV / scaledLoad
                        theseLines.append('  {:s} {:.2f}+{:.2f}j;'.format(lst[0].replace('power', 'impedance'),
                                                                          zLoad.real, -zLoad.imag))  # conjugate!
                    elif bCurrent:
                        iLoad = scaledLoad / nomV
                        theseLines.append('  {:s} {:.2f}{:.2f}j;'.format(lst[0].replace('power', 'current'),
                                                                         iLoad.real, -iLoad.imag))  # conjugate
                elif 'SWING' not in ln:  # the swing node will be in a source substation instead
                    if thisClass == 'load' and lst[0] == 'name':  # check for a load name to replace
                        thisName = lst[1].lstrip('"').rstrip('";')
                        if thisName in newLoadNames:
                            xfscale = xfmrLoadScales[thisName]
                            print('$$$ rename {:s} to {:s}'.format(thisName, newLoadNames[thisName]))
                            ln = '  name {:s};'.format(newLoadNames[thisName])
                    if (thisClass == 'node') and lst[0] == 'name':  # find the swing node; write a substation for it
                        thisName = lst[1].lstrip('"').rstrip('";')
                        if thisName == caseConfig['SwingNode']:
                            print(substationTemplate.format(primary_voltage=caseConfig['TransformerKVHi'] * 1000.0,
                                                            secondary_voltage=caseConfig['TransformerKVLo'] * 1000.0,
                                                            transformer_kva=caseConfig['TransformerMVA'] * 1000.0,
                                                            nominal_voltage=caseConfig['SourceNominalVLN'],
                                                            substation_watts=caseConfig['TransformerMVA'] * 1000000.0,
                                                            swing_node=caseConfig['SwingNode']), file=op)

                    theseLines.append(ln)
        if len(lst) > 1:
            if lst[0] == 'nominal_voltage':
                nomV = float(lst[1].strip(';'))
            if lst[0] == 'object':
                thisClass = lst[1]
            if lst[0] == 'name':
                thisName = lst[1].lstrip('"').rstrip('";')
                if thisName in meters:
                    meters.append(lst[1])
                    thisClass = 'meter'
                    theseLines.append(billingMeterLines.format(base_price=caseConfig['BasePrice'],
                                                               monthly_fee=caseConfig['MonthlyFee']))

    if len(theseLines) > 0:
        writeGlmClass(theseLines, thisClass, op)

    ip.close()
    op.close()

    gname = '{:s}/{:s}.glm'.format(caseConfig['CaseDir'], caseConfig['CaseName'])
    gp = open(gname, 'w')
    print(gldLines.format(root=caseConfig['CaseName'],
                          sdate=caseConfig['StartDate'],
                          edate=caseConfig['EndDate'],
                          metrics_interval=caseConfig['MetricsPeriod'],
                          gld_step=caseConfig['GldStep'],
                          vsource=caseConfig['SourceNominalVLN'] * caseConfig['SourceNominalVpu']), file=gp)
    gp.close()
    print('{:.3f} kW total load'.format(nomkW))


# dictionary of buildings with GridLAB-D meters
def prepare_bldg_dict(caseConfig):
    oname = '{:s}/BuildingDefinitions.json'.format(caseConfig['CaseDir'])
    print('dictionary for buildings to', oname)

    diction = {}
    for row in caseConfig['Buildings']:
        diction[row['ID']] = {'Name': row['Name'],
                           'Meter': row['Meter'],
                           'Vnom': row['Vnom'],
                           'XfKVA': row['XfKVA'],
                           'EpScale': row['EpScale'],
                           'Pbase': row['Pbase']}

    op = open(oname, 'w')
    json.dump(diction, op, ensure_ascii=False, indent=2)
    op.close()


# dictionary of building meters and inverters
def prepare_glm_dict(caseConfig):
    oname = '{:s}/{:s}_glm_dict.json'.format(caseConfig['CaseDir'], caseConfig['CaseName'])
    print('dictionary for meters to', oname)

    feeder_id = caseConfig['CaseName']
    inverters = {}
    meters = {}
    feeders = {}
    #  meters['pv_mtr'] = {'feeder_id':feeder_id,'phases':'ABC','vll':480.0,'vln':277.13,'children':['pv_inv']}
    #  inverters['pv_inv'] = {'feeder_id':feeder_id, 'billingmeter_id':'pv_mtr',
    #                         'rated_W':125000.0,'resource':'solar','inv_eta':1.0}
    for row in caseConfig['Buildings']:
        mtr_id = row['Meter']
        mtr_load = row['Name']
        vll = row['Vnom']
        vln = float('{:.3f}'.format(vll / math.sqrt(3.0)))
        meters[mtr_id] = {'feeder_id': feeder_id, 'phases': 'ABC', 'vll': vll, 'vln': vln, 'children': [mtr_load]}

    feeders[feeder_id] = {'house_count': 0, 'inverter_count': 0, 'base_feeder': caseConfig['BaseFeederName']}
    diction = {'bulkpower_bus': caseConfig['BulkBusName'],
            'FedName': 'gld_1',
            'transformer_MVA': caseConfig['TransformerMVA'],
            'feeders': feeders,
            'billingmeters': meters,
            'houses': {},
            'inverters': inverters,
            'capacitors': {},
            'regulators': {}}

    op = open(oname, 'w')
    json.dump(diction, op, ensure_ascii=False, indent=2)
    op.close()


def prepare_glm_helics(caseConfig, fedMeters, fedLoadNames):

    gld = HelicsMsg('gld_1', int(caseConfig['GldStep']))
    gld.pubs(False, 'distribution_load', 'complex', 'sourcebus', 'distribution_load')
    for bldg, meter in fedMeters.items():
        load = fedLoadNames[bldg]
        agFed = 'agent' + bldg
        gld.subs(agFed + '/power_A', 'complex', load, 'constant_power_A')
        gld.subs(agFed + '/power_B', 'complex', load, 'constant_power_B')
        gld.subs(agFed + '/power_C', 'complex', load, 'constant_power_C')
        gld.subs(agFed + '/bill_mode', 'string', meter, 'bill_mode')
        gld.subs(agFed + '/price', 'double', meter, 'price')
        gld.subs(agFed + '/monthly_fee', 'double', meter, 'monthly_fee')
        for prop in ['measured_voltage_A']:
            gld.pubs(False, meter + '/' + prop, 'complex', meter, prop)
    oname = '{:s}/gld_{:s}.json'.format(caseConfig['CaseDir'], caseConfig['CaseName'])
    print('HELICS pub/sub for GridLAB-D to', oname)
    gld.write_file(oname)


brkTemplate = "(exec helics_broker -f {nFed} --name=mainbroker &> broker.log &)"
plyTemplate = "(exec helics_player --input=prices.txt --local --time_units=ns --stop {nSec}s &> player.log &)"
recTemplate = "(exec helics_recorder --input=helicsRecorder.json --timedelta 1s --period {period}s --stop {nSec}s &> tracer.log &)"
gldTemplate = "(exec gridlabd -D USE_HELICS {root}.glm &> gridlabd.log &)"
epTemplate = "(export HELICS_CONFIG_FILE={epcfg} && exec energyplus -w epWeather.epw -d {outdir} {idfname} &> {eplog} &)"
agjTemplate = "(exec eplus_agent_helics {agjcfg} &> {aglog} &)"
shedTemplate = "(exec python3 commshed.py {tmax} {period} {thresh} {kw_cap} &> commshed.log &)"


def prepare_run_script(caseConfig, fedMeters):
    StartDate = caseConfig['StartDate']
    EndDate = caseConfig['EndDate']
    time_fmt = '%Y-%m-%d %H:%M:%S'
    dt1 = datetime.strptime(StartDate, time_fmt)
    dt2 = datetime.strptime(EndDate, time_fmt)
    seconds = int((dt2 - dt1).total_seconds())
    days = seconds / 86400
    WeatherYear = dt1.year
    nFeds = 2 * len(fedMeters) + 4  # 2 for each E+ building, plus GridLAB-D, commshed.py, recorder and player
    period = caseConfig['MetricsPeriod']
    caseName = caseConfig['CaseName']
    print('run', nFeds, 'federates for', days, 'days or', seconds, 'seconds in weather year', WeatherYear)

    fname = '{:s}/run.sh'.format(caseConfig['CaseDir'])
    fp = open(fname, 'w')
    print(brkTemplate.format(nFed=nFeds), file=fp)
    print(recTemplate.format(nSec=seconds, period=period), file=fp)
    print(plyTemplate.format(nSec=seconds), file=fp)
    print(gldTemplate.format(root=caseName), file=fp)
    print(shedTemplate.format(tmax=seconds,
                              period=int(3600 / caseConfig['EpStepsPerHour']),
                              thresh=caseConfig['ConsensusThreshKW'],
                              kw_cap=caseConfig['ConsensusCapKW']), file=fp)
    for bldg in fedMeters:
        idfname = bldg + '.idf'
        outdir = 'out' + bldg
        epcfg = 'ep_' + caseName + '_' + bldg + '.json'
        eplog = 'ep_' + bldg + '.log'
        agcfg = 'ag_' + caseName + '_' + bldg + '.json'
        agjcfg = 'agj_' + caseName + '_' + bldg + '.json'
        aglog = 'ag_' + bldg + '.log'
        print(epTemplate.format(epcfg=epcfg, outdir=outdir, idfname=idfname, eplog=eplog), file=fp)
        print(agjTemplate.format(agjcfg=agjcfg, aglog=aglog), file=fp)
    fp.close()
    st = os.stat(fname)
    os.chmod(fname, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def make_gld_eplus_case(fname, bGlmReady=False):
    fp = open(fname, 'r').read()
    caseConfig = json.loads(fp)
    caseDir = caseConfig['CaseDir']
    if os.path.exists(caseDir):
        shutil.rmtree(caseDir)
    os.makedirs(caseDir)
    template_dir = caseConfig['TemplateDir']
    support_dir = caseConfig['SupportDir']
    print('read', len(caseConfig['Buildings']), 'buildings from', fname, 'writing to', caseDir)
    if bGlmReady:
        shutil.copy(caseConfig['BaseGLMFile'], '{:s}/{:s}.glm'.format(caseDir, caseConfig['CaseName']))
    else:
        prepare_glm_file(caseConfig)
    prepare_glm_dict(caseConfig)
    prepare_bldg_dict(caseConfig)
    fedMeters, fedLoads, fedLoadNames = configure_eplus(caseConfig, template_dir)
    if bGlmReady:
        fedLoadNames = fedLoads
    prepare_glm_helics(caseConfig, fedMeters, fedLoadNames)
    prepare_run_script(caseConfig, fedMeters)

    fn = '{:s}/clean.sh'.format(caseDir)
    fp = open(fn, 'w')
    print("rm - f *.log", file=fp)
    print("rm - f *.csv", file=fp)
    print("rm - f *.out", file=fp)
    print("rm - f *.xml", file=fp)
    print("rm - f *.audit", file=fp)
    print("rm - f", file=fp)
    print("broker_trace.txt", file=fp)
    print("rm - f * metrics.json", file=fp)
    print("rm - f * dict.json", file=fp)
    print("rm - f", file=fp)
    print("out.txt", file=fp)

    for bldg in caseConfig['Buildings']:
        print('rm -rf out{:d}_{:s}'.format(bldg['ID'], bldg['Name']), file=fp)
    fp.close()
    st = os.stat(fn)
    os.chmod(fn, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    shutil.copy(template_dir + 'commshed.py', caseDir)
    shutil.copy(template_dir + 'gplots.py', caseDir)
    shutil.copy(template_dir + 'eplots.py', caseDir)
    shutil.copy(template_dir + 'prices.txt', caseDir)
    shutil.copy(template_dir + 'commshedConfig.json', caseDir)
    shutil.copy(template_dir + 'helicsRecorder.json', caseDir)
    shutil.copy(caseConfig['TMYFile'], '{:s}/{:s}'.format(caseDir, 'gldWeather.tmy3'))
    # process TMY3 ==> TMY2 ==> EPW
    cmdline = 'TMY3toTMY2_ansi {:s}/gldWeather.tmy3 > {:s}/epWeather.tmy2'.format(caseDir, caseDir)
    print(cmdline)
    pw1 = subprocess.Popen(cmdline, shell=True)
    pw1.wait()
    cmdline = """python3 -c "import tesp_support.TMYtoEPW as tesp;tesp.convert_tmy2_to_epw('""" + caseDir + '/epWeather' + """')" """
    print(cmdline)
    pw2 = subprocess.Popen(cmdline, shell=True)
    pw2.wait()
    os.remove('{:s}/epWeather.tmy2'.format(caseDir))
