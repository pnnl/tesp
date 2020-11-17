from pyomo.environ import *

def initialize_price_senstive_load(model,
                        price_sensitive_load_names=None,
                        price_sensitive_load_at_bus=None):

    model.PriceSensitiveLoads = Set(initialize=price_sensitive_load_names)
    model.PriceSensitiveLoadsAtBus = Set(model.Buses, initialize=price_sensitive_load_at_bus)



def maximum_minimum_power_demand_loads(model, minimum_power_demand=None, maximum_power_demand=None):

    model.MinimumPowerDemand = Param(model.PriceSensitiveLoads,model.TimePeriods, initialize=minimum_power_demand, within=NonNegativeReals, default=0.0)
    model.MaximumPowerDemand = Param(model.PriceSensitiveLoads,model.TimePeriods, initialize=maximum_power_demand, within=NonNegativeReals, default=0.0)

def piece_wise_linear_benefit(model, points=None, values=None):
    # benefits associated with each price-sensitive load, for each time period.
    model.BenefitPiecewisePoints = Param(model.PriceSensitiveLoads,model.TimePeriods, initialize=points)
    model.BenefitPiecewiseValues = Param(model.PriceSensitiveLoads,model.TimePeriods, initialize=values)

def quadratic_benefit_coefficients(model, coefficient_c0=None, coefficient_c1=None, coefficient_c2=None):
    ##################################################################################################################
    # demand benefit coefficients (for the quadratic) c0=constant, c1=linear coefficient, c2=quadratic coefficient. #
    ##################################################################################################################
    #\e_j
    model.BenifitCoefficientC0 = Param(model.PriceSensitiveLoads,model.TimePeriods, default=0.0, initialize=coefficient_c0) # units are $/hr (or whatever the time unit is).
    #\d_j
    model.BenifitCoefficientC1 = Param(model.PriceSensitiveLoads,model.TimePeriods, default=0.0, initialize=coefficient_c1) # units are $/MWhr.
    #\f_j
    model.BenifitCoefficientC2 = Param(model.PriceSensitiveLoads,model.TimePeriods, default=0.0, initialize=coefficient_c2) # units are $/(MWhr^2).


def initialize_load_demand(model):
    # amount of power consumed by load, at each time period.
    def demand_bounds_rule(m, l, t):
        return (m.MinimumPowerDemand[l,t], m.MaximumPowerDemand[l,t])

    model.PSLoadDemand = Var(model.PriceSensitiveLoads, model.TimePeriods, within=NonNegativeReals, bounds=demand_bounds_rule)
    model.LoadBenefit = Var(model.PriceSensitiveLoads, model.TimePeriods, within=NonNegativeReals)

def load_benefit(model):

    model.LoadDemandPiecewisePoints = {}
    model.LoadDemandPiecewiseValues = {}
    #click.echo("In generators.py production_cost ")
    for l in model.PriceSensitiveLoads:
        for t in model.TimePeriods:
            load_demand_piecewise_points_rule(model, l, t)
    #print ('m.LoadDemandPiecewisePoints: ',model.LoadDemandPiecewisePoints)
    #print ('m.LoadDemandPiecewiseValues: ',model.LoadDemandPiecewiseValues)

def load_demand_piecewise_points_rule(m, l, t):
    #click.echo("In generators.py power_generation_piecewise_points_rule ")
    #maximum_demand_benefit = value(m.MinimumProductionCost[g])
    if len(m.BenefitPiecewisePoints[l,t]) > 0:
        #click.echo("In model generator.py power_generation_piecewise_points_rule - printing list(m.CostPiecewisePoints[g]): " + str(list(m.CostPiecewisePoints[g])))
        m.LoadDemandPiecewisePoints[l,t] = list(m.BenefitPiecewisePoints[l,t])
        #m.LoadDemandPiecewiseValues[l,t] = list(m.BenefitPiecewiseValues[l,t])
        temp = list(m.BenefitPiecewiseValues[l,t])
        #click.echo("In model generator.py power_generation_piecewise_points_rule - printing list(m.CostPiecewiseValues[g]): " + str(temp))
        m.LoadDemandPiecewiseValues[l,t] = {}
        for i in range(len(m.BenefitPiecewisePoints[l,t])):
            #print ('m.LoadDemandPiecewisePoints[l,t][i] ',m.LoadDemandPiecewisePoints[l,t][i])
            m.LoadDemandPiecewiseValues[l,t][m.LoadDemandPiecewisePoints[l,t][i]] = temp[i]
        # MinimumPowerOutput will be one of our piecewise points, so it is safe to add (0,0)
        # TODO: we need to check if this applies to price sensitive loads
        if m.BenefitPiecewisePoints[l,t][0] != 0:
            m.BenefitPiecewisePoints[l,t].insert(0,0)
        m.BenefitPiecewiseValues[l,t][0] = 0
    elif value(m.BenifitCoefficientC2[l,t]) == 0:
        # If cost is linear, we only need two points -- (0,CostA0-MinCost) and (MaxOutput, MaxCost)
        m.BenefitPiecewiseValues[l, t] = [value(m.MinimumPowerDemand[l]), value(m.MaximumPowerDemand[l])]
        m.BenefitPiecewiseValues[l,t] = {}
        m.BenefitPiecewiseValues[l,t][0] = value(m.BenifitCoefficientC0[l,t])
        m.BenefitPiecewiseValues[l,t][m.BenefitPiecewisePoints[l,t][1]] = \
                value(m.BenifitCoefficientC0[l,t]) + \
                value(m.BenifitCoefficientC1[l,t]) * m.BenefitPiecewisePoints[l, t][1]
    else:
        min_power = value(m.MinimumPowerDemand[l])
        max_power = value(m.MaximumPowerDemand[l])
        # TODO: we need to find where this is coming from since builder.py is not used
        n = value(m.NumGeneratorCostCurvePieces)
        #click.echo("In generators.py n: " + str(n))
        width = (max_power - min_power) / float(n)
        if width == 0:
            m.BenefitPiecewisePoints[l, t] = [min_power]
        else:
            m.BenefitPiecewisePoints[l, t] = [min_power + i*width for i in range(0,n+1)]
            # NOTE: due to numerical precision limitations, the last point in the x-domain
            #       of the generation piecewise cost curve may not be precisely equal to the
            #       maximum power output level of the generator. this can cause Piecewise to
            #       sqawk, as it would like the upper bound of the variable to be represented
            #       in the domain. so, we will make it so.
            m.BenefitPiecewisePoints[l, t][-1] = max_power
        m.BenefitPiecewiseValues[l,t] = {}
        for i in range(n+1):
            m.BenefitPiecewiseValues[l,t][m.BenefitPiecewisePoints[l,t][i]] = \
                       value(m.BenifitCoefficientC0[l,t]) + \
                       value(m.BenifitCoefficientC1[l,t]) * m.BenefitPiecewisePoints[l, t][i] + \
                       value(m.BenifitCoefficientC2[l,t]) * m.BenefitPiecewisePoints[l, t][i]**2
        if m.BenefitPiecewisePoints[l, t][0] != 0:
            m.BenefitPiecewisePoints[l, t].insert(0,0)
            m.BenefitPiecewiseValues[l, t][0] = 0
