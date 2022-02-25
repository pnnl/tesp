# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: make_comm_eplus.py

import tesp_support.api as tesp

if __name__ == '__main__':
    tesp.make_gld_eplus_case(fname='CommDef.json')
