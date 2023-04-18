# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: make_comm_base.py

import tesp_support.tesp_case as tc

if __name__ == '__main__':
    tc.make_tesp_case('Nocomm_Base.json')
    tc.make_tesp_case('Eplus_Restaurant.json')
    tc.make_tesp_case('SGIP1c.json')
