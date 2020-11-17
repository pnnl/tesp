from pyomo.environ import *
import click


def initialize_generators(model,
                        generator_names=None,
                        generator_at_bus=None):

    model.Generators = Set(initialize=generator_names)
    model.GeneratorsAtBus = Set(model.Buses, initialize=generator_at_bus)


# def initialize_non_dispatchable_generators(model,
                                        # non_dispatchable_generator_names=None,
                                        # non_dispatchable_generator_at_bus=None):

    # model.NonDispatchableGenerators = Set(initialize=non_dispatchable_generator_names)
    # model.NonDispatchableGeneratorsAtBus = Set(model.Buses, initialize=non_dispatchable_generator_at_bus)

def generation_maximum_power_init(model):
    for g, t in model.EnforceMaximumPower:
        model.MaximumPowerAvailable[g, t] = model.EnforceMaximumPower[g, t]
        model.MaximumPowerAvailable[g, t].fixed = True

def generator_bus_contribution_factor(model):
    model.GeneratorBusContributionFactor = Param(model.Generators, model.Buses, within=NonNegativeReals, default=1.0)

def initialize_maximum_power(model):

    # maximum power output for each generator, at each time period.
    model.MaximumPowerAvailable = Var(model.Generators, model.TimePeriods, within=NonNegativeReals)
    model.MinimumPowerAvailable = Var(model.Generators, model.TimePeriods, within=NonNegativeReals)


    model.EnforceMaximumPower = Param(model.Generators, model.TimePeriods, within=NonNegativeReals)


def failure_probablity(model):

    # TODO : Add validator
    model.FailureProbablity = Param(model.Generators, default=0.0)


def forced_outage(model):

    model.GeneratorForcedOutage = Param(model.Generators * model.TimePeriods, within=Binary, default=False)


def maximum_minimum_power_output_generators(model, minimum_power_output=None, maximum_power_output=None):


    # TODO add validation that maximum power output is greater than minimum power output

    model.MinimumPowerOutput = Param(model.Generators, initialize=minimum_power_output, within=NonNegativeReals, default=0.0)
    model.MaximumPowerOutput = Param(model.Generators, initialize=maximum_power_output, within=NonNegativeReals, default=0.0)


# def maximum_minimim_power_output_non_dispatchable_generators(model, minimum_power_output=None, maximum_power_output=None):

    # model.MinimumNonDispatchablePowerOutput = Param(model.NonDispatchableGenerators,
                                            # model.TimePeriods,
                                            # within=NonNegativeReals,
                                            # default=0.0,
                                            # mutable=True)

    # model.MaximumNonDispatchablePowerOutput = Param(model.NonDispatchableGenerators,
                                            # model.TimePeriods,
                                            # within=NonNegativeReals,
                                            # default=0.0,
                                            # mutable=True)


def ramp_up_ramp_down_limits(model, ramp_up_limits=None, ramp_down_limits=None):

    #NRU_j
    model.NominalRampUpLimit = Param(model.Generators, within=NonNegativeReals, initialize=ramp_up_limits)
    #NRD_j
    model.NominalRampDownLimit = Param(model.Generators, within=NonNegativeReals, initialize=ramp_down_limits)


def start_up_shut_down_ramp_limits(model, start_up_ramp_limits=None, shut_down_ramp_limits=None, max_power_available=None):
    # #NSU_j
    # model.StartupRampLimit = Param(model.Generators, within=NonNegativeReals, initialize=start_up_ramp_limits)
    # #NSD_j
    # model.ShutdownRampLimit = Param(model.Generators, within=NonNegativeReals, initialize=shut_down_ramp_limits)
    #These are actually SSU and SSD from the manual
    ssu = {}
    for key in start_up_ramp_limits:
        ssu[key] = min(max_power_available[key], start_up_ramp_limits[key] * model.TimePeriodLength.value)

    # Startup
    model.StartupRampLimit = Param(model.Generators, within=NonNegativeReals, initialize=ssu)

    ssd = {}
    for key in shut_down_ramp_limits:
        ssd[key] = min(max_power_available[key], shut_down_ramp_limits[key] * model.TimePeriodLength.value)

    #ShutDown
    model.ShutdownRampLimit = Param(model.Generators, within=NonNegativeReals, initialize=ssd)
    # The above matches the manual's SSD and SSU


def minimum_up_minimum_down_time(model, minimum_up_time=None, minimum_down_time=None):
    #UT_j
    model.MinimumUpTime = Param(model.Generators, within=NonNegativeIntegers, default=0, initialize=minimum_up_time)
    #DT_j
    model.MinimumDownTime = Param(model.Generators, within=NonNegativeIntegers, default=0, initialize=minimum_down_time)


