# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: make_comm_base.py

# import tesp_support.tesp_api as tesp
import tesp_support.tesp_case as tesp

if __name__ == '__main__':
    tesp.make_tesp_case('Nocomm_Base.json')
    tesp.make_tesp_case('Eplus_Restaurant.json')
    tesp.make_tesp_case('SGIP1c.json')
