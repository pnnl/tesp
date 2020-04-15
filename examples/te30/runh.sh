declare -r TESP_SUPPORT=$TESP_INSTALL/share/support
declare -r SCHED_PATH=$TESP_SUPPORT/schedules

# start a FNCS federation for energyplus with agent
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 2 &> fncs_broker.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w $TESP_SUPPORT/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r Merged.idf &> helics_eplus.log &)
(export FNCS_CONFIG_FILE=eplus_agent.yaml && exec eplus_agent 2d 5m SchoolDualController eplus_TE_ChallengeH_metrics.json 0.02 25 4 4 helics_eplus_agent.json &> helics_eplus_agent.log &)

# start a HELICS federation for GridLAB-D, substation, weather and PYPOWER; the E+ agent was already started as part of the FNCS federation
(exec helics_broker -f 5 --loglevel=4 --name=mainbroker &> helics_broker.log &)
(exec gridlabd -D SCHED_PATH=$SCHED_PATH -D USE_HELICS -D METRICS_FILE=TE_ChallengeH_metrics.json TE_Challenge.glm &> helics_gridlabd.log &)
(export WEATHER_CONFIG=TE_Challenge_HELICS_Weather_Config.json && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" &> helics_weather.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('te30_pp.json','TE_ChallengeH',helicsConfig='pypowerConfig.json')" &> helics_pypower.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('TE_Challenge_agent_dict.json','TE_ChallengeH',helicsConfig='TE_Challenge_HELICS_substation.json')" &> helics_substation.log &)

