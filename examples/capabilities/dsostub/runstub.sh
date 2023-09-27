#!/bin/bash

mkdir -p "$1"
if [ -d "$1" ]
then

  archive_folder="."
  touch "./$1/run.sh"
  python3 -c "import tesp_support.dsot.helpers_dsot as tesp; tesp.write_management_script('$archive_folder', '$1', '.', 0, 0)"

  cd "$1" || exit
  rm -f "./*metrics.h5"
  rm -f "./*metrics.json"
  rm -f "./*dict.json"
  rm -f "./*.log"
  rm -f "./*opf.csv"
  rm -f "./*pf.csv"
  rm -f "./*.dat"
  mkdir -p PyomoTempFiles

  cp -f ../case_config.json .

  python3 -c "import sys; sys.path.insert(1,'..'); import dsoStub; dsoStub.dso_make_stub('./case_config')"

echo "#!/bin/bash

(exec helics_broker -f 7 --loglevel=warning --name=mainbroker &> broker.log &)
(exec python3 -c \"import sys; sys.path.insert(1,'..');import dsoStub;dsoStub.dso_loop('./case_config')\" &> dso.log &)
(exec python3 -c \"import tesp_support.api.tso_psst as tesp;tesp.tso_psst_loop('./case_config')\" &> ./tso.log &)
(exec python3 -c \"import tesp_support.api.player as tesp;tesp.load_player_loop('./case_config', 'genMn')\" &> ./gen_player.log &)
(exec python3 -c \"import tesp_support.api.player as tesp;tesp.load_player_loop('./case_config', 'genForecastHr')\" &> ./alt_player.log &)
(exec python3 -c \"import tesp_support.api.player as tesp;tesp.load_player_loop('./case_config', 'indLoad')\" &> ./ind_player.log &)
(exec python3 -c \"import tesp_support.api.player as tesp;tesp.load_player_loop('./case_config', 'gldLoad')\" &> ./gld_player.log &)
(exec python3 -c \"import tesp_support.api.player as tesp;tesp.load_player_loop('./case_config', 'refLoadMn')\" &> ./ref_player.log &)
" > run.sh

fi