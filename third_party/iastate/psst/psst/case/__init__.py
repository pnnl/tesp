import os
import logging
import click

from builtins import super
import pandas as pd
import numpy as np

from .descriptors import (Name, Version, BaseMVA, BusName, Bus, Branch, BranchName,
                        Gen, GenName, GenCost, Load, Period, _Attributes)

from . import matpower

logger = logging.getLogger(__name__)
pd.options.display.max_rows = 999
pd.options.display.max_columns = 999

current_directory = os.path.realpath(os.path.dirname(__file__))


class PSSTCase(object):

    name = Name()
    version = Version()
    baseMVA = BaseMVA()
    bus = Bus()
    bus_name = BusName()
    branch = Branch()
    branch_name = BranchName()
    gen = Gen()
    gencost = GenCost()
    gen_name = GenName()
    load = Load()
    period = Period()
    _attributes = _Attributes()
    #click.echo("PSSTCase Hi: ")

    def __init__(self, filename=None, mode='r'):
        #click.echo("PSSTCase __init__ Hi: ")
        self._attributes = list()
        if filename is not None:
            #click.echo("if filename: "+filename)
            self._filename = filename
        else:
            #click.echo("else filename: "+filename)
            self._filename = os.path.join(current_directory, '..', 'cases', 'case.m')
            #click.echo("else filename: "+filename)
        if mode == 'r' or mode == 'read':
            #click.echo("mode: "+mode)
            self._read_matpower(self)

    def __repr__(self):
        name = getattr(self, 'name', None)
        gen_name = getattr(self, 'gen_name', None)
        bus_name = getattr(self, 'bus_name', None)
        branch_name = getattr(self, 'branch_name', None)
        name_string = 'name={}'.format(name) if name is not None else ''
        gen_string = 'Generators={}'.format(len(gen_name)) if gen_name is not None else ''
        bus_string = 'Buses={}'.format(len(bus_name)) if bus_name is not None else ''
        branch_string = 'Branches={}'.format(len(branch_name)) if branch_name is not None else ''
        l = [s for s in [name_string, gen_string, bus_string, branch_string] if s != '']
        if len(l) > 1:
            repr_string = ', '.join(l)
        elif len(l) == 1:
            repr_string = l[0]
        else:
            repr_string = ''

        return '<{}.{}({})>'.format(
                    self.__class__.__module__,
                    self.__class__.__name__,
                    repr_string,
                )

    @classmethod
    def _read_matpower(cls, mpc, auto_assign_names=True, fill_loads=True, remove_empty=True, reset_generator_status=True):

        if not isinstance(mpc, cls):
            #click.echo("1 _read_matpower: ")
            filename = mpc
            mpc = cls(filename, mode=None)

        with open(os.path.abspath(mpc._filename)) as f:
            #click.echo("2 _read_matpower: ")
            #click.echo("mpc: "+ str(mpc))
            #click.echo("mpc: "+ mpc._filename)
            #click.echo("f: "+ str(f))
            string = f.read()
            #click.echo("string: "+ string)

        for attribute in matpower.find_attributes(string):
            #click.echo(" mpc: "+ str(mpc))
            #click.echo("3 _read_matpower attribute: "+ attribute)
            _list = matpower.parse_file(attribute, string)
            #click.echo(" _list: "+ str(_list))
            if _list is not None:
                if len(_list) == 1 and (attribute=='version' or attribute=='baseMVA'):
                    #click.echo(" _list[0][0]: "+ str(_list[0][0]))
                    setattr(mpc, attribute, _list[0][0])
                else:
                    cols = max([len(l) for l in _list])
                    columns = matpower.COLUMNS.get(attribute, [i for i in range(0, cols)])
                    columns = columns[:cols]
                    if cols > len(columns):
                        if attribute != 'gencost':
                            logger.warning('Number of columns greater than expected number.')
                        columns = columns[:-1] + ['{}_{}'.format(columns[-1], i) for i in range(cols - len(columns), -1, -1)]
                    df = pd.DataFrame(_list, columns=columns)

                    if attribute == 'bus':
                        df.set_index('BUS_I',inplace=True)

                    #click.echo(" df: "+ str(df))
                    setattr(mpc, attribute, df)
                mpc._attributes.append(attribute)

        #click.echo(" mpc: "+ str(mpc.bus))
        mpc.name = matpower.find_name(string)

        #click.echo(" mpc.gencost['NCOST']: "+ str(mpc.gencost))
        if auto_assign_names is True:
            #click.echo(" 1 checking: ")
            #click.echo(" mpc.bus_name: "+ str(mpc.bus_name))
            #click.echo(" mpc.bus_name: "+ str(mpc.gen_name))
            #click.echo(" mpc.bus_name: "+ str(mpc.branch_name))
            mpc.bus_name = mpc.bus_name
            mpc.gen_name = mpc.gen_name
            mpc.branch_name = mpc.branch_name
            #click.echo(" mpc.bus_name: "+ str(mpc.bus_name))
            #click.echo(" mpc.bus_name: "+ str(mpc.gen_name))
            #click.echo(" mpc.bus_name: "+ str(mpc.branch_name))

        #click.echo(" mpc.gencost['NCOST']: "+ str(mpc.gencost))
        if fill_loads is True:
            for i, row in mpc.bus.iterrows():
                mpc.load.loc[:, i] = row['PD']

        if mpc.bus_name.intersection(mpc.gen_name).values.size != 0:
            logger.warning('Bus and Generator names may be identical. This could cause issues when plotting.')

        mpc.gen.loc[mpc.gen['RAMP_10'] == 0, 'RAMP_10'] = mpc.gen['PMAX']
        mpc.gen['STARTUP_RAMP'] = mpc.gen['PMAX']
        mpc.gen['SHUTDOWN_RAMP'] = mpc.gen['PMAX']
        mpc.gen['MINIMUM_UP_TIME'] = 0
        mpc.gen['MINIMUM_DOWN_TIME'] = 0
        #click.echo(" mpc.gencost['NCOST']: "+ str(mpc.gencost))
        try:
            mpc.gencost.loc[mpc.gencost['COST_2'] == 0, 'NCOST'] = 2
        except KeyError as e:
            logger.warning(e)

        mpc.gen_status = pd.DataFrame([mpc.gen['GEN_STATUS'] for i in mpc.load.index])
        mpc.gen_status.index = mpc.load.index
        if reset_generator_status:
            mpc.gen_status.loc[:, :] = np.nan

        #click.echo(" mpc.gencost['NCOST']: "+ str(mpc.gencost))
        #click.echo("End _read_matpower: ")
        return mpc


read_matpower = PSSTCase._read_matpower
