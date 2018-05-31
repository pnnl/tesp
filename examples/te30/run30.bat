set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=
set FNCS_TRACE=no
set FNCS_TIME_DELTA=

set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 35 ^>broker.log 2^>^&1

rem set FNCS_LOG_LEVEL=
set FNCS_CONFIG_FILE=eplus.yaml
start /b cmd /c energyplus -w ../../support/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../../support/energyplus/SchoolDualController.idf ^>eplus.log 2^>^&1

set FNCS_CONFIG_FILE=eplus_json.yaml
start /b cmd /c eplus_json 2d 5m School_DualController eplus_TE_Challenge_metrics.json ^>eplus_json.log 2^>^&1

rem set FNCS_CONFIG_FILE=tracer.yaml
rem start /b cmd /c fncs_tracer 2d tracer.out ^>tracer.log 2^>^&1

set FNCS_CONFIG_FILE=pypower30.yaml
start /b cmd /c python fncsPYPOWER.py TE_Challenge "2013-07-01 00:00:00" 172800 300 5 ^>pypower.log 2^>^&1

set FNCS_CONFIG_FILE=
set FNCS_LOG_LEVEL=
set FNCS_LOG_STDOUT=yes
start /b cmd /c gridlabd TE_Challenge.glm ^>gridlabd.log 2^>^&1 

rem set FNCS_LOG_LEVEL=
set FNCS_TIME_DELTA=5s
start /b cmd /c python double_auction.py input/auction_registration.json TE_Challenge ^>auction.log 2^>^&1

set FNCS_LOG_STDOUT=no
set FNCS_LOG_LEVEL=
set FNCS_TIME_DELTA=5s

start /b cmd /c python house_controller.py input/controller_registration_F1_house_B0_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_C1_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_C2_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_B3_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_B4_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A5_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_B6_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_B7_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A8_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A9_thermostat_controller.json 
start /b cmd /c python house_controller.py input/controller_registration_F1_house_C10_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A11_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A12_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A13_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_C14_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A15_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A16_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_C17_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_C18_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_B19_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_B20_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_C21_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_B22_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_B23_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_B24_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A25_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A26_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_C27_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_A28_thermostat_controller.json
start /b cmd /c python house_controller.py input/controller_registration_F1_house_C29_thermostat_controller.json
