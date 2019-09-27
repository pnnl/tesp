import numpy as np;
import scipy.interpolate as ip;
import pypower.api as pp;
import tesp_support.api as tesp;
import tesp_support.fncs as fncs;
import json;
import math;
from copy import deepcopy;
import psst.cli as pst;
import pandas as pd;

casename = 'ercot_8'
ames_DAM_case_file = "./../DAMReferenceModel.dat"
ames_RTM_case_file = "./../RTMReferenceModel.dat"

load_shape = [0.6704,
              0.6303,
              0.6041,
              0.5902,
              0.5912,
              0.6094,
              0.6400,
              0.6725,
              0.7207,
              0.7584,
              0.7905,
              0.8171,
              0.8428,
              0.8725,
              0.9098,
              0.9480,
              0.9831,
              1.0000,
              0.9868,
              0.9508,
              0.9306,
              0.8999,
              0.8362,
              0.7695,
              0.6704]  # wrap to the next day


# from 'ARIMA-Based Time Series Model of Stochastic Wind Power Generation'
# return dict with rows like wind['unit'] = [bus, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, p]
def make_wind_plants(ppc):
    gen = ppc['gen']
    genCost = ppc['gencost']
    plants = {}
    Pnorm = 165.6
    for i in range(gen.shape[0]):
        busnum = int(gen[i, 0])
        c2 = float(genCost[i, 4])
        if c2 < 2e-5:  # genfuel would be 'wind'
            MW = float(gen[i, 8])
            scale = MW / Pnorm
            Theta0 = 0.05 * math.sqrt(scale)
            Theta1 = -0.1 * scale
            StdDev = math.sqrt(1.172 * math.sqrt(scale))
            Psi1 = 1.0
            Ylim = math.sqrt(MW)
            alag = Theta0
            ylag = Ylim
            unRespMW = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            plants[str(i)] = [busnum, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, unRespMW]
    return plants


# this differs from tesp_support because of additions to FNCS, and Pnom==>Pmin for generators
def make_dictionary(ppc, rootname):
    """ Helper function to write the JSON metafile for post-processing

    Args:
      ppc (dict): PYPOWER case file structure
      rootname (str): to write rootname_m_dict.json
    """
    fncsBuses = {}
    generators = {}
    unitsout = []
    branchesout = []
    bus = ppc['bus']
    gen = ppc['gen']
    genCost = ppc['gencost']
    fncsBus = ppc['FNCS']
    units = ppc['UnitsOut']
    branches = ppc['BranchesOut']

    for i in range(gen.shape[0]):
        busnum = int(gen[i, 0])
        bustype = bus[busnum - 1, 1]
        if bustype == 1:
            bustypename = 'pq'
        elif bustype == 2:
            bustypename = 'pv'
        elif bustype == 3:
            bustypename = 'swing'
        else:
            bustypename = 'unknown'
        gentype = 'other'  # as opposed to simple cycle or combined cycle
        c2 = float(genCost[i, 4])
        c1 = float(genCost[i, 5])
        c0 = float(genCost[i, 6])
        if c2 < 2e-5:  # assign fuel types from the IA State default costs
            genfuel = 'wind'
        elif c2 < 0.0003:
            genfuel = 'nuclear'
        elif c1 < 25.0:
            genfuel = 'coal'
        else:
            genfuel = 'gas'
        generators[str(i + 1)] = {'bus': int(busnum), 'bustype': bustypename, 'Pmin': float(gen[i, 9]),
                                  'Pmax': float(gen[i, 8]), 'genfuel': genfuel, 'gentype': gentype,
                                  'StartupCost': float(genCost[i, 1]), 'ShutdownCost': float(genCost[i, 2]), 'c2': c2,
                                  'c1': c1, 'c0': c0}

    for i in range(fncsBus.shape[0]):
        busnum = int(fncsBus[i, 0])
        busidx = busnum - 1
        fncsBuses[str(busnum)] = {'Pnom': float(bus[busidx, 2]), 'Qnom': float(bus[busidx, 3]),
                                  'area': int(bus[busidx, 6]), 'zone': int(bus[busidx, 10]),
                                  'ampFactor': float(fncsBus[i, 2]), 'GLDsubstations': [fncsBus[i, 1]],
                                  'curveScale': float(fncsBus[i, 5]), 'curveSkew': int(fncsBus[i, 6])}

    for i in range(units.shape[0]):
        unitsout.append({'unit': int(units[i, 0]), 'tout': int(units[i, 1]), 'tin': int(units[i, 2])})

    for i in range(branches.shape[0]):
        branchesout.append({'branch': int(branches[i, 0]), 'tout': int(branches[i, 1]), 'tin': int(branches[i, 2])})

    dp = open(rootname + '_m_dict.json', 'w')
    ppdict = {'baseMVA': ppc['baseMVA'], 'fncsBuses': fncsBuses, 'generators': generators, 'UnitsOut': unitsout,
              'BranchesOut': branchesout}
    print(json.dumps(ppdict), file=dp, flush=True)
    dp.close()


def parse_mva(arg):
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
    for i in range(len(tok)):
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


def print_gld_load(ppc, gld_load, msg, ts):
    bus = ppc['bus']
    fncsBus = ppc['FNCS']
    print(msg, 'at', ts)
    print('bus, genidx, pbus, qbus, pcrv, qcrv, pgld, qgld, unresp, resp_max, c2, c1, deg')
    for row in fncsBus:
        busnum = int(row[0])
        gld_scale = float(row[2])
        pbus = bus[busnum - 1, 2]
        qbus = bus[busnum - 1, 3]
        pcrv = gld_load[busnum]['pcrv']
        qcrv = gld_load[busnum]['qcrv']
        pgld = gld_load[busnum]['p'] * gld_scale
        qgld = gld_load[busnum]['q'] * gld_scale
        resp_max = gld_load[busnum]['resp_max'] * gld_scale
        unresp = gld_load[busnum]['unresp'] * gld_scale
        c2 = gld_load[busnum]['c2'] / gld_scale
        c1 = gld_load[busnum]['c1']
        deg = gld_load[busnum]['deg']
        genidx = gld_load[busnum]['genidx']
        print(busnum, genidx,
              '{: .2f}'.format(pbus),
              '{: .2f}'.format(qbus),
              '{: .2f}'.format(pcrv),
              '{: .2f}'.format(qcrv),
              '{: .2f}'.format(pgld),
              '{: .2f}'.format(qgld),
              '{: .2f}'.format(unresp),
              '{: .2f}'.format(resp_max),
              '{: .8f}'.format(c2),
              '{: .8f}'.format(c1),
              '{: .1f}'.format(deg))


