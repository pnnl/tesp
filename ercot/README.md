# TESP Models for DSO+T Study

Copyright (c) 2018, Battelle Memorial Institute

These files implement 8-bus and 200-bus models of ERCOT for the FY19
DSO+T study. The bulk system generation and loads were developed from public
information by clustering techniques. The bulk system lines were constructed
from Delaunay triangulation as a starting point, refined by PYPOWER load
flow solutions at peak load. Bulk wind generation varies according to a
limited limited autoregressive integrated moving average (LARIMA) model.

The distribution system model and weather files are based on four of the 
PNNL taxonomy feeders for region 5, after model order reduction of the primary.
This selection will be expanded later.

Presently, the GridLAB-D and PYPOWER simulators are federated with transactive
agents using FNCS. Later, PYPOWER will be replaced with AMES, and a Modelica
simulator for large buildings will be added. We may also change FNCS to
HELICS, but this is not decided yet.

TESP and this model will continuously evolve during the term of the FY19
DSO+T. In order to keep up with changes will working on the DSO+T study:

1.  Check for new binary releases on a weekly basis from 
https://github.com/pnnl/tesp/releases You may also receive email notice of 
significant new releases.  New features in GridLAB-D and the 
large-building simulator will be distributed this way.  

2. Use "git pull" and "pip install tesp_support --upgrade" on a daily basis.  Most of the updates are distributed this way.  

The sub-directory structure is:

- *bulk_system* contains the standalone bulk generation, load and transmission system model; update the bulk system model from here
- *case8* contains the complete 8-bus model; run simulations from here
- *dist_system* contains the reduced-order feeder models; populate feeders with houses from here

