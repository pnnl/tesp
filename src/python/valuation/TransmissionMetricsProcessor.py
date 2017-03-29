#	Copyright (C) 2017 Battelle Memorial Institute
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;
import xarray as xr

class TransmissionMetricsProcessor:
    casename = ""
    casepath =""
    bus_metrics = None
    gen_metrics = None
    def __init__(self,case_name="",case_path=""):
        self.casename = case_name
        self.casepath = case_path

    def loadAllMetricsFromJSONFiles(self,case_name="",case_path=""):
        if(len(case_name)>0):
            self.casename = case_name
        if(len(case_path)>0):
            self.casepath = case_path
        
        lp = open(self.casepath + self.casename + "_m_dict.json").read()
        dict = json.loads(lp)
        baseMVA = dict['baseMVA']
        ampFactor = dict['ampFactor']
        gen_keys = list(dict['generators'].keys())
        gen_keys.sort()
        bus_keys = list(dict['fncsBuses'].keys())
        bus_keys.sort()
        print("\n\nFile", self.casename, "has baseMVA", baseMVA, "with GLD load scaling =", ampFactor)
        # print("\nGenerator Dictionary:")
        # print("Unit Bus Type Pnom Pmax Costs[Start Stop C2 C1 C0]")
        # for key in gen_keys:
        #     row = dict['generators'][key]
        #     print(key, row['bus'], row['bustype'], row['Pnom'], row['Pmax'], "[", row['StartupCost'],
        #           row['ShutdownCost'], row['c2'], row['c1'], row['c0'], "]")

        print("\nFNCS Bus Dictionary:")
        print("Bus Pnom Qnom [GridLAB-D Substations]")
        for key in bus_keys:
            row = dict['fncsBuses'][key]
            print(key, row['Pnom'], row['Qnom'], row['GLDsubstations'])

        # read the bus metrics file
        lp_b = open(self.casepath + "bus_" + self.casename + "_metrics.json").read()
        lst_b = json.loads(lp_b)
        # print("\nBus Metrics data starting", lst_b['StartTime'])

        # make a sorted list of the times, and NumPy array of times in hours
        lst_b.pop('StartTime')
        # lst_b.pop('System base MVA')
        # lst_b.pop('Number of buses')
        # lst_b.pop('Number of generators')
        # lst_b.pop('Network name')
        meta_b = lst_b.pop('Metadata')
        times = list(map(int, list(lst_b.keys())))
        times.sort()
        print("There are", len(times), "sample times at", times[1] - times[0], "second intervals")

        hrs = np.array(times, dtype=np.float)
        denom = 3600.0
        hrs /= denom
        time_interval_hours = (times[1] - times[0]) / denom

        # parse the metadata for things of specific interest
        print("\nBus Metadata [Variable Index Units] for", len(lst_b[str(times[0])]), "objects")
        for key, val in meta_b.items():
            #    print (key, val['index'], val['units'])
            if key == 'LMP_P':
                LMP_P_IDX = val['index']
                LMP_P_UNITS = val['units']
            elif key == 'LMP_Q':
                LMP_Q_IDX = val['index']
                LMP_Q_UNITS = val['units']
            elif key == 'PD':
                PD_IDX = val['index']
                PD_UNITS = val['units']
            elif key == 'PQ':
                QD_IDX = val['index']
                QD_UNITS = val['units']
            elif key == 'Vang':
                VANG_IDX = val['index']
                VANG_UNITS = val['units']
            elif key == 'Vmag':
                VMAG_IDX = val['index']
                VMAG_UNITS = val['units']
            elif key == 'Vmax':
                VMAX_IDX = val['index']
                VMAX_UNITS = val['units']
            elif key == 'Vmin':
                VMIN_IDX = val['index']
                VMIN_UNITS = val['units']

        # create a NumPy array of all bus metrics
        data_b = np.empty(shape=(len(bus_keys), len(times), len(lst_b[str(times[0])][bus_keys[0]])), dtype=np.float)
        print("\nConstructed", data_b.shape, "NumPy array for Buses")
        j = 0
        for key in bus_keys:
            i = 0
            for t in times:
                ary = lst_b[str(t)][bus_keys[j]]
                data_b[j, i, :] = ary
                i = i + 1
            j = j + 1

        # display some averages
        # print("Average real power LMP =", data_b[0, :, LMP_P_IDX].mean(), LMP_P_UNITS)
        # print("Maximum bus voltage =", data_b[0, :, VMAG_IDX].max(), VMAG_UNITS)
        # print("Minimum bus voltage =", data_b[0, :, VMIN_IDX].max(), VMIN_UNITS)

        # read the generator metrics file
        lp_g = open(self.casepath + "gen_" + self.casename + "_metrics.json").read()
        lst_g = json.loads(lp_g)
        # print("\nGenerator Metrics data starting", lst_g['StartTime'])

        # make a sorted list of the times, and NumPy array of times in hours
        lst_g.pop('StartTime')
        meta_g = lst_g.pop('Metadata')
        # print("\nGenerator Metadata [Variable Index Units] for", len(lst_g[str(times[0])]), "objects")
        for key, val in meta_g.items():
            # print(key, val['index'], val['units'])
            if key == 'Pgen':
                PGEN_IDX = val['index']
                PGEN_UNITS = val['units']
            elif key == 'Qgen':
                QGEN_IDX = val['index']
                QGEN_UNITS = val['units']

        # create a NumPy array of all bus metrics
        data_g = np.empty(shape=(len(gen_keys), len(times), len(lst_g[str(times[0])][gen_keys[0]])), dtype=np.float)
        print("\nConstructed", data_g.shape, "NumPy array for Generators")
        j = 0
        for key in gen_keys:
            i = 0
            for t in times:
                ary = lst_g[str(t)][gen_keys[j]]
                data_g[j, i, :] = ary
                i = i + 1
            j = j + 1

        ## transform to a xarray dataset


        self.bus_metrics = xr.Dataset({'LMP_P': (['busNum', 'time'], data_b[:, :, LMP_P_IDX]),
                                     'PD': (['busNum', 'time'], data_b[:, :, PD_IDX]),
                                     'QD': (['busNum', 'time'], data_b[:, :, QD_IDX]),
                                     'VMAG': (['busNum', 'time'], data_b[:, :, VMAG_IDX]),
                                     },
                                    coords={'busNum': list(map(int, bus_keys)),
                                            'time': hrs})  # or hrs
        ## TODO add the bus-feeder and bus substation relationship to the attrs
        #bus_metrics.attrs["bus_substation_map"] = {7: 'SUBSTATION7'}
        self.bus_metrics.attrs["bus_info_dict"] = dict['fncsBuses']

        # processing the generation part metrics

        # TODO The emission rate info could be specified in a JSON file
        # generation emission rate table (lb/MWh)
        # Combination of the tables 11.3 and 11. 5 in the last years' report
        #                         CO2                SOX        NOX
        # coal                   205.57*10.09     0.1*10.09     0.06*10.09
        # natrual gas (CC)       117.08*7.67      0.001*7.67    0.0075*7.67
        # natrual gas (CT)       117.08*11.37     0.001*11.37   0.0075*11.37

        gen_emission_rate = {'coal': [205.57 * 10.09, 0.1 * 10.09, 0.06 * 10.09],
                             'gas_combinedcycle': [117.08 * 7.67, 0.001 * 7.67, 0.0075 * 7.67],
                             'gas_singlecycle': [117.08 * 11.37, 0.001 * 11.37, 0.0075 * 11.37]}
        #print('gen_emission_rate')

        gen_cost = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)
        gen_revenue = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)
        gen_emission_co2 = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)
        gen_emission_sox = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)
        gen_emission_nox = np.empty(shape=(len(gen_keys), len(times)), dtype=np.float)

        co2_emission_rate = np.empty(shape=(len(gen_keys)), dtype=np.float)
        sox_emission_rate = np.empty(shape=(len(gen_keys)), dtype=np.float)
        nox_emission_rate = np.empty(shape=(len(gen_keys)), dtype=np.float)


        j = 0
        for key in gen_keys:
            c0 = dict['generators'][key]['c0']
            c1 = dict['generators'][key]['c1']
            c2 = dict['generators'][key]['c2']
            co2_emission_rate[j] = 0
            sox_emission_rate[j] = 0
            nox_emission_rate[j] = 0

            if (dict['generators'][key]['genfuel']) == 'gas':
                if ((dict['generators'][key]['gentype'] == 'combinedcycle') | (
                    dict['generators'][key]['gentype'] == 'combinedcycle')):
                    co2_emission_rate[j] = \
                    gen_emission_rate[dict['generators'][key]['genfuel'] + "_" + dict['generators'][key]['gentype']][0]
                    sox_emission_rate[j] = \
                        gen_emission_rate[
                            dict['generators'][key]['genfuel'] + "_" + dict['generators'][key]['gentype']][1]
                    nox_emission_rate[j] = \
                        gen_emission_rate[
                            dict['generators'][key]['genfuel'] + "_" + dict['generators'][key]['gentype']][2]

            elif (dict['generators'][key]['genfuel']) == 'coal':
                co2_emission_rate[j] = gen_emission_rate[dict['generators'][key]['genfuel']][0]
                sox_emission_rate[j] = gen_emission_rate[dict['generators'][key]['genfuel']][1]
                nox_emission_rate[j] = gen_emission_rate[dict['generators'][key]['genfuel']][2]
            else:
                print('genfuel type', dict['generators'][key]['genfuel'], ' has zero emission or not supported yet!!')

            #print('gen_id, c0, c1, c2:', key, c0, c1, c2)
            i = 0
            for t in times:
                pgen = data_g[j, i, PGEN_IDX]
                gen_cost[j, i] = (c2 * pgen * pgen + c1 * pgen + c0)* time_interval_hours
                gen_revenue[j,i]=data_b[0, i, LMP_P_IDX]*1000.0* pgen * time_interval_hours  # LMP in $/kWh
                #print("gen:", key, co2_emission_rate[j], pgen, time_interval_hours)
                gen_emission_co2[j, i] = co2_emission_rate[j] * pgen * time_interval_hours
                gen_emission_sox[j, i] = sox_emission_rate[j] * pgen * time_interval_hours
                gen_emission_nox[j, i] = nox_emission_rate[j] * pgen * time_interval_hours
                # TODO
                # gen_payment[j,i]=pgen*LMP

                i = i + 1
            j = j + 1

        # print ( "\nco2 rate:",co2_emission_rate)
        # print ( "\nsox rate:",sox_emission_rate)

        self.gen_metrics = xr.Dataset({'PGEN': (['busNum', 'time'], data_g[:, :, PGEN_IDX]),
                                     'QGEN': (['busNum', 'time'], data_g[:, :, QGEN_IDX]),
                                     'COST': (['busNum', 'time'], gen_cost),
                                     'REVENUE': (['busNum', 'time'],gen_revenue),
                                     'EMISSION_CO2': (['busNum', 'time'], gen_emission_co2),
                                     'EMISSION_SOX': (['busNum', 'time'], gen_emission_sox),
                                     'EMISSION_NOX': (['busNum', 'time'], gen_emission_nox),
                                     },
                                    coords={'busNum': list(map(int, gen_keys)),
                                            'time': hrs})  # times or hrs

        ## add the generator dictionary to the attributes of the dataset
        self.gen_metrics.attrs["gen_info_dict"] = dict['generators']
        ##TODO add ancillary generator unit info

    def loadBusMetricsFromNetCMFFile(self, bus_metrics_netCMF):
        self.bus_metrics = xr.open_dataset(bus_metrics_netCMF)


    def loadGenMetricsFromNetCMFFile(self, gen_metrics_netCMF):
        self.gen_metrics = xr.open_dataset(gen_metrics_netCMF)

    def saveBusMetricsToNetCMFFile(self,new_bus_metrics_netCMF):

        self.bus_metrics.to_netcdf(new_bus_metrics_netCMF)
        print('Bus related base metrics are save to : ',new_bus_metrics_netCMF)

    def saveGenMetricsToNetCMFFile(self, new_gen_metrics_netCMF):
        self.gen_metrics.to_netcdf(new_gen_metrics_netCMF)
        print('Gen related base metrics are save to : ', new_gen_metrics_netCMF)

    def get_bus_metrics(self):
        return self.bus_metrics



    def get_bus_metrics_at_time(self, a_time_instance):
        return self.bus_metrics.sel(time = a_time_instance)

    def get_bus_metrics_for_period(self, start_time, end_time):
        return self.bus_metrics.where(np.logical_and(self.bus_metrics.time >= start_time, self.bus_metrics.time < end_time), drop = True)

    def get_bus_metrics_at_bus(self, bus_num):
        return self.bus_metrics.sel(busNum = bus_num)

    def get_allBus_LMP(self):
        return self.bus_metrics.LMP_P

    def get_bus_LMP(self, bus_num):
        return self.bus_metrics.sel(busNum = bus_num).LMP_P

    #
    #-------------------------------- The following are generator related metrics---------------------------------------
    #
    def get_gen_metrics(self):
        return self.gen_metrics
    def get_gen_metrics_for_period(self, start_time, end_time):
        return self.gen_metrics.where(np.logical_and(self.gen_metrics.time >= start_time, self.gen_metrics.time < end_time), drop = True)

    def get_eachGen_cost(self):
        return self.gen_metrics.COST.sum(dim = 'time')

    def get_allGen_cost(self):
        return self.gen_metrics.COST.sum()

    def get_eachGen_revenue(self):
        return self.gen_metrics.REVENUE.sum(dim = 'time')

    def get_allGen_revenue(self):
        return self.gen_metrics.REVENUE.sum()

    def get_eachGen_CO2_emissions(self):
        return self.gen_metrics.EMISSION_CO2.sum(dim='time')

    def get_allGen_CO2_emissions(self):
        return self.gen_metrics.EMISSION_CO2.sum().values

    def get_eachGen_SOx_emissions(self):
        return self.gen_metrics.EMISSION_SOX.sum().sum(dim='time')

    def get_allGen_SOx_emissions(self):
        return self.gen_metrics.EMISSION_SOX.sum().values

    def get_eachGen_NOx_emissions(self):
        return self.gen_metrics.EMISSION_NOX.sum().sum(dim='time')

    def get_allGen_NOx_emissions(self):
        return self.gen_metrics.EMISSION_NOX.sum().values

    def get_cost_at_gen(self, busNum):
        return self.gen_metrics.sel(busNum = busNum).GENCOST.sum(dim='time')