def scucDAM(data, output, solver):
    c, ZonalDataComplete, priceSenLoadData = pst.read_model(data.strip("'"))
    model = pst.build_model(c, ZonalDataComplete=ZonalDataComplete, PriceSenLoadData=priceSenLoadData)
    model.solve(solver=solver)
    instance = model._model

    uc = "./SCUCResultsUC.dat"
    with open(uc, 'w') as outfile:
        results = {}
        for g in instance.Generators.value:
            for t in instance.TimePeriods:
                results[(g, t)] = instance.UnitOn[g, t]

        for g in sorted(instance.Generators.value):
            outfile.write("%s\n" % str(g).ljust(8))
            for t in sorted(instance.TimePeriods):
                outfile.write("% 1d \n" % (int(results[(g, t)].value + 0.5)))

    uc_df = pd.DataFrame(pst.read_unit_commitment(uc.strip("'")))
    c.gen_status = uc_df.astype(int)

    model = pst.build_model(c, ZonalDataComplete=ZonalDataComplete, PriceSenLoadData=priceSenLoadData)
    model.solve(solver=solver)
    instance = model._model

    DA_LMPs = [[0 for x in range(hours_in_a_day)] for y in range(total_bus_num)]
    DA_LMPs_pub = [[0 for x in range(hours_in_a_day)] for y in range(total_bus_num)]
    for h, r in model.results.lmp.iterrows():
        bn = 1
        for _, lmp in r.iteritems():
            if lmp is None:
                lmp = 0
            DA_LMPs[bn - 1][h] = -round(lmp, 2)  # publishing $/kwh
            DA_LMPs_pub[bn - 1][h] = -round(lmp * 0.001, 2)  # publishing $/kwh
            bn = bn + 1

    for i in range(fncsBus.shape[0]):
        lmps = {'bus' + str(i + 1): [DA_LMPs_pub[i]]}
        fncs.publish('LMP_DA_Bus_' + str(i + 1), json.dumps(lmps))

    # with open(output, 'w') as outfile:  #dispatch
    #   results = {}
    #   resultsPowerGen = {}
    #   instance = model._model
    #   for g in instance.Generators.value:
    #     for t in instance.TimePeriods:
    #       results[(g, t)] = instance.UnitOn[g, t]
    #       resultsPowerGen[(g, t)] = instance.PowerGenerated[g, t]
    #
    #   for g in sorted(instance.Generators.value):
    #     outfile.write("%s\n" % str(g).ljust(8))
    #     for t in sorted(instance.TimePeriods):
    #       outfile.write("% 1d %6.3f %6.2f %6.2f\n" % (
    #       int(results[(g, t)].value + 0.5), resultsPowerGen[(g, t)].value, 0.0, 0.0))  # not sure why DK added 0.0, 0.0

    dispatch = {}
    resultsPowerGen = {}
    try:
        for g in sorted(instance.Generators.value):
            dispatch[g] = []
            for t in sorted(instance.TimePeriods):
                resultsPowerGen[(g, t)] = instance.PowerGenerated[g, t]
                dispatch[g].append(resultsPowerGen[(g, t)].value * baseS)
    except:
        return uc_df, {}, [[]]

    # with open('./SCUCSVPOutcomes.dat', 'w') as outfile:
    #   instance = model._model
    #   SlackVariablePower = {}
    #   for b in instance.Buses.value:
    #     for t in instance.TimePeriods:
    #       SlackVariablePower[(b, t)] = instance.LoadGenerateMismatch[b, t]
    #
    #   for b in sorted(instance.Buses.value):
    #     outfile.write("%s\n" % str(b).ljust(8))
    #     for t in sorted(instance.TimePeriods):
    #       outfile.write(" %6.2f \n" % (SlackVariablePower[(b, t)].value))
    #
    if (len(priceSenLoadData) is not 0):
      with open('./SCUCPriceSensitiveLoad.dat', 'w') as outfile:
        instance = model._model
        PriceSenLoadDemand = {}
        for l in instance.PriceSensitiveLoads.value:
          for t in instance.TimePeriods:
            PriceSenLoadDemand[(l, t)] = instance.PSLoadDemand[l, t].value

        for l in sorted(instance.PriceSensitiveLoads.value):
          outfile.write("%s\n" % str(l).ljust(8))
          for t in sorted(instance.TimePeriods):
            outfile.write(" %6.2f \n" % (PriceSenLoadDemand[(l, t)]))
      #print('PriceSenLoadDemand = \n', PriceSenLoadDemand)

    return uc_df, dispatch, DA_LMPs


def scedRTM(data, output, solver):
    uc = "./SCUCResultsUC.dat"
    uc_df = pd.DataFrame(pst.read_unit_commitment(uc.strip("'")))

    c, ZonalDataComplete, priceSenLoadData = pst.read_model(data.strip("'"))
    c.gen_status = uc_df.astype(int)

    model = pst.build_model(c, ZonalDataComplete=ZonalDataComplete, PriceSenLoadData=priceSenLoadData)
    model.solve(solver=solver)
    instance = model._model

    # with open('./SCEDSVPOutcomes.dat', 'w') as outfile:
    #   instance = model._model
    #   SlackVariablePower = {}
    #   for b in instance.Buses.value:
    #     for t in instance.TimePeriods:
    #       SlackVariablePower[(b, t)] = instance.LoadGenerateMismatch[b, t]
    #
    #   for b in sorted(instance.Buses.value):
    #     outfile.write("%s\n" % str(b).ljust(8))
    #     for t in sorted(instance.TimePeriods):
    #       outfile.write(" %6.2f \n" % (SlackVariablePower[(b, t)].value))

    RT_LMPs = [[0 for x in range(TAU)] for y in range(total_bus_num)]
    RT_LMPs_pub = [[0 for x in range(TAU)] for y in range(total_bus_num)]
    for h, r in model.results.lmp.iterrows():
        bn = 1
        for _, lmp in r.iteritems():
            if lmp is None:
                lmp = 0
            RT_LMPs[bn - 1][h] = -round(lmp, 2)  # publishing $/kwh
            RT_LMPs_pub[bn - 1][h] = -round(lmp * 0.001, 2)  # publishing $/kwh
            bn = bn + 1
        if h == TAU:
            break

    for i in range(fncsBus.shape[0]):
        lmps = {'bus' + str(i + 1): [RT_LMPs_pub[i]]}
        fncs.publish('LMP_RT_Bus_' + str(i + 1), json.dumps(lmps))  # publishing $/kwh

    # with open(output.strip("'"), 'w') as f:
    #   f.write("LMP\n")
    #   # click.echo("..." + str(model.results.lmp))
    #   for h, r in model.results.lmp.iterrows():
    #     bn = 1
    #     for _, lmp in r.iteritems():
    #       if lmp is None:
    #         lmp = 0
    #       f.write(str(bn) + ' : ' + str(h + 1) + ' : ' + str(round(lmp, 2)) + "\n")
    #       bn = bn + 1
    #   f.write("END_LMP\n")
    #
    #   f.write("GenCoResults\n")
    #   instance = model._model
    #
    #   for g in instance.Generators.value:
    #     f.write("%s\n" % str(g).ljust(8))
    #     for t in instance.TimePeriods:
    #       f.write("Minute: {}\n".format(str(t + 1)))
    #       f.write("\tPowerGenerated: {}\n".format(round(instance.PowerGenerated[g, t].value, 3)))
    #       f.write("\tProductionCost: {}\n".format(round(instance.ProductionCost[g, t].value, 3)))
    #       f.write("\tStartupCost: {}\n".format(round(instance.StartupCost[g, t].value, 3)))
    #       f.write("\tShutdownCost: {}\n".format(round(instance.ShutdownCost[g, t].value, 3)))
    #   f.write("END_GenCoResults\n")
    #
    #   f.write("VOLTAGE_ANGLES\n")
    #   for bus in sorted(instance.Buses):
    #     for t in instance.TimePeriods:
    #       f.write('{} {} : {}\n'.format(str(bus), str(t + 1), str(round(instance.Angle[bus, t].value, 3))))
    #   f.write("END_VOLTAGE_ANGLES\n")
    #
    #   # Write out the Daily LMP
    #   # f.write("DAILY_BRANCH_LMP\n")
    #   # f.write("END_DAILY_BRANCH_LMP\n")
    #   # Write out the Daily Price Sensitive Demand
    #   # f.write("DAILY_PRICE_SENSITIVE_DEMAND\n")
    #   # f.write("END_DAILY_PRICE_SENSITIVE_DEMAND\n")
    #   # Write out which hour has a solution
    #
    #   f.write("HAS_SOLUTION\n")
    #   h = 0
    #   max_hour = 24  # FIXME: Hard-coded number of hours.
    #   while h < max_hour:
    #     f.write("1\t")  # FIXME: Hard-coded every hour has a solution.
    #     h += 1
    #   f.write("\nEND_HAS_SOLUTION\n")

    dispatch = {}
    resultsPowerGen = {}
    try:
        for g in sorted(instance.Generators.value):
            dispatch[g] = []
            for t in sorted(instance.TimePeriods):
                resultsPowerGen[(g, t)] = instance.PowerGenerated[g, t]
                dispatch[g].append(resultsPowerGen[(g, t)].value * baseS)
                if t == TAU:
                    break
    except:
        return {}, []

    return dispatch, RT_LMPs


