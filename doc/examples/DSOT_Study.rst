..
    _ Copyright (C) 2021-2022 Battelle Memorial Institute
    _ file: DSOT_Study.rst

DSO+T Study Draft Examples and Documents
========================================

This section links to models and design documents for the DSO+T study
that PNNL is conducting in FY19. Most of this material will be incorporated
into the main TESP documentation as the described models and agents
are fully integrated with the platform. In the meantime, this section
provides a roadmap to the existing draft documentation, for those working
on the DSO+T study. No technical support can be provided for material
referenced from this section, outside of the DSO+T study team.

ERCOT System Models
-------------------

The DSO+T study will be conducted on reduced-order 8-bus and 200-bus
models of the ERCOT system in Texas. Each bus will have a GridLAB-D
substation that serves from one to three feeders. The 8-bus model with
supporting files are distributed with the TESP installers, but not yet
documented as part of TESP. For more information about this 8-bus 
model, see:

* `ERCOT Directory Readme`_
* `ERCOT Bulk System Model Readme`_
* `ERCOT Feeder Model Readme`_
* `ERCOT 8-Bus TESP Example Readme`_

DSO+T Agents
------------

New agents for the DSO+T study include batteries, day-ahead markets
and transformer control to optimize loss-of-life. Some of these agents
have been developed and tested outside of TESP, under an internal
PNNL code repository. These agents are being integrated into TESP.
For draft documentation of the standalone agents, see:

* `Day-Ahead Battery Bidding`_
* `Transformer Lifetime Agent`_
* `Stand-alone Agent Testing`_

Water Heater Modeling
---------------------

The GridLAB-D water heater model, as currently implemented, does not
offer enough flexibility to participate in transactive systems. Upgrades
are planned for the DSO+T study, as detailed in:

* `Water Heater Model Gaps - Overview`_
* `Water Heater Model Gaps - Presentation`_
* `Water Heater Stratified Layer Model`_
* `Water Heater Agent`_

.. _`ERCOT Directory Readme`: https://github.com/pnnl/tesp/blob/develop/ercot/README.md
.. _`ERCOT Bulk System Model Readme`: https://github.com/pnnl/tesp/blob/develop/ercot/bulk_system/README.md
.. _`ERCOT Feeder Model Readme`: https://github.com/pnnl/tesp/blob/develop/ercot/dist_system/README.md
.. _`ERCOT 8-Bus TESP Example Readme`: https://github.com/pnnl/tesp/blob/develop/ercot/case8/README.md
.. _`Day-Ahead Battery Bidding`: https://github.com/pnnl/tesp/blob/develop/ercot/pdf/DayAheadBidsBattery.pdf
.. _`Transformer Lifetime Agent`: https://github.com/pnnl/tesp/blob/develop/ercot/pdf/Transformer_transactive_control.pdf
.. _`Stand-alone Agent Testing`: https://github.com/pnnl/tesp/blob/develop/ercot/pdf/MasterScriptDocumentation.pdf
.. _`Water Heater Model Gaps - Overview`: https://github.com/pnnl/tesp/blob/develop/ercot/pdf/Water_Heater_Model_Deficiency_for_B2G.pdf
.. _`Water Heater Model Gaps - Presentation`: https://github.com/pnnl/tesp/blob/develop/ercot/pdf/EWH_11_6_2018.pdf
.. _`Water Heater Stratified Layer Model`: https://github.com/pnnl/tesp/blob/develop/ercot/pdf/Fixed_Layers_Stratified_Water_Heater.pdf
.. _`Water Heater Agent`: https://github.com/pnnl/tesp/blob/develop/ercot/pdf/DSO%2BT_Water_Heater_Agent.pdf

