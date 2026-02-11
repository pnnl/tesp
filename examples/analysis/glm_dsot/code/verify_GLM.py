"""This script was written to check generated .glms against existing .glms that 
have been tested and are known to solve successfully.
"""
from tesp_support.api.modify_GLM import GLMModifier
import tesp_support.api.parse_helpers as helpers
import os
import matplotlib.pyplot as plt
import numpy as np


def parse_water_demand(val):
        """
        Parse strings like 'small_1*1.00' or 'small_1 * 1.00' into 
         (schedule, multiplier).
        
        Returns (schedule, multiplier) or (None, None) if it can't be parsed.
        """
        if val is None:
            return None, None
        s = str(val).strip().rstrip(";")

        # Expect 'name*multiplier' or 'name * multiplier'
        parts = s.split("*")
        if len(parts) != 2:
            return None, None

        schedule = parts[0].strip()
        mult_str = parts[1].strip()

        try:
            multiplier = float(mult_str)
        except ValueError:
            return None, None

        return schedule, multiplier

class Read:
    def __init__(self, data_path, in_file_glm, label):
        self.label = label  # "New" or "Old", etc.
        self.glm = GLMModifier()
        i_glm, success = self.glm.read_model(os.path.join(data_path, in_file_glm))
        if not success:
            exit()

        print(f'[{self.label}] Total Houses: {len(i_glm.house.items())}')
        sf = 0
        sf_floor_area = 0
        mf = 0
        mf_floor_area = 0
        mh = 0
        mh_floor_area = 0
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

        self.wh_params = {
            "schedule_skew": [],
            "heating_element_capacity": [],
            "thermostat_deadband": [],
            "tank_diameter": [],
            "tank_UA": [],
            "tank_volume": [],
            "discrete_step_size": [],
            "lower_tank_setpoint": [],
            "upper_tank_setpoint": [],
            "T_mixing_valve": [],
        }
        
        self.wh_water_demand = {}

        for wh_name, water_heaters in i_glm.waterheater.items():
            for key in self.wh_params.keys():
                val = helpers.parse_number(water_heaters.get(key))
                self.wh_params[key].append(val)
            
            wd_raw = water_heaters.get("water_demand")
            sched, mult = parse_water_demand(wd_raw)
            if sched is not None and mult is not None:
                if sched not in self.wh_water_demand:
                    self.wh_water_demand[sched] = []
                self.wh_water_demand[sched].append(mult)

        for house_name, house in i_glm.house.items():
            groupid = house["groupid"]
            floor_area = house["floor_area"]
            if groupid == 'SINGLE_FAMILY':
                sf += 1
                sf_floor_area += int(floor_area)
            if groupid == 'MULTI_FAMILY':
                mf += 1
                mf_floor_area += int(floor_area)
            if groupid == 'MOBILE_HOME':
                mh += 1
                mf_floor_area += int(floor_area)
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

        print(f'[{self.label}]         Single-Family: {sf}')
        try:
            print(f'[{self.label}]             Avg floor area: {sf_floor_area/sf}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Multi-Family: {mf}')
        try:
            print(f'[{self.label}]             Avg floor area: {mf_floor_area/mf}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Mobile-Home: {mh}')
        try:
            print(f'[{self.label}]             Avg floor area: {mh_floor_area/mh}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Office: {of}')
        try:
            print(f'[{self.label}]             Avg floor area: {of_floor_area/of}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Warehouse: {wh}')
        try:
            print(f'[{self.label}]             Avg floor area: {wh_floor_area/wh}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Big Box: {bb}')
        try:
            print(f'[{self.label}]             Avg floor area: {bb_floor_area/bb}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Strip Mall: {sm}')
        try:
            print(f'[{self.label}]             Avg floor area: {sm_floor_area/sm}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Education: {ed}')
        try:
            print(f'[{self.label}]             Avg floor area: {ed_floor_area/ed}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Food Service: {fs}')
        try:
            print(f'[{self.label}]             Avg floor area: {fs_floor_area/fs}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Food Sales: {fsale}')
        try:
            print(f'[{self.label}]             Avg floor area: {fsale_floor_area/fsale}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Lodging: {lg}')
        try:
            print(f'[{self.label}]             Avg floor area: {lg_floor_area/lg}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Healthcare: {he}')
        try:
            print(f'[{self.label}]             Avg floor area: {he_floor_area/he}')
        except ZeroDivisionError:
            pass
        print(f'[{self.label}]         Low-Occupancy: {lo}')
        try:
            print(f'[{self.label}]             Avg floor area: {lo_floor_area/lo}')
        except ZeroDivisionError:
            pass

        # Feeder / network object counts
        total_ziploads = len(i_glm.ZIPload.items())
        total_nodes = len(i_glm.node.items())
        total_triplex_nodes = len(i_glm.triplex_node.items())
        total_overhead_lines = len(i_glm.overhead_line_conductor.items())
        total_line_spacing = len(i_glm.line_spacing.items())
        total_line_config = len(i_glm.line_configuration.items())
        total_triplex_meters = len(i_glm.triplex_meter.items())
        total_triplex_lines = len(i_glm.triplex_line.items())
        total_metrics = len(i_glm.metrics_collector.items())
        total_recorders = len(i_glm.recorder.items())
        total_evs = len(i_glm.evcharger_det.items())
        total_inverters = len(i_glm.inverter.items())

        print(f'[{self.label}] Total ZIPLoads: {total_ziploads}')
        print(f'[{self.label}] Total Nodes: {total_nodes}')
        print(f'[{self.label}] Total Triplex Nodes: {total_triplex_nodes}')
        print(f'[{self.label}] Total Overhead Lines: {total_overhead_lines}')
        print(f'[{self.label}] Total Line Spacing: {total_line_spacing}')
        print(f'[{self.label}] Total Line Configuration: {total_line_config}')
        print(f'[{self.label}] Total Triplex Meters: {total_triplex_meters}')
        print(f'[{self.label}] Total Triplex Lines: {total_triplex_lines}')
        print(f'[{self.label}] Total Triplex Nodes: {total_triplex_nodes}')
        print(f'[{self.label}] Total Metrics Collectors: {total_metrics}')
        print(f'[{self.label}] Total Recorders: {total_recorders}')
        print(f'[{self.label}] Total EVs: {total_evs}')
        print(f'[{self.label}] Total Inverters: {total_inverters}')

        sol = 0
        bat = 0
        for inv_name, inverter in i_glm.inverter.items():
            groupid = inverter["groupid"]
            if groupid == 'sol_inverter':
                sol += 1
            if groupid == 'batt_inverter':
                bat += 1
        print(f'[{self.label}]         PV: {sol}')
        print(f'[{self.label}]         Batteries: {bat}')

        # store values for plotting/comparison
        self.building_counts = {
            "Single-Family": sf,
            "Multi-Family": mf,
            "Mobile-Home": mh,
            "Office": of,
            "Warehouse": wh,
            "Big Box": bb,
            "Strip Mall": sm,
            "Education": ed,
            "Food Service": fs,
            "Food Sales": fsale,
            "Lodging": lg,
            "Healthcare": he,
            "Low-Occupancy": lo,
        }

        def safe_avg(total_area, count):
            return total_area / count if count > 0 else 0.0

        self.avg_floor_area = {
            "Single-Family": safe_avg(sf_floor_area, sf),
            "Multi-Family": safe_avg(mf_floor_area, mf),
            "Mobile-Home": safe_avg(mh_floor_area, mh),
            "Office": safe_avg(of_floor_area, of),
            "Warehouse": safe_avg(wh_floor_area, wh),
            "Big Box": safe_avg(bb_floor_area, bb),
            "Strip Mall": safe_avg(sm_floor_area, sm),
            "Education": safe_avg(ed_floor_area, ed),
            "Food Service": safe_avg(fs_floor_area, fs),
            "Food Sales": safe_avg(fsale_floor_area, fsale),
            "Lodging": safe_avg(lg_floor_area, lg),
            "Healthcare": safe_avg(he_floor_area, he),
            "Low-Occupancy": safe_avg(lo_floor_area, lo),
        }

        self.pv_count = sol
        self.battery_count = bat

        # Feeder configuration-related counts for comparison
        self.feeder_config = {
            "Nodes": total_nodes,
            "Triplex Nodes": total_triplex_nodes,
            "Overhead Lines": total_overhead_lines,
            "Line Spacing": total_line_spacing,
            "Line Config": total_line_config,
            "Triplex Meters": total_triplex_meters,
            "Triplex Lines": total_triplex_lines,
        }
    

