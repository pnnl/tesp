Standard Third-Party Tools
==========================

TESP, as a platform, is largely dependent on third-party simulation tools to perform the kinds of analysis that are common in transactive energy scenarios. The tools summarized on this page are those that have been commonly used in TESP and are considered somewhat "standard" when using TESP. This obviously doesn't preclude the use of other simulation tools but the installation and integration of said tool will fall on the user.  When applicable and appropriate, the source code (along with the compiled executable) for these tools is provided with a complete TESP installation and when not, the just the executables are included. By providing access to the source and linking to their repositories, users should be able to not only customize the tools in their installations but also update their code from the repository to receive bug fixes and/or feature updates. The following is a brief description of each of the tools; much more comprehensive documentation for each can be found on their respective websites.

`GridLAB-D <https://www.gridlabd.org>`_
---------------------------------------
GridLAB-D is a power distribution system simulation tool that not only solves three-phase unbalanced power flows (as is common in distribution system tools) but also includes simple thermodynamic models for houses including HVAC systems and water heaters. The inclusion of the multi-domain models allows the tool to model an integrated distribution system (wires and loads) and represent a wider variety of common transactive energy scenarios. GridLAB-D also include models for solar PV installations with inverters, automated voltage management equipment (voltage regulators and switched capacitors), and diesel generators. TESP uses GridLAB-D to model distribution system physics and customer load behavior.

`PYPOWER <https://pypi.org/project/PYPOWER/>`_
-----------------------------------------------
PYPOWER is a Python re-implementation of `MATPOWER <https://matpower.org>`_ in Python using common Python libraries to perform the mathematical heavy lifting. TESP uses PYPOWER to solve the real-time energy market dispatch (through an optimal power flow) and the transmission system physics (through traditional power flows).

`EnergyPlus <https://energyplus.net>`_
---------------------------------------
EnergyPlus is a building system simulator that is typically used to model large (at least relative to residential buildings), multi-zone commercial buildings. These models include representations of both the physical components/structures of the buildings (*e.g.* walls, windows, roofs) but also heating and cooling equipment as well as their associated controllers. TESP uses EnergyPlus to model commercial structures and associate them with particular points in the GridLAB-D model.

`ns-3 <https://www.nsnam.org>`_
--------------------------------
ns-3 is a discrete-event communication system simulator that TESP uses to model communication system effects between the various agents in a transactive system. ns-3 has built-in models to present common protocol stacks (TCP/IP, UDP/IP), wireless protocols such as Wifi (802.11) and LTE networks, as well as various routing protocols (*e.g.* OLSR, AODV). 

`HELICS <https://helics.org>`_
-------------------------------
HELICS is a co-simulation platform that is used to integrate all of the above tools along with the custom agents created by the TESP team and distributed with TESP. HELICS allows the passing of physical values or abstract messages between the TESP simulation tools during run-time allowing each simulation tool to affect the others. For example, PYPOWER produces a substation voltage for GridLAB-D and GridLAB-D, using that voltage, produces a load for PYPOWER. 
