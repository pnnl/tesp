# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: tso_psst_f.py

import os
import math
import json
import logging as log
import numpy as np
import pandas as pd
import pypower.api as pp
import psst.cli as pst
import tesp_support.fncs as fncs
from copy import deepcopy
from datetime import datetime

from .helpers import parse_mva
from .tso_helpers import load_json_case, make_dictionary, dist_slack
from .metrics_collector import MetricsStore, MetricsCollector


def make_generator_plants(ppc, renewables):
    gen = ppc['gen']
    genFuel = ppc['genfuel']
    plants = {}
    for i in range(gen.shape[0]):
        busnum = int(gen[i, 0])
        if genFuel[i][0] in renewables:
            MW = float(gen[i, 8])
            unRespMW = [0] * 48
            plants[str(genFuel[i][2])] = [busnum, MW, unRespMW, genFuel[i][2]]
    return plants


def tso_psst_loop_f(casename):

    def scucDAM(data):
        c, ZonalDataComplete, priceSenLoadData = pst.read_model(data.strip("'"))
        if day > -1:
            model = pst.build_model(c, ZonalDataComplete=ZonalDataComplete, PriceSenLoadData=priceSenLoadData, Op='scuc')
            model.solve(solver=solver)
            instance = model._model

            uc = os.path.join(output_Path, file_time + "uc.dat")
            with open(uc, 'w') as outfile:
                results = {}
                for g in instance.Generators.value:
                    for t in instance.TimePeriods:
                        results[(g, t)] = instance.UnitOn[g, t]

                for g in sorted(instance.Generators.value):
                    outfile.write("%s\n" % str(g).ljust(8))
                    for t in sorted(instance.TimePeriods):
                        outfile.write("% 1d \n" % (int(results[(g, t)].value + 0.5)))

            uc_df = pst.read_unit_commitment(uc.strip("'"))
        else:
            uc_df = write_default_schedule()
        c.gen_status = uc_df.astype(int)

        model = pst.build_model(c, ZonalDataComplete=ZonalDataComplete, PriceSenLoadData=priceSenLoadData)
        outcomes = model.solve(solver=solver)
        instance = model._model

        sum_lmp = 0.0
        DA_LMPs = [[0 for _ in range(hours_in_a_day)] for _ in range(total_bus_num)]
        for h, r in model.results.lmp.iterrows():
            for b, lmp in sorted(r.iteritems()):
                bn = int(b[3:])
                if lmp is None:
                    lmp = 0
                else:
                    lmp = abs(lmp)
                sum_lmp += lmp
                DA_LMPs[bn - 1][h] = round(lmp, 4)  # publishing $/kwh/p.u.h

        if sum_lmp <= 0:
            log.warning("WARNING: Writing out possible unsolved DA Case")
            fle = os.path.join(output_Path, str(day) + "_dam.dat")
            os.rename(psst_case, fle)

        dispatch = {}
        if outcomes[1] == 'optimal':
            status = True
            for g in sorted(instance.Generators.value):
                dispatch[g] = []
                for t in sorted(instance.TimePeriods):
                    dispatch[g].append(instance.PowerGenerated[g, t].value * baseS)
        else:
            status = False
            if da_lmps != {}:
                log.warning('Exception: unable to obtain LMPS and dispatch from PSST')
                log.warning('Using previous day schedule, dispatch, and LMPs')
                uc_df = da_schedule
                DA_LMPs = da_lmps
                dispatch = da_dispatch
            else:
                log.critical('ERROR - No DA starting point')
                exit()

        for ii in range(dsoBus.shape[0]):
            fncs.publish('lmp_da_' + str(ii + 1), json.dumps(DA_LMPs[ii]))
            row = DA_LMPs[ii]
            da_lmp_store.append_data(
                ts,
                'da_lmp{}'.format(str(ii+1)),
                row[0], row[1], row[2], row[3], row[4], row[5],
                row[6], row[7], row[8], row[9], row[10], row[11],
                row[12], row[13], row[14], row[15], row[16], row[17],
                row[18], row[19], row[20], row[21], row[22], row[23]
            )

        # log.debug("DA line power")
        # log.debug(model.results.line_power)
        for ii in range(branch.shape[0]):
            row = []
            limit = branch[ii, 5] / baseS
            for t in sorted(instance.TimePeriods):
                row.append(instance.LinePower[ii + 1, t].value / limit)
            da_line_store.append_data(
                ts,
                'da_line{}'.format(str(ii+1)),
                row[0], row[1], row[2], row[3], row[4], row[5],
                row[6], row[7], row[8], row[9], row[10], row[11],
                row[12], row[13], row[14], row[15], row[16], row[17],
                row[18], row[19], row[20], row[21], row[22], row[23]
            )

        for g in dispatch:
            row = dispatch[g]
            da_gen_q_store.append_data(
                ts,
                'da_gen_q{}'.format(str(g)),
                row[0], row[1], row[2], row[3], row[4], row[5],
                row[6], row[7], row[8], row[9], row[10], row[11],
                row[12], row[13], row[14], row[15], row[16], row[17],
                row[18], row[19], row[20], row[21], row[22], row[23]
            )

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

        lseDispatch = {}
        if len(priceSenLoadData) != 0:
            for ld in sorted(instance.PriceSensitiveLoads.value):
                lseDispatch[ld] = []
                for t in sorted(instance.TimePeriods):
                    lseDispatch[ld].append(instance.PSLoadDemand[ld, t].value)
                    # log.debug(str(ld) + " cleared quantity for hour " + str(t) + " --> " + str(instance.PSLoadDemand[ld, t].value))
            for ii in range(dsoBus.shape[0]):
                bus_num = ii + 1
                gld_scale = float(dsoBus[ii, 2])
                lse = 'LSE' + str(bus_num)
                try:
                    row = lseDispatch[lse]
                except:
                    # log.debug("LSE "+str(bus_num) + " is not price sensitive, so returning zero for it")
                    row = np.zeros(24).tolist()  # hard-coded to be 24
                for z in range(len(row)):
                    if row[z] is None:
                        row[z] = 0
                    row[z] = (unRespMW[ii][z] + (row[z] / gld_scale * baseS)) * gld_scale
                fncs.publish('cleared_q_da_' + str(bus_num), json.dumps(row))
                da_q_store.append_data(
                    ts,
                    'da_q{}'.format(str(ii+1)),
                    row[0], row[1], row[2], row[3], row[4], row[5],
                    row[6], row[7], row[8], row[9], row[10], row[11],
                    row[12], row[13], row[14], row[15], row[16], row[17],
                    row[18], row[19], row[20], row[21], row[22], row[23]
                )
        else:
            for ii in range(dsoBus.shape[0]):
                row = []
                bus_num = ii + 1
                gld_scale = float(dsoBus[ii, 2])
                for z in range(24):
                    if dso_bid:
                        row.append((respMaxMW[ii][z] + unRespMW[ii][z]) * gld_scale)
                    else:
                        row.append(gld_load[bus_num]['pcrv'])
                fncs.publish('cleared_q_da_' + str(bus_num), json.dumps(row))
                da_q_store.append_data(
                    ts,
                    'da_q{}'.format(str(bus_num)),
                    row[0], row[1], row[2], row[3], row[4], row[5],
                    row[6], row[7], row[8], row[9], row[10], row[11],
                    row[12], row[13], row[14], row[15], row[16], row[17],
                    row[18], row[19], row[20], row[21], row[22], row[23]
                )

        return status, uc_df, dispatch, DA_LMPs

    def scedRTM(data, uc_df):
        c, ZonalDataComplete, priceSenLoadData = pst.read_model(data.strip("'"))
        c.gen_status = uc_df.astype(int)

        model = pst.build_model(c, ZonalDataComplete=ZonalDataComplete, PriceSenLoadData=priceSenLoadData, Op='sced')
        outcomes = model.solve(solver=solver)
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

        sum_lmp = 0.0
        RT_LMPs = [[0 for _ in range(TAU)] for _ in range(total_bus_num)]
        for h, r in model.results.lmp.iterrows():
            for b, lmp in sorted(r.iteritems()):
                bn = int(b[3:])
                if lmp is None:
                    lmp = 0
                else:
                    lmp = abs(lmp)
                sum_lmp += lmp
                RT_LMPs[bn - 1][h] = round(lmp * 12, 4)  # publishing  $/kwh/p.u.h
            if h == TAU:
                break

        if sum_lmp <= 0:
            log.warning("WARNING: Writing out possible unsolved RT Case")
            temp = os.path.join(output_Path, print_time + "rtm.dat")
            os.rename(psst_case, temp)
            temp = os.path.join(output_Path, str(day) + "_" + str(hour) + "_uc.dat")
            uc = open(temp, 'w')
            print(rt_schedule, file=uc)
            uc.close()

        dispatch = {}
        if outcomes[1] == 'optimal':
            status = True
            for g in sorted(instance.Generators.value):
                dispatch[g] = []
                for t in sorted(instance.TimePeriods):
                    dispatch[g].append(instance.PowerGenerated[g, t].value * baseS)
                    if t == TAU:
                        break
        else:
            status = False
            if rt_lmps != {}:
                log.warning('Exception: unable to obtain LMPS and dispatch from PSST')
                log.warning('Using previous day schedule, dispatch, and LMPs')
                RT_LMPs = rt_lmps
                for ii in range(numGen):
                    if genFuel[ii][0] not in renewables:
                        name = "GenCo" + str(ii + 1)
                        dispatch[name] = []
                        dispatch[name].append(gen[ii, 1])
            else:
                log.critical('ERROR - No RT starting point')
                exit()

        # set the lmps and generator dispatch and publish
        for ii in range(bus.shape[0]):
            fncs.publish('lmp_rt_' + str(ii + 1), json.dumps(RT_LMPs[ii]))  # publishing $/kwh
            bus[ii, 13] = RT_LMPs[ii][0]
        for ii in range(numGen):
            if genFuel[ii][0] not in renewables:
                name = "GenCo" + str(ii + 1)
                gen[ii, 1] = dispatch[name][0]
            # else:
                # dispatch for renewables i.e curtail
                # gen[ii, 1] this was set in rt_curtail_renewables()

        # log.debug("RT line power")
        # log.debug(model.results.line_power)
        for ii in range(branch.shape[0]):
            row = []
            limit = branch[ii, 5] / baseS
            for t in sorted(instance.TimePeriods):
                row.append(instance.LinePower[ii + 1, t].value / limit)
            rt_line_store.append_data(
                ts,
                'rt_line{}'.format(str(ii+1)),
                row[0]
            )

        #   f.write("VOLTAGE_ANGLES\n")
        #   for bus in sorted(instance.Buses):
        #     for t in instance.TimePeriods:
        #       f.write('{} {} : {}\n'.format(str(bus), str(t + 1), str(round(instance.Angle[bus, t].value, 3))))
        #   f.write("END_VOLTAGE_ANGLES\n")

        lseDispatch = {}
        if len(priceSenLoadData) != 0:
            for ld in sorted(instance.PriceSensitiveLoads.value):
                lseDispatch[ld] = []
                for t in sorted(instance.TimePeriods):
                    lseDispatch[ld].append(instance.PSLoadDemand[ld, t].value)

            for ii in range(dsoBus.shape[0]):
                bus_num = ii + 1
                gld_scale = float(dsoBus[ii, 2])
                lse = 'LSE' + str(bus_num)
                try:
                    row = lseDispatch[lse]
                except:
                    # log.debug("LSE " + str(ii+1) + " is not price sensitive, so returning zero for it")
                    row = np.zeros(TAU).tolist()

                for z in range(len(row)):
                    ld = gld_load[bus_num]['unresp']
                    if ld <= 0:                          # no bid add the unresp through tape event
                        ld = gld_load[bus_num]['p']
                    if row[z] is None:
                        row[z] = 0
                    row[z] = (ld + (row[z] / gld_scale * baseS)) * gld_scale
                fncs.publish('cleared_q_rt_' + str(bus_num), json.dumps(row[0]))
                # log.debug('Bus ' + str(ii+1) + ' cleared - [fixed, flex] ' + '[' + str(gld_load[ii+1]['unresp']) + ', ' + str(row[0] - gld_load[ii+1]['unresp']) + ']')
                rt_q_store.append_data(
                    ts,
                    'rt_q{}'.format(str(ii+1)),
                    row[0]
                )
        else:
            for ii in range(dsoBus.shape[0]):
                bus_num = ii + 1
                gld_scale = float(dsoBus[ii, 2])
                if dso_bid:
                    ld = gld_load[bus_num]['unresp']
                    if ld <= 0:                           # no bid add the unresp through tape event
                        ld = gld_load[bus_num]['p']
                    ld = (ld + gld_load[bus_num]['resp_max']) * gld_scale
                else:
                    ld = gld_load[bus_num]['pcrv']

                row = []
                for z in range(TAU):
                    row.append(ld)
                fncs.publish('cleared_q_rt_' + str(bus_num), json.dumps(row[0]))
                rt_q_store.append_data(
                    ts,
                    'rt_q{}'.format(str(bus_num)),
                    row[0]
                )

        return status, dispatch, RT_LMPs

    def write_rtm_schedule(uc_df1):
        data = []
        hh = hour + 1
        for jj in range(TAU):
            rr = {}
            for ii in range(numGen):
                if genFuel[ii][0] not in renewables:
                    name = "GenCo" + str(ii + 1)
                    if name in uc_df1.keys():
                        rr[name] = uc_df1.at[hh, name]
            data.append(rr)
        df = pd.DataFrame(data, index=range(1, 2))
        return df

    def write_default_schedule():
        data = []
        for jj in range(24):
            rr = {}
            for ii in range(numGen):
                if genFuel[ii][0] not in renewables:
                    name = "GenCo" + str(ii + 1)
                    rr[name] = 1
            data.append(rr)
        df = pd.DataFrame(data)
        return df

    def da_curtail_renewables(tot_gen_down, tot_gen_up):
        log.info('Total TSO ramp up: ' + str(tot_gen_up) + ', Total TSO ramp down: ' + str(tot_gen_down))

        da_curtail = [[]] * hours_in_a_day
        for jj in range(hours_in_a_day):
            total_neg = 0
            total_dso = 0
            neg_loads = [0] * (bus.shape[0] + 1)
            for key, row in generator_plants.items():
                neg_loads[row[0]] += float(row[2][jj+24]) / baseS
                total_neg += float(row[2][jj+24]) / baseS

            dso_loads = []
            nobid_unresp_da[jj] = []
            for ii in range(bus.shape[0]):
                bus_num = ii + 1
                if bus_num <= dsoBus.shape[0]:      # only low voltage bus and with dso
                    total = unRespMW[ii][jj]
                    if not priceSensLoad:
                        total += respMaxMW[ii][jj]
                    if total == 0:                   # no unresp bid add through tape event
                        total = gld_load_hist[bus_num][jj+24]
                        nobid_unresp_da[jj].append(total)
                    total = (total * float(dsoBus[ii][2])) / baseS
                else:                                # high voltage buses are added
                    total = unRespMW[ii][jj] / baseS
                dso_loads.append(total)
                total_dso += total

            log.debug('DA Total Renewables: ' + str(total_neg))
            log.debug('DA Total DSO Load: ' + str(total_dso))

            cnt = 0
            curtail = 1.0
            if used_curtail:
                # in dsot we want 100 MVA thermal generation, no renewables, min nuclear 43.2 MVA
                if total_dso - total_neg < genLowerLimit:
                    while True:
                        cnt += 1
                        curtail = 1.0 - (0.01 * cnt)
                        curtail_renew = total_neg * curtail
                        if total_dso - curtail_renew < genLowerLimit or cnt == 100:
                            break

                while True:
                    tot_dso = 0.0
                    da_curtail[jj] = []
                    for ii in range(bus.shape[0]):
                        bus_num = ii + 1
                        total = dso_loads[ii] - (neg_loads[bus_num] * curtail)
                        tot_dso += total
                        da_curtail[jj].append(total)

                    tot_res_up = tot_dso + (tot_dso * reserveUp)
                    tot_res_down = tot_dso - (tot_dso * reserveDown)
                    if tot_gen_down <= tot_res_down and tot_res_up <= tot_gen_up:
                        log.debug('We are great')
                        break

                    cnt += 1
                    last = curtail
                    curtail = 1.0 - (0.01 * cnt)
                    if curtail < 0:
                        curtail = last
                        log.debug('May not solve, GLD Load:\n ' + str(gld_load))
                        break
            else:
                tot_dso = 0.0
                da_curtail[jj] = []
                for ii in range(bus.shape[0]):
                    bus_num = ii + 1
                    total = dso_loads[ii] - neg_loads[bus_num]
                    tot_dso += total
                    da_curtail[jj].append(total)

            log.info('DA Hour: ' + str(jj + 1))
            log.info('Total DSO Load: ' + str(total_dso))
            log.info('Total DSO to PSST: ' + str(tot_dso) + ', Total Renewables: ' + str(total_neg))
            log.info('Used Renewables:' + '{: .3f}'.format(total_neg*curtail) + ', Percent:' + '{: .0f}'.format(curtail*100))
        return da_curtail

    def rt_curtail_renewables(znumGen, zgenFuel, zgen, tot_gen_down, tot_gen_up):
        log.info('Total TSO ramp up: ' + str(tot_gen_up) + ', Total TSO ramp down: ' + str(tot_gen_down))

        total_neg = 0
        total_dso = 0
        neg_loads = [0] * (bus.shape[0] + 1)
        for key, row in generator_plants.items():
            for jj in range(znumGen):
                if zgenFuel[jj][2] == row[3]:
                    neg_loads[row[0]] += zgen[jj, 1] / baseS
                    total_neg += zgen[jj, 1] / baseS

        dso_loads = []
        for ii in range(bus.shape[0]):
            total = 0.0
            bus_num = ii + 1
            if bus_num <= dsoBus.shape[0]:  # only low voltage bus and with dso
                total = gld_load[bus_num]['unresp']
                if not priceSensLoad:
                    total += gld_load[bus_num]['resp_max']
                if total == 0:  # no unresp bid add through tape event
                    total = gld_load[bus_num]['p']
                    nobid_unresp_rt[ii] = total
                total = (total * float(dsoBus[ii][2])) / baseS
            # else:                                       # high voltage buses are added
            # where is this in real time
            dso_loads.append(total)
            total_dso += total

        log.debug('RT Total Renewables: ' + str(total_neg))
        log.debug('RT Total DSO Load: ' + str(total_dso))

        cnt = 0
        curtail = 1.0
        if used_curtail:
            # in dost we want 100 MVA thermal generation, no renewables, min nuclear 43.2 MVA
            if total_dso - total_neg < genLowerLimit:
                while True:
                    cnt += 1
                    curtail = 1.0 - (0.01 * cnt)
                    curtail_renew = total_neg * curtail
                    if total_dso - curtail_renew < genLowerLimit or cnt == 100:
                        break

            while True:
                tot_dso = 0.0
                rt_curtail = []
                for ii in range(bus.shape[0]):
                    bus_num = ii + 1
                    total = dso_loads[ii] - (neg_loads[bus_num] * curtail)
                    tot_dso += total
                    rt_curtail.append(total)

                tot_res_up = tot_dso + (tot_dso * 0.0001)
                tot_res_down = tot_dso - (tot_dso * 0.0001)
                # tot_res_up = tot_dso + (tot_dso * reserveUp * RTDur_in_hrs)
                # tot_res_down = tot_dso - (tot_dso * reserveDown * RTDur_in_hrs)
                if tot_gen_down <= tot_res_down and tot_res_up <= tot_gen_up:
                    log.debug('We are great')
                    break

                cnt += 1
                last = curtail
                curtail = 1.0 - (0.01 * cnt)
                if curtail < 0:
                    curtail = last
                    log.debug('May not solve, GLD Load:\n ' + str(gld_load))
                    break

            # Set renewable generation for curtailment
            tot_lost = 0
            for key, row in generator_plants.items():
                for jj in range(znumGen):
                    if zgenFuel[jj][2] == row[3]:
                        tot_lost += zgen[jj, 1] * (1.0 - curtail)
                        zgen[jj, 1] = zgen[jj, 1] * curtail
        else:
            rt_curtail = []
            tot_dso = 0.0
            for ii in range(bus.shape[0]):
                bus_num = ii + 1
                total = dso_loads[ii] - neg_loads[bus_num]
                tot_dso += total
                rt_curtail.append(total)

        log.info('Total DSO Load: ' + str(total_dso))
        log.info('Total DSO to PSST: ' + str(tot_dso) + ', Total Renewables: ' + str(total_neg))
        log.info('Used Renewables:' + '{: .3f}'.format(total_neg*curtail) + ', Percent:' + '{: .0f}'.format(curtail*100))
        return rt_curtail

    def write_psst_file(fname, dayahead, zgen, zgenCost, zgenFuel, znumGen):
        fp = open(fname, 'w')
        print('# Written by tso_psst_f.py, format: psst\n', file=fp)
        print('set StageSet := FirstStage SecondStage ;\n', file=fp)
        print('set CommitmentTimeInStage[FirstStage] := 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 ;', file=fp)
        print('set CommitmentTimeInStage[SecondStage] := ;\n', file=fp)
        print('set GenerationTimeInStage[FirstStage] := ;', file=fp)
        print('set GenerationTimeInStage[SecondStage] := 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 ;', file=fp)
        print('', file=fp)

        writeLine = 'set Buses :='
        for ii in range(bus.shape[0]):
            writeLine = writeLine + ' Bus' + str(ii + 1)
        print(writeLine + ' ;', file=fp)
        print('', file=fp)

        print('set TransmissionLines :=', file=fp)
        for ii in range(branch.shape[0]):
            if branch[ii, 1] > branch[ii, 0]:
                fbus = int(branch[ii, 0])
                tbus = int(branch[ii, 1])
            else:
                fbus = int(branch[ii, 1])
                tbus = int(branch[ii, 0])
            print('Bus' + str(fbus) + ' Bus' + str(tbus), file=fp)
        print(';\n', file=fp)

        print('param NumTransmissionLines :=', str(branch.shape[0]), ';\n', file=fp)

        print('param: BusFrom BusTo ThermalLimit Reactance :=', file=fp)
        for ii in range(branch.shape[0]):
            if branch[ii, 1] > branch[ii, 0]:
                fbus = int(branch[ii, 0])
                tbus = int(branch[ii, 1])
            else:
                fbus = int(branch[ii, 1])
                tbus = int(branch[ii, 0])
            #  // Convert  MaxCap  from SI to  PU
            limit = branch[ii, 5] / baseS
            #  // Convert  reactance  from SI to  PU, x(pu) = x / Zo = x / (Vo ^ 2 / So) = (x * So) / Vo ^ 2
            reactance = (branch[ii, 3] * baseS) / (baseV_dict[int(branch[ii, 0])]*baseV_dict[int(branch[ii, 0])])
            print(str(ii + 1) + ' Bus' + str(fbus) + ' Bus' + str(tbus) +
                  '{: .2f}'.format(limit) + '{: .2E}'.format(reactance), file=fp)
        print(';\n', file=fp)

        writeLine = 'set ThermalGenerators :='
        for ii in range(znumGen):
            if zgenFuel[ii][0] not in renewables:
                writeLine = writeLine + ' GenCo' + str(ii + 1)
        print(writeLine, ';', file=fp)
        for ii in range(bus.shape[0]):
            writeLine = 'set ThermalGeneratorsAtBus[Bus' + str(ii + 1) + '] :='
            for jj in range(znumGen):
                if int(zgen[jj, 0]) == ii + 1 and zgenFuel[jj][0] not in renewables:
                    writeLine = writeLine + ' GenCo' + str(jj + 1)
            print(writeLine, ';', file=fp)
        print('', file=fp)

        print('param BalPenPos :=', str(priceCap), ';\n', file=fp)
        print('param BalPenNeg :=', str(priceCap), ';\n', file=fp)

        # psst time period length is in hours
        if (dayahead):
            print('param TimePeriodLength := 1 ;\n', file=fp)
            print('param NumTimePeriods := ', str(hours_in_a_day), ';\n', file=fp)
        else:
            print('param TimePeriodLength :=', str(RTDur_in_hrs), ';\n', file=fp)
            print('param NumTimePeriods :=', str(TAU), ';\n', file=fp)

        print('param: PowerGeneratedT0 ScaledUnitOnT0State InitialTimeON InitialTimeOFF '
              'MinimumPowerOutput MaximumPowerOutput ScaledMinimumUpTime ScaledMinimumDownTime '
              'ScaledRampUpLimit ScaledRampDownLimit ScaledStartupRampLimit ScaledShutdownRampLimit '
              'ScaledColdStartTime ColdStartCost HotStartCost ShutdownCost :=', file=fp)

        renew_avail = 0
        P_avail = 0
        Pmin_avail = 0
        Pmax_avail = 0
        for ii in range(znumGen):
            if zgenFuel[ii][0] in renewables:
                renew_avail += zgen[ii][1] / baseS
            else:
                name = 'GenCo' + str(ii + 1)
                Pmax = zgen[ii, 8] / baseS
                Pmin = zgen[ii, 9] / baseS
                if Pmin > Pmax:
                    log.debug("ERROR: Some thing is wrong with " + name + ' in ' + fname)
                    log.debug('=====: Pmax:' + '{: .4}'.format(Pmax) + ', Pmin:' + '{: .4}'.format(Pmin))
                    Pmax = Pmin

                # TODO fill out gen min up an down in parameters
                minDn = 0
                minUp = 0

                # unitOnT0 State counter in hours set in day ahead schedule
                unitOnT0 = zgenFuel[ii][3]
                powerT0 = zgen[ii][1] / baseS

                if dayahead:
                    # scale ramp up and down for the generator
                    ramp = zgen[ii][16] * 60.0 / baseS
                    if day == 1 and not priceSensLoad:
                        if 0 < powerT0:
                            unitOnT0 = 1
                else:
                    # scale ramp up and down for the generator
                    ramp = zgen[ii][16] * 5.0 / baseS

                if unitOnT0 > 0:
                    if powerT0 < Pmin:
                        powerT0 = Pmin
                else:
                    if not dayahead:
                        powerT0 = 0

                if 0 < powerT0:
                    P_avail += powerT0
                    Pmin_avail += max(Pmin, powerT0 - ramp)
                    Pmax_avail += min(Pmax, powerT0 + ramp)
                    if unitOnT0 < 0:
                        log.info("WARNING: " + name + ' in ' + fname + ' might power off')
                        log.info('=====: powerT0:' + '{: .4}'.format(powerT0) + ', unitOnT0: ' + str(unitOnT0))

                print(name + '{: .6f}'.format(powerT0) + ' ' + str(unitOnT0) + ' 0 0' +
                      '{: .6f}'.format(Pmin) + '{: .6f}'.format(Pmax) + ' ' + str(minUp) + ' ' + str(minDn) +
                      '{: .6f}'.format(ramp) + '{: .6f}'.format(ramp) +
                      '{: .6f}'.format(ramp) + '{: .6f}'.format(ramp) +
                      ' 0' + '{: .6f}'.format(zgenCost[ii][1]) + '{: .6f}'.format(zgenCost[ii][1]) +
                      '{: .6f}'.format(zgenCost[ii][2]), file=fp)
                # Set gen = powerT0 level
                zgen[ii][1] = powerT0 * baseS

        print(' ;\n', file=fp)
        log.info("TSO Power " + str(P_avail))

        print('param: ID atBus EndPointSoc MaximumEnergy NominalRampDownInput NominalRampUpInput '
              'NominalRampDownOutput NominalRampUpOutput MaximumPowerInput MinimumPowerInput '
              'MaximumPowerOutput MinimumPowerOutput MinimumSoc EfficiencyEnergy :=', file=fp)
        print(' ;\n', file=fp)

        print('param StorageFlag := 0.0 ;\n', file=fp)
        if dso_bid:
            print('param PriceSenLoadFlag :=', str(priceSensLoad), ';\n', file=fp)
        else:
            print('param PriceSenLoadFlag := 0;\n', file=fp)

        if dayahead:
            print('param DownReservePercent :=', str(reserveDown), ';\n', file=fp)
            print('param UpReservePercent :=', str(reserveUp), ';\n', file=fp)
        else:
            # scaled reserve to 5 min
            # possibly a fudge factor since we run can restart with a new day ahead
            print('param DownReservePercent :=', str(0.0001), ';\n', file=fp)
            print('param UpReservePercent :=', str(0.0001), ';\n', file=fp)
            # print('param DownReservePercent :=', str(reserveDown * RTDur_in_hrs), ';\n', file=fp)
            # print('param UpReservePercent :=', str(reserveUp * RTDur_in_hrs), ';\n', file=fp)

        print('param HasZonalReserves :=', str(zonalReserves), ';\n', file=fp)

        if zonalReserves:
            print('param NumberOfZones :=', str(len(zones)), ';\n', file=fp)
            writeLine = 'set Zones :='
            for jj in range(len(zones)):
                writeLine = writeLine + ' Zone' + str(jj + 1)
            print(writeLine, ';\n', file=fp)

            print('param: Buses ReserveDownZonalPercent ReserveUpZonalPercent :=', file=fp)
            for jj in range(len(zones)):
                buses = ''
                for ii in range(bus.shape[0]):
                    if zones[jj][0] == bus[ii, 10]:
                        if buses == '':
                            buses = 'Bus' + str(ii + 1) + ','
                        else:
                            buses = buses + 'Bus' + str(ii + 1) + ','
                print('Zone' + str(jj + 1) + ' ' + buses +
                      '{: .1f}'.format(zones[jj][2]) + '{: .1f}'.format(zones[jj][3]), file=fp)
            print(';\n', file=fp)

        # Market ie bidding from a dso (dsoBus) and bus
        # in dsot there are multiple bus' for a dso
        if dso_bid:
            if dayahead:
                net = da_curtail_renewables(Pmin_avail, Pmax_avail)
            else:
                net = rt_curtail_renewables(znumGen, zgenFuel, zgen, Pmin_avail, Pmax_avail)

            print('param: NetFixedLoadForecast :=', file=fp)
            for ii in range(bus.shape[0]):
                bus_num = ii + 1
                if dayahead:                                      # 12am to 12am
                    for jj in range(hours_in_a_day):
                        print('Bus' + str(bus_num) + ' ' + str(jj + 1) + ' {:.5f}'.format(net[jj][ii]), file=fp)
                else:                                             # real time
                    print('Bus' + str(bus_num) + ' 1' + ' {:.5f}'.format(net[ii]), file=fp)
                    # log.debug("RT Fixed Load LSE_" + str(bus_num) + ", MW :" + str(net[ii]))
                print('', file=fp)
            print(';\n', file=fp)

            if priceSensLoad:
                writeLine = 'set PricesSensitiveLoadNames :='
                for ii in range(dsoBus.shape[0] - 1):
                    writeLine = writeLine + ' LSE' + str(ii + 1) + ','
                print(writeLine + ' LSE' + str(ii + 2), ';\n', file=fp)

                print('param: Name ID atBus hourIndex d e f SLMax NS :=', file=fp)
                for ii in range(dsoBus.shape[0]):
                    bus_num = ii + 1
                    gld_scale = float(dsoBus[ii][2])
                    if dayahead:                                # 12am to 12am
                        for jj in range(hours_in_a_day):
                            print('LSE' + str(bus_num) + ' ' + str(bus_num) + ' Bus' + str(bus_num) +
                                  ' ' + str(jj + 1) +
                                  ' {: .5f}'.format(respC0[ii][jj]) +
                                  ' {: .5f}'.format(respC1[ii][jj] / gld_scale) +
                                  ' {: .5f}'.format(respC2[ii][jj] / (gld_scale * gld_scale)) +
                                  ' {: .5f}'.format((respMaxMW[ii][jj] * gld_scale) / baseS) +
                                  ' ' + str(NS), file=fp)
                        print('', file=fp)
                    else:                                         # real time
                        for jj in range(TAU):
                            print('LSE' + str(bus_num) + ' ' + str(bus_num) + ' Bus' + str(bus_num) +
                                  ' ' + str(jj + 1) +
                                  ' {: .5f}'.format(gld_load[bus_num]['c0']) +
                                  ' {: .5f}'.format(gld_load[bus_num]['c1'] / gld_scale) +
                                  ' {: .5f}'.format(gld_load[bus_num]['c2'] / (gld_scale * gld_scale)) +
                                  ' {: .5f}'.format((gld_load[bus_num]['resp_max'] * gld_scale) / baseS) +
                                  ' ' + str(NS), file=fp)
                            # log.debug("RT Max Flex Load LSE_" + str(bus_num) + ", MW :" + str(gld_load[bus_num]['resp_max']/ baseS))
                        print('', file=fp)
                print(';\n', file=fp)
        else:
            # no bid using gld_load (tape player/gridlab)
            print('param: NetFixedLoadForecast :=', file=fp)
            for ii in range(bus.shape[0]):
                bus_num = ii + 1
                if dayahead:
                    for jj in range(hours_in_a_day):
                        ndg = 0
                        for key, row in generator_plants.items():
                            if row[0] == bus_num:
                                ndg += float(row[2][jj+24])
                        if bus_num <= dsoBus.shape[0]:
                            net = ref_load_hist[bus_num][jj+24] - ndg  # uses history
                        else:
                            net = - ndg
                        print('Bus' + str(bus_num) + ' ' + str(jj + 1) + ' {:.4f}'.format(net / baseS), file=fp)
                else:
                    ndg = 0
                    for key, row in generator_plants.items():
                        if row[0] == bus_num:
                            for jj in range(znumGen):
                                if zgenFuel[jj][2] == row[3]:
                                    ndg += zgen[jj, 1]
                    if bus_num <= dsoBus.shape[0]:
                        net = gld_load[bus_num]['pcrv'] - ndg
                    else:
                        net = - ndg
                    for jj in range(TAU):
                        print('Bus' + str(bus_num) + ' ' + str(jj + 1) + ' {:.4f}'.format(net / baseS), file=fp)
                print('', file=fp)
            print(';\n', file=fp)

        print('param: a b c NS :=', file=fp)
        for ii in range(znumGen):
            if zgenFuel[ii][0] not in renewables:
                c0 = zgenCost[ii, 6]
                c1 = zgenCost[ii, 5]
                c2 = zgenCost[ii, 4]
                ns = '1'
                if c0 > 0 and c1 > 0 and c2 > 0:
                    ns = str(NS)
                print('GenCo' + str(ii + 1) + '{: .5f}'.format(c0) +
                      '{: .5f}'.format(c1) + '{: .5f}'.format(c2) + ' ' + ns, file=fp)
        print(';\n', file=fp)
        fp.close()

    def update_cost_and_load():
        # update cost coefficients, set dispatchable load, put unresp load on bus
        bus_total = {'pcrv': 0, 'p': 0, 'p_r': 0, 'unresp': 0, 'resp_max': 0}
        for row in dsoBus:
            busnum = int(row[0])
            gld_scale = float(row[2])
            load = gld_load[busnum]
            log.debug("Bus" + str(busnum) + " " + str(load))

            # track the latest bid in the metrics and power
            if load['unresp'] > 0:  # we have a bid
                load['p'] = load['unresp']
                load['q'] = load['unresp'] * 0.57
                unresp = load['unresp'] * gld_scale
                resp_max = load['resp_max'] * gld_scale
                c2 = load['c2'] / gld_scale * gld_scale
                c1 = load['c1'] / gld_scale
                c0 = load['c0']
                deg = load['deg']
            else:
                unresp = load['p'] * gld_scale
                resp_max = 0
                c2 = 0
                c1 = 0
                c0 = 0
                deg = 0

            load['pcrv'] = load['p'] * gld_scale
            load['qcrv'] = load['q'] * gld_scale
            bus[busnum - 1, 2] = load['pcrv']
            bus[busnum - 1, 3] = load['qcrv']

            bus_total['pcrv'] += load['pcrv']
            bus_total['p'] += load['p']
            bus_total['p_r'] += load['p_r']
            bus_total['unresp'] += load['unresp']
            bus_total['resp_max'] += load['resp_max']

            bus_accum[str(busnum)][8] = unresp
            bus_accum[str(busnum)][9] = resp_max
            bus_accum[str(busnum)][10] = c1
            bus_accum[str(busnum)][11] = c2

            log.debug("Turn on responsive / dispatchable loads")
            for idx in range(numGen, gen.shape[0]):
                if genFuel[idx][2] == load['genidx']:
                    log.debug('Bus' + str(busnum) + ', Gen' + str(idx))
                    gen[idx, 9] = -resp_max
                    if deg == 2:
                        genCost[idx, 3] = 3
                        genCost[idx, 4] = -c2
                        genCost[idx, 5] = c1
                    elif deg == 1:
                        genCost[idx, 3] = 2
                        genCost[idx, 4] = c1
                        genCost[idx, 5] = 0.0
                    else:
                        genCost[idx, 3] = 1
                        genCost[idx, 4] = 999.0
                        genCost[idx, 5] = 0.0
                    genCost[idx, 6] = c0
        log.info('Total ' + str(bus_total))

    def use_generator(add_gen_index, del_gen_index):
        for j in range(len(ugen)):
            for i in range(len(gen)):
                if ugenFuel[j][2] == genFuel[i][2]:
                    ugen[j] = gen[i]
                    ugenCost[j] = genCost[i]
                    ugenFuel[j] = genFuel[i]
                    break

        nGen = unumGen
        agen = []
        agenCost = []
        agenFuel = []
        for j in range(len(ugen)):
            if ugenFuel[j][2] in del_gen_index:
                nGen -= 1
                if ugenFuel[j][3] < 0:
                    ugenFuel[j][3] -= 1
                else:
                    ugenFuel[j][3] = -1
            else:
                agen.append(ugen[j])
                agenCost.append(ugenCost[j])
                agenFuel.append(ugenFuel[j])
        return np.array(agen), np.array(agenCost), agenFuel, nGen

    # Initialize the program
    try:
        try:
            hours_in_a_day = 24
            secs_in_a_hr = 3600

            ppc = load_json_case(casename + '.json')
            ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['opf_dc'], OPF_ALG_DC=200)  # dc for
            ppopt_regular = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['pf_dc'], PF_MAX_IT=20, PF_ALG=1)  # ac for power flow

            logger = log.getLogger()
            # logger.setLevel(log.INFO)
            logger.setLevel(log.WARNING)
            # logger.setLevel(log.DEBUG)
            log.info('starting tso loop...')

            if ppc['solver'] == 'cbc':
                ppc['gencost'][:, 4] = 0.0  # can't use quadratic costs with CBC solver

            # these have been aliased from case name .json file
            bus = ppc['bus']
            # bus: [[bus id, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin, LAM P, LAM Q]]
            # bus type: 1 = load, 2 = gen(PV) and 3 = swing
            branch = ppc['branch']
            # branch: [[from bus, to bus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax]]
            gen = ppc['gen']
            # gen: [[bus id, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin,(11 zeros)]]
            genCost = ppc['gencost']
            # gencost: [[2, startup, shutdown, 3, c2, c1, c0]]
            genFuel = ppc['genfuel']
            # genFuel: [[fuel type, fuel name, id, uniton]]
            zones = ppc['zones']
            # zones: [[zone id, name, ReserveDownZonalPercent, ReserveUpZonalPercent]]
            dsoBus = ppc['DSO']
            # DSO: [[bus id, name, gld_scale, Pnom, Qnom, curve_scale, curve_skew, Pinit, Qinit]]

            # Not being used at this time
            # UnitsOut: idx, time out[s], time back in[s]
            # BranchesOut: idx, time out[s], time back in[s]

            numGen = gen.shape[0]
            unumGen = gen.shape[0]
            renewables = ppc['renewables']

            # set configurations case name from .json file
            priceSensLoad = 0
            if ppc['priceSensLoad']:
                priceSensLoad = 1

            StartTime = ppc['StartTime']
            tmax = int(ppc['Tmax'])
            period = int(ppc['Period'])
            dt = int(ppc['dt'])
            swing_bus = int(ppc['swing_bus'])
            noScale = ppc['noScale']

            ames = ppc['ames']
            solver = ppc['solver']
            if pst.SOLVER is not None:
                solver = pst.SOLVER

            priceCap = 2 * ppc['priceCap']
            used_curtail = ppc['curtail']
            genLowerLimit = ppc['genLowerLimit']
            reserveDown = ppc['reserveDown']
            reserveUp = ppc['reserveUp']
            zonalReserves = ppc['zonalReserves']
            casefile = ppc['caseName']
            output_Path = ppc['outputPath']
            baseS = int(ppc['baseMVA'])     # base_S in ercot_8.json baseMVA
            baseV = int(bus[0, 9])          # base_V in ercot_8.json bus row 0-7, column 9, should be the same for all buses
            # create bus dictionary
            baseV_dict = {}
            for ibus in range(len(bus)):
                baseV_dict.update({int(bus[ibus, 0]): int(bus[ibus, 9])})
        finally:
            log.info('Finished reading settings')
        try:
            collector = MetricsCollector.factory(start_time=StartTime, write_hdf5=True)
            # create lists of (name, unit) pairs (order determines indices)
            bus_store = MetricsStore(
                name_units_pairs=[
                    ('LMP_P', 'USD/kwh'),
                    ('LMP_Q', 'USD/kvarh'),
                    ('PD', 'MW'),
                    ('QD', 'MVAR'),
                    ('Vang', 'deg'),
                    ('Vmag', 'pu'),
                    ('Vmax', 'pu'),
                    ('Vmin', 'pu'),
                    ('unresp', 'MW'),
                    ('resp_max', 'MW'),
                    ('c1', '$/MW'),
                    ('c2', '$/MW^2')
                ],
                file_string='bus_{}'.format(casefile),
                collector=collector,
            )
            gen_store = MetricsStore(
                name_units_pairs=[
                    ('Pgen', 'MW'),
                    ('Qgen', 'MVAR'),
                    ('LMP_P', 'USD/kwh')
                ],
                file_string='gen_{}'.format(casefile),
                collector=collector,
            )
            sys_store = MetricsStore(
                name_units_pairs=[
                    ('Ploss', 'MW'),
                    ('Converged', 'true/false')
                ],
                file_string='sys_{}'.format(casefile),
                collector=collector
            )
            da_lmp_store = MetricsStore(
                name_units_pairs=[
                    ('LMP_1', 'USD/kwh'), ('LMP_2', 'USD/kwh'), ('LMP_3', 'USD/kwh'), ('LMP_4', 'USD/kwh'),
                    ('LMP_5', 'USD/kwh'), ('LMP_6', 'USD/kwh'), ('LMP_7', 'USD/kwh'), ('LMP_8', 'USD/kwh'),
                    ('LMP_9', 'USD/kwh'), ('LMP_10', 'USD/kwh'), ('LMP_11', 'USD/kwh'), ('LMP_12', 'USD/kwh'),
                    ('LMP_13', 'USD/kwh'), ('LMP_14', 'USD/kwh'), ('LMP_15', 'USD/kwh'), ('LMP_16', 'USD/kwh'),
                    ('LMP_17', 'USD/kwh'), ('LMP_18', 'USD/kwh'), ('LMP_19', 'USD/kwh'), ('LMP_20', 'USD/kwh'),
                    ('LMP_21', 'USD/kwh'), ('LMP_22', 'USD/kwh'), ('LMP_23', 'USD/kwh'), ('LMP_24', 'USD/kwh')
                ],
                file_string='da_lmp_{}'.format(casefile),
                collector=collector,
            )
            da_line_store = MetricsStore(
                name_units_pairs=[
                    ('Line_1', 'line/limit'), ('Line_2', 'line/limit'), ('Line_3', 'line/limit'), ('Line_4', 'line/limit'),
                    ('Line_5', 'line/limit'), ('Line_6', 'line/limit'), ('Line_7', 'line/limit'), ('Line_8', 'line/limit'),
                    ('Line_9', 'line/limit'), ('Line_10', 'line/limit'), ('Line_11', 'line/limit'), ('Line_12', 'line/limit'),
                    ('Line_13', 'line/limit'), ('Line_14', 'line/limit'), ('Line_15', 'line/limit'), ('Line_16', 'line/limit'),
                    ('Line_17', 'line/limit'), ('Line_18', 'line/limit'), ('Line_19', 'line/limit'), ('Line_20', 'line/limit'),
                    ('Line_21', 'line/limit'), ('Line_22', 'line/limit'), ('Line_23', 'line/limit'), ('Line_24', 'line/limit')
                ],
                file_string='da_line_{}'.format(casefile),
                collector=collector,
            )
            da_gen_q_store = MetricsStore(
                name_units_pairs=[
                    ('ClearQ_1', 'MW'), ('ClearQ_2', 'MW'), ('ClearQ_3', 'MW'), ('ClearQ_4', 'MW'),
                    ('ClearQ_5', 'MW'), ('ClearQ_6', 'MW'), ('ClearQ_7', 'MW'), ('ClearQ_8', 'MW'),
                    ('ClearQ_9', 'MW'), ('ClearQ_10', 'MW'), ('ClearQ_11', 'MW'), ('ClearQ_12', 'MW'),
                    ('ClearQ_13', 'MW'), ('ClearQ_14', 'MW'), ('ClearQ_15', 'MW'), ('ClearQ_16', 'MW'),
                    ('ClearQ_17', 'MW'), ('ClearQ_18', 'MW'), ('ClearQ_19', 'MW'), ('ClearQ_20', 'MW'),
                    ('ClearQ_21', 'MW'), ('ClearQ_22', 'MW'), ('ClearQ_23', 'MW'), ('ClearQ_24', 'MW')
                ],
                file_string='da_gen_q_{}'.format(casefile),
                collector=collector,
            )
            da_q_store = MetricsStore(
                name_units_pairs=[
                    ('ClearQ_1', 'MW'), ('ClearQ_2', 'MW'), ('ClearQ_3', 'MW'), ('ClearQ_4', 'MW'),
                    ('ClearQ_5', 'MW'), ('ClearQ_6', 'MW'), ('ClearQ_7', 'MW'), ('ClearQ_8', 'MW'),
                    ('ClearQ_9', 'MW'), ('ClearQ_10', 'MW'), ('ClearQ_11', 'MW'), ('ClearQ_12', 'MW'),
                    ('ClearQ_13', 'MW'), ('ClearQ_14', 'MW'), ('ClearQ_15', 'MW'), ('ClearQ_16', 'MW'),
                    ('ClearQ_17', 'MW'), ('ClearQ_18', 'MW'), ('ClearQ_19', 'MW'), ('ClearQ_20', 'MW'),
                    ('ClearQ_21', 'MW'), ('ClearQ_22', 'MW'), ('ClearQ_23', 'MW'), ('ClearQ_24', 'MW')
                ],
                file_string='da_q_{}'.format(casefile),
                collector=collector,
            )
            rt_line_store = MetricsStore(
                name_units_pairs=[('Line', 'line/limit')],
                file_string='rt_line_{}'.format(casefile),
                collector=collector,
            )
            rt_q_store = MetricsStore(
                name_units_pairs=[('ClearQ', 'MW')],
                file_string='rt_q_{}'.format(casefile),
                collector=collector,
            )
        finally:
            log.info('metrics collection started')
        try:
            # set day_of_year
            s = datetime.strptime(ppc['StartTime'], '%Y-%m-%d %H:%M:%S')
            # uncomment below for debug outages for good testing day 7, hour 144
            # hour events 175,184,210,212...
            # s = datetime.strptime("2016-01-07 00:00:00", '%Y-%m-%d %H:%M:%S')
            day_of_year = s.timetuple().tm_yday

            idx_add = []
            idx_del = []
            planned_df = []
            unplanned_df = []
            planned_outage_dict = {}
            outages = ppc['outages']
            outagesUnplanned = ppc['outagesUnplanned']
            # read planned/unplanned outage data from csv file
            if outages:
                planned_df = pd.read_csv(ppc['planned'], index_col=0)
            if outagesUnplanned:
                unplanned_df = pd.read_csv(ppc['unplanned'], index_col=0)

            # initialize for variable wind/solar generator plants
            generator_plants = {}
            if ppc['genPower']:
                log.info('wind/solar power fluctuation requested')
                generator_plants = make_generator_plants(ppc, renewables)
            if len(generator_plants) < 1:
                log.info('there are no generator plants in this case')
                log.info('remove any wind/solar generator in generator fleet')
                ngen = []
                ngenCost = []
                ngenFuel = []
                for i in range(numGen):
                    if genFuel[i][0] not in renewables:
                        ngen.append(gen[i])
                        ngenCost.append(genCost[i])
                        ngenFuel.append(genFuel[i])
                ppc['gen'] = np.array(ngen)
                ppc['gencost'] = np.array(ngenCost)
                ppc['genfuel'] = ngenFuel
                gen = ppc['gen']
                genCost = ppc['gencost']
                genFuel = ppc['genfuel']
                numGen = gen.shape[0]
                unumGen = gen.shape[0]
        finally:
            log.info('Started outages and renewables')
        try:
            log.info('making dictionary for plotting later')
            make_dictionary(ppc)

            # initialize for day-ahead, OPF and time stepping
            ts = 0
            Pload = 0
            opf = False
            tnext_opf_pp = 0
            tnext_opf_ames = 0
            mn = 0
            hour = -1
            day = 1            
            lastDay = 1
            file_time = ''
            print_time = ''
            psst_case = ''

            MaxDay = tmax // 86400  # days in simulation
            RTDur_in_hrs = period / secs_in_a_hr
            RTOPDur = period // 60  # in minutes
            TAU = 1
            NS = 4  # number of segments
            dso_bid = False
            schedule = {}

            da_status = False
            da_status_cnt = 0
            da_run_cnt = 0
            da_percent = 0
            da_schedule = {}
            da_lmps = {}
            da_dispatch = {}
            last_dispatch = {}

            rt_status = False
            rt_status_cnt = 0
            rt_run_cnt = 0
            rt_percent = 0
            rt_schedule = {}
            rt_lmps = {}
            rt_dispatch = {}

            # listening to message objects key on bus number
            gld_load = {}
            gld_load_hist = {}
            ind_load_hist = {}
            ref_load_hist = {}
            nobid_unresp_da = [[]] * hours_in_a_day
            nobid_unresp_rt = [0] * dsoBus.shape[0]

            # we need to adjust Pmin downward so the OPF and PF can converge, or else implement unit commitment
            if not ames:
                for row in gen:
                    row[9] = 0.1 * row[8]

            # TODO: more efficient to concatenate outside a loop, lot to do
            # dsoBus[] (i.e. dso) is one to one with the bus[] to fnscBus length
            # bus length must be >= fnscBus length
            # bus must be in order from low(138) to high(345) voltage
            # dsoBus (DSOT, ERCOT stub) at this point only low voltage bus are used
            for i in range(dsoBus.shape[0]):
                busnum = i + 1
                gld_load_hist[busnum] = {}
                ind_load_hist[busnum] = {}
                ref_load_hist[busnum] = {}
                if noScale:
                    dsoBus[i, 2] = 1.0  # gld_scale
                # Sets a generator for each dso for responsive loads
                ppc['gen'] = np.concatenate(
                    (ppc['gen'], np.array([[busnum, 0, 0, 0, 0, 1, 250, 1, 0, -5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])))
                ppc['gencost'] = np.concatenate(
                    (ppc['gencost'], np.array([[2, 0, 0, 3, 0.0, 0.0, 0.0]])))
                ppc['genfuel'].append(['', '', -busnum, 0])

                gld_load[busnum] = {'pcrv': 0, 'qcrv': 0, 'p': 0, 'q': 0, 'p_r': 0, 'q_r': 0,
                                    'unresp': 0, 'resp_max': 0, 'c2': 0, 'c1': 0, 'c0': 0, 'deg': 0, 'genidx': -busnum}

            # needed to be re-aliased after np.concatenate
            gen = ppc['gen']
            genCost = ppc['gencost']
            genFuel = ppc['genfuel']

            # log.info('DSO Connections: bus, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew, Pinit, Qinit')
            # log.info(dsoBus)
            # log.info(gld_load)
            # log.info(gen)
            # log.info(genCost)

            # interval for metrics recording
            tnext_metrics = 0
            metrics_record_interval = ppc['Interval']
            tnext_write_metrics = metrics_record_interval

            loss_accum = 0
            conv_accum = True
            n_accum = 0
            bus_accum = {}
            gen_accum = {}

            for i in range(dsoBus.shape[0]):
                busnum = int(dsoBus[i, 0])
                bus_accum[str(busnum)] = [0, 0, 0, 0, 0, 0, 0, 99999.0, 0, 0, 0, 0]

            for i in range(gen.shape[0]):
                gen_accum[str(genFuel[i][2])] = [0, 0, 0]

            total_bus_num = bus.shape[0]
            last_unRespMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
            last_respMaxMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
            unRespMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
            respMaxMW = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
            respC2 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
            respC1 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
            respC0 = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
            resp_deg = np.zeros([total_bus_num, hours_in_a_day], dtype=float)
        finally:
            log.info('Finished initialize for day-ahead, time stepping variables')
            log.info('Finished initialize for bus and dso variables')
    finally:
        log.info('Finished initializing the program')

    fncs.initialize()

    # Set column header for output files
    line = "seconds, OPFconverged, TotalLoad, TotalGen, SwingGen"
    line2 = "seconds, PFConverged, TotalLoad, TotalGen, TotalLoss, SwingGen"
    for i in range(bus.shape[0]):
        line += ", " + "LMP" + str(i+1)
        line2 += ", " + "v" + str(i + 1)
    for i in range(numGen):
        if "wind" in genFuel[i][0]:
            line += ", wind" + str(genFuel[i][2])
        elif "nuclear" in genFuel[i][0]:
            line += ", nuc" + str(genFuel[i][2])
        elif "coal" in genFuel[i][0]:
            line += ", coal" + str(genFuel[i][2])
        elif "solar" in genFuel[i][0]:
            line += ", solar" + str(genFuel[i][2])
        else:
            line += ", gas" + str(genFuel[i][2])
    line += ", TotRenGen, TotRenGenHr, TotalGLDLoad, DALoad, DAGen, DAGen+TotRenGenHR, Percent, Status"

    op = open(os.path.join(output_Path, 'opf.csv'), 'w')
    vp = open(os.path.join(output_Path, 'pf.csv'), 'w')
    print(line, sep=', ', file=op, flush=True)
    print(line2, sep=', ', file=vp, flush=True)

    # initialize schedule and generators
    # schedule = write_default_schedule()
    for i in range(numGen):
        genFuel[i][3] = -1                     # turn off generators
        if "nuclear" in genFuel[i][0]:         # nuclear always on
            genCost[i][2] = genCost[i][1]      # big shut down cost
            genCost[i][1] = 0                  # no startup cost
            genFuel[i][3] = 1                  # turn on generator
        if genFuel[i][0] not in renewables:
            # gen[i, 1] = gen[i, 8]              # set to maximum real power output (MW)
            gen[i, 1] = gen[i, 9] + ((gen[i, 8] - gen[i, 9]) * 0.55)

    # copy of originals for outages
    ugen = deepcopy(gen)
    ugenCost = deepcopy(genCost)
    ugenFuel = deepcopy(genFuel)

    # MAIN LOOP starts here
    new_event = False
    while ts <= tmax:
        # start by getting the latest inputs from GridLAB-D and the auction
        events = fncs.get_events()
        for topic in events:
            new_event = True
            val = fncs.get_value(topic)
            log.debug("at " + str(ts) + " " + topic + " " + val)
        # running from load_player - wind/solar generator
            if 'GEN_POWER_' in topic or 'ALT_POWER_' in topic:
                if ppc['genPower']:
                    gen_id = int(topic[10:])
                    p = float(val)
                    for i in range(numGen):
                        if genFuel[i][2] == gen_id:
                            if gen[i, 8] < p:
                                gen[i, 8] = p
                            if gen[i, 9] > p:
                                gen[i, 9] = p
                            gen[i, 1] = p
                log.debug("at " + str(ts) + " " + topic + " " + val)
            elif 'GEN_PWR_HIST_' in topic or 'ALT_PWR_HIST_' in topic:
                if ppc['genPower']:
                    gen_id = topic[13:]
                    generator_plants[gen_id][2] = json.loads(val)
                log.debug("at " + str(ts) + " " + topic + " " + val)
        # getting the latest inputs from DSO day ahead and real time
            elif 'DA_BID_' in topic:
                dso_bid = True
                busnum = int(topic[7:]) - 1
                da_bid = json.loads(val)
                # keys unresp_mw, resp_max_mw, resp_c2, resp_c1, resp_deg; each array[hours_in_a_day]
                last_unRespMW[busnum] = deepcopy(unRespMW[busnum])
                last_respMaxMW[busnum] = deepcopy(respMaxMW[busnum])
                unRespMW[busnum] = da_bid['unresp_mw']     # fix load
                respMaxMW[busnum] = da_bid['resp_max_mw']  # slmax
                respC2[busnum] = da_bid['resp_c2']
                respC1[busnum] = da_bid['resp_c1']
                respC0[busnum] = da_bid['resp_c0']
                resp_deg[busnum] = da_bid['resp_deg']
                log.debug("at " + str(ts) + " " + topic + " " + str(da_bid))
            elif 'RT_BID_' in topic:
                dso_bid = True
                busnum = int(topic[7:])
                rt_bid = json.loads(val)
                # keys unresp_mw, resp_max_mw, resp_c2, resp_c1, resp_deg;
                gld_load[busnum]['unresp'] = rt_bid['unresp_mw']      # fix load
                gld_load[busnum]['resp_max'] = rt_bid['resp_max_mw']  # slmax
                gld_load[busnum]['c2'] = rt_bid['resp_c2']
                gld_load[busnum]['c1'] = rt_bid['resp_c1']
                gld_load[busnum]['c0'] = rt_bid['resp_c0']
                gld_load[busnum]['deg'] = rt_bid['resp_deg']
                log.debug("at " + str(ts) + " " + topic + " " + str(rt_bid))
        # running from load_player - taped bus load
            elif 'GLD_LOAD_' in topic:
                busnum = int(topic[9:])
                p, q = parse_mva(val)
                gld_load[busnum]['p'] = p     # MW
                gld_load[busnum]['q'] = q     # MW
                log.debug("at " + str(ts) + " " + topic + " " + val)
            elif 'GLD_LD_HIST_' in topic:
                busnum = int(topic[12:])
                gld_load_hist[busnum] = json.loads(val)
                log.debug("at " + str(ts) + " " + topic + " " + val)
        # running from load_player - taped ref bus load
            elif 'REF_LOAD_' in topic:
                busnum = int(topic[9:])
                p, q = parse_mva(val)
                gld_load[busnum]['p_r'] = p  # MW
                gld_load[busnum]['q_r'] = q  # MW
                log.debug("at " + str(ts) + " " + topic + " " + val)
            elif 'REF_LD_HIST_' in topic:
                busnum = int(topic[12:])
                ref_load_hist[busnum] = json.loads(val)
                log.debug("at " + str(ts) + " " + topic + " " + val)

        if new_event:
            log.info("at " + str(ts))
            # update cost coefficients, set dispatchable load, put unresp load on bus
            update_cost_and_load()
            # tso.print_mod_load(ppc['bus'], ppc['DSO'], gld_load, 'EVT', ts)
            log.info('bus_load = ' + str(bus[:, 2].sum()))
            log.info('gen_power = ' + str(gen[:, 1].sum()))

        # run SCED/SCUC in AMES/PSST to establish the next day's unit commitment and dispatch
        if ts >= tnext_opf_ames and ames:
            opf = True
            if mn % 60 == 0:
                hour = hour + 1
                mn = 0
                if hour == 24:
                    hour = 0
                    day = day + 1
                    day_of_year = day_of_year + 1
                    if day_of_year == 366:
                        day_of_year = 1

            # set print time for different outputs
            print_time = str(day) + '_' + str(hour) + '_' + str(mn) + '_'

            # un-comment file_time for multiple AMES files
            # file_time = print_time

            # Run the day ahead
            if hour == 10 and mn == 0:
                idx_add = []
                idx_del = []
                if outages:
                    # test for plan outages, make day positive to test
                    # have to know the day before the outage exists
                    # day_of_year is the count day since jan 1
                    # planned_df is zero base
                    for idx in range(len(planned_df[str(day_of_year)])):
                        if planned_df[str(day_of_year)][idx] == 1:
                            # delete generator for that day
                            planned_outage_dict.update({idx: 0})
                            idx_del.append(idx)
                        elif idx in planned_outage_dict.keys():
                            # this means that generator was out, but now is back in service
                            idx_add.append(idx)
                            del planned_outage_dict[idx]
                    log.info("Outages modified gen in DA " + str(idx_add) + str(idx_del))
                da_gen, da_genCost, da_genFuel, da_numGen = use_generator(idx_add, idx_del)

                psst_case = os.path.join(output_Path, file_time + "dam.dat")
                write_psst_file(psst_case, True, da_gen, da_genCost, da_genFuel, da_numGen)
                da_status, da_schedule, da_dispatch, da_lmps = scucDAM(psst_case)
                da_run_cnt += 1
                if da_status:
                    da_status_cnt += 1
                da_percent = da_status_cnt / da_run_cnt
                log.info("DA Status: " + str(da_status))
                log.info("DA Percent Status: " + str(da_percent))
                log.info("DA LMPs: \n" + str(print_time) + str(da_lmps))
                log.debug("DA Gen dispatches: \n" + str(da_dispatch))
                log.debug("DA Unit Schedule:\n" + str(da_schedule))

            # Real time and update the dispatch schedules in ppc
            if day > 1:
                # Change the DA Schedule and the dispatchable generators
                if day > lastDay:
                    # new day starts now
                    # refresh gen data and schedule
                    last_dispatch = deepcopy(da_dispatch)
                    da_gen, da_genCost, da_genFuel, da_numGen = use_generator(idx_add, idx_del)
                    schedule = deepcopy(da_schedule)
                    ppc['gen'] = deepcopy(da_gen)
                    ppc['gencost'] = deepcopy(da_genCost)
                    ppc['genfuel'] = deepcopy(da_genFuel)
                    gen = ppc['gen']
                    genCost = ppc['gencost']
                    genFuel = ppc['genfuel']
                    numGen = da_numGen
                    lastDay = day

                # uptime and downtime in hour for each generator and set gen status
                # and are counted using commitment schedule for the day
                if mn == 0:
                    for i in range(numGen):
                        if genFuel[i][0] not in renewables:
                            name = "GenCo" + str(i + 1)
                            if name in schedule.keys():
                                gen[i, 7] = int(schedule.at[hour + 1, name])
                                if gen[i, 7] == 1:
                                    if genFuel[i][3] > 0:
                                        genFuel[i][3] += 1
                                    else:
                                        genFuel[i][3] = 1
                                else:
                                    if genFuel[i][3] < 0:
                                        genFuel[i][3] -= 1
                                    else:
                                        genFuel[i][3] = -1

                    # get the schedule for this hour
                    rt_schedule = write_rtm_schedule(schedule)

                    # unplanned outage implementation on the hour
                    if outagesUnplanned:
                        # convert day and hour to 0-8760
                        hour_of_year = hour + ((day_of_year-1) * 24)
                        for idx in range(len(unplanned_df[str(hour_of_year)])):
                            if unplanned_df[str(hour_of_year)][idx] == 1:
                                for igen in range(numGen):
                                    if genFuel[igen][2] == idx:
                                        name = 'GenCo' + str(igen + 1)
                                        log.info("Unplanned outage " + str(hour_of_year) + " min " + str(mn))
                                        gen[igen][1] = 0
                                        genFuel[igen][3] = -1
                                        if name in rt_schedule.keys():
                                            rt_schedule[name] = '0'
                                            log.info("Changing schedule for " + genFuel[igen][0] + ", " + name + ", Gen Id " + str(idx))
                                        else:
                                            log.info("No schedule for " + genFuel[igen][0] + ", " + name + ", Gen Id " + str(idx))

                # Run the real time and publish the LMP
                psst_case = os.path.join(output_Path, file_time + "rtm.dat")
                write_psst_file(psst_case, False, gen, genCost, genFuel, numGen)
                rt_status, rt_dispatch, rt_lmps = scedRTM(psst_case, rt_schedule)
                rt_run_cnt += 1
                if rt_status:
                    rt_status_cnt += 1
                rt_percent = rt_status_cnt / rt_run_cnt
                log.info("RT Status: " + str(rt_status))
                log.info("RT Percent Status: " + str(rt_percent))
                log.info("RT LMPs: \n" + str(print_time) + str(rt_lmps))
                log.debug("RT Gen dispatches: \n" + str(rt_dispatch))
                log.debug("RT Unit Schedule:\n" + str(rt_schedule))

            # write OPF metrics
            Pswing = 0
            for idx in range(numGen):
                if gen[idx, 0] == swing_bus:
                    Pswing += gen[idx, 1]

            sum_w = 0
            sum_hr = 0
            for key, row in generator_plants.items():
                for idx in range(numGen):
                    if genFuel[idx][2] == row[3]:
                        sum_w += gen[idx, 1]
                        sum_hr += float(row[2][hour])

            line = str(ts) + ', ' + "True" + ','
            line += '{: .2f}'.format(bus[:, 2].sum()) + ','
            line += '{: .2f}'.format(gen[:, 1].sum()) + ','
            line += '{: .2f}'.format(Pswing) + ','
            da_sum = 0
            for idx in range(bus.shape[0]):
                line += '{: .2f}'.format(bus[idx, 13]) + ','
                da_sum += last_unRespMW[idx][hour] + last_respMaxMW[idx][hour]

            # Must keep the generators in original order for printing when outages are applied
            for uidx in range(unumGen):
                notUsed = True
                for idx in range(numGen):
                    if ugenFuel[uidx][2] == genFuel[idx][2]:
                        line += '{: .2f}'.format(gen[idx, 1]) + ','
                        notUsed = False
                        break
                if notUsed:
                    line += ' 0,'

            line += '{: .2f}'.format(sum_w) + ',' + '{: .2f}'.format(sum_hr) + ',' + \
                    '{: .2f}'.format(sum(nobid_unresp_rt)) + ','

            line += '{: .2f}'.format(da_sum) + ','
            if len(last_dispatch) > 0:
                da_sum = 0
                for key, row in last_dispatch.items():
                    da_sum += row[hour]
                line += '{: .2f}'.format(da_sum) + ','
            else:
                line += ' 0,'
            line += '{: .2f}'.format(da_sum + sum_hr) + ','
            line += '{: .2f}'.format(rt_percent) + ', ' + str(rt_status)

            print(line, sep=', ', file=op, flush=True)

            mn = mn + RTOPDur  # period // 60
            tnext_opf_ames += period

        # run OPF to establish the prices and economic dispatch - currently period = 300s
        if ts >= tnext_opf_pp and not ames:
            opf = True
            ropf = pp.runopf(ppc, ppopt_market)
            if not ropf[0]['success']:
                conv_accum = False
                print('ERROR/WARN: runopf did not converge at', ts)
            opf_bus = deepcopy(ropf['bus'])
            opf_gen = deepcopy(ropf['gen'])
            Pswing = 0
            for idx in range(opf_gen.shape[0]):
                if opf_gen[idx, 0] == swing_bus:
                    Pswing += opf_gen[idx, 1]

            sum_w = 0
            for key, row in generator_plants.items():
                for idx in range(numGen):
                    if genFuel[idx][2] == row[3]:
                        sum_w += gen[idx, 1]

            line = str(ts) + ',' + "True" + ','
            line += '{: .2f}'.format(opf_bus[:, 2].sum()) + ','
            line += '{: .2f}'.format(opf_gen[:, 1].sum()) + ','
            line += '{: .2f}'.format(Pswing)
            for idx in range(opf_bus.shape[0]):
                line += ',' + '{: .4f}'.format(opf_bus[idx, 13])
            for idx in range(opf_gen.shape[0]):
                if numGen > idx:
                    line += ',' + '{: .2f}'.format(opf_gen[idx, 1])
            line += ',{: .2f}'.format(sum_w)
            print(line, sep=', ', file=op, flush=True)

            tnext_opf_pp += period

            # always run the regular power flow for voltages and performance metrics
            ppc['bus'][:, 13] = opf_bus[:, 13]  # set the lmp
            ppc['gen'][:, 1] = opf_gen[:, 1]  # set the economic dispatch
            bus = ppc['bus']  # needed to be re-aliased because of [:, ] operator
            gen = ppc['gen']  # needed to be re-aliased because of [:, ] operator

        # add the actual scaled GridLAB-D loads to the baseline loads
        if new_event:
            for row in dsoBus:
                busnum = int(row[0])
                load = gld_load[busnum]
                log.debug("Turn off responsive / dispatchable loads")
                for idx in range(numGen, gen.shape[0]):
                    if genFuel[idx][2] == load['genidx']:
                        log.debug('Bus' + str(busnum) + ', Gen' + str(idx))
                        gen[idx, 1] = 0  # p
                        gen[idx, 2] = 0  # q
                        gen[idx, 9] = 0  # pmin
        new_event = False

        # update generation with consideration for distributed slack bus
        if opf:
            # tso.print_mod_load(ppc['bus'], ppc['DSO'], gld_load, 'OPF', ts)
            # log.info('bus_opf = ' + str(bus[:, 2].sum()))
            # log.info('gen_opf = ' + str(gen[:, 1].sum()))
            ppc['gen'] = gen
            ppc['gen'][:, 1] = dist_slack(ppc, Pload)
            gen = ppc['gen']   # needed to be re-aliased because of [:, ] operator
            # tso.print_mod_load(ppc['bus'], ppc['DSO'], gld_load, 'DIST', ts)
            # log.info('bus_dist = ' + str(bus[:, 2].sum()))
            # log.info('gen_dist = ' + str(gen[:, 1].sum()))
            opf = False

        rpf = pp.runpf(ppc, ppopt_regular)
        # TODO: add a check if does not converge, switch to DC
        if not rpf[0]['success']:
            conv_accum = False
            print('ERROR: runpf did not converge at', ts)
        #   pp.printpf(100.0,
        #               bus=rpf[0]['bus'],
        #               gen=rpf[0]['gen'],
        #               branch=rpf[0]['branch'],
        #               fd=sys.stdout,
        #               et=rpf[0]['et'],
        #               success=rpf[0]['success'])
        rBus = rpf[0]['bus']
        rGen = rpf[0]['gen']
        # tso.print_mod_load(ppc['bus'], ppc['DSO'], gld_load, 'PF', ts)
        # log.info('bus_pf = ' + str(rBus[:, 2].sum()))
        # log.info('gen_pf = ' + str(rGen[:, 1].sum()))

        Pload = rBus[:, 2].sum()
        Pgen = rGen[:, 1].sum()
        Ploss = Pgen - Pload
        Pswing = 0
        for idx in range(rGen.shape[0]):
            if rGen[idx, 0] == swing_bus:
                Pswing += rGen[idx, 1]

        line = str(ts) + ', ' + "True" + ','
        line += '{: .2f}'.format(Pload) + ',' + '{: .2f}'.format(Pgen) + ','
        line += '{: .2f}'.format(Ploss) + ',' + '{: .2f}'.format(Pswing)
        for idx in range(rBus.shape[0]):
            line += ',' + '{: .2f}'.format(rBus[idx, 7])  # bus per-unit voltages
        print(line, sep=', ', file=vp, flush=True)

        # update the metrics
        n_accum += 1
        loss_accum += Ploss
        for i in range(dsoBus.shape[0]):
            busnum = dsoBus[i, 0]
            busidx = int(dsoBus[i, 0]) - 1
            row = rBus[busidx].tolist()
            # publish the bus VLN for GridLAB-D
            bus_vln = 1000.0 * row[7] * row[9] / math.sqrt(3.0)
            fncs.publish('three_phase_voltage_' + busnum, bus_vln)

            # publish the bus LMP [$/kwh] ?for GridLAB-D
            # if ames:
            #     lmp = float(bus[busidx, 13]) * 0.001
            # else:
            #     lmp = float(opf_bus[busidx, 13]) * 0.001
            # fncs.publish('LMP_Bus' + busnum, str(lmp))  # publishing $/kwh

            # LMP_P, LMP_Q, PD, QD, Vang, Vmag, Vmax, Vmin: row[11] and row[12] are Vmax and Vmin constraints
            PD = row[2]  # + resp # TODO, if more than one FNCS bus, track scaled_resp separately
            Vpu = row[7]
            bus_accum[busnum][0] += row[13] * 0.001
            bus_accum[busnum][1] += row[14] * 0.001
            bus_accum[busnum][2] += PD
            bus_accum[busnum][3] += row[3]
            bus_accum[busnum][4] += row[8]
            bus_accum[busnum][5] += Vpu
            if Vpu > bus_accum[busnum][6]:
                bus_accum[busnum][6] = Vpu
            if Vpu < bus_accum[busnum][7]:
                bus_accum[busnum][7] = Vpu

        for i in range(rGen.shape[0]):
            idx = str(genFuel[i][2])
            row = rGen[i].tolist()
            busidx = int(row[0] - 1)
            # Pgen, Qgen, LMP_P (includes the responsive load as dispatched by OPF)
            gen_accum[idx][0] += row[1]
            gen_accum[idx][1] += row[2]
            if ames:
                gen_accum[idx][2] += float(bus[busidx, 13]) * 0.001
            else:
                gen_accum[idx][2] += float(opf_bus[busidx, 13]) * 0.001

        # write the metrics
        if ts >= tnext_metrics:
            # ('Ploss', 'MW'),
            # ('Converged', 'true/false')
            sys_store.append_data(
                ts,
                casename,
                loss_accum / n_accum,
                conv_accum,
            )

            for i in range(dsoBus.shape[0]):
                busnum = dsoBus[i, 0]
                met = bus_accum[busnum]
                # ('LMP_P', 'USD/kwh'),
                # ('LMP_Q', 'USD/kvarh'),
                # ('PD', 'MW'),
                # ('QD', 'MVAR'),
                # ('Vang', 'deg'),
                # ('Vmag', 'pu'),
                # ('Vmax', 'pu'),
                # ('Vmin', 'pu'),
                # ('unresp', 'MW'),
                # ('resp_max', 'MW'),
                # ('c1', '$/MW'),
                # ('c2', '$/MW^2')
                bus_store.append_data(
                    ts,
                    'bus{}'.format(busnum),
                    met[0] / n_accum, met[1] / n_accum,
                    met[2] / n_accum, met[3] / n_accum,
                    met[4] / n_accum, met[5] / n_accum,
                    met[6], met[7],
                    met[8], met[9],
                    met[10], met[11],
                )
                bus_accum[busnum] = [0, 0, 0, 0, 0, 0, 0, 99999.0, 0, 0, 0, 0]

            for i in range(rGen.shape[0]):
                idx = str(genFuel[i][2])
                met = gen_accum[idx]
                # ('Pgen', 'MW'),
                # ('Qgen', 'MVAR'),
                # ('LMP_P', 'USD/kwh'),
                gen_store.append_data(
                    ts,
                    'gen{}'.format(idx),
                    met[0] / n_accum,
                    met[1] / n_accum,
                    met[2] / n_accum,
                )
                gen_accum[idx] = [0, 0, 0]

            tnext_metrics += period
            n_accum = 0
            loss_accum = 0
            conv_accum = True

        if ts >= tnext_write_metrics or ts >= tmax:
            log.debug('writing metrics at ' + str(ts))
            # write all known metrics to disk
            collector.write_metrics()
            tnext_write_metrics += metrics_record_interval

        # request the next time step, if necessary
        if ts >= tmax:
            log.info('breaking out at ' + str(ts))
            break
        ts = fncs.time_request(min(ts + dt, tmax))

    # ======================================================
    log.info('finalize metrics writing')
    collector.finalize_writing()
    log.info('closing files')
    op.close()
    vp.close()
    log.info('finalizing FNCS tso federate')
    fncs.finalize()


if __name__ == "__main__":
    tso_psst_loop_f('./generate_case_config')
