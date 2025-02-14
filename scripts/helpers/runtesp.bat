ECHO off

REM Copyright (C) 2021-2023 Battelle Memorial Institute
REM file: runtesp.bat

IF NOT DEFINED TESPDIR GOTO no_tesp

REM == standard use
SET /p tesp_ver=<"%TESPDIR%\scripts\tesp_version"
SET /p grid_ver=<"%TESPDIR%\scripts\grid_version"
SET IMAGE=pnnl/tesp:%tesp_ver%_ubuntu_%grid_ver%

REM == for custom use
REM IMAGE=cosim-build:tesp_22.04.1
REM IMAGE=cosim-cplex:tesp_22.04.1

SET SIM_UID=1001
SET SIM_HOME=/home/worker

ECHO "Should always confirm that you are logged in to docker using 'docker login'"

IF DEFINED %1% GOTO background

:foreground
ECHO "Running foreground image %IMAGE%"
docker run -it --rm --name foregroundWorker ^
 -e LOCAL_USER_ID=%SIM_UID% ^
 --mount type=bind,source="%TESPDIR%",destination="%SIM_HOME%/tesp" ^
 --workdir=%SIM_HOME% ^
 %IMAGE% ^
 bash

GOTO end

:background
ECHO "Running background image %IMAGE%"
docker run -itd --rm --name backgroundWorker ^
 -e LOCAL_USER_ID=%SIM_UID% ^
 --mount type=bind,source="%TESPDIR%",destination="%SIM_HOME%/tesp" ^
 --workdir=%SIM_HOME% ^
 %IMAGE% ^
 bash -c "%1%"

:end
ECHO "So long TESP folks!"
EXIT /b 1

:no_tesp
ECHO "Set the 'TESPDIR' environment variable for the TESP directory"
ECHO "Command line terminal example:"
ECHO "C:\> set /p TESPDIR=C:\Users\JoeUser\tesp"
ECHO "Permanently set an environment variable for the current user:"
ECHO "C:\> setx TESPDIR 'C:\Users\JoeUser\tesp'"
ECHO "Permanently set global environment variable (for all users):"
ECHO "C:\> setx /M TESPDIR 'C:\Users\JoeUser\tesp'"
EXIT /b 1
