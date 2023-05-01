# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: __init__.py
"""TESP is the Transactive Energy Simulation Platform tesp_support contains the
Python files that are part of TESP

Example:
    To start PYPOWER for connection to FNCS::

        import tesp_support.api.tso_PYPOWER_f as tesp
        tesp.tso_pypower_loop_f('te30_pp.json','TE_Challenge')

    To start PYPOWER for connection to HELICS::

        import tesp_support.api.tso_PYPOWER as tesp
        tesp.tso_pypower_loop('te30_pp.json','TE_Challenge', helicsConfig='tso.json')
"""
