declare -r TESP_SUPPORT=$TESP_INSTALL/share/support

#python3 -c "import tesp_support.api as tesp;tesp.merge_idf('$TESP_SUPPORT/energyplus/FullServiceRestaurant.idf','emsFullServiceRestaurant.idf', '2013-01-03 00:00:00', '2013-01-05 00:00:00', 'Merged.idf')"

#python3 -c "import tesp_support.api as tesp;tesp.merge_idf('SchoolBase.idf','emsSchoolBase.idf', '2013-01-03 00:00:00', '2013-01-05 00:00:00', 'Merged.idf')"
python3 -c "import tesp_support.api as tesp;tesp.merge_idf('SchoolBase.idf','emsSchoolBase.idf', '2013-08-01 00:00:00', '2013-08-03 00:00:00', 'Merged.idf')"

(export FNCS_LOG_STDOUT=yes && exec fncs_broker 4 &> broker.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w $TESP_SUPPORT/energyplus/USA_IN_Indianapolis.Intl.AP.724380_TMY3.epw -d output -r Merged.idf &> eplus.log &)
(export FNCS_LOG_STDOUT=yes && exec fncs_player 2d prices.txt &> player.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m SchoolDualController eplus_eplus_metrics.json  0.10 50 6 6 &> eplus_json.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 2d tracer.out &> tracer.log &)
