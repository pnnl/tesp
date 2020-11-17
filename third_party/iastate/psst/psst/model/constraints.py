import numpy as np
from functools import partial
import click
import logging

from pyomo.environ import *

logger = logging.getLogger(__file__)

eps = 1e-3

def fix_first_angle_rule(m,t, slack_bus=1):
    return m.Angle[m.Buses[slack_bus], t] == 0.0

def lower_line_power_bounds_rule(m, l, t):
    if m.EnforceLine[l] and np.any(np.absolute(m.ThermalLimit[l]) > eps):
        return -m.ThermalLimit[l] <= m.LinePower[l, t]
    else:
        return Constraint.Skip

def upper_line_power_bounds_rule(m, l, t):
    if m.EnforceLine[l] and np.any(np.absolute(m.ThermalLimit[l]) > eps):
        return m.ThermalLimit[l] >= m.LinePower[l, t]
    else:
        return Constraint.Skip

def line_power_ptdf_rule(m, l, t):
    return m.LinePower[l,t] == sum(float(m.PTDF[l, i]) * m.NetPowerInjectionAtBus[b, t] for i, b in enumerate(m.Buses))

def line_power_rule(m, l, t):
    if m.B[l] == 99999999:
        logger.debug(" Line Power Angle constraint skipped for line between {} and {} ".format(m.BusFrom[l], m.BusTo[l]))
        return Constraint.Skip
    else:
        return m.LinePower[l,t] == m.B[l] * (m.Angle[m.BusFrom[l], t] - m.Angle[m.BusTo[l], t])

def calculate_total_demand(m, t, PriceSenLoadFlag=False):
    constraint = sum(m.Demand[b,t] for b in m.Buses)

    if PriceSenLoadFlag is True:
        constraint = constraint + sum(sum(m.PSLoadDemand[l,t] for l in m.PriceSensitiveLoadsAtBus[b]) for b in m.Buses)

    constraint = m.TotalDemand[t] == constraint

    return constraint

# def calculate_total_net_load(m, t):
    # return m.TotalNetLoad[t] == sum(m.Demand[b,t] for b in m.Buses) + sum(m.PSLoadDemand[l,t] for l in m.PriceSensitiveLoadsAtBus)

def neg_load_generate_mismatch_tolerance_rule(m, b):
   return sum((m.negLoadGenerateMismatch[b,t] for t in m.TimePeriods)) >= 0.0

def pos_load_generate_mismatch_tolerance_rule(m, b):
   return sum((m.posLoadGenerateMismatch[b,t] for t in m.TimePeriods)) >= 0.0

def neg_global_reserve_mismatch_tolerance_rule(m):
   return sum((m.negGlobalReserveMismatch[t] for t in m.TimePeriods)) >= 0.0

def pos_global_reserve_mismatch_tolerance_rule(m):
   return sum((m.posGlobalReserveMismatch[t] for t in m.TimePeriods)) >= 0.0

# (35)
def power_balance(m, b, t, StorageFlag=False, NDGFlag=False, PriceSenLoadFlag=False):
    # Power balance at each node (S)
    # bus b, time t (S)

    constraint = m.NetPowerInjectionAtBus[b, t] + sum(m.LinePower[l,t] for l in m.LinesTo[b]) \
           - sum(m.LinePower[l,t] for l in m.LinesFrom[b]) \
           + m.LoadGenerateMismatch[b,t] == 0

    return constraint

##  This function defines m.NetPowerInjectionAtBus[b, t] constraint
def net_power_at_bus_rule(m, b, t, StorageFlag=False, NDGFlag=False, PriceSenLoadFlag=False):
    constraint = sum((1 - m.GeneratorForcedOutage[g,t]) * m.GeneratorBusContributionFactor[g, b] * m.PowerGenerated[g, t] for g in m.GeneratorsAtBus[b])

    if StorageFlag is True:
        constraint = constraint + sum(m.PowerOutputStorage[s, t] for s in m.StorageAtBus[b]) \
           - sum(m.PowerInputStorage[s, t] for s in m.StorageAtBus[b])

    if NDGFlag is True:
        constraint = constraint + sum(m.NondispatchablePower[g, t] for g in m.NondispatchableGeneratorsAtBus[b])

    # if NDGFlag is True:
        # constraint = constraint + sum(m.NondispatchablePowerUsed[g, t] for g in m.NondispatchableGeneratorsAtBus[b])

    constraint = constraint + m.LoadGenerateMismatch[b,t]

    constraint = constraint - m.Demand[b, t]

    if PriceSenLoadFlag is True:
        constraint = constraint - sum(m.PSLoadDemand[l,t] for l in m.PriceSensitiveLoadsAtBus[b])


    constraint = m.NetPowerInjectionAtBus[b, t] == constraint

    return constraint


