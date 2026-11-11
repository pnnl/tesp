# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Redesigned device agents.

Each device agent performs only two tasks:

1. Observe - retrieve the current physical state of the device, either from
   the GridLAB-D object (physics-based, full) or from a stub (light physics
   model or statistical approximation).
2. Define Flexibility - given the observation, project the feasible power
   range, an amenity mapping, and a baseline operating point for each market
   interval.

Customer preference curves and bid curves are formed by device-agnostic
scripts from the flexibility output and are not part of the device agents.
"""
