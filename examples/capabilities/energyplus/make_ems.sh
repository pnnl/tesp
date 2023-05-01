#!/bin/bash
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: make_ems.sh

python3 -c "import tesp_support.api.proces as tesp;tesp.make_ems('./output','ems.idf',writeSummary=True,bHELICS=False)"

