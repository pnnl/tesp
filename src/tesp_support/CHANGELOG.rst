Changelog
=========

Version 1.0.0 (2017-06-08)
--------------------------
* Initial release

Version 0.2 (2017-10-14)
------------------------
* For NIST TE Challenge 2

Version 0.1.4 (2018-09-30)
--------------------------
* For GridAPPS-D Demo
* GridLAB-D feature/1146 branch with FNCS-controlled switching

Version 0.1.9 (2018-12-13)
--------------------------
* Three desktop version installers for Mac, Windows and Linux
* Tutorial video
* DSO+T study files

Version 0.9.2 (2020-09-11)
--------------------------
* Support for HELICS and EnergyPlus 9.3
* Bundled with ns-3 (HELICS) and opendsscmd (FNCS)
* Execution on Linux or Docker
* Postprocessing on Linux, Windows or Mac OS X

Version 0.9.5 (2021-03-09)
--------------------------
* Standalone housing generator
* Plot functions can save files
* Case-generated SGIP1 example
* Fixed the FNCS SGIP1 example

Version 1.0.1 (2021-04-23)
--------------------------
* No longer supports Windows
* Updates to consensus mechanism
* Balanced three-phase houses for housing generator
* Remove deprecated solar and battery attributes
* Update to HELICS 2.6.1

Version 1.2.0 (2022-10-3)
--------------------------
* Added data.py to for shared data with TESP, recommended using TESP install
* Added several APIs for plot GridLAB-D and EnergyPlus attributes
* Added player server
* Added DSOT agents and feeder generators
* Update to HELICS 3.3.0

Version 1.2.3 (2022-11-22)
--------------------------
* Fix the EnergyPlus to work with newer compiler and updated version number
* Fix read the docs document warnings and fix clean shell script for energyplus
* Added Ubuntu apt install version dependencies for 18.04,20.04,22.04
* Revised pip and venv for install script
* Revised clean scripts, clean up models directory
* Add loadshed* examples for auto test
* Fixed the installation for Ubuntu 22.04
* Fixed monitor.py and tesp_case.py when not using EnergyPlus,
* Minor fix for feeders generator when using name_prefix
* Fixed complex python to use helics complex type

Version 1.2.4 (2022-12-1)
--------------------------
* Fix version number in tesp_support for PyPI distribution and read the docs
* Fix the version.sh, move documentation to end of the install, fix warning in Consensus_Usecase.rst
* Fix git patch warning for FNCS and EnergyPlus
* GridLAB-D triplex_node no longer uses power_12_real and power12_reac, this has commented out for SGIP1*.glm files
* Add pypi packaging to stamping process, refined docker build in scripts/docker, moved HELICS version checker to build

Version 1.3.0 (2023-9-23)
--------------------------
* Refactor the TESP PyPI installation for better division between api vs custom (one off) file
* Upgrade all models(GridLAB-D, EnergyPlus, NS3) to work with HELICS 3.4
* Add modifier.py for GridLAB-D models

Version 1.3.1 (2023-10-3)
--------------------------
* Fix modifier.py for GridLAB-D models, upgrade np.float to np.float64

Version 1.3.2 (2023-10-27)
--------------------------
* Another fix for model and modifier for GridLAB-D models

Version 1.3.3 (2023-12-4)
--------------------------
* Add tesp_component download in tesp_support pypi, add schedule in model_GLM.py
* Minor changes to path for RECS system feeder
* Restructured, new RECS parameters, updated to include income, new hvac setpoint RECS data, teleworking.
* Fix postposing for DSOT
* Dockerfile for each module getting ready for dockerize COSU Simulations
* Change directory structure