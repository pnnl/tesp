#!/bin/bash

mkdir $1
if [ -d "$1" ]
then

  archive_folder="/mnt/simdata/done"
  python3 -c "import tesp_support.helpers_dsot_v1 as tesp; tesp.write_management_script('$archive_folder', '$1', '.', 0, 0)"

  cd $1
  rm -f *metrics.h5
  rm -f *metrics.json
  rm -f *dict.json
  rm -f *.log
  rm -f *opf.csv
  rm -f *pf.csv
  rm -f *.dat

  cp -f ../8_system_case_config.json generate_case_config.json
  #cp -f ../8_hi_system_case_config.json generate_case_config.json

  #cp -f ../200_system_case_config.json generate_case_config.json
  #cp -f ../200_hi_system_case_config.json generate_case_config.json

  python3 -c "import sys; sys.path.insert(1,'..'); import dsoStub; dsoStub.dso_make_yaml('./generate_case_config')"

echo "
#export FNCS_FATAL=YES
#export FNCS_LOG_STDOUT=yes
export FNCS_LOG_LEVEL=INFO

(export FNCS_BROKER=\"tcp://*:5570\" && exec fncs_broker 7 &> ./broker.log &)
(export FNCS_CONFIG_FILE=dso.yaml && exec python3 -c \"import sys; sys.path.insert(1,'..'); import dsoStub; dsoStub.dso_loop('./generate_case_config')\" &> dso.log &)
(export FNCS_CONFIG_FILE=tso.yaml && exec python3 -c \"import tesp_support.fncsTSO as tesp;tesp.tso_loop('./generate_case_config')\" &> ./tso.log &)
(export FNCS_CONFIG_FILE=gen_player.yaml && exec python3 -c \"import tesp_support.load_player as tesp;tesp.load_player_loop('./generate_case_config', 'genMn')\" &> ./gen_player.log &)
(export FNCS_CONFIG_FILE=alt_player.yaml && exec python3 -c \"import tesp_support.load_player as tesp;tesp.load_player_loop('./generate_case_config', 'genForecastHr')\" &> ./alt_player.log &)
(export FNCS_CONFIG_FILE=ind_player.yaml && exec python3 -c \"import tesp_support.load_player as tesp;tesp.load_player_loop('./generate_case_config', 'indLoad')\" &> ./ind_player.log &)
(export FNCS_CONFIG_FILE=gld_player.yaml && exec python3 -c \"import tesp_support.load_player as tesp;tesp.load_player_loop('./generate_case_config', 'gldLoad')\" &> ./gld_player.log &)
(export FNCS_CONFIG_FILE=ref_player.yaml && exec python3 -c \"import tesp_support.load_player as tesp;tesp.load_player_loop('./generate_case_config', 'refLoadMn')\" &> ./ref_player.log &)
" > run.sh
  chmod 755 run.sh

fi