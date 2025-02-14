# Copyright (c) 2017-2024 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: __init__.py
""" Transactive Energy Simulation Platform (TESP)
Contains the python packages for the tesp_support

Example:
    To start PYPOWER for connection to FNCS::

        import tesp_support.original.tso_PYPOWER_f as tesp
        tesp.tso_pypower_loop_f('te30_pp.json','TE_Challenge')

    To start PYPOWER for connection to HELICS::

        import tesp_support.api.tso_PYPOWER as tesp
        tesp.tso_pypower_loop('te30_pp.json','TE_Challenge', helicsConfig='tso.json')
"""
