from pyomo.environ import *



def initialize_network(model,
                    transmission_lines=None,
                    bus_from=None,
                    bus_to=None):

    model.TransmissionLines = Set(initialize=transmission_lines)

    model.BusFrom = Param(model.TransmissionLines, initialize=bus_from)
    model.BusTo = Param(model.TransmissionLines, initialize=bus_to)




# Alternative to lines_to
def _derive_connections_to(m, b):
   return (l for l in m.TransmissionLines if m.BusTo[l]==b)

# Alternative to lines_from
def _derive_connections_from(m, b):
   return (l for l in m.TransmissionLines if m.BusFrom[l]==b)


def derive_network(model,
                lines_from=_derive_connections_from,
                lines_to=_derive_connections_to):

    model.LinesTo = Set(model.Buses, initialize=lines_to)
    model.LinesFrom = Set(model.Buses, initialize=lines_from)




def _get_b_from_Reactance(m, l):
    if m.Reactance[l] < 0:
        return 0
    if m.Reactance[l] == 0:
        return 99999999
    else:
        return 1/float(m.Reactance[l])


def calculate_network_parameters(model,
                                reactance=None,
                                suseptance=_get_b_from_Reactance):

    model.Reactance = Param(model.TransmissionLines, initialize=reactance)
    model.B = Param(model.TransmissionLines, initialize=suseptance)


def enforce_thermal_limits(model,
                        thermal_limit=None,
                        enforce_line=True):

    model.ThermalLimit = Param(model.TransmissionLines, initialize=thermal_limit)
    model.EnforceLine = Param(model.TransmissionLines, initialize=enforce_line)