def _initial_time_periods_online_rule(m, g):
   if not value(m.UnitOnT0[g]):
      return 0
   else:
      return int(min(value(m.NumTimePeriods),
             round(max(0, value(m.MinimumUpTime[g]) - value(m.UnitOnT0State[g])) / value(m.TimePeriodLength))))

def _initial_time_periods_offline_rule(m, g):
   if value(m.UnitOnT0[g]):
      return 0
   else:
      return int(min(value(m.NumTimePeriods),
             round(max(0, value(m.MinimumDownTime[g]) + value(m.UnitOnT0State[g])) / value(m.TimePeriodLength)))) # m.UnitOnT0State is negative if unit is off


def initial_state(model, initial_state=None,
                initial_time_periods_online=_initial_time_periods_online_rule,
                initial_time_periods_offline=_initial_time_periods_offline_rule
                ):

    model.UnitOnT0State = Param(model.Generators, within=Reals, initialize=initial_state, mutable=True)

    def t0_unit_on_rule(m, g):
        return int(value(m.UnitOnT0State[g]) >= 1)

    #v_j(0) --> Value follows immediated from \hat{v}_j value. DON'T SET
    model.UnitOnT0 = Param(model.Generators, within=Binary, initialize=t0_unit_on_rule, mutable=True)

    #Calculated
    model.InitialTimePeriodsOnLine = Param(model.Generators, within=NonNegativeIntegers, initialize=_initial_time_periods_online_rule, mutable=True)

    #Calcualted
    model.InitialTimePeriodsOffLine = Param(model.Generators, within=NonNegativeIntegers, initialize=_initial_time_periods_offline_rule, mutable=True)


def hot_start_cold_start_costs(model,
                            hot_start_costs=None,
                            cold_start_costs=None,
                            cold_start_hours=None,
                            shutdown_cost_coefficient=None):

    ###############################################
    # startup cost parameters for each generator. #
    ###############################################

    #CSH_j
    model.ColdStartHours = Param(model.Generators, within=NonNegativeIntegers, default=0, initialize=cold_start_hours) # units are hours.

    #HSC_j
    model.HotStartCost = Param(model.Generators, within=NonNegativeReals, default=0.0, initialize=hot_start_costs) # units are $.
    #CSC_j
    model.ColdStartCost = Param(model.Generators, within=NonNegativeReals, default=0.0, initialize=cold_start_costs) # units are $.

    ##################################################################################
    # shutdown cost for each generator. in the literature, these are often set to 0. #
    ##################################################################################

    model.ShutdownCostCoefficient = Param(model.Generators, within=NonNegativeReals, default=0.0, initialize=shutdown_cost_coefficient) # units are $.


def _minimum_production_cost_fn(m, g):
    # Minimum production cost (needed because Piecewise constraint on ProductionCost
    # has to have lower bound of 0, so the unit can cost 0 when off -- this is added
    # back in to the objective if a unit is on
    if len(m.CostPiecewisePoints[g]) > 1:
        return m.CostPiecewiseValues[g].first() * m.FuelCost[g]
    elif len(m.CostPiecewisePoints[g]) == 1:
        # If there's only one piecewise point given, that point should be (MaxPower, MaxCost) -- i.e. the cost function is linear through (0,0),
        # so we can find the slope of the line and use that to compute the cost of running at minimum generation
        return m.MinimumPowerOutput[g] * (m.CostPiecewiseValues[g].first() / m.MaximumPowerOutput[g]) * m.FuelCost[g]
    else:
        return  m.FuelCost[g] * \
               (m.ProductionCostA0[g] + \
                m.ProductionCostA1[g] * m.MinimumPowerOutput[g] + \
                m.ProductionCostA2[g] * m.MinimumPowerOutput[g]**2)


def minimum_production_cost(model, minimum_production_cost=_minimum_production_cost_fn):
    model.MinimumProductionCost = Param(model.Generators, within=NonNegativeReals, initialize=_minimum_production_cost_fn, mutable=True)


def quadratic_cost_coefficients(model, production_cost_a=None, production_cost_b=None, production_cost_c=None):
    ##################################################################################################################
    # production cost coefficients (for the quadratic) a0=constant, a1=linear coefficient, a2=quadratic coefficient. #
    ##################################################################################################################

    #\a_j
    model.ProductionCostA0 = Param(model.Generators, default=0.0) # units are $/hr (or whatever the time unit is).
    #\b_j
    model.ProductionCostA1 = Param(model.Generators, default=0.0) # units are $/MWhr.
    #\c_j
    model.ProductionCostA2 = Param(model.Generators, default=0.0) # units are $/(MWhr^2).


def piece_wise_linear_cost(model, points=None, values=None):
    # production cost associated with each generator, for each time period.
    model.CostPiecewisePoints = Set(model.Generators, initialize=points, ordered=True)
    #click.echo("In model generator.py piece_wise_linear_cost - printing CostPiecewisePoints: " + str(model.CostPiecewisePoints))
    model.CostPiecewiseValues = Set(model.Generators, initialize=values, ordered=True)

