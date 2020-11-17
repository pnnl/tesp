set FNCS_FATAL=yes
set FNCS_TIME_DELTA=
set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 5 ^>broker.log 2^>^&1
set FNCS_CONFIG_FILE=eplus.yaml
start /b cmd /c energyplus -w FL-Miami_Intl_Ap.epw -d output -r SchoolDualController.idf ^>eplus.log 2^>^&1
set FNCS_CONFIG_FILE=eplus_json.yaml
start /b cmd /c eplus_json 432000s 300s SchoolDualController eplus_TE_metrics.json 0.02 25 4 4 ^>eplus_json.log 2^>^&1
set FNCS_CONFIG_FILE=
start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=TE_metrics.json TE.glm ^>gridlabd.log 2^>^&1
set FNCS_CONFIG_FILE=TE_substation.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.substation_loop('TE_agent_dict.json','TE', 1200)" ^>substation.log 2^>^&1
set FNCS_CONFIG_FILE=pypower.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.pypower_loop('TE_pp.json','TE')" ^>pypower.log 2^>^&1