# give meaning to the positive and negative parts of the mismatch
# def posneg_rule(m, b, t):
    # return m.posLoadGenerateMismatch[b, t] - m.negLoadGenerateMismatch[b, t] == m.LoadGenerateMismatch[b, t]

#(36)
def pos_rule(m, b, t):
    return m.posLoadGenerateMismatch[b, t] >= m.LoadGenerateMismatch[b, t]

#(37)
def neg_rule(m, b, t):
    return m.negLoadGenerateMismatch[b, t] >= - m.LoadGenerateMismatch[b, t]


def pos_global_reserve_rule(m, t):
    return m.posGlobalReserveMismatch[t] >= m.GlobalReserveMismatch[t]

def neg_global_reserve_rule(m, t):
    return m.negGlobalReserveMismatch[t] >= - m.GlobalReserveMismatch[t]


# def global_posneg_rule(m, t):
    # return m.posGlobalLoadGenerateMismatch[t] - m.negGlobalLoadGenerateMismatch[t] == m.GlobalLoadGenerateMismatch[t]

# def enforce_reserve_requirements_rule(m, t, StorageFlag=False,
                                        # NDGFlag=False,
                                        # has_global_reserves=False):

    # constraint = sum(m.MaximumPowerAvailable[g, t] for g in m.Generators)

    # if NDGFlag is True:
        # constraint = constraint + sum(m.NondispatchablePowerUsed[n,t] for n in m.NondispatchableGenerators)

    # if StorageFlag is True:
        # constraint = constraint + sum(m.PowerOutputStorage[s,t] for s in m.Storage)

    # if has_global_reserves is True:
        # constraint = constraint - m.ReserveRequirement[t]

    # constraint = constraint == m.TotalDemand[t] + m.GlobalLoadGenerateMismatch[t]
    ##constraint = constraint >= m.TotalDemand[t] 

    # return constraint

def enforce_reserve_up_requirements_rule(m, t, StorageFlag=False,
                                        NDGFlag=False,
                                        PriceSenLoadFlag=False,
                                        has_global_reserves=False):

    constraint = sum(m.MaximumPowerAvailable[g, t] for g in m.Generators)

    if NDGFlag is True:
        constraint = constraint + sum(m.NondispatchablePowerUsed[n,t] for n in m.NondispatchableGenerators)

    # if StorageFlag is True:
        # constraint = constraint + sum(m.PowerOutputStorage[s,t] for s in m.Storage)

    if has_global_reserves is True:
        constraint = constraint - m.ReserveUpRequirement[t]

    constraint = constraint == m.TotalDemand[t] + m.GlobalReserveMismatch[t]

    # if PriceSenLoadFlag is False:
    # constraint = constraint >= m.TotalDemand[t]
    # else:
        # # consider fixed loads and price sensitive loads
        # constraint = constraint >= m.TotalNetLoad[t]

    return constraint
def enforce_reserve_down_requirements_rule(m, t, StorageFlag=False,
                                        NDGFlag=False,
                                        PriceSenLoadFlag=False,
                                        has_global_reserves=False):

    constraint = sum(m.MinimumPowerAvailable[g, t] for g in m.Generators)

    if NDGFlag is True:
        constraint = constraint + sum(m.NondispatchablePowerUsed[n,t] for n in m.NondispatchableGenerators)

    # if StorageFlag is True:
        # constraint = constraint + sum(m.PowerOutputStorage[s,t] for s in m.Storage)

    if has_global_reserves is True:
        constraint = constraint + m.ReserveDownRequirement[t]

    constraint = constraint == m.TotalDemand[t] + m.GlobalReserveMismatch[t]

    # if PriceSenLoadFlag is False:
    # constraint = constraint <= m.TotalDemand[t]
    # else:
        # # consider fixed loads and price sensitive loads
        # constraint = constraint <= m.TotalNetLoad[t]

    return constraint

def enforce_zonal_reserve_down_requirement_rule(m, rz, t,
                                        PriceSenLoadFlag=False):
    constraint = sum(m.MinimumPowerAvailable[g, t] for g in m.GeneratorsInReserveZone[rz])

    if PriceSenLoadFlag is False:
        constraint = constraint <= (1 - m.ReserveDownZonalPercent[rz])* sum(m.Demand[d, t] for d in m.DemandInReserveZone[rz])
    else:
        constraint = constraint <= (1 - m.ReserveDownZonalPercent[rz]) * (sum(m.Demand[d, t] for d in m.DemandInReserveZone[rz]) + sum(m.PSLoadDemand[l,t] for l in m.PriceSenLoadInReserveZone[rz]))

    return constraint
    # return sum(m.MinimumPowerAvailable[g, t] for g in m.GeneratorsInReserveZone[rz]) <= (1 - m.ReserveDownZonalPercent[rz])* sum(m.Demand[d, t] for d in m.DemandInReserveZone[rz])

