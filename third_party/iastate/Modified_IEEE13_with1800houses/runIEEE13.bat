set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=DEBUG4
set FNCS_TRACE=yes
set FNCS_TIME_DELTA=

set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 6 ^>broker.log 2^>^&1

set FNCS_CONFIG_FILE=tracer.yaml
start /b cmd /c fncs_tracer 2d tracer.out ^>tracer.log 2^>^&1

set FNCS_CONFIG_FILE=auction_Market_1.yaml
start /b cmd /c python auction_Market_1.py IEEE13 "2013-07-01 00:00:00" 172800 600 ^>auctionMarket1.log 2^>^&1

set FNCS_CONFIG_FILE=
set FNCS_LOG_LEVEL=DEBUG4
set FNCS_LOG_STDOUT=yes
start /b cmd /c gridlabd IEEE13.glm ^>gridlabd.log 2^>^&1 

set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=DEBUG4
set FNCS_TIME_DELTA=60s

start /b cmd /c python house_controller.py input/controller_registration_F1_house_B22_thermostat_controller.json ^>F1_house_B22.log 2^>^&1
start /b cmd /c python house_controller.py input/controller_registration_house_1_2_thermostat_controller.json ^>house_1_2.log 2^>^&1
start /b cmd /c python house_controller.py input/controller_registration_house_1_3_thermostat_controller.json ^>house_1_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_1_4_thermostat_controller.json ^>house_1_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_1_5_thermostat_controller.json ^>house_1_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_1_6_thermostat_controller.json ^>house_1_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_1_7_thermostat_controller.json ^>house_1_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_1_8_thermostat_controller.json ^>house_1_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_1_9_thermostat_controller.json ^>house_1_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_1_10_thermostat_controller.json ^>house_1_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_1_11_thermostat_controller.json ^>house_1_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_1_12_thermostat_controller.json ^>house_1_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_2_1_thermostat_controller.json ^>house_2_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_2_thermostat_controller.json ^>house_2_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_3_thermostat_controller.json ^>house_2_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_4_thermostat_controller.json ^>house_2_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_5_thermostat_controller.json ^>house_2_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_6_thermostat_controller.json ^>house_2_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_7_thermostat_controller.json ^>house_2_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_8_thermostat_controller.json ^>house_2_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_9_thermostat_controller.json ^>house_2_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_10_thermostat_controller.json ^>house_2_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_11_thermostat_controller.json ^>house_2_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_2_12_thermostat_controller.json ^>house_2_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_3_1_thermostat_controller.json ^>house_3_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_2_thermostat_controller.json ^>house_3_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_3_thermostat_controller.json ^>house_3_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_4_thermostat_controller.json ^>house_3_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_5_thermostat_controller.json ^>house_3_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_6_thermostat_controller.json ^>house_3_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_7_thermostat_controller.json ^>house_3_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_8_thermostat_controller.json ^>house_3_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_9_thermostat_controller.json ^>house_3_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_10_thermostat_controller.json ^>house_3_10.log 2^>^&1
REM REM start /b cmd /c python house_controller.py input/controller_registration_house_3_11_thermostat_controller.json ^>house_3_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_3_12_thermostat_controller.json ^>house_3_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_4_1_thermostat_controller.json ^>house_4_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_2_thermostat_controller.json ^>house_4_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_3_thermostat_controller.json ^>house_4_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_4_thermostat_controller.json ^>house_4_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_5_thermostat_controller.json ^>house_4_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_6_thermostat_controller.json ^>house_4_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_7_thermostat_controller.json ^>house_4_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_8_thermostat_controller.json ^>house_4_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_9_thermostat_controller.json ^>house_4_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_10_thermostat_controller.json ^>house_4_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_11_thermostat_controller.json ^>house_4_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_4_12_thermostat_controller.json ^>house_4_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_5_1_thermostat_controller.json ^>house_5_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_2_thermostat_controller.json ^>house_5_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_3_thermostat_controller.json ^>house_5_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_4_thermostat_controller.json ^>house_5_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_5_thermostat_controller.json ^>house_5_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_6_thermostat_controller.json ^>house_5_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_7_thermostat_controller.json ^>house_5_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_8_thermostat_controller.json ^>house_5_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_9_thermostat_controller.json ^>house_5_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_10_thermostat_controller.json ^>house_5_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_11_thermostat_controller.json ^>house_5_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_5_12_thermostat_controller.json ^>house_5_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_6_1_thermostat_controller.json ^>house_6_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_6_2_thermostat_controller.json ^>house_6_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_6_3_thermostat_controller.json ^>house_6_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_6_4_thermostat_controller.json ^>house_6_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_6_5_thermostat_controller.json ^>house_6_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_6_6_thermostat_controller.json ^>house_6_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_6_7_thermostat_controller.json ^>house_6_7.log 2^>^&1
REM REM start /b cmd /c python house_controller.py input/controller_registration_house_6_8_thermostat_controller.json ^>house_6_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_6_9_thermostat_controller.json ^>house_6_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_6_10_thermostat_controller.json ^>house_6_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_6_11_thermostat_controller.json ^>house_6_11.log 2^>^&1
REM REM start /b cmd /c python house_controller.py input/controller_registration_house_6_12_thermostat_controller.json ^>house_6_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_7_1_thermostat_controller.json ^>house_7_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_2_thermostat_controller.json ^>house_7_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_3_thermostat_controller.json ^>house_7_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_4_thermostat_controller.json ^>house_7_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_5_thermostat_controller.json ^>house_7_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_6_thermostat_controller.json ^>house_7_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_7_thermostat_controller.json ^>house_7_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_8_thermostat_controller.json ^>house_7_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_9_thermostat_controller.json ^>house_7_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_10_thermostat_controller.json ^>house_7_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_11_thermostat_controller.json ^>house_7_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_7_12_thermostat_controller.json ^>house_7_12.log 2^>^&1


