import os
import click


generator_data_str_format = '{bus}\t{Pg}\t{Qg}\t{Qmax}\t{Qmin}\t{Vg}\t{mBase}\t{status}\t{Pmax}\t{Pmin}\t{Pc1}\t{Pc2}\t{Qc1min}\t{Qc1max}\t{Qc2min}\t{Qc2max}\t{ramp_agc}\t{ramp_10}\t{ramp_30}\t{ramp_q}\t{apf}'.format

current_directory = os.path.realpath(os.path.dirname(__file__))
#click.echo("printing current_directory: " + current_directory)


def int_else_float_except_string(s):
    try:
        f = float(s.replace(',', '.'))
        i = int(f)
        return i if i==f else f
    except ValueError:
        return s


def has_number(string):
    return any(c.isdigit() for c in string)


def dict_to_repr(d):
    string = ''
    for i, (k, v) in enumerate(d.items()):
        if i == 0:
            string = string + '{}={}'.format(k, v)
        else:
            string = string + ', {}={}'.format(k, v)
    return string


def make_interpolater(domain_min, domain_max, range_min, range_max):
    # Figure out how 'wide' each range is
    domain_span = domain_max - domain_min
    range_span = range_max - range_min

    try:
        # Compute the scale factor between left and right values
        scale_factor = float(range_span) / float(domain_span)
    except ZeroDivisionError:
        scale_factor = 0

    # create interpolation function using pre-calculated scaleFactor
    def interp_fn(value):
        return range_min + (value-domain_min)*scale_factor

    return interp_fn


def create_gen_data(**kwargs):
    gen_data = dict()

    gen_data['bus'] = kwargs.pop('bus', 0)
    gen_data['Pg'] = kwargs.pop('Pg', 0)
    gen_data['Qg'] = kwargs.pop('Qg', 0)
    gen_data['Qmax'] = kwargs.pop('Qmax', 0)
    gen_data['Qmin'] = kwargs.pop('Qmin', 0)
    gen_data['Vg'] = kwargs.pop('Vg', 0)
    gen_data['mBase'] = kwargs.pop('mBase', 0)
    gen_data['status'] = kwargs.pop('status', 0)
    gen_data['Pmax'] = kwargs.pop('Pmax', 0)
    gen_data['Pmin'] = kwargs.pop('Pmin', 0)
    gen_data['Pc1'] = kwargs.pop('Pc1', 0)
    gen_data['Pc2'] = kwargs.pop('Pc2', 0)
    gen_data['Qc1min'] = kwargs.pop('Qc1min', 0)
    gen_data['Qc1max'] = kwargs.pop('Qc1max', 0)
    gen_data['Qc2min'] = kwargs.pop('Qc2min', 0)
    gen_data['Qc2max'] = kwargs.pop('Qc2max', 0)
    gen_data['ramp_agc'] = kwargs.pop('ramp_agc', 0)
    gen_data['ramp_10'] = kwargs.pop('ramp_10', 0)
    gen_data['ramp_30'] = kwargs.pop('ramp_30', 0)
    gen_data['ramp_q'] = kwargs.pop('ramp_q', 0)
    gen_data['apf'] = kwargs.pop('apf', 0)

    return gen_data


def read_unit_commitment(uc):

    with open(uc) as f:
        data = f.read()

    uc_dict = dict()
    for l in data.splitlines():
        if l.startswith('#'):
            continue
        l = l.strip()

        if l == '1' or l=='0':
            uc.append(l)
        else:
            uc = []
            uc_dict[l] = uc
    return uc_dict


def find_generators(data):
    DIRECTIVE = r'set ThermalGenerators :='
    for l in data.splitlines():
        if l.startswith(DIRECTIVE):
            return l.split('=')[1].strip('; ').split()


def find_buses(data):
    for l in data.splitlines():
        DIRECTIVE = 'set Buses := '
        if l.startswith(DIRECTIVE):
            return l.split(DIRECTIVE)[1].strip(';').split()