def enforce_zonal_reserve_up_requirement_rule(m, rz, t,
                                        PriceSenLoadFlag=False):
    constraint = sum(m.MaximumPowerAvailable[g, t] for g in m.GeneratorsInReserveZone[rz])

    if PriceSenLoadFlag is False:
        constraint = constraint >= (1 + m.ReserveUpZonalPercent[rz]) * sum(m.Demand[d, t] for d in m.DemandInReserveZone[rz])
    else:
        constraint = constraint >= (1 + m.ReserveUpZonalPercent[rz]) * (sum(m.Demand[d, t] for d in m.DemandInReserveZone[rz]) + sum(m.PSLoadDemand[l,t] for l in m.PriceSenLoadInReserveZone[rz]))

    return constraint
    # return sum(m.MaximumPowerAvailable[g, t] for g in m.GeneratorsInReserveZone[rz]) >= (1 + m.ReserveUpZonalPercent[rz])* sum(m.Demand[d, t] for d in m.DemandInReserveZone[rz])

# def calculate_regulating_reserve_up_available_per_generator(m, g, t):
    # return m.RegulatingReserveUpAvailable[g, t] == m.MaximumPowerAvailable[g,t] - m.PowerGenerated[g,t]

# def enforce_zonal_reserve_requirement_rule(m, rz, t):
    # return sum(m.RegulatingReserveUpAvailable[g,t] for g in m.GeneratorsInReserveZone[rz]) >= m.ZonalReserveRequirement[rz, t]

# def enforce_generator_output_limits_rule_part_a(m, g, t):
   # return m.MinimumPowerOutput[g] * m.UnitOn[g, t] <= m.PowerGenerated[g,t]

def enforce_generator_output_limits_rule_part_a(m, g, t):
   return m.MinimumPowerAvailable[g,t] <= m.PowerGenerated[g,t]

def enforce_generator_output_limits_rule_part_b(m, g, t):
   return m.PowerGenerated[g,t] <= m.MaximumPowerAvailable[g, t]

def enforce_generator_output_limits_rule_part_c(m, g, t):
   return m.MaximumPowerAvailable[g,t] <= m.MaximumPowerOutput[g] * m.UnitOn[g, t]

def enforce_generator_output_limits_rule_part_d(m, g, t):
   return m.MinimumPowerAvailable[g,t] >= m.MinimumPowerOutput[g] * m.UnitOn[g, t]

def enforce_max_available_ramp_up_rates_rule(m, g, t):
   # 4 cases, split by (t-1, t) unit status (RHS is defined as the delta from m.PowerGenerated[g, t-1])
   # (0, 0) - unit staying off:   RHS = maximum generator output (degenerate upper bound due to unit being off)
   # (0, 1) - unit switching on:  RHS = startup ramp limit
   # (1, 0) - unit switching off: RHS = standard ramp limit minus startup ramp limit plus maximum power output (degenerate upper bound due to unit off)
   # (1, 1) - unit staying on:    RHS = standard ramp limit plus power generated in previous time period
   if t == 0:
      return m.MaximumPowerAvailable[g, t] <= m.PowerGeneratedT0[g] + \
                                              m.NominalRampUpLimit[g] * m.UnitOnT0[g] + \
                                              m.StartupRampLimit[g] * (m.UnitOn[g, t] - m.UnitOnT0[g]) + \
                                              m.MaximumPowerOutput[g] * (1 - m.UnitOn[g, t])
   else:
      return m.MaximumPowerAvailable[g, t] <= m.PowerGenerated[g, t-1] + \
                                              m.NominalRampUpLimit[g] * m.UnitOn[g, t-1] + \
                                              m.StartupRampLimit[g] * (m.UnitOn[g, t] - m.UnitOn[g, t-1]) + \
                                              m.MaximumPowerOutput[g] * (1 - m.UnitOn[g, t])

def enforce_max_available_ramp_down_rates_rule(m, g, t):
    # 4 cases, split by (t, t+1) unit status
    # (0, 0) - unit staying off:   RHS = 0 (degenerate upper bound)
    # (0, 1) - unit switching on:  RHS = maximum generator output minus shutdown ramp limit (degenerate upper bound) - this is the strangest case.
    # (1, 0) - unit switching off: RHS = shutdown ramp limit
    # (1, 1) - unit staying on:    RHS = maximum generator output (degenerate upper bound)
    #NOTE: As expressed in Carrion-Arroyo and subsequently here, this constraint does NOT consider ramp down from initial conditions to t=1!
    #if t == value(m.NumTimePeriods):
    #   return Constraint.Skip
    #else:
    #   return m.MaximumPowerAvailable[g, t] <= \
            #          m.MaximumPowerOutput[g] * m.UnitOn[g, t+1] + \
            #          m.ShutdownRampLimit[g] * (m.UnitOn[g, t] - m.UnitOn[g, t+1])

    #This version fixes the problem with ignoring initial conditions mentioned in the above note

    if t == 0:
        return m.MaximumPowerAvailable[g, t] <= \
                m.MaximumPowerOutput[g] * m.UnitOn[g, t] + \
                m.ShutdownRampLimit[g] * (m.UnitOnT0[g] - m.UnitOn[g, t])
    else:
        return m.MaximumPowerAvailable[g, t-1] <= \
                m.MaximumPowerOutput[g] * m.UnitOn[g, t] + \
                m.ShutdownRampLimit[g] * (m.UnitOn[g, t-1] - m.UnitOn[g, t])