REM start /b cmd /c python house_controller.py input/controller_registration_house_8_1_thermostat_controller.json ^>house_8_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_2_thermostat_controller.json ^>house_8_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_3_thermostat_controller.json ^>house_8_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_4_thermostat_controller.json ^>house_8_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_5_thermostat_controller.json ^>house_8_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_6_thermostat_controller.json ^>house_8_6.log 2^>^&1
REM REM start /b cmd /c python house_controller.py input/controller_registration_house_8_7_thermostat_controller.json ^>house_8_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_8_thermostat_controller.json ^>house_8_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_9_thermostat_controller.json ^>house_8_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_10_thermostat_controller.json ^>house_8_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_11_thermostat_controller.json ^>house_8_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_8_12_thermostat_controller.json ^>house_8_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_9_1_thermostat_controller.json ^>house_9_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_2_thermostat_controller.json ^>house_9_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_3_thermostat_controller.json ^>house_9_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_4_thermostat_controller.json ^>house_9_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_5_thermostat_controller.json ^>house_9_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_6_thermostat_controller.json ^>house_9_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_7_thermostat_controller.json ^>house_9_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_8_thermostat_controller.json ^>house_9_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_9_thermostat_controller.json ^>house_9_9.log 2^>^&1
REM REM start /b cmd /c python house_controller.py input/controller_registration_house_9_10_thermostat_controller.json ^>house_9_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_11_thermostat_controller.json ^>house_9_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_9_12_thermostat_controller.json ^>house_9_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_10_1_thermostat_controller.json ^>house_10_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_2_thermostat_controller.json ^>house_10_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_3_thermostat_controller.json ^>house_10_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_4_thermostat_controller.json ^>house_10_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_5_thermostat_controller.json ^>house_10_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_6_thermostat_controller.json ^>house_10_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_7_thermostat_controller.json ^>house_10_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_8_thermostat_controller.json ^>house_10_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_9_thermostat_controller.json ^>house_10_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_10_thermostat_controller.json ^>house_10_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_11_thermostat_controller.json ^>house_10_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_10_12_thermostat_controller.json ^>house_10_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_11_1_thermostat_controller.json ^>house_11_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_2_thermostat_controller.json ^>house_11_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_3_thermostat_controller.json ^>house_11_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_4_thermostat_controller.json ^>house_11_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_5_thermostat_controller.json ^>house_11_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_6_thermostat_controller.json ^>house_11_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_7_thermostat_controller.json ^>house_11_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_8_thermostat_controller.json ^>house_11_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_9_thermostat_controller.json ^>house_11_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_10_thermostat_controller.json ^>house_11_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_11_thermostat_controller.json ^>house_11_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_11_12_thermostat_controller.json ^>house_11_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_12_1_thermostat_controller.json ^>house_12_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_2_thermostat_controller.json ^>house_12_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_3_thermostat_controller.json ^>house_12_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_4_thermostat_controller.json ^>house_12_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_5_thermostat_controller.json ^>house_12_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_6_thermostat_controller.json ^>house_12_6.log 2^>^&1
REM REM start /b cmd /c python house_controller.py input/controller_registration_house_12_7_thermostat_controller.json ^>house_12_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_8_thermostat_controller.json ^>house_12_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_9_thermostat_controller.json ^>house_12_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_10_thermostat_controller.json ^>house_12_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_11_thermostat_controller.json ^>house_12_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_12_12_thermostat_controller.json ^>house_12_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_13_1_thermostat_controller.json ^>house_13_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_2_thermostat_controller.json ^>house_13_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_3_thermostat_controller.json ^>house_13_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_4_thermostat_controller.json ^>house_13_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_5_thermostat_controller.json ^>house_13_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_6_thermostat_controller.json ^>house_13_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_7_thermostat_controller.json ^>house_13_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_8_thermostat_controller.json ^>house_13_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_9_thermostat_controller.json ^>house_13_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_10_thermostat_controller.json ^>house_13_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_11_thermostat_controller.json ^>house_13_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_13_12_thermostat_controller.json ^>house_13_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_14_1_thermostat_controller.json ^>house_14_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_2_thermostat_controller.json ^>house_14_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_3_thermostat_controller.json ^>house_14_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_4_thermostat_controller.json ^>house_14_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_5_thermostat_controller.json ^>house_14_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_6_thermostat_controller.json ^>house_14_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_7_thermostat_controller.json ^>house_14_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_8_thermostat_controller.json ^>house_14_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_9_thermostat_controller.json ^>house_14_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_10_thermostat_controller.json ^>house_14_10.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_11_thermostat_controller.json ^>house_14_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_14_12_thermostat_controller.json ^>house_14_12.log 2^>^&1

REM start /b cmd /c python house_controller.py input/controller_registration_house_15_1_thermostat_controller.json ^>house_15_1.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_2_thermostat_controller.json ^>house_15_2.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_3_thermostat_controller.json ^>house_15_3.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_4_thermostat_controller.json ^>house_15_4.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_5_thermostat_controller.json ^>house_15_5.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_6_thermostat_controller.json ^>house_15_6.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_7_thermostat_controller.json ^>house_15_7.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_8_thermostat_controller.json ^>house_15_8.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_9_thermostat_controller.json ^>house_15_9.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_10_thermostat_controller.json ^>house_15_10.log 2^>^&1
REM REM start /b cmd /c python house_controller.py input/controller_registration_house_15_11_thermostat_controller.json ^>house_15_11.log 2^>^&1
REM start /b cmd /c python house_controller.py input/controller_registration_house_15_12_thermostat_controller.json ^>house_15_12.log 2^>^&1