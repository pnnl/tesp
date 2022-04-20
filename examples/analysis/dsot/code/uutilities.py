# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: uutilities.py


import os
import re
import json
import tesp_support.helpers_dsot_v1 as helpers


class HelicsMsg(object):

    def __init__(self, name):
        self._name = name
        # self._level = "debug"
        self._level = "warning"
        self._subs = []
        self._pubs = []
        pass

    def write_file(self, _dt, _fn):
        msg = {"name": self._name,
               "period": _dt,
               "logging": self._level,
               "publications": self._pubs,
               "subscriptions": self._subs}
        op = open(_fn, 'w', encoding='utf-8')
        json.dump(msg, op, ensure_ascii=False, indent=2)
        op.close()

    def pubs_append(self, _g, _k, _t, _o, _p):
        # for object and property is for internal code interface for gridlabd
        self._pubs.append({"global": _g, "key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def pubs_append_n(self, _g, _k, _t):
        self._pubs.append({"global": _g, "key": _k, "type": _t})

    def subs_append(self, _k, _t, _o, _p):
        # for object and property is for internal code interface for gridlabd
        self._subs.append({"key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def subs_append_n(self, _n, _k, _t):
        self._subs.append({"name": _n, "key": _k, "type": _t})


def write_players_msg(case_name, sys_config, dt):
    # write player helics message file for load and generator players

    dso_cnt = len(sys_config['FNCS'])
    players = sys_config["players"]
    for idx in range(len(players)):
        player = sys_config[players[idx]]
        pf = HelicsMsg(player[0] + "player")
        if player[8]:
            # load
            for i in range(dso_cnt):
                bs = str(i + 1)
                pf.pubs_append_n(False, player[0] + "_load_" + bs, "string")
                pf.pubs_append_n(False, player[0] + "_ld_hist_" + bs, "string")
        else:
            # power
            genfuel = sys_config["genfuel"]
            for i in range(len(genfuel)):
                if genfuel[i][0] in sys_config["renewables"]:
                    idx = str(genfuel[i][2])
                    if player[6]:
                        pf.pubs_append_n(False, player[0] + "_power_" + idx, "string")
                    if player[7]:
                        pf.pubs_append_n(False, player[0] + "_pwr_hist_" + idx, "string")
        pf.write_file(dt, case_name + "/" + player[0] + "_player.json")


def initialize_config_dict(fgconfig):

    # https://stackoverflow.com/questions/41555953/how-to-assign-global-variables-from-dictionary#41556423

    if fgconfig is not None:
        ConfigDict = {}
        with open(fgconfig,'r') as fgfile:
            confile = fgfile.read()
            ConfigDict = json.loads(confile)
            for dictionary in ConfigDict:
                    globals()[dictionary] = ConfigDict[dictionary]
            fgfile.close()
        with open("./e_config.json",'w') as fgfile:
            confile = fgfile.read()
            ConfigDict = json.loads(confile)
            for dictionary in ConfigDict:
                    globals()[dictionary] = ConfigDict[dictionary]
            fgfile.close()


if __name__ == "__main__":
    initialize_config_dict("./8_system_case_config.json")

    pass
    # write_FNCS_config_yaml_file_header()
    # write_FNCS_config_yaml_file_values('abc', dict())