def fuel_cost(model, fuel_cost=1):

    model.FuelCost = Param(model.Generators, default=1.0, initialize=fuel_cost)


# a function for use in piecewise linearization of the cost function.
def production_cost_function(m, g, t, x):
    return m.TimePeriodLength * m.PowerGenerationPiecewiseValues[g,t][x] * m.FuelCost[g]


def production_cost(model):

    model.PowerGenerationPiecewisePoints = {}
    model.PowerGenerationPiecewiseValues = {}
    #click.echo("In generators.py production_cost ")
    for g in model.Generators:
        for t in model.TimePeriods:
            power_generation_piecewise_points_rule(model, g, t)
    #print ('model.PowerGenerationPiecewisePoints: ', model.PowerGenerationPiecewisePoints)
    #print ('model.PowerGenerationPiecewiseValues: ', model.PowerGenerationPiecewiseValues)


def power_generation_piecewise_points_rule(m, g, t):
    #click.echo("In generators.py power_generation_piecewise_points_rule ")
    minimum_production_cost = value(m.MinimumProductionCost[g])
    if len(m.CostPiecewisePoints[g]) > 0:
        #click.echo("In model generator.py power_generation_piecewise_points_rule - printing list(m.CostPiecewisePoints[g]): " + str(list(m.CostPiecewisePoints[g])))
        m.PowerGenerationPiecewisePoints[g,t] = list(m.CostPiecewisePoints[g])
        temp = list(m.CostPiecewiseValues[g])
        #click.echo("In model generator.py power_generation_piecewise_points_rule - printing list(m.CostPiecewiseValues[g]): " + str(temp))
        m.PowerGenerationPiecewiseValues[g,t] = {}
        for i in range(len(m.CostPiecewisePoints[g])):
            m.PowerGenerationPiecewiseValues[g,t][m.PowerGenerationPiecewisePoints[g,t][i]] = temp[i] - minimum_production_cost
        # MinimumPowerOutput will be one of our piecewise points, so it is safe to add (0,0)
        if m.PowerGenerationPiecewisePoints[g,t][0] != 0:
            m.PowerGenerationPiecewisePoints[g,t].insert(0,0)
        m.PowerGenerationPiecewiseValues[g,t][0] = 0
    elif value(m.ProductionCostA2[g]) == 0:
        # If cost is linear, we only need two points -- (0,CostA0-MinCost) and (MaxOutput, MaxCost)
        m.PowerGenerationPiecewisePoints[g, t] = [0, value(m.MaximumPowerOutput[g])]
        m.PowerGenerationPiecewiseValues[g,t] = {}
        m.PowerGenerationPiecewiseValues[g,t][0] = value(m.ProductionCostA0[g]) - minimum_production_cost
        m.PowerGenerationPiecewiseValues[g,t][m.PowerGenerationPiecewisePoints[g,t][1]] = \
                value(m.ProductionCostA0[g]) + \
                value(m.ProductionCostA1[g]) * m.PowerGenerationPiecewisePoints[g, t][1] \
                - minimum_production_cost
    else:
        min_power = value(m.MinimumPowerOutput[g])
        max_power = value(m.MaximumPowerOutput[g])
        n = value(m.NumGeneratorCostCurvePieces)
        #click.echo("In generators.py n: " + str(n))
        width = (max_power - min_power) / float(n)
        if width == 0:
            m.PowerGenerationPiecewisePoints[g, t] = [min_power]
        else:
            m.PowerGenerationPiecewisePoints[g, t] = [min_power + i*width for i in range(0,n+1)]
            # NOTE: due to numerical precision limitations, the last point in the x-domain
            #       of the generation piecewise cost curve may not be precisely equal to the
            #       maximum power output level of the generator. this can cause Piecewise to
            #       sqawk, as it would like the upper bound of the variable to be represented
            #       in the domain. so, we will make it so.
            m.PowerGenerationPiecewisePoints[g, t][-1] = max_power
        m.PowerGenerationPiecewiseValues[g,t] = {}
        for i in range(n+1):
            m.PowerGenerationPiecewiseValues[g,t][m.PowerGenerationPiecewisePoints[g,t][i]] = \
                       value(m.ProductionCostA0[g]) + \
                       value(m.ProductionCostA1[g]) * m.PowerGenerationPiecewisePoints[g, t][i] + \
                       value(m.ProductionCostA2[g]) * m.PowerGenerationPiecewisePoints[g, t][i]**2 \
                       - minimum_production_cost
        if m.PowerGenerationPiecewisePoints[g, t][0] != 0:
            m.PowerGenerationPiecewisePoints[g, t].insert(0,0)
            m.PowerGenerationPiecewiseValues[g, t][0] = 0