def write_psst_file(fname, dayahead):
    fp = open(fname, 'w')
    print('# Written by fncsTSO.py', file=fp)
    print('', file=fp)
    print('set StageSet := FirstStage SecondStage ;', file=fp)
    print('', file=fp)
    print('set CommitmentTimeInStage[FirstStage] := 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 ;',
          file=fp)
    print('set CommitmentTimeInStage[SecondStage] := ;', file=fp)
    print('', file=fp)
    print('set GenerationTimeInStage[FirstStage] := ;', file=fp)
    print('set GenerationTimeInStage[SecondStage] := 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 ;',
          file=fp)
    print('', file=fp)

    writeLine = 'set Buses :='
    for i in range(bus.shape[0]):
        writeLine = writeLine + ' Bus' + str(i + 1)
    writeLine = writeLine + ' ;'
    print(writeLine, file=fp)
    print('', file=fp)

    print('set TransmissionLines :=', file=fp)
    for i in range(branch.shape[0]):
        if branch[i, 1] > branch[i, 0]:
            fbus = int(branch[i, 0])
            tbus = int(branch[i, 1])
        else:
            fbus = int(branch[i, 1])
            tbus = int(branch[i, 0])
        writeLine = 'Bus' + str(fbus) + ' Bus' + str(tbus)
        print(writeLine, file=fp)
    print(';', file=fp)
    print('', file=fp)

    writeLine = 'param NumTransmissionLines := ' + str(branch.shape[0]) + ' ;'
    print(writeLine, file=fp)
    print('', file=fp)

    print('param: BusFrom BusTo ThermalLimit Reactance :=', file=fp)
    for i in range(branch.shape[0]):
        if branch[i, 1] > branch[i, 0]:
            fbus = int(branch[i, 0])
            tbus = int(branch[i, 1])
        else:
            fbus = int(branch[i, 1])
            tbus = int(branch[i, 0])
        #  // Convert  MaxCap  from SI to  PU
        limit = branch[i, 5] / baseS
        #  // Convert  reactance  from SI to  PU, x(pu) = x / Zo = x / (Vo ^ 2 / So) = (x * So) / Vo ^ 2
        reactance = branch[i, 3] * baseS / (baseV * baseV)
        writeLine = str(i + 1) + ' Bus' + str(fbus) + ' Bus' + str(tbus) + '{: .2f}'.format(limit) + '{: .2E}'.format(reactance)
        print(writeLine, file=fp)
    print(';', file=fp)
    print('', file=fp)

    writeLine = 'set ThermalGenerators :='
    for i in range(gen.shape[0]):
        if gen[i, 9] > 0 and  genCost[i, 4] > 2e-5:     # not in wind_plants
            writeLine = writeLine + ' GenCo' + str(i + 1)
    print(writeLine, ';', file=fp)
    print('', file=fp)
    for i in range(bus.shape[0]):
        writeLine = 'set ThermalGeneratorsAtBus[Bus' + str(i + 1) + '] :='
        for j in range(gen.shape[0]):
            if int(gen[j, 0]) == i + 1 and gen[j, 9] > 0 and genCost[j, 4] > 2e-5:   # not in wind_plants
                writeLine = writeLine + ' GenCo' + str(j + 1)
        print(writeLine, ';', file=fp)
    print('', file=fp)

    print('param BalPenPos := 1000000 ;', file=fp)
    print('', file=fp)
    print('param BalPenNeg := 1000000 ;', file=fp)
    print('', file=fp)

    if (dayahead):
        print('param TimePeriodLength := 1 ;', file=fp)
        print('', file=fp)
        print('param NumTimePeriods := ' + str(hours_in_a_day) + ' ;', file=fp)
        print('', file=fp)
    else:
        print('param TimePeriodLength := 1 ;', file=fp)
        print('', file=fp)
        print('param NumTimePeriods := ' + str(TAU) + ' ;', file=fp)
        print('', file=fp)

    print(
        'param: PowerGeneratedT0 UnitOnT0State MinimumPowerOutput MaximumPowerOutput MinimumUpTime MinimumDownTime NominalRampUpLimit NominalRampDownLimit StartupRampLimit ShutdownRampLimit ColdStartHours ColdStartCost HotStartCost ShutdownCostCoefficient :=',
        file=fp)
    for i in range(gen.shape[0]):
        if gen[i, 9] > 0 and genCost[i, 4] > 2e-5:   # not in wind_plants
            name = 'GenCo' + str(i + 1)
            Pmax = gen[i, 8] / baseS
            Pmin = gen[i, 9] / baseS
            # powerT0
            if len(rt_dispatch) == 0:
                powerT0 = Pmax * 0.5
            else:
                powerT0 = rt_dispatch[name][0] / baseS
            # unitOnT0State
            unitOnT0 = gen_ames[str(i)][0]  # counter in hours
            if Pmin < Pmax:
                writeLine = name + '{: .6f}'.format(powerT0) + ' ' + str(unitOnT0) + '{: .6f}'.format(
                    Pmin) + '{: .6f}'.format(Pmax) + \
                            ' 0 0 0.000000 0.000000 0.000000 0.000000 0 0.000000 0.000000 0.000000'
            else:
                # TODO: wtf should never happen but does
                writeLine = name + '{: .6f}'.format(powerT0) + ' ' + str(unitOnT0) + '{: .6f}'.format(
                    0.0) + '{: .6f}'.format(Pmax) + \
                            ' 0 0 0.000000 0.000000 0.000000 0.000000 0 0.000000 0.000000 0.000000'
                print("Some thing is wrong with " + name + ' in ' + fname)
            print(writeLine, file=fp)
    print(' ;', file=fp)
    print('', file=fp)

    print(
        'param: ID atBus EndPointSoc MaximumEnergy NominalRampDownInput NominalRampUpInput NominalRampDownOutput NominalRampUpOutput MaximumPowerInput MinimumPowerInput MaximumPowerOutput MinimumPowerOutput MinimumSoc EfficiencyEnergy :=',
        file=fp)
    print(' ;', file=fp)
    print('', file=fp)

    print('param StorageFlag := 0.0 ;', file=fp)
    print('', file=fp)
    print('param PriceSenLoadFlag :=', str(with_market), ';', file=fp)
    print('', file=fp)
    print('param ReserveDownSystemPercent := 0.2 ;', file=fp)
    print('', file=fp)
    print('param ReserveUpSystemPercent := 0.3 ;', file=fp)
    print('', file=fp)
    print('param HasZonalReserves := false ;', file=fp)
    print('', file=fp)
    print('param NumberOfZones :=', str(len(zones)), ';', file=fp)
    print('', file=fp)

    writeLine = 'set Zones :='
    for j in range(len(zones)):
        writeLine = writeLine + ' Zone' + str(j + 1)
    print(writeLine, ';', file=fp)
    print('', file=fp)

    print('param: Buses ReserveDownZonalPercent ReserveUpZonalPercent :=', file=fp)
    for j in range(len(zones)):
        buses = ''
        for i in range(bus.shape[0]):
            if zones[j][0] == bus[i, 10]:
                if buses == '':
                    buses = 'Bus' + str(i + 1) + ','
                else:
                    buses = buses + 'Bus' + str(i + 1) + ','
        writeLine = 'Zone' + str(j + 1) + ' ' + buses + '{: .1f}'.format(zones[j][2]) + '{: .1f}'.format(zones[j][3])
        print(writeLine, file=fp)
    print(';', file=fp)
    print('', file=fp)

    if not with_market:
        print('param: NetDemand :=', file=fp)
        for i in range(bus.shape[0]):
            busnum = i + 1
            gld_scale = float(fncsBus[i][2])
            if dayahead:
                for j in range(hours_in_a_day):
                    ndg = 0
                    for key, row in wind_plants.items():
                        if row[0] == busnum:
                            ndg += row[9][j]
                    net = (gld_load[busnum]['pcrv'] + gld_load[busnum]['p'] * gld_scale) - ndg
                    writeLine = 'Bus' + str(busnum) + ' ' + str(j + 1) + ' {:.4f}'.format(net / baseS)
                    print(writeLine, file=fp)
            else:
                ndg = 0
                for key, row in wind_plants.items():
                    if row[0] == busnum:
                        ndg += row[9][wind_hour]
                net = (gld_load[busnum]['pcrv'] + gld_load[busnum]['p'] * gld_scale) - ndg
                for j in range(TAU):
                    writeLine = 'Bus' + str(busnum) + ' ' + str(j + 1) + ' {:.4f}'.format(net / baseS)
                    print(writeLine, file=fp)
            print('', file=fp)
        print(';', file=fp)
        print('', file=fp)
    else:
        print('param: NetDemand :=', file=fp)
        for i in range(bus.shape[0]):
            busnum = i + 1
            if dayahead:
                for j in range(hours_in_a_day):
                    ndg = 0
                    for key, row in wind_plants.items():
                        if row[0] == busnum:
                            ndg += row[9][j]
                    net = respMaxMW[i][j] + unRespMW[i][j] - ndg
                    writeLine = 'Bus' + str(busnum) + ' ' + str(j + 1) + ' {:.4f}'.format(net / baseS)
                    print(writeLine, file=fp)
            else:
                ndg = 0
                for key, row in wind_plants.items():
                    if row[0] == busnum:
                        ndg += row[9][wind_hour]
                gld_scale = float(fncsBus[i][2])
                net = ((gld_load[busnum]['resp_max'] + gld_load[busnum]['unresp']) * gld_scale) - ndg
                for j in range(TAU):
                    writeLine = 'Bus' + str(busnum) + ' ' + str(j + 1) + ' {:.4f}'.format(net / baseS)
                    print(writeLine, file=fp)
            print('', file=fp)
        print(';', file=fp)
        print('', file=fp)

        writeLine = 'set PricesSensitiveLoadNames :='
        for i in range(bus.shape[0] - 1):
            writeLine = writeLine + ' LSE' + str(i + 1) + ','
        writeLine = writeLine + ' LSE' + str(i + 2)
        print(writeLine, ';', file=fp)
        print('', file=fp)

        print('param: Name ID atBus hourIndex BenefitCoefficientC0 BenefitCoefficientC1 BenefitCoefficientC2 SLMin SLMax :=', file=fp)
        for i in range(bus.shape[0]):
            busnum = i + 1
            if (dayahead):
                for j in range(hours_in_a_day):
                    writeLine = 'LSE' + str(busnum) + ' ' + str(busnum) + ' Bus' + str(busnum) + ' ' + str(j + 1) + \
                                ' 0.0' + ' {: .2f}'.format(respC1[i][j]) + ' {: .2f}'.format(respC2[i][j]) + \
                                ' 0.0' + ' {: .2f}'.format(respMaxMW[i][j] / baseS)
                    print(writeLine, file=fp)
                print('', file=fp)
            else:
                gld_scale = float(fncsBus[i][2])
                resp_max = gld_load[busnum]['resp_max'] * gld_scale
                c2 = gld_load[busnum]['c2'] / gld_scale
                c1 = gld_load[busnum]['c1']
                for j in range(TAU):
                    writeLine = 'LSE' + str(busnum) + ' ' + str(busnum) + ' Bus' + str(busnum) + ' ' + str(j + 1) + \
                                ' 0.0' + ' {: .2f}'.format(c1) + ' {: .2f}'.format(c2) + \
                                ' 0.0' + ' {: .2f}'.format(resp_max / baseS)
                    print(writeLine, file=fp)
                print('', file=fp)
        print(';', file=fp)
        print('', file=fp)

    print('param: ProductionCostA0 ProductionCostA1 ProductionCostA2 NS :=', file=fp)
    for i in range(gen.shape[0]):
        if gen[i, 9] > 0 and genCost[i, 5] > 0 and genCost[i, 4] and genCost[i, 4] > 2e-5:  # not in wind_plants
            c0 = genCost[i, 6]
            c1 = genCost[i, 5]
            c2 = genCost[i, 4]
            writeLine = 'GenCo' + str(i + 1) + '{: .5f}'.format(c0) + \
                        '{: .5f}'.format(c1) + '{: .5f}'.format(c2) + ' ' + str(NS)
            print(writeLine, file=fp)
    print(';', file=fp)

    fp.close()


