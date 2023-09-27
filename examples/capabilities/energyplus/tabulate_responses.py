# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: tabulate_responses.py
# usage 'python3 tabulate_metrics.py'

import os

import tesp_support.api.process_eplus as te

bldgs = ['FullServiceRestaurant',
         'Hospital',
         'LargeHotel',
         'LargeOffice',
         'MediumOffice',
         'MidriseApartment',
         'OutPatient',
         'PrimarySchool',
         'QuickServiceRestaurant',
         'SecondarySchool',
         'SmallHotel',
         'SmallOffice',
         'StandaloneRetail',
         'StripMall',
         'SuperMarket',
         'Warehouse']


def get_kw(season, market, building):
    name_root = '{:s}_{:s}_{:s}'.format(season, market, building)
    _metrics = te.read_eplus_metrics(os.getcwd(), name_root, quiet=True)
    data = _metrics['data_e']
    idx_e = _metrics['idx_e']
    avg_kw = 0.001 * data[:, idx_e['ELECTRIC_DEMAND_IDX']].mean()
    return avg_kw


print('{:25s}        {:8s} {:8s} {:8s} {:8s}'.format('Building', 'Summer', '', 'Winter', ''))
print('{:25s} {:>8s} {:>8s} {:>8s} {:>8s}'.format('', 'Base', 'Resp', 'Base', 'Resp'))

for bldg in bldgs:
    kw1 = get_kw('Summer', 'NoMkt', bldg)
    kw2 = get_kw('Summer', 'Mkt', bldg)
    kw3 = get_kw('Winter', 'NoMkt', bldg)
    kw4 = get_kw('Winter', 'Mkt', bldg)
    print('{:25s} {:8.2f} {:8.2f} {:8.2f} {:8.2f}'.format(bldg, kw1, kw2, kw3, kw4))