def plot_comparison(new_read: Read, old_read: Read):
    width = 0.35

    # Feeder config comparison
    feeder_labels = list(new_read.feeder_config.keys())
    new_counts = np.array([new_read.feeder_config[l] for l in feeder_labels])
    old_counts = np.array([old_read.feeder_config[l] for l in feeder_labels])

    # keep groups that appear in at least one GLM
    mask = (new_counts + old_counts) > 0
    labels_counts = np.array(feeder_labels)[mask]
    new_counts = new_counts[mask]
    old_counts = old_counts[mask]

    if len(labels_counts) > 0:
        x = np.arange(len(labels_counts))
        plt.figure(figsize=(10, 6))
        bars_old = plt.bar(x - width/2, old_counts, width, label=old_read.label)
        bars_new = plt.bar(x + width/2, new_counts, width, label=new_read.label)
        for bars in (bars_old, bars_new):
            for bar in bars:
                height = bar.get_height()
                if height == 0:
                    continue
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.0f}",         # or "{:.1f}" for averages, etc.
                    ha="center",
                    va="bottom",
                    fontsize=8
                )
        plt.xticks(x, labels_counts, rotation=45, ha="right")
        plt.ylabel("Count")
        plt.title("Feeder Config Counts by Group: Old vs New")
        plt.legend()
        plt.tight_layout()


    # 1) Building counts comparison
    labels = list(new_read.building_counts.keys())
    new_counts = np.array([new_read.building_counts[l] for l in labels])
    old_counts = np.array([old_read.building_counts[l] for l in labels])

    # keep groups that appear in at least one GLM
    mask = (new_counts + old_counts) > 0
    labels_counts = np.array(labels)[mask]
    new_counts = new_counts[mask]
    old_counts = old_counts[mask]

    if len(labels_counts) > 0:
        x = np.arange(len(labels_counts))
        plt.figure(figsize=(10, 6))
        bars_old = plt.bar(x - width/2, old_counts, width, label=old_read.label)
        bars_new = plt.bar(x + width/2, new_counts, width, label=new_read.label)
        for bars in (bars_old, bars_new):
            for bar in bars:
                height = bar.get_height()
                if height == 0:
                    continue
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.0f}",         # or "{:.1f}" for averages, etc.
                    ha="center",
                    va="bottom",
                    fontsize=8
                )
        plt.xticks(x, labels_counts, rotation=45, ha="right")
        plt.ylabel("Count")
        plt.title("Building Counts by Group: Old vs New")
        plt.legend()
        plt.tight_layout()

    # 2) Average floor area comparison
    floor_labels = list(new_read.avg_floor_area.keys())
    new_avg = np.array([new_read.avg_floor_area[l] for l in floor_labels])
    old_avg = np.array([old_read.avg_floor_area[l] for l in floor_labels])

    mask_avg = (new_avg + old_avg) > 0
    floor_labels_plot = np.array(floor_labels)[mask_avg]
    new_avg = new_avg[mask_avg]
    old_avg = old_avg[mask_avg]

    if len(floor_labels_plot) > 0:
        x2 = np.arange(len(floor_labels_plot))
        plt.figure(figsize=(10, 6))
        bars_old = plt.bar(x2 - width/2, old_avg, width, label=old_read.label)
        bars_new = plt.bar(x2 + width/2, new_avg, width, label=new_read.label)
        for bars in (bars_old, bars_new):
            for bar in bars:
                height = bar.get_height()
                if height == 0:
                    continue
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.0f}",         # or "{:.1f}" for averages, etc.
                    ha="center",
                    va="bottom",
                    fontsize=8
                )
        plt.xticks(x2, floor_labels_plot, rotation=45, ha="right")
        plt.ylabel("Average Floor Area")
        plt.title("Average Floor Area by Group: Old vs New")
        plt.legend()
        plt.tight_layout()

    # 3) PV and battery counts comparison
    labels_inv = ["PV", "Battery"]
    new_inv = [new_read.pv_count, new_read.battery_count]
    old_inv = [old_read.pv_count, old_read.battery_count]

    if any(new_inv) or any(old_inv):
        x3 = np.arange(len(labels_inv))
        plt.figure(figsize=(6, 5))
        bars_old = plt.bar(x3 - width/2, old_inv, width, label=old_read.label)
        bars_new = plt.bar(x3 + width/2, new_inv, width, label=new_read.label)
        for bars in (bars_old, bars_new):
            for bar in bars:
                height = bar.get_height()
                if height == 0:
                    continue
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.0f}",         # or "{:.1f}" for averages, etc.
                    ha="center",
                    va="bottom",
                    fontsize=8
                )
        plt.xticks(x3, labels_inv)
        plt.ylabel("Count")
        plt.title("Inverter Counts (PV / Battery): Old vs New")
        plt.legend()
        plt.tight_layout()

    plt.show()