def write_ames_base_case(fname):
    fp = open(fname, 'w')
    print('// Base SI', file=fp)
    print('BASE_S ', str(baseS), file=fp)  # TODO unit check
    print('// Base Voltage', file=fp)
    print('BASE_V ', str(baseV), file=fp)  # TODO unit check
    print('', file=fp)

    print('// Simulation Parameters', file=fp)
    print('MaxDay ' + str(MaxDay), file=fp)
    print('RTOPDur ' + str(RTOPDur), file=fp)
    print('RandomSeed 695672061', file=fp)
    print('// ThresholdProbability 0.999', file=fp)
    print('PriceSensitiveDemandFlag 1', file=fp)
    print('ReserveDownSystemPercent 0.2', file=fp)
    print('ReserveUpSystemPercent 0.3', file=fp)
    print('BalPenPos 1000000', file=fp)
    print('BalPenNeg 1000000', file=fp)
    print('NDGFlag 1', file=fp)

    print('// Bus Data', file=fp)
    print('NumberOfBuses', bus.shape[0], file=fp)
    print('NumberOfReserveZones', len(zones), file=fp)
    print('', file=fp)

    print('#ZoneDataStart', file=fp)
    print('// ZoneName   Buses   ReserveDownZonalPercent   ReserveUpZonalPercent', file=fp)
    for j in range(len(zones)):
        name = 'Zone' + str(j + 1)
        buses = ''
        for i in range(bus.shape[0]):
            if zones[j][0] == bus[i, 10]:
                if buses == '':
                    buses = str(i + 1)
                else:
                    buses = buses + ',' + str(i + 1)
        print(name, buses, '{: .1f}'.format(zones[j][2]), '{: .1f}'.format(zones[j][3]), file=fp)
    print('#ZoneDataEnd', file=fp)
    print('', file=fp)

    print('#LineDataStart', file=fp)
    print('// Name   From   To   MaxCap(MWs)   Reactance(ohms)', file=fp)
    # branch: fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
    # AMES wants branch name, from bus(< to bus), to bus, capacity(MVA), total X(pu)
    for i in range(branch.shape[0]):
        name = 'Line' + str(i + 1)
        if branch[i, 1] > branch[i, 0]:
            fbus = int(branch[i, 0])
            tbus = int(branch[i, 1])
        else:
            fbus = int(branch[i, 1])
            tbus = int(branch[i, 0])
        print(name, fbus, tbus, '{: .2f}'.format(branch[i, 5]), '{: .6f}'.format(branch[i, 3]), file=fp)
    print('#LineDataEnd', file=fp)
    print('', file=fp)

    print('#GenDataStart', file=fp)
    print('// Name   ID   atBus   SCost($H)   a($/MWh)   b($MW^2h)   CapL(MW)   CapU(MW)   Segments   InitMoney',
          file=fp)
    # TODO: replace ppc['gencost'] with dictionary of hourly bids, collected from the GridLAB-D agents over FNCS
    # gen: bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin,(11 zeros)
    # gencost: 2, startup, shutdown, 3, c2, c1, c0
    # AMES wants name, ID, bus, c0, c1, c2, capL, capU, NS, InitMoney
    for i in range(gen.shape[0]):
        name = 'GenCo' + str(i + 1)
        fbus = int(gen[i, 0])
        Pmax = gen[i, 8]
        Pmin = gen[i, 9]
        c0 = genCost[i, 6]
        c1 = genCost[i, 5]
        c2 = genCost[i, 4]
        if Pmin > 0 and genCost[i, 4] > 2e-5:   # not in wind_plants
            print(name, str(i + 1), fbus, '{: .2f}'.format(c0), '{: .2f}'.format(c1),
                  '{: .6f}'.format(c2), '{: .2f}'.format(Pmin), '{: .2f}'.format(Pmax),
                  NS, '{: .2f}'.format(100000.0), file=fp)
    print('#GenDataEnd', file=fp)
    print('', file=fp)

    print('#LSEDataFixedDemandStart', file=fp)
    # ppc arrays(bus type 1=load, 2 = gen(PV) and 3 = swing)
    # bus: bus_i, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin
    # AMES wants name, ID, bus, 8x hourly demands, in three blocks
    # Define a dictionary of hourly load forecasts, collected from ppc
    #    GridLAB-D via FNCS, to replace ppc['bus']
    lse = []
    for i in range(bus.shape[0]):
        Pd = unRespMW[i] + respMaxMW[i]
        fbus = int(bus[i, 0])
        lse.append([fbus, Pd])
    print('// Name ID atBus H-00 H-01 H-02 H-03 H-04 H-05 H-06 H-07', file=fp)
    for i in range(len(lse)):
        Pd = lse[i][1]
        print('LSE' + str(i + 1), str(i + 1), lse[i][0], '{: .2f}'.format(Pd[0]), '{: .2f}'.format(Pd[1]),
              '{: .2f}'.format(Pd[2]), '{: .2f}'.format(Pd[3]), '{: .2f}'.format(Pd[4]),
              '{: .2f}'.format(Pd[5]), '{: .2f}'.format(Pd[6]), '{: .2f}'.format(Pd[7]), file=fp)
    print('// Name ID atBus H-08 H-09 H-10 H-11 H-12 H-13 H-14 H-15', file=fp)
    for i in range(len(lse)):
        Pd = lse[i][1]
        print('LSE' + str(i + 1), str(i + 1), lse[i][0], '{: .2f}'.format(Pd[8]), '{: .2f}'.format(Pd[9]),
              '{: .2f}'.format(Pd[10]), '{: .2f}'.format(Pd[11]), '{: .2f}'.format(Pd[12]),
              '{: .2f}'.format(Pd[13]), '{: .2f}'.format(Pd[14]), '{: .2f}'.format(Pd[15]), file=fp)
    print('// Name ID atBus H-16 H-17 H-18 H-19 H-20 H-21 H-22 H-23', file=fp)
    for i in range(len(lse)):
        Pd = lse[i][1]
        print('LSE' + str(i + 1), str(i + 1), lse[i][0], '{: .2f}'.format(Pd[16]), '{: .2f}'.format(Pd[17]),
              '{: .2f}'.format(Pd[18]), '{: .2f}'.format(Pd[19]), '{: .2f}'.format(Pd[20]),
              '{: .2f}'.format(Pd[21]), '{: .2f}'.format(Pd[22]), '{: .2f}'.format(Pd[23]), file=fp)
    print('#LSEDataFixedDemandEnd', file=fp)
    print('', file=fp)

    # Wind Plants, AMES wants name, ID, bus, 8x hourly demands, in three blocks
    print('#NDGDataStart', file=fp)
    i = 1
    print('// Name ID atBus H-00 H-01 H-02 H-03 H-04 H-05 H-06 H-07', file=fp)
    for key, row in wind_plants.items():
        Pd = row[9]
        print('NDG' + str(i), str(i), row[0], '{: .2f}'.format(Pd[0]), '{: .2f}'.format(Pd[1]),
              '{: .2f}'.format(Pd[2]), '{: .2f}'.format(Pd[3]), '{: .2f}'.format(Pd[4]),
              '{: .2f}'.format(Pd[5]), '{: .2f}'.format(Pd[6]), '{: .2f}'.format(Pd[7]), file=fp)
        i += 1
    i = 1
    print('// Name ID atBus H-08 H-09 H-10 H-11 H-12 H-13 H-14 H-15', file=fp)
    for key, row in wind_plants.items():
        Pd = row[9]
        print('NDG' + str(i), str(i), row[0], '{: .2f}'.format(Pd[8]), '{: .2f}'.format(Pd[9]),
              '{: .2f}'.format(Pd[10]), '{: .2f}'.format(Pd[11]), '{: .2f}'.format(Pd[12]),
              '{: .2f}'.format(Pd[13]), '{: .2f}'.format(Pd[14]), '{: .2f}'.format(Pd[15]), file=fp)
        i += 1
    i = 1
    print('// Name ID atBus H-16 H-17 H-18 H-19 H-20 H-21 H-22 H-23', file=fp)
    for key, row in wind_plants.items():
        Pd = row[9]
        print('NDG' + str(i), str(i), row[0], '{: .2f}'.format(Pd[16]), '{: .2f}'.format(Pd[17]),
              '{: .2f}'.format(Pd[18]), '{: .2f}'.format(Pd[19]), '{: .2f}'.format(Pd[20]),
              '{: .2f}'.format(Pd[21]), '{: .2f}'.format(Pd[22]), '{: .2f}'.format(Pd[23]), file=fp)
        i += 1
    print('#NDGDataEnd', file=fp)
    print('', file=fp)

    print('#LSEDataPriceSensitiveDemandStart', file=fp)
    print('// Name   ID    atBus   hourIndex   d   e   f   pMin   pMax', file=fp);
    lse = []
    for i in range(bus.shape[0]):
        Pd = unRespMW[i]
        fbus = int(bus[i, 0])
        lse.append([fbus, Pd])

    for i in range(len(lse)):
        Pd = lse[i][1]
        for k in range(hours_in_a_day):
            print('LSE' + str(i + 1), str(i + 1), lse[i][0], str(k + 1),
                  '{: .2f}'.format(0), '{: .2f}'.format(0.1),
                  '{: .2f}'.format(0), '{: .2f}'.format(Pd[k]), file=fp)
    print('#LSEDataPriceSensitiveDemandEnd', file=fp)
    fp.close()

