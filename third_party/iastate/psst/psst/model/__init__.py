import logging
import click

import pandas as pd
import numpy as np

from .model import (create_model, initialize_buses,
                initialize_time_periods, initialize_model, Suffix
                    )
from .network import (initialize_network, derive_network, calculate_network_parameters, enforce_thermal_limits)
from .generators import (initialize_generators, initial_state, maximum_minimum_power_output_generators,
                        ramp_up_ramp_down_limits, start_up_shut_down_ramp_limits, minimum_up_minimum_down_time,
                        fuel_cost, piece_wise_linear_cost,
                        production_cost, minimum_production_cost,
                        hot_start_cold_start_costs,
                        forced_outage,
                        generator_bus_contribution_factor)

from .price_sensitive_load import (initialize_price_senstive_load, maximum_minimum_power_demand_loads,
                                   piece_wise_linear_benefit,initialize_load_demand,
                                   quadratic_benefit_coefficients, load_benefit)

from .reserves import initialize_global_reserves, initialize_regulating_reserves, initialize_zonal_reserves
from .demand import (initialize_demand)

from .constraints import (constraint_line, constraint_total_demand, constraint_net_power,
                        constraint_load_generation_mismatch,
                        constraint_power_balance,
                        constraint_reserves,
                        constraint_generator_power,
                        constraint_up_down_time,
                        constraint_for_cost,
                        constraint_for_benefit,
                        objective_function)

from ..solver import solve_model, PSSTResults
from ..case.utils import calculate_PTDF

logger = logging.getLogger(__file__)