def plot_waterheater_histograms_comparison(new_read, old_read, bins=20):
    """Side-by-side histograms for New vs Old for each waterheater parameter."""
    all_keys = set(new_read.wh_params.keys()) | set(old_read.wh_params.keys())
    keys = [
        k for k in all_keys
        if len(new_read.wh_params.get(k, [])) > 0
        or len(old_read.wh_params.get(k, [])) > 0
    ]

    n = len(keys)
    ncols = 3
    nrows = (n + ncols - 1) // ncols

    plt.figure(figsize=(6 * ncols, 3 * nrows))

    for idx, key in enumerate(keys, start=1):
        plt.subplot(nrows, ncols, idx)

        new_vals = new_read.wh_params.get(key, [])
        old_vals = old_read.wh_params.get(key, [])

        # combined range for the histogram bins
        all_vals = new_vals + old_vals
        if not all_vals:
            continue

        plt.hist(
            old_vals,
            bins=bins,
            histtype="step",
            linewidth=2,
            color="blue",
            label=old_read.label,
        )
        plt.hist(
            new_vals,
            bins=bins,
            alpha=0.5,
            color="orange",
            edgecolor="black",
            label=new_read.label,
        )

        plt.title(key)
        plt.xlabel(key)
        plt.ylabel("Count")
        plt.legend()

    plt.suptitle("Waterheater Parameter Distributions – Old vs New")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

    # Water heater demand
    all_scheds = set(new_read.wh_water_demand.keys()) | set(old_read.wh_water_demand.keys())
    scheds = [
        s for s in all_scheds
        if len(new_read.wh_water_demand.get(s, [])) > 0
        or len(old_read.wh_water_demand.get(s, [])) > 0
    ]

    if scheds:
        n = len(scheds)
        ncols = 3
        nrows = (n + ncols - 1) // ncols

        plt.figure(figsize=(6 * ncols, 3 * nrows))

        for idx, sched in enumerate(scheds, start=1):
            plt.subplot(nrows, ncols, idx)

            new_vals = new_read.wh_water_demand.get(sched, [])
            old_vals = old_read.wh_water_demand.get(sched, [])

            if not new_vals and not old_vals:
                continue

            plt.hist(
                old_vals,
                bins=bins,
                histtype="step",
                linewidth=2,
                color="blue",
                label=old_read.label,
            )
            plt.hist(
                new_vals,
                bins=bins,
                alpha=0.5,
                color="orange",
                edgecolor="black",
                label=new_read.label,
            )

            plt.title(sched)
            plt.xlabel("Water demand multiplier")
            plt.ylabel("Count")
            plt.legend()

        plt.suptitle("Water Demand Multipliers by Schedule – Old vs New")
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()

def read_new():
    data_path = os.path.expandvars('$TESPDIR/examples/analysis/glm_dsot/code')
    num = 2
    in_file_glm = f'feeder_test_pv_bt_fl_ev/Substation_{num}/Substation_{num}.glm'
    print('---------------New----------------')
    return Read(data_path, in_file_glm, label="New")


def read_old():
    data_path = os.path.expandvars('$TESPDIR/examples/analysis/dsot/code')
    num = 2
    in_file_glm = f'Substation_{num}_original.glm'
    print('---------------Old----------------')
    return Read(data_path, in_file_glm, label="Old")


if __name__ == "__main__":
    new_read = read_new()
    old_read = read_old()
    plot_comparison(new_read, old_read)
    plot_waterheater_histograms_comparison(new_read, old_read)