# Old Constraint (19) 
# def enforce_ramp_down_limits_rule(m, g, t):
    # # 4 cases, split by (t-1, t) unit status:
    # # (0, 0) - unit staying off:   RHS = maximum generator output (degenerate upper bound)
    # # (0, 1) - unit switching on:  RHS = standard ramp-down limit minus shutdown ramp limit plus maximum generator output - this is the strangest case
    # #NOTE: This may never be physically true, but if a generator has ShutdownRampLimit >> MaximumPowerOutput, this constraint causes problems
    # # (1, 0) - unit switching off: RHS = shutdown ramp limit
    # # (1, 1) - unit staying on:    RHS = standard ramp-down limit
    # if t == 0:
    #     return m.PowerGeneratedT0[g] - m.PowerGenerated[g, t] <= \
    #             m.NominalRampDownLimit[g] * m.UnitOn[g, t] + \
    #             m.ShutdownRampLimit[g]  * (m.UnitOnT0[g] - m.UnitOn[g, t]) + \
    #             m.MaximumPowerOutput[g] * (1 - m.UnitOnT0[g])
    # else:
    #    return m.PowerGenerated[g, t-1] - m.PowerGenerated[g, t] <= \
    #            m.NominalRampDownLimit[g]  * m.UnitOn[g, t] + \
    #            m.ShutdownRampLimit[g]  * (m.UnitOn[g, t-1] - m.UnitOn[g, t]) + \
    #            m.MaximumPowerOutput[g] * (1 - m.UnitOn[g, t-1])

# Modified Constraint (19) 
def enforce_ramp_down_limits_rule(m, g, t):
    # 4 cases, split by (t-1, t) unit status:
    # (0, 0) - unit staying off:   RHS = maximum generator output (degenerate upper bound)
    # (0, 1) - unit switching on:  RHS = standard ramp-down limit minus shutdown ramp limit plus maximum generator output - this is the strangest case
    #NOTE: This may never be physically true, but if a generator has ShutdownRampLimit >> MaximumPowerOutput, this constraint causes problems
    # (1, 0) - unit switching off: RHS = shutdown ramp limit
    # (1, 1) - unit staying on:    RHS = standard ramp-down limit
    if t == 0:
        return m.PowerGeneratedT0[g] - m.MinimumPowerAvailable[g, t] <= \
                m.NominalRampDownLimit[g] * m.UnitOn[g, t] + \
                m.ShutdownRampLimit[g]  * (m.UnitOnT0[g] - m.UnitOn[g, t]) + \
                m.MaximumPowerOutput[g] * (1 - m.UnitOnT0[g])
    else:
       return m.PowerGenerated[g, t-1] - m.MinimumPowerAvailable[g, t] <= \
               m.NominalRampDownLimit[g]  * m.UnitOn[g, t] + \
               m.ShutdownRampLimit[g]  * (m.UnitOn[g, t-1] - m.UnitOn[g, t]) + \
               m.MaximumPowerOutput[g] * (1 - m.UnitOn[g, t-1])

def enforce_ramp_up_limits_rule(m, g, t):
    # 4 cases, split by (t-1, t) unit status:
    # (0, 0) - unit staying off:   RHS = maximum generator output (degenerate upper bound)
    # (0, 1) - unit switching on:  RHS = standard ramp-down limit minus shutdown ramp limit plus maximum generator output - this is the strangest case
    #NOTE: This may never be physically true, but if a generator has ShutdownRampLimit >> MaximumPowerOutput, this constraint causes problems
    # (1, 0) - unit switching off: RHS = shutdown ramp limit
    # (1, 1) - unit staying on:    RHS = standard ramp-down limit
    if t == 0:
        return m.PowerGeneratedT0[g] - m.PowerGenerated[g, t] >= \
                -1 * ( m.NominalRampUpLimit[g] * m.UnitOn[g, t] ) + \
                -1 * ( m.StartupRampLimit[g]  * (m.UnitOnT0[g] - m.UnitOn[g, t]) ) + \
                -1 * ( m.MaximumPowerOutput[g] * (1 - m.UnitOnT0[g]) )
    else:
       return m.PowerGenerated[g, t-1] - m.PowerGenerated[g, t] >= \
               -1 * ( m.NominalRampUpLimit[g]  * m.UnitOn[g, t] ) + \
               -1 * ( m.StartupRampLimit[g]  * (m.UnitOn[g, t-1] - m.UnitOn[g, t]) ) + \
               -1 * ( m.MaximumPowerOutput[g] * (1 - m.UnitOn[g, t-1]) )