def build_model(case,
                generator_df=None,
                load_df=None,
                branch_df=None,
                bus_df=None,
                ZonalDataComplete=None,
                PriceSenLoadData=None,
                previous_unit_commitment_df=None,
                base_MVA=None,
                base_KV=1,
                config=None):

    if base_MVA is None:
        base_MVA = case.baseMVA

    #click.echo("args: " + str(generator_df) + str(load_df) + str(branch_df) + str(bus_df) + str(previous_unit_commitment_df) + str(base_MVA) + str(base_KV) + str(config))

    # Configuration
    if config is None:
        config = dict()

    zonalData = ZonalDataComplete['zonalData']
    zonalBusData = ZonalDataComplete['zonalBusData']
    ReserveUpZonalPercent = ZonalDataComplete['ReserveUpZonalPercent']
    ReserveDownZonalPercent = ZonalDataComplete['ReserveDownZonalPercent']
    #click.echo("printing zonalData:" + str(zonalData) + str(zonalBusData) + str(ReserveUpZonalPercent) + str(ReserveDownZonalPercent))

    # Get configuration parameters from dictionary
    use_ptdf = config.pop('use_ptdf', False)

    # Get case data
    #click.echo("case.gen: "+ str(case.gen))
    #click.echo("case.gencost: "+ str(case.gencost))
    generator_df = generator_df or pd.merge(case.gen, case.gencost, left_index=True, right_index=True)
    load_df = load_df or case.load
    branch_df = branch_df or case.branch
    bus_df = bus_df or case.bus
    ReserveDownSystemPercent = case.ReserveDownSystemPercent
    ReserveUpSystemPercent = case.ReserveUpSystemPercent

    #click.echo("generator_df: "+ str(generator_df))
    #click.echo("load_df: "+ str(load_df))

    branch_df.index = branch_df.index.astype(object)
    generator_df.index = generator_df.index.astype(object)
    bus_df.index = bus_df.index.astype(object)
    load_df.index = load_df.index.astype(object)
    #click.echo("printing load_df.index:" + str(load_df.index))
    #click.echo("printing generator_df.index:" + str(generator_df.index))

    branch_df = branch_df.astype(object)
    generator_df = generator_df.astype(object)
    bus_df = bus_df.astype(object)
    load_df = load_df.astype(object)

    #click.echo("printing load_df:" + str(load_df))
    #click.echo("generator_df: "+ str(generator_df))

    # Build model information

    model = create_model()

    initialize_buses(model, bus_names=bus_df.index)
    initialize_time_periods(model, time_periods=list(load_df.index), time_period_length=case.TimePeriodLength)

    # Build network data
    initialize_network(model, transmission_lines=list(branch_df.index), bus_from=branch_df['F_BUS'].to_dict(), bus_to=branch_df['T_BUS'].to_dict())

    lines_to = {b: list() for b in bus_df.index.unique()}
    lines_from = {b: list() for b in bus_df.index.unique()}

    for i, l in branch_df.iterrows():
        lines_from[l['F_BUS']].append(i)
        lines_to[l['T_BUS']].append(i)

    derive_network(model, lines_from=lines_from, lines_to=lines_to)
    calculate_network_parameters(model, reactance=(branch_df['BR_X'] / base_MVA).to_dict())
    enforce_thermal_limits(model, thermal_limit=branch_df['RATE_A'].to_dict())

    # Build generator data

    generator_at_bus = {b: list() for b in generator_df['GEN_BUS'].unique()}

    for i, g in generator_df.iterrows():
        generator_at_bus[g['GEN_BUS']].append(i)

    #click.echo("printing generator_at_bus:" + str(generator_at_bus))

    #print('generator_at_bus',generator_at_bus)
    initialize_generators(model,
                        generator_names=generator_df.index,
                        generator_at_bus=generator_at_bus)

    fuel_cost(model)

    maximum_minimum_power_output_generators(model,
                                        minimum_power_output=generator_df['PMIN'].to_dict(),
                                        maximum_power_output=generator_df['PMAX'].to_dict())

    ramp_up_ramp_down_limits(model, ramp_up_limits=generator_df['RAMP_10'].to_dict(), ramp_down_limits=generator_df['RAMP_10'].to_dict())

    start_up_shut_down_ramp_limits(model, start_up_ramp_limits=generator_df['STARTUP_RAMP'].to_dict(), shut_down_ramp_limits=generator_df['SHUTDOWN_RAMP'].to_dict(),
                                   max_power_available=generator_df['PMAX'].to_dict())

    minimum_up_minimum_down_time(model, minimum_up_time=generator_df['MINIMUM_UP_TIME'].astype(int).to_dict(), 
                                 minimum_down_time=generator_df['MINIMUM_DOWN_TIME'].astype(int).to_dict())

    forced_outage(model)

    generator_bus_contribution_factor(model)

    #print("previous_unit_commitment_df 1 :", previous_unit_commitment_df, flush=True)
    
    if previous_unit_commitment_df is None:
        previous_unit_commitment = dict()
        for g in generator_df.index:
            previous_unit_commitment[g] = [0] * len(load_df)
        previous_unit_commitment_df = pd.DataFrame(previous_unit_commitment)
        previous_unit_commitment_df.index = load_df.index

    #print("previous_unit_commitment_df 2 :", previous_unit_commitment_df, flush=True)
    
    diff = previous_unit_commitment_df.diff()
    #print("diff?:", diff, flush=True)

    initial_state_dict = dict()
    for col in diff.columns:
        s = diff[col].dropna()
        diff_s = s[s!=0]
        if diff_s.empty:
            ##print("Checking 1:", flush=True)
            check_row = previous_unit_commitment_df[col].head(1)
            #print("check_row: ", check_row, flush=True)
        else:
            ##print("Checking 2:", flush=True)
            check_row = diff_s.tail(1)

        if check_row.values == -1 or check_row.values == 0:
            ##print("Checking 3:", flush=True)
            initial_state_dict[col] = -1 * (len(load_df) - int(check_row.index.values))
            #print("initial_state_dict[col]: len(load_df): int(check_row.index.values): ", initial_state_dict[col], len(load_df), int(check_row.index.values), flush=True)
        else:
            ##print("Checking 4:", flush=True)
            initial_state_dict[col] = len(load_df) - int(check_row.index.values)

    logger.debug("Initial State of generators is {}".format(initial_state_dict))
    initial_state_dict = generator_df['UnitOnT0State'].to_dict()
    #print("Gen initial_state_dict:", initial_state_dict, flush=True)

    initial_state(model, initial_state=initial_state_dict)

    # setup production cost for generators

    points = dict()
    values = dict()

    for i, g in generator_df.iterrows():
        #click.echo("i:" + i + " g: " + str(g))
        if g['NCOST'] == 2:
            logger.debug("NCOST=2")
            if g['PMIN'] == g['PMAX']:
                small_increment = 1
            else:
                small_increment = 0
            points[i] = np.linspace(g['PMIN'], g['PMAX'] + small_increment, num=int(g['NS'])+1)
            values[i] = g['COST_0'] + g['COST_1'] * points[i]
        if g['NCOST'] == 3:
            points[i] = np.linspace(g['PMIN'], g['PMAX'], num=int(g['NS'])+1)
            values[i] = g['COST_0'] + g['COST_1'] * points[i] + g['COST_2'] * points[i] ** 2

    #click.echo("printing points: " + str(points))
    #click.echo("printing values: " + str(values))

    for k, v in points.items():
        points[k] = [float(i) for i in v]
    for k, v in values.items():
        values[k] = [float(i) for i in v]

    #click.echo("Again printing points: " + str(points))
    #click.echo("Again printing values: " + str(values))
    piece_wise_linear_cost(model, points, values)



    minimum_production_cost(model)
    production_cost(model)

    # setup start up and shut down costs for generators

    cold_start_hours = case.gencost['COLD_START_HOURS'].astype(int).to_dict()
    #click.echo("In build_model - printing cold_start_hours:" + str(cold_start_hours))
    hot_start_costs = case.gencost['STARTUP_HOT'].to_dict()
    #click.echo("In build_model - printing hot_start_costs:" + str(hot_start_costs))
    cold_start_costs = case.gencost['STARTUP_COLD'].to_dict()
    #click.echo("In build_model - printing cold_start_costs:" + str(cold_start_costs))
    shutdown_coefficient = case.gencost['SHUTDOWN_COEFFICIENT'].to_dict()
    #click.echo("In build_model - printing shutdown_coefficient:" + str(shutdown_coefficient))

    hot_start_cold_start_costs(model, hot_start_costs=hot_start_costs, cold_start_costs=cold_start_costs, cold_start_hours=cold_start_hours, shutdown_cost_coefficient=shutdown_coefficient)

    # Build load data
    load_dict = dict()
    columns = load_df.columns
    for i, t in load_df.iterrows():
        for col in columns:
            load_dict[(col, i)] = t[col]
    #click.echo('load_dict, load_df ' +str(load_dict))

    initialize_demand(model, demand=load_dict)

    # Initialize Pyomo Variables
    initialize_model(model,positive_mismatch_penalty=case.PositiveMismatchPenalty,negative_mismatch_penalty=case.NegativeMismatchPenalty)

    # price sensitive load

    if case.PriceSenLoadFlag == 0:
        PriceSenLoadFlag = False
    else:
        PriceSenLoadFlag = True


    # adding segments for price sensitive loads
    segments = config.pop('segments', 5)
    psl_points = dict()
    psl_values = dict()
    #print(PriceSenLoadData)

    pmin_values = dict()
    pmax_values = dict()

    coefficient_e_values = dict()
    coefficient_d_values = dict()
    coefficient_f_values = dict()

    #print('segments=',segments)
    if PriceSenLoadFlag is True:
        if PriceSenLoadData is not None:
            psl_names =[]
            psl_at_buses={}
            for name, hour in PriceSenLoadData:
                if(name not in psl_names):
                    psl_names.append(name)
                psl_record = PriceSenLoadData[name,hour]
                if(psl_record['atBus'] not in psl_at_buses.keys()):
                    psl_at_buses[psl_record['atBus']] = []
                if name not in psl_at_buses[psl_record['atBus']]:
                    #TODO need to check whether append() function is suitable for multiple loads at the same bus
                    psl_at_buses[psl_record['atBus']].append(name)

                psl_points[name,hour] = np.linspace(psl_record['Pmin'], psl_record['Pmax'], num=int(segments))
                psl_values[name,hour] = psl_record['d'] + psl_record['e'] * psl_points[name,hour] + psl_record['f'] * psl_points[name,hour] ** 2
                pmin_values[name,hour] = psl_record['Pmin']
                pmax_values[name,hour] = psl_record['Pmax']

                coefficient_d_values[name, hour] = psl_record['d']
                coefficient_e_values[name,hour] = psl_record['e']
                coefficient_f_values[name, hour] = psl_record['f']


            for k, v in psl_points.items():
                psl_points[k] = [float(i) for i in v]
            for k, v in psl_values.items():
                psl_values[k] = [float(i) for i in v]
            #print('psl_names:',psl_names)
            #print('psl_at_buses:', psl_at_buses)
            initialize_price_senstive_load(model,
                                           price_sensitive_load_names=psl_names,
                                           price_sensitive_load_at_bus=psl_at_buses)

            maximum_minimum_power_demand_loads(model,
                                               minimum_power_demand=pmin_values,
                                               maximum_power_demand=pmax_values)

            initialize_load_demand(model)

            #print('d =', coefficient_d_values)
            #print('e =', coefficient_e_values)
            #print('f =', coefficient_f_values)
            quadratic_benefit_coefficients(model,
                                           coefficient_c0=coefficient_d_values,
                                           coefficient_c1=coefficient_e_values,
                                           coefficient_c2=coefficient_f_values)
            #print ('psl points:',psl_points)
            #print('psl values:', psl_values)
            piece_wise_linear_benefit(model, psl_points, psl_values)
            load_benefit(model)
            constraint_for_benefit(model)
        else:
            PriceSenLoadFlag = False
            raise RuntimeError('PriceSenLoadFlag is set to be True, but no Price Sensitive Load Data is correctly loaded')



    initialize_global_reserves(model, ReserveDownSystemPercent=ReserveDownSystemPercent, ReserveUpSystemPercent=ReserveUpSystemPercent)
    initialize_regulating_reserves(model, )

    #click.echo('HasZonalReserves? '+zonalData['HasZonalReserves'])
    if zonalData['HasZonalReserves'] is True:
        initialize_zonal_reserves(model, PriceSenLoadFlag=PriceSenLoadFlag, zone_names=zonalData['Zones'], buses_at_each_zone=zonalBusData, ReserveDownZonalPercent=ReserveDownZonalPercent, ReserveUpZonalPercent=ReserveUpZonalPercent)

    # impose Pyomo Constraints
    if case.StorageFlag == 0:
        bStorageFlag = False
    else:
        bStorageFlag = True

    constraint_net_power(model, StorageFlag=bStorageFlag, PriceSenLoadFlag=PriceSenLoadFlag)

    if use_ptdf is True:
        ptdf = calculate_PTDF(case, precision=config.pop('ptdf_precision', None), tolerance=config.pop('ptdf_tolerance', None))
        constraint_line(model, ptdf=ptdf)
    else:
        constraint_line(model, slack_bus=bus_df.index.get_loc(bus_df[bus_df['TYPE'] == 3].index[0])+1)
        # Pyomo is 1-indexed for sets, and MATPOWER type of bus should be used to get the slack bus

    constraint_power_balance(model, PriceSenLoadFlag=PriceSenLoadFlag)

    constraint_total_demand(model, PriceSenLoadFlag=PriceSenLoadFlag)
    constraint_load_generation_mismatch(model)
    constraint_reserves(model, has_zonal_reserves=zonalData['HasZonalReserves'], PriceSenLoadFlag=PriceSenLoadFlag)
    constraint_generator_power(model)
    constraint_up_down_time(model)
    constraint_for_cost(model)

    # Add objective function
    objective_function(model, PriceSenLoadFlag=PriceSenLoadFlag)

    for t, row in case.gen_status.iterrows():
        for g, v in row.iteritems():
            if not pd.isnull(v):
                try:
                    model.UnitOn[g, t].fixed = True
                    model.UnitOn[g, t] = int(float(v))
                except:
                    pass


    model.dual = Suffix(direction=Suffix.IMPORT)

    # output the model
    # model.pprint(filename="model.out")
    return PSSTModel(model)


class PSSTModel(object):

    def __init__(self, model, is_solved=False):
        self._model = model
        self._is_solved = is_solved
        self._status = None
        self._results = None

    def __repr__(self):

        repr_string = 'status={}'.format(self._status)

        string = '<{}.{}({})>'.format(
                    self.__class__.__module__,
                    self.__class__.__name__,
                    repr_string,)


        return string

    def solve(self, solver='glpk', verbose=False, keepfiles=True, **kwargs):
        solve_model(self._model, solver=solver, verbose=verbose, keepfiles=keepfiles, **kwargs)
        self._results = PSSTResults(self._model)

    @property
    def results(self):
        return self._results