# Initialize the program

x = np.array(range(25))
y = np.array(load_shape)
l = len(x)
t = np.linspace(0, 1, l - 2, endpoint=True)
t = np.append([0, 0, 0], t)
t = np.append(t, [1, 1, 1])
tck_load = [t, [x, y], 3]
#u3 = np.linspace(0, 1, num=86400 / 300 + 1, endpoint=True)
#newpts = ip.splev(u3, tck_load)

ppc = tesp.load_json_case('./../' + casename + '.json')
ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['opf_dc'], OPF_ALG_DC=200)  # dc for
ppopt_regular = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['pf_dc'], PF_MAX_IT=20, PF_ALG=1)  # ac for power flow

ames = ppc['ames']

with_market = 0
if ppc['withMarket']:
    with_market = 1

wind_period = 0
if ppc['windPower']:
    wind_period = 3600

StartTime = ppc['StartTime']
tmax = int(ppc['Tmax'])
period = int(ppc['Period'])
dt = int(ppc['dt'])
baseS = int(ppc['baseMVA'])  # base_S in ames
baseV = int(100)  # base_V in ames
swing_bus = int(ppc['swing_bus'])

# these have been aliased
bus = ppc['bus']
branch = ppc['branch']
gen = ppc['gen']
genCost = ppc['gencost']
zones = ppc['zones']
fncsBus = ppc['FNCS']

if ppc['noScale']:
    for row in fncsBus:
        row[2] = 1
        row[5] = 1
        row[6] = 1

# ppc arrays(bus type 1=load, 2 = gen(PV) and 3 = swing)
# bus: bus id, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin
# zones: zone id, name, ReserveDownZonalPercent, ReserveUpZonalPercent
# branch: from bus, to bus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
# gen: bus id, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin,(11 zeros)
# gencost: 2, startup, shutdown, 3, c2, c1, c0
# FNCS: bus id, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew, Pinit, Qinit
# UnitsOut: idx, time out[s], time back in[s]
# BranchesOut: idx, time out[s], time back in[s]

# initialize for metrics collection
bus_mp = open('bus_' + casename + '_metrics.json', 'w')
gen_mp = open('gen_' + casename + '_metrics.json', 'w')
sys_mp = open('sys_' + casename + '_metrics.json', 'w')
bus_meta = {'LMP_P': {'units': 'USD/kwh', 'index': 0}, 'LMP_Q': {'units': 'USD/kvarh', 'index': 1},
            'PD': {'units': 'MW', 'index': 2}, 'QD': {'units': 'MVAR', 'index': 3},
            'Vang': {'units': 'deg', 'index': 4},
            'Vmag': {'units': 'pu', 'index': 5}, 'Vmax': {'units': 'pu', 'index': 6},
            'Vmin': {'units': 'pu', 'index': 7},
            'unresp': {'units': 'MW', 'index': 8}, 'resp_max': {'units': 'MW', 'index': 9},
            'c1': {'units': '$/MW', 'index': 10}, 'c2': {'units': '$/MW^2', 'index': 11}}
