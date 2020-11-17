from pyomo.environ import *

def create_model():
    model = ConcreteModel()
    return model

def initialize_buses(model,
                    bus_names=None,
                    ):

    model.Buses = Set(ordered=True, initialize=bus_names)


# def initialize_zones(model,
                    # zone_names=None,
                    # buses_at_each_zone=None
                    # ):

    # model.Zones = Set(ordered=True, initialize=zone_names)
    # model.BusesAtEachZone = Set(model.Zones, initialize=buses_at_each_zone)

def initialize_time_periods(model,
                    time_periods=None,
                    time_period_length=1.0
                    ):

    if time_periods is None:
        number_of_time_periods = None
    else:
        number_of_time_periods = len(time_periods)

    model.TimePeriods = Set(initialize=time_periods)
    model.NumTimePeriods = Param(initialize=number_of_time_periods)
    model.TimePeriodLength = Param(initialize=time_period_length)

def initialize_model(model,
                    time_period_length=1.0,
                    stage_set=['FirstStage', 'SecondStage'],
                    positive_mismatch_penalty=1e5,
                    negative_mismatch_penalty=1e5
                    ):

    model.CostCurveType = Param(mutable=True)

    model.StageSet = Set(initialize=stage_set)

    model.CommitmentTimeInStage = Set(model.StageSet,
                                      within=model.TimePeriods,
                                     initialize={'FirstStage': model.TimePeriods,
                                                'SecondStage': list()})

    model.GenerationTimeInStage = Set(model.StageSet,
                                      within=model.TimePeriods,
                                     initialize={'FirstStage': list(),
                                                'SecondStage': model.TimePeriods})

    model.CommitmentStageCost = Var(model.StageSet, within=NonNegativeReals)
    model.GenerationStageCost = Var(model.StageSet, within=NonNegativeReals)

    model.StageCost = Var(model.StageSet, within=NonNegativeReals)

    # model.TotalLoadBenefit = Var(within=NonNegativeReals, initialize=0)

    model.PowerGeneratedT0 = Var(model.Generators, within=NonNegativeReals)

    # indicator variables for each generator, at each time period.
    model.UnitOn = Var(model.Generators, model.TimePeriods, within=Binary, initialize=1) #previously initialised to 1.

    # amount of power flowing along each line, at each time period
    model.LinePower = Var(model.TransmissionLines, model.TimePeriods, initialize=0)

    model.NetPowerInjectionAtBus = Var(model.Buses, model.TimePeriods, initialize=0)

    # Demand related variables
    # TotalDemand can be used to handle all kinds of loads, NDGs and DERs
    model.TotalDemand = Var(model.TimePeriods, within=NonNegativeReals)

    #TotalNetLoad is not required
    #model.TotalNetLoad considers the price-sensitive load, potentially DERs in the future
    # model.TotalNetLoad = Var(model.TimePeriods, within=NonNegativeReals)

    #\Lambda
    model.LoadPositiveMismatchPenalty = Param(within=NonNegativeReals, initialize=positive_mismatch_penalty)
    model.LoadNegativeMismatchPenalty = Param(within=NonNegativeReals, initialize=negative_mismatch_penalty)

    # amount of power produced by each generator, at each time period.
    def power_bounds_rule(m, g, t):
        return (0.0, m.MaximumPowerOutput[g])
#        return (m.MinimumPowerOutput[g], m.MaximumPowerOutput[g])

    # TODO within=NonNegativeReals should be changed to within=Reals
    model.PowerGenerated = Var(model.Generators, model.TimePeriods, within=NonNegativeReals, bounds=power_bounds_rule)

    # maximum power output for each generator, at each time period.
    model.MaximumPowerAvailable = Var(model.Generators, model.TimePeriods, within=NonNegativeReals)

    # minimum possible power output for each generator, at each time period.
    model.MinimumPowerAvailable = Var(model.Generators, model.TimePeriods, within=NonNegativeReals)

    # voltage angles at the buses (S) (lock the first bus at 0) in radians
    model.Angle = Var(model.Buses, model.TimePeriods, within=Reals, bounds=(-3.14159265,3.14159265))

    ###################
    # cost components #
    ###################

    # production cost associated with each generator, for each time period.
    model.ProductionCost = Var(model.Generators, model.TimePeriods, within=NonNegativeReals)

    # startup and shutdown costs for each generator, each time period.
    model.StartupCost = Var(model.Generators, model.TimePeriods, within=NonNegativeReals)
    model.ShutdownCost = Var(model.Generators, model.TimePeriods, within=NonNegativeReals)

    # (implicit) binary denoting whether starting up a generator will cost HotStartCost or ColdStartCost
    model.HotStart = Var(model.Generators, model.TimePeriods, bounds=(0,1))

    #################
    # Load Mismatch #
    #################

    model.LoadGenerateMismatch = Var(model.Buses, model.TimePeriods, within = Reals, initialize=0)
    model.posLoadGenerateMismatch = Var(model.Buses, model.TimePeriods, within = NonNegativeReals, initialize=0)
    model.negLoadGenerateMismatch = Var(model.Buses, model.TimePeriods, within = NonNegativeReals, initialize=0)

    model.GlobalReserveMismatch = Var(model.TimePeriods, within = Reals, initialize=0)
    model.posGlobalReserveMismatch = Var(model.TimePeriods, within = NonNegativeReals, initialize=0)
    model.negGlobalReserveMismatch = Var(model.TimePeriods, within = NonNegativeReals, initialize=0)

    # model.GlobalLoadGenerateMismatch = Var(model.TimePeriods, within = Reals, initialize=0)
    # model.posGlobalLoadGenerateMismatch = Var(model.TimePeriods, within = NonNegativeReals, initialize=0)
    # model.negGlobalLoadGenerateMismatch = Var(model.TimePeriods, within = NonNegativeReals, initialize=0)
