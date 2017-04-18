(export FNCS_LOG_STDOUT=yes && exec fncs_broker 4 &> broker.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w ../USA_IN_Indianapolis.Intl.AP.724380_TMY3.epw -d output -r ../RefBldgPrimarySchoolNew2004DualControllerv8.3Fncs.idf &> eplus.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_LOG_LEVEL=DEBUG4 && exec fncs_player 1d prices.txt &> player.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 1d 5m School_DualController eplus.json &> eplus_json.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 1d tracer.out &> tracer.log &)