gen_meta = {'Pgen': {'units': 'MW', 'index': 0}, 'Qgen': {'units': 'MVAR', 'index': 1},
            'LMP_P': {'units': 'USD/kwh', 'index': 2}}
sys_meta = {'Ploss': {'units': 'MW', 'index': 0}, 'Converged': {'units': 'true/false', 'index': 1}}
bus_metrics = {'Metadata': bus_meta, 'StartTime': StartTime}
gen_metrics = {'Metadata': gen_meta, 'StartTime': StartTime}
sys_metrics = {'Metadata': sys_meta, 'StartTime': StartTime}
make_dictionary(ppc, casename)

# initialize for variable wind
wind_plants = {}
tnext_wind = tmax + 2 * dt  # by default, never fluctuate the wind plants
if wind_period > 0:
    wind_plants = make_wind_plants(ppc)
    if len(wind_plants) < 1:
        print('warning: wind power fluctuation requested, but there are no wind plants in this case')
    else:
        tnext_wind = 0

# initialize for day-ahead, OPF and time stepping
ts = 0
tnext_opf = 0
tnext_ames = 0
wind_hour = 0
mn = 0
hour = -1
day = 1
MaxDay = tmax // 86400  # days in simulation
RTOPDur = period // 60  # in minutes
RTDeltaT = 1  # in minutes
TAU = RTOPDur // RTDeltaT
hours_in_a_day = 24
NS = 4  # number of segments
gen_ames = {}
da_schedule = {}
da_lmps = {}
da_dispatch = {}
rt_lmps = {}
rt_dispatch = {}

# we need to adjust Pmin downward so the OPF and PF can converge, or else implement unit commitment
for row in gen:
    row[9] = 0.1 * row[8]

# listening to GridLAB-D and its auction objects
gld_load = {}  # key on bus number
print('FNCS Connections: bus, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew, Pinit, Qinit')
print(fncsBus)