# compute startup costs for each generator, for each time period
def compute_hot_start_rule(m, g, t):
    if t <= value(m.ColdStartHours[g]):
        if t - value(m.ColdStartHours[g]) <= value(m.UnitOnT0State[g]):
            m.HotStart[g, t] = 1
            m.HotStart[g, t].fixed = True
            return Constraint.Skip
        else:
            return m.HotStart[g, t] <= sum( m.UnitOn[g, i] for i in range(1, t) )
    else:
        return m.HotStart[g, t] <= sum( m.UnitOn[g, i] for i in range(t - m.ColdStartHours[g], t) )


def compute_startup_costs_rule_minusM(m, g, t):
    if t == 0:
        return m.StartupCost[g, t] >= m.ColdStartCost[g] - (m.ColdStartCost[g] - m.HotStartCost[g])*m.HotStart[g, t] \
                                      - m.ColdStartCost[g]*(1 - (m.UnitOn[g, t] - m.UnitOnT0[g]))
    else:
        return m.StartupCost[g, t] >= m.ColdStartCost[g] - (m.ColdStartCost[g] - m.HotStartCost[g])*m.HotStart[g, t] \
                                      - m.ColdStartCost[g]*(1 - (m.UnitOn[g, t] - m.UnitOn[g, t-1]))


# compute the per-generator, per-time period shutdown costs.
def compute_shutdown_costs_rule(m, g, t):
    if t == 0:
        return m.ShutdownCost[g, t] >= m.ShutdownCostCoefficient[g] * (m.UnitOnT0[g] - m.UnitOn[g, t])
    else:
        return m.ShutdownCost[g, t] >= m.ShutdownCostCoefficient[g] * (m.UnitOn[g, t-1] - m.UnitOn[g, t])


def enforce_up_time_constraints_initial(m, g):
   if value(m.InitialTimePeriodsOnLine[g]) == 0:
      return Constraint.Skip
   return sum((1 - m.UnitOn[g, t]) for t in m.TimePeriods if (t+1) <= value(m.InitialTimePeriodsOnLine[g])) == 0.0 #Modified:Swathi - changed t to (t+1)


# constraint for each time period after that not involving the initial condition.
@simple_constraint_rule
def enforce_up_time_constraints_subsequent(m, g, t):
   if t <= value(m.InitialTimePeriodsOnLine[g]):
      # handled by the EnforceUpTimeConstraintInitial constraint.
      return Constraint.Skip
   elif t <= (value(m.NumTimePeriods - m.MinimumUpTime[g]) + 1):
      # the right-hand side terms below are only positive if the unit was off in the previous time period but on in this one =>
      # the value is the minimum number of subsequent consecutive time periods that the unit is required to be on.
      if t == 0:
         return sum(m.UnitOn[g, n] for n in m.TimePeriods if n >= t and n <= (t + value(m.MinimumUpTime[g]) - 1)) >= \
                m.MinimumUpTime[g] * (m.UnitOn[g, t] - m.UnitOnT0[g])
      else:
         return sum(m.UnitOn[g, n] for n in m.TimePeriods if n >= t and n <= (t + value(m.MinimumUpTime[g]) - 1)) >= \
                m.MinimumUpTime[g] * (m.UnitOn[g, t] - m.UnitOn[g, t-1])
   else:
      # handle the final (MinimumUpTime[g] - 1) time periods - if a unit is started up in
      # this interval, it must remain on-line until the end of the time span.
      if t == 0: # can happen when small time horizons are specified
         return sum((m.UnitOn[g, n] - (m.UnitOn[g, t] - m.UnitOnT0[g])) for n in m.TimePeriods if n >= t) >= 0.0
      else:
         return sum((m.UnitOn[g, n] - (m.UnitOn[g, t] - m.UnitOn[g, t-1])) for n in m.TimePeriods if n >= t) >= 0.0


# constraint due to initial conditions.
def enforce_down_time_constraints_initial(m, g):
   if value(m.InitialTimePeriodsOffLine[g]) == 0:
      return Constraint.Skip
   return sum(m.UnitOn[g, t] for t in m.TimePeriods if (t+1) <= value(m.InitialTimePeriodsOffLine[g])) == 0.0


