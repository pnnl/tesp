# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: make_comm_eplus.py

# usage 'python3 make_comm_eplus.py'
import json
import tesp_support.api as tesp

if __name__ == '__main__':
  print ('usage: python3 make_comm_eplus.py')
  tesp.make_gld_eplus_case (fname = 'CommDef.json')