def read_model(model_data, base_file=None):

    #click.echo("In psst utils.py read_model method")
    with open(model_data) as f:
        data = f.read()
        #click.echo("printing data:" + data)

    from .case import PSSTCase
    if base_file:
        c = PSSTCase(base_file)
    else:
        c = PSSTCase(os.path.join(current_directory, '../cases/case.m'))
    #click.echo("printing file path: " + os.path.join(current_directory, '../cases/case.m'))
    #click.echo("printing c: " + str(c))

    ag = find_generators(data)
    for g in ag:
        c.gen.loc[g] = c.gen.loc['GenCo0']
        c.gencost.loc[g] = c.gencost.loc['GenCo0']

    if 'GenCo0' not in ag:
        c.gen.drop('GenCo0', inplace=True)
        c.gencost.drop('GenCo0', inplace=True)

    DIRECTIVE = 'set ThermalGeneratorsAtBus'
    for l in data.splitlines():
        if l.startswith(DIRECTIVE):
            bus, gen = l.split(DIRECTIVE)[1].split(':=')
            bus = bus.replace(']', '').replace('[', '').strip()
            gen = gen.replace(';', '').strip()
            gen_ary =gen.split(' ')
            for gen_i in gen_ary:
                c.gen.loc[gen_i, 'GEN_BUS'] = bus

    c.PriceSenLoadFlag = 0.0
    for l in data.splitlines():
        if l.startswith('param StorageFlag'):
            c.StorageFlag = float(l.split(':=')[1].split(';')[0].replace(' ', ''))
        if l.startswith('param NDGFlag'):
            c.NDGFlag = float(l.split(':=')[1].split(';')[0].replace(' ', ''))
        if l.startswith('param PriceSenLoadFlag'):
            c.PriceSenLoadFlag = float(l.split(':=')[1].split(';')[0].replace(' ', ''))

    for l in data.splitlines():
        if l.startswith('param ReserveDownSystemPercent'):
            c.ReserveDownSystemPercent = float(l.split(':=')[1].split(';')[0].replace(' ', ''))
        if l.startswith('param ReserveUpSystemPercent'):
            c.ReserveUpSystemPercent = float(l.split(':=')[1].split(';')[0].replace(' ', ''))

    zonalData = {'NumberOfZones': 0, 'Zones': '', 'HasZonalReserves': False}

    for l in data.splitlines():
        if l.startswith('param NumberOfZones'):
            zonalData['NumberOfZones'] = float(l.split(':=')[1].split(';')[0].replace(' ', ''))

    for l in data.splitlines():
        if l.startswith('param HasZonalReserves'):
            flag_str = l.split(':=')[1].split(';')[0].replace(' ', '')
            if flag_str == 'True' or flag_str == 'true':
                zonalData['HasZonalReserves'] = True

    #click.echo('HasZonalReserves:'+str(zonalData['HasZonalReserves']))

    for l in data.splitlines():
        DIRECTIVE = 'set Zones := '
        if l.startswith(DIRECTIVE):
            zonalData['Zones'] = l.split(DIRECTIVE)[1].strip(';').split()

    ReserveDownZonalPercent = {}
    ReserveUpZonalPercent = {}
    zonalBusData = {}

    READ = False
    for l in data.splitlines():
        if l.strip() == ';':
            READ = False
        if l.startswith('param: Buses ReserveDownZonalPercent ReserveUpZonalPercent'):
            READ = True
            continue
        if READ is True:
            z, Buses, RDZP, RUZP = l.split(" ")
            #click.echo('z, Buses, RDZP, RUZP'+ str(z)+str(Buses)+str(RDZP)+str(RUZP))
            ReserveDownZonalPercent[z] = float(RDZP)
            ReserveUpZonalPercent[z] = float(RUZP)
            BusTrim = Buses[:-1]
            BusSplit = BusTrim.split(',')
            zonalBusData[z] = BusSplit

    #click.echo("print zonalData: " + str(zonalData))
    #click.echo("print ReserveDownZonalPercent: " + str(ReserveDownZonalPercent))
    #click.echo("print ReserveUpZonalPercent: " + str(ReserveUpZonalPercent))
    #click.echo("print zonalBusData: " + str(zonalBusData))

    READ = False
    for l in data.splitlines():
        if l.strip() == ';':
            READ = False

        if l == 'param: PowerGeneratedT0 UnitOnT0State MinimumPowerOutput MaximumPowerOutput MinimumUpTime MinimumDownTime NominalRampUpLimit NominalRampDownLimit StartupRampLimit ShutdownRampLimit ColdStartHours ColdStartCost HotStartCost ShutdownCostCoefficient :=':
            READ = True
            continue

        if READ is True:
            g, pg, status, min_g, max_g, min_up_time, min_down_time, ramp_up_rate, ramp_down_rate, startup_ramp_rate, shutdown_ramp_rate, coldstarthours, coldstartcost, hotstartcost, shutdowncostcoefficient = l.split()

            #click.echo("In psst utils.py read gen info:")
            #click.echo("In psst - UnitOnT0State :" + str(c.gen.loc[g, 'UnitOnT0State']))
            #click.echo("Reading model data - printing STARTUP or cold_start_cost:" + str(c.gen.loc[g, 'STARTUP']) + str(cold_start_cost))

            c.gen.loc[g, 'PMAX'] = float(max_g.replace(',', '.'))  # Handle europe number format TODO: use better fix!
            c.gen.loc[g, 'PG'] = float(pg.replace(',', '.'))
            c.gen.loc[g, 'UnitOnT0State'] = int(status.replace(',','.'))
            c.gen.loc[g, 'PMIN'] = float(min_g.replace(',', '.'))
            c.gen.loc[g, 'MINIMUM_UP_TIME'] = int(min_up_time)
            c.gen.loc[g, 'MINIMUM_DOWN_TIME'] = int(min_down_time)
            ramp_up = float(ramp_up_rate.replace(',', '.'))
            # print('ramp_up:'+ str(ramp_up))
            c.gen.loc[g, 'RAMP_10'] = 9999 if ramp_up == 0 else ramp_up
            # print('ramp_up:'+str(c.gen.loc[g, 'RAMP_10']))
            ramp_down = float(ramp_down_rate.replace(',', '.'))
            # print('ramp_down:'+str(ramp_down))
            c.gen.loc[g, 'RAMP_DOWN'] = 9999 if ramp_down == 0 else ramp_down
            # print('ramp_down:'+str(c.gen.loc[g, 'RAMP_DOWN']))
            startup_ramp = float(startup_ramp_rate.replace(',', '.'))
            #            c.gen.loc[g, 'STARTUP_RAMP'] = 9999 if startup_ramp == 0 else startup_ramp
            c.gen.loc[g, 'STARTUP_RAMP'] = startup_ramp
            shutdown_ramp = float(shutdown_ramp_rate.replace(',', '.'))
            #            c.gen.loc[g, 'SHUTDOWN_RAMP'] = 9999 if shutdown_ramp == 0 else shutdown_ramp
            c.gen.loc[g, 'SHUTDOWN_RAMP'] = shutdown_ramp
            cold_start_hours = float(coldstarthours.replace(',', '.'))
            c.gencost.loc[g, "COLD_START_HOURS"] = cold_start_hours
            cold_start_cost = float(coldstartcost.replace(',', '.'))
            c.gencost.loc[g, "STARTUP_COLD"] = cold_start_cost
            hot_start_cost = float(hotstartcost.replace(',', '.'))
            c.gencost.loc[g, "STARTUP_HOT"] = hot_start_cost
            shutdown_costcoefficient = float(shutdowncostcoefficient.replace(',', '.'))
            c.gencost.loc[g, "SHUTDOWN_COEFFICIENT"] = shutdown_costcoefficient


    branch_number = 1
    for l in data.splitlines():
        if l.strip() == ';':
            READ = False

        if l == 'param: BusFrom BusTo ThermalLimit Reactance :=':
            READ = True
            continue

        if READ is True:
            _, b1, b2, tl, r = l.split()
            c.branch.loc[branch_number] = c.branch.loc[0]
            c.branch.loc[branch_number, 'F_BUS'] = b1
            c.branch.loc[branch_number, 'T_BUS'] = b2
            c.branch.loc[branch_number, 'BR_X'] = float(r.replace(',', '.'))
            c.branch.loc[branch_number, 'RATE_A'] = float(tl.replace(',', '.'))
            branch_number = branch_number + 1

    c.branch.drop(0, inplace=True)

    ag = find_buses(data)
    for b in ag:
        c.bus.loc[b] = c.bus.loc['Bus1']

    if 'Bus1' not in ag:
        c.bus.drop('Bus1', inplace=True)

    READ = False
    DIRECTIVE = 'param: NetDemand :='
    for l in data.splitlines():
        if l.strip() == ';':
            READ = False

        if l.strip() == '':
            continue

        if l == 'param: NetDemand :=':
            READ = True
            continue

        if READ is True:
            b, t, v = l.split()
            c.load.loc[t, b] = float(v.replace(',', '.'))

    c.load = c.load.fillna(0)
    c.load.drop(0, inplace=True)
    c.load.index = range(0, len(c.load.index))

    # Make Bus1 slack
    c.bus.loc['Bus1', 'TYPE'] = 3.0

    READ = False
    DIRECTIVE = 'param: ProductionCostA0 ProductionCostA1 ProductionCostA2 NS :='
    for l in data.splitlines():
        if l.strip() == ';':
            READ = False

        if l.strip() == '':
            continue

        if l == DIRECTIVE:
            READ = True
            continue

        if READ is True:
            g, a0, a1, a2, NS = l.split()
            c.gencost.loc[g, "COST_2"] = float(a2.replace(',', '.'))
            c.gencost.loc[g, "COST_1"] = float(a1.replace(',', '.'))
            c.gencost.loc[g, "COST_0"] = float(a0.replace(',', '.'))
            #c.gencost.loc[g, "N_COST"] = 3 # Does DK intend to keep NCOST instead of N_COST?
            c.gencost.loc[g, "NCOST"] = 3 # Added NCOST to 3 - Swathi
            c.gencost.loc[g, "NS"] = int(NS.replace(',', '.'))

    READ = False
    priceSenLoadData = {}
    DIRECTIVE = 'set PriceSensitiveLoadNames :='
    for l in data.splitlines():
        if l.startswith(DIRECTIVE):
            continue
            #priceSenLoadData['Names'] = l.split(DIRECTIVE)[1].strip(';').split()

    READ = False
    DIRECTIVE ='param: Name ID atBus hourIndex BenefitCoefficientC0 BenefitCoefficientC1 BenefitCoefficientC2 SLMin SLMax :='

    #Name	   ID	  atBus	 hourIndex	   BenefitCoefficientC0   BenefitCoefficientC1     BenefitCoefficientC2	   SLMin SLMax
    for l in data.splitlines():
        if l.strip() == ';':
            READ = False

        if l.strip() == '':
            continue

        if l == DIRECTIVE:
            READ = True
            continue

        if READ is True:
            Name,ID,atBus,hourIndex,d,e,f,SLMin,SLMax = l.split()
            priceSenLoadData[Name,(int(hourIndex)-1)] = {'ID':ID,'atBus': atBus,'hourIndex':int(hourIndex),'d':float(d),'e':float(e),'f':float(f),'Pmin':float(SLMin), 'Pmax':float(SLMax)}

    #click.echo("printing c.gencost.loc: " + str(c.gencost.loc))
    #click.echo("printing c.gencost: " + str(c.gencost))
    #click.echo("printing c: " + str(c))


    c.PositiveMismatchPenalty = 1e6
    c.NegativeMismatchPenalty = 1e6

    for l in data.splitlines():
        if l.startswith('param BalPenPos'):
            c.PositiveMismatchPenalty = float(l.split(':=')[1].split(';')[0].replace(' ', ''))

    for l in data.splitlines():
        if l.startswith('param BalPenNeg'):
            c.NegativeMismatchPenalty = float(l.split(':=')[1].split(';')[0].replace(' ', ''))

    c.TimePeriodLength = 2

    for l in data.splitlines():
        if l.startswith('param TimePeriodLength'):
            c.TimePeriodLength = float(l.split(':=')[1].split(';')[0].replace(' ', ''))

    #click.echo("printing TimePeriodLength: " + str(c.TimePeriodLength))

    ZonalDataComplete = {'zonalData': zonalData, 'zonalBusData': zonalBusData, 'ReserveDownZonalPercent': ReserveDownZonalPercent, 'ReserveUpZonalPercent': ReserveUpZonalPercent}

    return c, ZonalDataComplete, priceSenLoadData  #, NDGData
