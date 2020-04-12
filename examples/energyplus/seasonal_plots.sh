declare -r ROOT=$1
declare -r TITLE=$2

python3 -c "import tesp_support.process_eplus as ep;ep.process_eplus ('Winter$ROOT', '$TITLE, January 3-4', 'Winter$ROOT.png')"
python3 -c "import tesp_support.process_eplus as ep;ep.process_eplus ('Summer$ROOT', '$TITLE, August 1-2', 'Summer$ROOT.png')"
