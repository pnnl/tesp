# weather Python files

Copyright (c) 2017-2022, Battelle Memorial Institute

This is the weather code repository for Python-based components of TESP

### File Directory

- *__init__.py*; boilerplate for a Python package
- *PSM_download.py*; simple script to download PSM weather files and convert them to DAT files
- *PSMv3toDAT.py*; this code reads in PSM v3 csv files to converts weather DAT format for common use by agents
- *README.md*; this file
- *TMY3toCSV.py*; converts TMY3 weather data to CSV format for common use by agents
- *TMYtoEPW.py*; command-line script that converts a TMY2 file to the EnergyPlus EPW format
- *weather_Agent.py*; publishes weather and forecasts based on a CSV file
