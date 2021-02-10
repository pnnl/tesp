
from pyomo.environ import *


def initialize_demand(model, demand=None):

    model.Demand = Param(model.Buses, model.TimePeriods, initialize=demand, default=0.0, mutable=True)