# constraint for each time period after that not involving the initial condition.
@simple_constraint_rule
def enforce_down_time_constraints_subsequent(m, g, t):
   if t <= value(m.InitialTimePeriodsOffLine[g]):
      # handled by the EnforceDownTimeConstraintInitial constraint.
      return Constraint.Skip
   elif t <= (value(m.NumTimePeriods - m.MinimumDownTime[g]) + 1):
      # the right-hand side terms below are only positive if the unit was off in the previous time period but on in this one =>
      # the value is the minimum number of subsequent consecutive time periods that the unit is required to be on.
      if t == 0:
         return sum((1 - m.UnitOn[g, n]) for n in m.TimePeriods if n >= t and n <= (t + value(m.MinimumDownTime[g]) - 1)) >= \
                m.MinimumDownTime[g] * (m.UnitOnT0[g] - m.UnitOn[g, t])
      else:
         return sum((1 - m.UnitOn[g, n]) for n in m.TimePeriods if n >= t and n <= (t + value(m.MinimumDownTime[g]) - 1)) >= \
                m.MinimumDownTime[g] * (m.UnitOn[g, t-1] - m.UnitOn[g, t])
   else:
      # handle the final (MinimumDownTime[g] - 1) time periods - if a unit is shut down in
      # this interval, it must remain off-line until the end of the time span.
      if t == 0: # can happen when small time horizons are specified
         return sum(((1 - m.UnitOn[g, n]) - (m.UnitOnT0[g] - m.UnitOn[g, t])) for n in m.TimePeriods if n >= t) >= 0.0
      else:
         return sum(((1 - m.UnitOn[g, n]) - (m.UnitOn[g, t-1] - m.UnitOn[g, t])) for n in m.TimePeriods if n >= t) >= 0.0


def commitment_in_stage_st_cost_rule(m, st):
    return m.CommitmentStageCost[st] == (sum(m.StartupCost[g,t] + m.ShutdownCost[g,t] for g in m.Generators for t in m.CommitmentTimeInStage[st]) + sum(sum(m.UnitOn[g,t] for t in m.CommitmentTimeInStage[st]) * m.MinimumProductionCost[g] * m.TimePeriodLength for g in m.Generators))


def generation_in_stage_st_cost_rule(m, st):
    return m.GenerationStageCost[st] == sum(m.ProductionCost[g, t] for g in m.Generators for t in m.GenerationTimeInStage[st]) + m.LoadPositiveMismatchPenalty * m.TimePeriodLength *\
    (sum(m.posLoadGenerateMismatch[b, t] for b in m.Buses for t in m.GenerationTimeInStage[st])) + m.LoadNegativeMismatchPenalty * m.TimePeriodLength *\
    (sum(m.negLoadGenerateMismatch[b, t] for b in m.Buses for t in m.GenerationTimeInStage[st])) + m.LoadPositiveMismatchPenalty * m.TimePeriodLength *\
    (sum(m.posGlobalReserveMismatch[t] for t in m.GenerationTimeInStage[st])) + m.LoadNegativeMismatchPenalty * m.TimePeriodLength *\
    (sum(m.negGlobalReserveMismatch[t] for t in m.GenerationTimeInStage[st]))


# def load_benefit_rule(m):
    # return m.TotalLoadBenefit == sum(m.LoadBenefit[l, t] for l in m.PriceSensitiveLoads for t in m.TimePeriods)


def StageCost_rule(m, st):
    return m.StageCost[st] == m.GenerationStageCost[st] + m.CommitmentStageCost[st]


def total_cost_objective_rule(m, PriceSenLoadFlag=False):
    if (PriceSenLoadFlag is True):
        return (sum(m.LoadBenefit[l, t] for l in m.PriceSensitiveLoads for t in m.TimePeriods) - sum(m.StageCost[st] for st in m.StageSet))
    return sum(m.StageCost[st] for st in m.StageSet)


def constraint_net_power(model, StorageFlag=False, NDGFlag=False, PriceSenLoadFlag=False):
    partial_net_power_at_bus_rule = partial(net_power_at_bus_rule, StorageFlag=StorageFlag, NDGFlag=NDGFlag, PriceSenLoadFlag=PriceSenLoadFlag)
    model.CalculateNetPowerAtBus = Constraint(model.Buses, model.TimePeriods, rule=partial_net_power_at_bus_rule)


################################################

