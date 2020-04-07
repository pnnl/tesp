#!/bin/bash
(exec helics_broker -f 2 --loglevel=4 --name=mainbroker &> broker.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('ppcase.json','ppcase',helicsConfig='pypowerConfig.json')" &> pypower.log &)
(exec helics_recorder --input=helicsRecorder.txt --stop 172801s &> recorder.log &)

