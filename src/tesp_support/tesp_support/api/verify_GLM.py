"""This script was written to check generated .glms against existing .glms that have been tested and are known to solve successfully.

"""
from api.modify_GLM import GLMModifier
import os
import numpy as np

class Read:
    def __init__(self, data_path, in_file_glm):
        self.glm = GLMModifier()

        i_glm, success = self.glm.read_model(os.path.join(data_path, in_file_glm))
        if not success:
            exit()

        print(f'Total Houses: {len(i_glm.house.items())}')
        sf = 0
        mf = 0
        mh = 0
        of = 0
        of_floor_area = 0
        wh = 0
        wh_floor_area = 0
        bb = 0
        bb_floor_area = 0
        sm = 0
        sm_floor_area = 0
        ed = 0
        ed_floor_area = 0
        fs = 0
        fs_floor_area = 0
        fsale = 0
        fsale_floor_area = 0
        lg = 0
        lg_floor_area = 0
        he = 0
        he_floor_area = 0
        lo = 0
        lo_floor_area = 0
        for house_name, house in i_glm.house.items():
            groupid = house["groupid"]
            floor_area = house["floor_area"]
            if groupid == 'SINGLE_FAMILY':
                sf += 1
            if groupid == 'MULTI_FAMILY':
                mf += 1
            if groupid == 'MOBILE_HOME':
                mh += 1
            if groupid == 'office':
                of += 1
                of_floor_area += int(floor_area)
            if groupid == 'warehouse_storage':
                wh += 1
                wh_floor_area += int(floor_area)
            if groupid == 'big_box':
                bb += 1
                bb_floor_area += int(floor_area)
            if groupid == 'strip_mall':
                sm += 1
                sm_floor_area += int(floor_area)
            if groupid == 'education':
                ed += 1
                ed_floor_area += int(floor_area)
            if groupid == 'food_service':
                fs += 1
                fs_floor_area += int(floor_area)
            if groupid == 'food_sales':
                fsale += 1
                fsale_floor_area += int(floor_area)
            if groupid == 'lodging':
                lg += 1
                lg_floor_area += int(floor_area)
            if groupid == 'healthcare_inpatient':
                he += 1
                he_floor_area += int(floor_area)
            if groupid == 'low_occupancy':
                lo += 1
                lo_floor_area += int(floor_area)
        print(f'        Single-Family: {sf}')
        print(f'        Multi-Family: {mf}')
        print(f'        Mobile-Home: {mh}')
        print(f'        Office: {of}')
        try:
            print(f'            Avg floor area: {of_floor_area/of}')
        except ZeroDivisionError:
            pass
        print(f'        Warehouse: {wh}')
        try:
            print(f'            Avg floor area: {wh_floor_area/wh}')
        except ZeroDivisionError:
            pass
        print(f'        Big Box: {bb}')
        try:
            print(f'            Avg floor area: {bb_floor_area/bb}')
        except ZeroDivisionError:
            pass
        print(f'        Strip Mall: {sm}')
        try:
            print(f'            Avg floor area: {sm_floor_area/sm}')
        except ZeroDivisionError:
            pass
        print(f'        Education: {ed}')
        try:
            print(f'            Avg floor area: {ed_floor_area/ed}')
        except ZeroDivisionError:
            pass
        print(f'        Food Service: {fs}')
        try:
            print(f'            Avg floor area: {fs_floor_area/fs}')
        except ZeroDivisionError:
            pass
        print(f'        Food Sales: {fsale}')
        try:
            print(f'            Avg floor area: {fsale_floor_area/fsale}')
        except ZeroDivisionError:
            pass
        print(f'        Lodging: {lg}')
        try:
            print(f'            Avg floor area: {lg_floor_area/lg}')
        except ZeroDivisionError:
            pass
        print(f'        Healthcare: {he}')
        try:
            print(f'            Avg floor area: {he_floor_area/he}')
        except ZeroDivisionError:
            pass
        print(f'        Low-Occupancy: {lo}')
        try:
            print(f'            Avg floor area: {lo_floor_area/lo}')
        except ZeroDivisionError:
            pass

        print(f'Total ZIPLoads: {len(i_glm.ZIPload.items())}')
        print(f'Total Nodes: {len(i_glm.node.items())}')
        print(f'Total Triplex Nodes: {len(i_glm.triplex_node.items())}')
        print(f'Total Overhead Lines: {len(i_glm.overhead_line_conductor.items())}')
        print(f'Total Line Spacing: {len(i_glm.line_spacing.items())}')
        print(f'Total Line Configuration: {len(i_glm.line_configuration.items())}')
        print(f'Total Triplex Meters: {len(i_glm.triplex_meter.items())}')
        print(f'Total Triplex Lines: {len(i_glm.triplex_line.items())}')
        print(f'Total Triplex Nodes: {len(i_glm.triplex_node.items())}')
        print(f'Total Metrics Collectors: {len(i_glm.metrics_collector.items())}')
        print(f'Total Recorders: {len(i_glm.recorder.items())}')
        print(f'Total EVs: {len(i_glm.evcharger_det.items())}')
        print(f'Total Inverters: {len(i_glm.inverter.items())}')
        sol = 0
        bat = 0
        for inv_name, inverter in i_glm.inverter.items():
            groupid = inverter["groupid"]
            if groupid == 'sol_inverter':
                sol += 1
            if groupid == 'batt_inverter':
                bat += 1
        print(f'        PV: {sol}')
        print(f'        Batteries: {bat}')



def read_new():
    data_path = os.path.expandvars('$TESPDIR/examples/analysis/glm_dsot/code')
    in_file_glm = '8_2016_05_pv_bt_fl_ev/Substation_1/Substation_1.glm'
    print('---------------New----------------')
    Read(data_path, in_file_glm)


def read_old():
    data_path = os.path.expandvars('$TESPDIR/examples/analysis/glm_dsot/data')
    in_file_glm = 'Substation_1.glm'
    print('---------------Old----------------')
    Read(data_path, in_file_glm)

if __name__ == "__main__":
    read_new()
    read_old()