def constraint_line(model, ptdf=None, slack_bus=1):

    model.LinePowerConstraintLower = Constraint(model.TransmissionLines, model.TimePeriods, rule=lower_line_power_bounds_rule)
    model.LinePowerConstraintHigher = Constraint(model.TransmissionLines, model.TimePeriods, rule=upper_line_power_bounds_rule)

    if ptdf is not None:
        model.PTDF = ptdf
        model.CalculateLinePower = Constraint(model.TransmissionLines, model.TimePeriods, rule=line_power_ptdf_rule)
    else:
        partial_fix_first_angle_rule = partial(fix_first_angle_rule, slack_bus=slack_bus)
        model.FixFirstAngle = Constraint(model.TimePeriods, rule=partial_fix_first_angle_rule)
        model.CalculateLinePower = Constraint(model.TransmissionLines, model.TimePeriods, rule=line_power_rule)


def constraint_total_demand(model, PriceSenLoadFlag=False):
    partial_calculate_total_demand = partial(calculate_total_demand, PriceSenLoadFlag=PriceSenLoadFlag)
    model.CalculateTotalDemand = Constraint(model.TimePeriods, rule=partial_calculate_total_demand)


def constraint_load_generation_mismatch(model):
    model.PosLoadGenerateMismatchTolerance = Constraint(model.Buses, rule=pos_load_generate_mismatch_tolerance_rule)
    model.NegLoadGenerateMismatchTolerance = Constraint(model.Buses, rule=neg_load_generate_mismatch_tolerance_rule)
    model.DefinePosMismatch = Constraint(model.Buses, model.TimePeriods, rule = pos_rule)
    model.DefineNegMismatch = Constraint(model.Buses, model.TimePeriods, rule = neg_rule)

    # model.Global_Reserve_PosMismatchTolerance = Constraint(rule=pos_global_reserve_mismatch_tolerance_rule)
    # model.Global_Reserve_NegMismatchTolerance = Constraint(rule=neg_global_reserve_mismatch_tolerance_rule)
    model.Global_Reserve_DefinePosMismatch = Constraint(model.TimePeriods, rule = pos_global_reserve_rule)
    model.Global_Reserve_DefineNegMismatch = Constraint(model.TimePeriods, rule = neg_global_reserve_rule)
    #model.Defineposneg_Mismatch = Constraint(model.Buses, model.TimePeriods, rule = posneg_rule)
    #model.Global_Defineposneg_Mismatch = Constraint(model.TimePeriods, rule = global_posneg_rule)


def constraint_power_balance(model, StorageFlag=False, NDGFlag=False, PriceSenLoadFlag=False):

    fn_power_balance = partial(power_balance, StorageFlag=StorageFlag, NDGFlag=NDGFlag, PriceSenLoadFlag=PriceSenLoadFlag)
    model.PowerBalance = Constraint(model.Buses, model.TimePeriods, rule=fn_power_balance)


def constraint_reserves(model, StorageFlag=False,
                            NDGFlag=False,
                            PriceSenLoadFlag=False,
                            has_global_reserves=True,
                            has_regulating_reserves=True,
                            has_zonal_reserves=False):

    if has_global_reserves is True:
        # fn_enforce_reserve_requirements = partial(enforce_reserve_requirements_rule, StorageFlag=StorageFlag,
                                                # NDGFlag=NDGFlag,
                                                # has_global_reserves=has_global_reserves)
        fn_enforce_reserve_up_requirements = partial(enforce_reserve_up_requirements_rule, StorageFlag=StorageFlag,
                                                NDGFlag=NDGFlag,
                                                PriceSenLoadFlag=PriceSenLoadFlag,
                                                has_global_reserves=has_global_reserves)
        fn_enforce_reserve_down_requirements = partial(enforce_reserve_down_requirements_rule, StorageFlag=StorageFlag,
                                                NDGFlag=NDGFlag,
                                                PriceSenLoadFlag=PriceSenLoadFlag,
                                                has_global_reserves=has_global_reserves)
        #model.EnforceReserveRequirements = Constraint(model.TimePeriods, rule=fn_enforce_reserve_requirements)
        model.EnforceReserveUpRequirements = Constraint(model.TimePeriods, rule=fn_enforce_reserve_up_requirements)
        model.EnforceReserveDownRequirements = Constraint(model.TimePeriods, rule=fn_enforce_reserve_down_requirements)

    # if has_regulating_reserves is True:
        # model.CalculateRegulatingReserveUpPerGenerator = Constraint(model.Generators, model.TimePeriods, rule=calculate_regulating_reserve_up_available_per_generator)

    if has_zonal_reserves is True:
        fn_enforce_zonal_reserve_down_requirement_rule = partial(enforce_zonal_reserve_down_requirement_rule,
                                                PriceSenLoadFlag=PriceSenLoadFlag)
        fn_enforce_zonal_reserve_up_requirement_rule = partial(enforce_zonal_reserve_up_requirement_rule,
                                                PriceSenLoadFlag=PriceSenLoadFlag)
        model.EnforceZonalReserveDownRequirements = Constraint(model.ReserveZones, model.TimePeriods, rule=fn_enforce_zonal_reserve_down_requirement_rule)
        model.EnforceZonalReserveUpRequirements = Constraint(model.ReserveZones, model.TimePeriods, rule=fn_enforce_zonal_reserve_up_requirement_rule)
        # model.EnforceZonalReserveRequirements = Constraint(model.ReserveZones, model.TimePeriods, rule=enforce_zonal_reserve_requirement_rule)