# TODO: this is hardwired for 8, more efficient to concatenate outside a loop
# for ? generator
for i in range(fncsBus.shape[0]):
    busnum = i + 1
    genidx = ppc['gen'].shape[0]
    # I suppose a generator for all sum generator a bus?
    ppc['gen'] = np.concatenate(
        (ppc['gen'], np.array([[busnum, 0, 0, 0, 0, 1, 250, 1, 0, -5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])))
    ppc['gencost'] = np.concatenate((ppc['gencost'], np.array([[2, 0, 0, 3, 0.0, 0.0, 0.0]])))
    gld_scale = float(fncsBus[i, 2])
    gld_load[busnum] = {'pcrv': 0, 'qcrv': 0, 'p': float(fncsBus[i, 7]) / gld_scale,
                        'q': float(fncsBus[i, 8]) / gld_scale,
                        'unresp': 0, 'resp_max': 0, 'c2': 0, 'c1': 0, 'deg': 0, 'genidx': genidx}

# needed to be re-aliased after np.concatenate
bus = ppc['bus']
gen = ppc['gen']
genCost = ppc['gencost']

# print(gld_load)
# print(gen)
# print(genCost)
tnext_metrics = 0
loss_accum = 0
conv_accum = True
n_accum = 0
bus_accum = {}
gen_accum = {}

for i in range(fncsBus.shape[0]):
    busnum = int(fncsBus[i, 0])
    bus_accum[str(busnum)] = [0, 0, 0, 0, 0, 0, 0, 99999.0, 0, 0, 0, 0]
for i in range(gen.shape[0]):
    gen_accum[str(i + 1)] = [0, 0, 0]
    gen_ames[str(i)] = [24]

total_bus_num = fncsBus.shape[0]
unRespMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
respMaxMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
respC2 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
respC1 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
respC0 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
resp_deg = np.zeros([total_bus_num, hours_in_a_day], dtype=float)

# TODO: orginal forecast
# for i in range(total_bus_num):
#     for j in range(hours_in_a_day):
#          respC1[i][j] = 60.0
#          respC2[i][j] = -2.0
#          unRespMW[i][j] = fncsBus[i][3] * 0.5   # * scale for each bus
#          respMaxMW[i][j] = fncsBus[i][3] * 0.5   # * scale for each bus

if ames:
    write_ames_base_case(casename + '_ames.dat')

# quit()
fncs.initialize()

op = open(casename + '_opf.csv', 'w')
vp = open(casename + '_pf.csv', 'w')
print('seconds, OPFconverged, TotalLoad, TotalGen, SwingGen, LMP1, LMP8, \
      gas1, coal1, nuc1, gas2, coal2, nuc2, gas3, coal3, gas4, gas5, coal5, gas7, \
      coal7, wind1, wind3, wind4, wind6, wind7',
      sep=', ', file=op, flush=True)
print('seconds, PFConverged, TotalLoad, TotalGen, TotalLoss, SwingGen, v1, v2, v3, v4, v5, v6, v7, v8',
      sep=', ', file=vp, flush=True)

# MAIN LOOP starts here
while ts <= tmax:
    # start by getting the latest inputs from GridLAB-D and the auction
    events = fncs.get_events()
    for topic in events:
        val = fncs.get_value(topic)
    # getting the latest inputs from GridLAB-D
        if 'UNRESPONSIVE_MW_' in topic:
            busnum = int(topic[16:])
            gld_load[busnum]['unresp'] = float(val)
        #      print ('UNRESPONSIVE_MW_', busnum, 'at', ts, '=', val, flush=True)
        elif 'RESPONSIVE_MAX_MW_' in topic:
            busnum = int(topic[18:])
            gld_load[busnum]['resp_max'] = float(val)
        #      print ('RESPONSIVE_MAX_MW_', busnum, 'at', ts, '=', val, flush=True)
        elif 'RESPONSIVE_C2_' in topic:
            busnum = int(topic[14:])
            gld_load[busnum]['c2'] = float(val)
        #      print ('RESPONSIVE_C2_', busnum, 'at', ts, '=', val, flush=True)
        elif 'RESPONSIVE_C1_' in topic:
            busnum = int(topic[14:])
            gld_load[busnum]['c1'] = float(val)
        #      print ('RESPONSIVE_C1_', busnum, 'at', ts, '=', val, flush=True)
        elif 'RESPONSIVE_DEG_' in topic:
            busnum = int(topic[15:])
            gld_load[busnum]['deg'] = int(val)
        #      print ('RESPONSIVE_DEG_', busnum, 'at', ts, '=', val, flush=True)
        #    elif 'wind_power' in topic:
        #      busnum = int(topic[15:])
        #      gld_load[busnum]['windpower'] = int(val)
    # getting the latest inputs from substations (DSO)
        elif 'SUBSTATION' in topic:  # gld
            busnum = int(topic[10:])
            p, q = parse_mva(val)
            gld_load[busnum]['p'] = float(p)
            gld_load[busnum]['q'] = float(q)
        elif 'DA_BID_' in topic:
            busnum = int(topic[7:]) - 1
            da_bid = json.loads(val)
            # keys unresp_mw, resp_max_mw, resp_c2, resp_c1, resp_deg; each array[hours_in_a_day]
            unRespMW[busnum] = da_bid['unresp_mw']  # fix load
            respMaxMW[busnum] = da_bid['resp_max_mw']  # slmax
            respC2[busnum] = da_bid['resp_c2']
            respC1[busnum] = da_bid['resp_c1']
            respC0[busnum] = 0.0  # da_bid['resp_c0']
            resp_deg[busnum] = da_bid['resp_deg']
            print('Day Ahead Bid for Bus', busnum, 'at', ts, '=', da_bid, flush=True)

    #  print(ts, 'FNCS inputs', gld_load, flush=True)
    # fluctuate the wind plants
    if ts >= tnext_wind:
        if ts % (wind_period * 24) == 0:
            for j in range(hours_in_a_day):
                for key, row in wind_plants.items():
                    # return dict with rows like wind['unit'] = [bus, MW, Theta0, Theta1, StdDev, Psi1, Ylim, alag, ylag, [24 hour p]]
                    Theta0 = row[2]
                    Theta1 = row[3]
                    StdDev = row[4]
                    Psi1 = row[5]
                    Ylim = row[6]
                    alag = row[7]
                    ylag = row[8]
                    if j > 0:
                        a = np.random.normal(0.0, StdDev)
                        y = Theta0 + a - Theta1 * alag + Psi1 * ylag
                        alag = a
                    else:
                        y = ylag
                    if y > Ylim:
                        y = Ylim
                    elif y < 0.0:
                        y = 0.0
                    p = y * y
                    if j > 0:
                        ylag = y
                    row[7] = alag
                    row[8] = ylag
                    if gen[int(key), 9] > p:
                        gen[int(key), 9] = p
                    row[9][j] = p

        for key, row in wind_plants.items():
            p = row[9][wind_hour]
            # reset the unit capacity; this will 'stick' for the next wind_period
            gen[int(key), 1] = p
        wind_hour += 1
        if wind_hour == 23:
            wind_hour = 0
        tnext_wind += wind_period

    # always baseline the loads from the curves
    for row in fncsBus:
        busnum = int(row[0])
        Pnom = float(row[3])
        Qnom = float(row[4])
        curve_scale = float(row[5])
        curve_skew = int(row[6])
        sec = (ts + curve_skew) % 86400
        h = float(sec) / 3600.0
        val = ip.splev([h / 24.0], tck_load)
        gld_load[busnum]['pcrv'] = Pnom * curve_scale * float(val[1])
        gld_load[busnum]['qcrv'] = Qnom * curve_scale * float(val[1])

    # run SCED/SCUC in AMES/PSST to establish the next day's unit commitment and dispatch
    if ts >= tnext_ames and ames:
        mn = mn + RTOPDur  # period // 60
        if mn % 60 == 0:
            hour = hour + 1
            mn = 0
            if hour == 24:
                mn = 0
                hour = 0
                day = day + 1

        for row in fncsBus:
            busnum = int(row[0])
            gld_scale = float(row[2])
            resp_max = gld_load[busnum]['resp_max'] * gld_scale
            unresp = gld_load[busnum]['unresp'] * gld_scale
            c2 = gld_load[busnum]['c2'] / gld_scale
            c1 = gld_load[busnum]['c1']
            deg = gld_load[busnum]['deg']
            # track the latest bid in the metrics
            bus_accum[str(busnum)][8] = unresp
            bus_accum[str(busnum)][9] = resp_max
            bus_accum[str(busnum)][10] = c1
            bus_accum[str(busnum)][11] = c2
            genidx = gld_load[busnum]['genidx']
            gen[genidx, 9] = -resp_max
            if deg == 2:
                genCost[genidx, 3] = 3
                genCost[genidx, 4] = -c2
                genCost[genidx, 5] = c1
            elif deg == 1:
                genCost[genidx, 3] = 2
                genCost[genidx, 4] = c1
                genCost[genidx, 5] = 0.0
            else:
                genCost[genidx, 3] = 1
                genCost[genidx, 4] = 999.0
                genCost[genidx, 5] = 0.0
            genCost[genidx, 6] = 0.0
            if ts > 0:
                bus[busnum - 1, 2] = gld_load[busnum]['pcrv'] + unresp   # + resp_max
                bus[busnum - 1, 3] = gld_load[busnum]['qcrv']
            else:  # use the initial condition for GridLAB-D contribution, which may be non-zero
                bus[busnum - 1, 2] = gld_load[busnum]['pcrv'] + gld_load[busnum]['p'] * gld_scale
                bus[busnum - 1, 3] = gld_load[busnum]['qcrv'] + gld_load[busnum]['q'] * gld_scale

        # Day ahead
        if hour == 12 and mn == 0:
            # Run the day ahead
            write_psst_file(ames_DAM_case_file, True)
            da_schedule, da_dispatch, da_lmps = scucDAM(ames_DAM_case_file, "GenCoSchedule.dat", "cplex")
            print("DA LMPs: \n", da_lmps)
            print("DA Gen dispatches: \n", da_dispatch)
            print("DA Unit Schedule: \n", da_schedule)

        # Real time and update the dispatch schedules in ppc
        sum_g = 0
        if day > 1:
            # Change the DA Schedule and the dispatch
            if mn == 0:
                for i in range(gen.shape[0]):
                    if gen[i, 9] > 0 and genCost[i, 4] > 2e-5:    # not in wind_plants
                        name = "GenCo" + str(i + 1)
                        # are the schedule from 12 on from the day ahead calculation
                        gen[i, 7] = da_schedule.at[hour, name]
                        if int(gen[i, 7]) == 1:
                            gen_ames[str(i)][0] += 1
                        else:
                            gen_ames[str(i)][0] -= 1

            # Run the real time and publish the LMP
            write_psst_file(ames_RTM_case_file, False)
            rt_dispatch, rt_lmps = scedRTM(ames_RTM_case_file, "RTMResults.dat", "cplex")
            print("RT LMPs: \n", rt_lmps)
            print("RT Gen dispatches: \n", rt_dispatch)

            for i in range(bus.shape[0]):
                bus[i, 13] = rt_lmps[i][0]

            for i in range(gen.shape[0]):
                name = "GenCo" + str(i + 1)
                if gen[i, 9] > 0 and genCost[i, 4] > 2e-5:    # not in wind_plants
                    gen[i, 1] = rt_dispatch[name][0]
                    sum_g += rt_dispatch[name][0]

#      TODO: fix swing bus
        Pswing = 0
        for idx in range(gen.shape[0]):
            if gen[idx, 0] == swing_bus:
                Pswing += gen[idx, 1]

        sum_w = 0
        for key, row in wind_plants.items():
            sum_w += row[9][wind_hour]

        line = str(ts) + ',' + "True" + ','
        line += '{: .2f}'.format(bus[:, 2].sum()) + ','
        line += '{: .2f}'.format(gen[:, 1].sum()) + ','
        line += '{: .2f}'.format(Pswing) + ','
        for idx in range(bus.shape[0]):
            line += '{: .4f}'.format(bus[idx, 13]) + ','
        for idx in range(gen.shape[0]):
            if gen[idx, 9] > 0:
                line += '{: .2f}'.format(gen[idx, 1]) + ','
        line += '{: .2f}'.format(sum_g) + ','
        line += '{: .2f}'.format(sum_w)
        print(line, sep=', ', file=op, flush=True)

        tnext_ames += period

        # run OPF to establish the prices and economic dispatch - currently period = 300s
    if ts >= tnext_opf and not ames:
        # update cost coefficients, set dispatchable load, put unresp+curve load on bus
        for row in fncsBus:
            busnum = int(row[0])
            gld_scale = float(row[2])
            resp_max = gld_load[busnum]['resp_max'] * gld_scale
            unresp = gld_load[busnum]['unresp'] * gld_scale
            c2 = gld_load[busnum]['c2'] / gld_scale
            c1 = gld_load[busnum]['c1']
            deg = gld_load[busnum]['deg']
            # track the latest bid in the metrics
            bus_accum[str(busnum)][8] = unresp
            bus_accum[str(busnum)][9] = resp_max
            bus_accum[str(busnum)][10] = c1
            bus_accum[str(busnum)][11] = c2
            genidx = gld_load[busnum]['genidx']
            gen[genidx, 9] = -resp_max
            if deg == 2:
                genCost[genidx, 3] = 3
                genCost[genidx, 4] = -c2
                genCost[genidx, 5] = c1
            elif deg == 1:
                genCost[genidx, 3] = 2
                genCost[genidx, 4] = c1
                genCost[genidx, 5] = 0.0
            else:
                genCost[genidx, 3] = 1
                genCost[genidx, 4] = 999.0
                genCost[genidx, 5] = 0.0
            genCost[genidx, 6] = 0.0
            if ts > 0:
                bus[busnum - 1, 2] = gld_load[busnum]['pcrv'] + unresp
                bus[busnum - 1, 3] = gld_load[busnum]['qcrv']
            else:  # use the initial condition for GridLAB-D contribution, which may be non-zero
                bus[busnum - 1, 2] = gld_load[busnum]['pcrv'] + gld_load[busnum]['p'] * gld_scale
                bus[busnum - 1, 3] = gld_load[busnum]['qcrv'] + gld_load[busnum]['q'] * gld_scale
        #    print_gld_load(ppc, gld_load, 'OPF', ts)
        ropf = pp.runopf(ppc, ppopt_market)
        if ropf['success'] == False:
            conv_accum = False
        opf_bus = deepcopy(ropf['bus'])
        opf_gen = deepcopy(ropf['gen'])
        Pswing = 0
        for idx in range(opf_gen.shape[0]):
            if opf_gen[idx, 0] == swing_bus:
                Pswing += opf_gen[idx, 1]

        line = str(ts) + ',' + "True" + ','
        line += '{: .2f}'.format(opf_bus[:, 2].sum()) + ','
        line += '{: .2f}'.format(opf_bus[:, 1].sum()) + ','
        line += '{: .2f}'.format(Pswing) + ','
        for idx in range(opf_bus.shape[0]):
            line += '{: .4f}'.format(opf_bus[idx, 13]) + ','
        for idx in range(opf_gen.shape[0]):
            if gen[idx, 9] > 0:
                line += '{: .2f}'.format(opf_gen[idx, 1]) + ','
        print(line, sep=', ', file=op, flush=True)

        tnext_opf += period

        # always run the regular power flow for voltages and performance metrics
        ppc['bus'][:, 13] = opf_bus[:, 13]  # set the lmp
        ppc['gen'][:, 1] = opf_gen[:, 1]  # set the economic dispatch
        bus = ppc['bus']  # needed to be re-aliased because of [:, ] operator
        gen = ppc['gen']  # needed to be re-aliased because of [:, ] operator

    # add the actual scaled GridLAB-D loads to the baseline curve loads, turn off dispatchable loads
    for row in fncsBus:
        busnum = int(row[0])
        gld_scale = float(row[2])
        Pgld = gld_load[busnum]['p'] * gld_scale
        Qgld = gld_load[busnum]['q'] * gld_scale
        bus[busnum - 1, 2] = gld_load[busnum]['pcrv'] + Pgld
        bus[busnum - 1, 3] = gld_load[busnum]['qcrv'] + Qgld
        genidx = gld_load[busnum]['genidx']
        gen[genidx, 1] = 0  # p
        gen[genidx, 2] = 0  # q
        gen[genidx, 9] = 0  # pmin
    #  print_gld_load(ppc, gld_load, 'RPF', ts)
    rpf = pp.runpf(ppc, ppopt_regular)
    if not rpf[0]['success']:
        conv_accum = False
        print('rpf did not converge at', ts)
    #   pp.printpf(100.0,
    #               bus=rpf[0]['bus'],
    #               gen=rpf[0]['gen'],
    #               branch=rpf[0]['branch'],
    #               fd=sys.stdout,
    #               et=rpf[0]['et'],
    #               success=rpf[0]['success'])
    rBus = rpf[0]['bus']
    rGen = rpf[0]['gen']
    Pload = rBus[:, 2].sum()
    Pgen = rGen[:, 1].sum()
    Ploss = Pgen - Pload
    Pswing = 0
    for idx in range(rGen.shape[0]):
        if rGen[idx, 0] == swing_bus:
            Pswing += rGen[idx, 1]
    print(ts, rpf[0]['success'],
          '{: .2f}'.format(Pload),
          '{: .2f}'.format(Pgen),
          '{: .2f}'.format(Ploss),
          '{: .2f}'.format(Pswing),
          '{: .3f}'.format(rBus[0, 7]),
          '{: .3f}'.format(rBus[1, 7]),
          '{: .3f}'.format(rBus[2, 7]),
          '{: .3f}'.format(rBus[3, 7]),
          '{: .3f}'.format(rBus[4, 7]),
          '{: .3f}'.format(rBus[5, 7]),
          '{: .3f}'.format(rBus[6, 7]),
          '{: .3f}'.format(rBus[7, 7]),
          sep=', ', file=vp, flush=True)

    # update the metrics
    n_accum += 1
    loss_accum += Ploss
    for i in range(fncsBus.shape[0]):
        busnum = int(fncsBus[i, 0])
        busidx = busnum - 1
        row = rBus[busidx].tolist()
        # publish the bus VLN and LMP [$/kwh] for GridLAB-D
        bus_vln = 1000.0 * row[7] * row[9] / math.sqrt(3.0)
        fncs.publish('three_phase_voltage_Bus' + str(busnum), bus_vln)
        if ames:
            lmp = float(bus[busidx, 13]) * 0.001
        else:
            lmp = float(opf_bus[busidx, 13]) * 0.001
        fncs.publish('LMP_Bus' + str(busnum), lmp)  # publishing $/kwh
        # LMP_P, LMP_Q, PD, QD, Vang, Vmag, Vmax, Vmin: row[11] and row[12] are Vmax and Vmin constraints
        PD = row[2]  # + resp # TODO, if more than one FNCS bus, track scaled_resp separately
        Vpu = row[7]
        bus_accum[str(busnum)][0] += row[13] * 0.001
        bus_accum[str(busnum)][1] += row[14] * 0.001
        bus_accum[str(busnum)][2] += PD
        bus_accum[str(busnum)][3] += row[3]
        bus_accum[str(busnum)][4] += row[8]
        bus_accum[str(busnum)][5] += Vpu
        if Vpu > bus_accum[str(busnum)][6]:
            bus_accum[str(busnum)][6] = Vpu
        if Vpu < bus_accum[str(busnum)][7]:
            bus_accum[str(busnum)][7] = Vpu
    for i in range(rGen.shape[0]):
        row = rGen[i].tolist()
        busidx = int(row[0] - 1)
        # Pgen, Qgen, LMP_P (includes the responsive load as dispatched by OPF)
        gen_accum[str(i + 1)][0] += row[1]
        gen_accum[str(i + 1)][1] += row[2]
        if ames:
            gen_accum[str(i + 1)][2] += float(bus[busidx, 13]) * 0.001
        else:
            gen_accum[str(i + 1)][2] += float(opf_bus[busidx, 13]) * 0.001

    # write the metrics
    if ts >= tnext_metrics:
        sys_metrics[str(ts)] = {casename: [loss_accum / n_accum, conv_accum]}

        bus_metrics[str(ts)] = {}
        for i in range(fncsBus.shape[0]):
            busnum = int(fncsBus[i, 0])
            busidx = busnum - 1
            row = rBus[busidx].tolist()
            met = bus_accum[str(busnum)]
            bus_metrics[str(ts)][str(busnum)] = [met[0] / n_accum, met[1] / n_accum, met[2] / n_accum, met[3] / n_accum,
                                                 met[4] / n_accum, met[5] / n_accum, met[6], met[7],
                                                 met[8], met[9], met[10], met[11]]
            bus_accum[str(busnum)] = [0, 0, 0, 0, 0, 0, 0, 99999.0, 0, 0, 0, 0]

        gen_metrics[str(ts)] = {}
        for i in range(rGen.shape[0]):
            met = gen_accum[str(i + 1)]
            gen_metrics[str(ts)][str(i + 1)] = [met[0] / n_accum, met[1] / n_accum, met[2] / n_accum]
            gen_accum[str(i + 1)] = [0, 0, 0]

        tnext_metrics += period
        n_accum = 0
        loss_accum = 0
        conv_accum = True

    # request the next time step, if necessary
    if ts >= tmax:
        print('breaking out at', ts, flush=True)
        break
    ts = fncs.time_request(min(ts + dt, tmax))

# ======================================================
print('writing metrics', flush=True)
print(json.dumps(sys_metrics), file=sys_mp, flush=True)
print(json.dumps(bus_metrics), file=bus_mp, flush=True)
print(json.dumps(gen_metrics), file=gen_mp, flush=True)
print('closing files', flush=True)
bus_mp.close()
gen_mp.close()
sys_mp.close()
op.close()
vp.close()
print('finalizing FNCS', flush=True)
fncs.finalize()