def constraint_generator_power(model):

    model.EnforceGeneratorOutputLimitsPartA = Constraint(model.Generators, model.TimePeriods, rule=enforce_generator_output_limits_rule_part_a)
    model.EnforceGeneratorOutputLimitsPartB = Constraint(model.Generators, model.TimePeriods, rule=enforce_generator_output_limits_rule_part_b)
    model.EnforceGeneratorOutputLimitsPartC = Constraint(model.Generators, model.TimePeriods, rule=enforce_generator_output_limits_rule_part_c)
    model.EnforceGeneratorOutputLimitsPartD = Constraint(model.Generators, model.TimePeriods, rule=enforce_generator_output_limits_rule_part_d)
    model.EnforceMaxAvailableRampUpRates = Constraint(model.Generators, model.TimePeriods, rule=enforce_max_available_ramp_up_rates_rule)
    model.EnforceMaxAvailableRampDownRates = Constraint(model.Generators, model.TimePeriods, rule=enforce_max_available_ramp_down_rates_rule)
    model.EnforceNominalRampDownLimits = Constraint(model.Generators, model.TimePeriods, rule=enforce_ramp_down_limits_rule)
    model.EnforceNominalRampUpLimits = Constraint(model.Generators, model.TimePeriods, rule=enforce_ramp_up_limits_rule)


def constraint_up_down_time(model):

    model.EnforceUpTimeConstraintsInitial = Constraint(model.Generators, rule=enforce_up_time_constraints_initial)
    model.EnforceUpTimeConstraintsSubsequent = Constraint(model.Generators, model.TimePeriods, rule=enforce_up_time_constraints_subsequent)

    model.EnforceDownTimeConstraintsInitial = Constraint(model.Generators, rule=enforce_down_time_constraints_initial)
    model.EnforceDownTimeConstraintsSubsequent = Constraint(model.Generators, model.TimePeriods, rule=enforce_down_time_constraints_subsequent)


def production_cost_function(m, g, t, x):
    # a function for use in piecewise linearization of the cost function.
    # print('production_cost_function: ', g, t, x)
    return m.TimePeriodLength * m.PowerGenerationPiecewiseValues[g,t][x] * m.FuelCost[g]


def load_benefit_function(m, g, t, x):
    # a function for use in piecewise linearization of the price sensitive load benefit function.
    # print ('load_benefit_function: ',g,t,int(x))
    return m.TimePeriodLength * m.LoadDemandPiecewiseValues[g,t][x]


def constraint_for_cost(model):

    model.ComputeProductionCosts = Piecewise(model.Generators * model.TimePeriods, model.ProductionCost, model.PowerGenerated, pw_pts=model.PowerGenerationPiecewisePoints, f_rule=production_cost_function, pw_constr_type='LB', warning_tol=1e-20)

    model.ComputeHotStart = Constraint(model.Generators, model.TimePeriods, rule=compute_hot_start_rule)
    model.ComputeStartupCostsMinusM = Constraint(model.Generators, model.TimePeriods, rule=compute_startup_costs_rule_minusM)
    model.ComputeShutdownCosts = Constraint(model.Generators, model.TimePeriods, rule=compute_shutdown_costs_rule)

    model.Compute_commitment_in_stage_st_cost = Constraint(model.StageSet, rule = commitment_in_stage_st_cost_rule)

    model.Compute_generation_in_stage_st_cost = Constraint(model.StageSet, rule = generation_in_stage_st_cost_rule)

    model.Compute_Stage_Cost = Constraint(model.StageSet, rule = StageCost_rule)


def constraint_for_benefit(model):

    model.ComputePSLoadBenefits = Piecewise(model.PriceSensitiveLoads * model.TimePeriods, model.LoadBenefit, model.PSLoadDemand, pw_pts=model.LoadDemandPiecewisePoints, f_rule=load_benefit_function, pw_constr_type='UB', warning_tol=1e-20)
    # model.ComputeTotalBenefit = Constraint(rule=load_benefit_rule)


def objective_function(model, PriceSenLoadFlag=False):
    if PriceSenLoadFlag is False:
        model.TotalCostObjective = Objective(rule=total_cost_objective_rule, sense=minimize)
    else:
        partial_total_cost_objective_rule = partial(total_cost_objective_rule, PriceSenLoadFlag=PriceSenLoadFlag)
        model.TotalCostObjective = Objective(rule=partial_total_cost_objective_rule, sense=maximize)