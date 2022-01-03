# class: DistributionMetricsProcessor.py
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;
import xarray as xr

class DistributionMetricsProcessor:
    casename = ""
    casepath =""
    subs_metrics = None
    meter_metrics = None
    house_metrics = None
    inverter_metrics = None
    auction_metrics = None
    sub_keys = None
    inv_keys = None
    hse_keys = None
    mtr_keys = None
    hrs = None
    time_interval_hours = 5/60; ##5 mins by default
    
    def __init__(self,case_name="",case_path=""):
        self.casename = case_name
        self.casepath = case_path
    
    def loadAllMetricsFromJSONFiles(self,case_name="",case_path=""):
        if(len(case_name)>0):
            self.casename = case_name
        if(len(case_path)>0):
            self.casepath = case_path
            
        # Start reading in and arranging the data
        lp = open (self.casepath+self.casename + "_glm_dict.json").read()
        dict = json.loads(lp)
        sub_keys = list(dict['feeders'].keys())
        sub_keys.sort()
        inv_keys = list(dict['inverters'].keys())
        inv_keys.sort()
        hse_keys = list(dict['houses'].keys())
        hse_keys.sort()
        mtr_keys = list(dict['billingmeters'].keys())
        mtr_keys.sort()
        xfMVA = dict['transformer_MVA']
        matBus = dict['matpower_id']
        print ("\n\nFile", self.casename, "has substation <", sub_keys[0], ">at Matpower bus<", matBus, ">with", xfMVA, "MVA transformer")
        print("\nFeeder Dictionary:")
        for key in sub_keys:
                row = dict['feeders'][key]
                print (key, "has", row['house_count'], "houses and", row['inverter_count'], "inverters")
        print("\nBilling Meter Dictionary:")
        for key in mtr_keys:
                row = dict['billingmeters'][key]
        #         print (key, "on phase", row['phases'], "of", row['feeder_id'], "with", row['children'])
        print("\nHouse Dictionary:")
        for key in hse_keys:
                row = dict['houses'][key]
#                 print (key, "on", row['billingmeter_id'], "has", row['sqft'], "sqft", row['cooling'], "cooling", row['heating'], "heating", row['wh_gallons'], "gal WH")
#                 # row['feeder_id'] is also available
        
        solar_id_array =[]
        battery_id_array =[]
        print("\nInverter Dictionary:")
        for key in inv_keys:
                row = dict['inverters'][key]
                print (key, "on", row['billingmeter_id'], "has", row['rated_W'], "W", row['resource'], "resource")
                if(row['resource'] =='solar'):
                    solar_id_array.append(key)
                elif(row['resource'] =='battery'):
                    battery_id_array.append(key)
                else:
                    print ('A new inverter source type not considered yet', row['resource'])
                # row['feeder_id'] is also available
        
        # In order to calculate the battery revenue, the auction json files are also read in and processed here
        lp = open (self.casepath + self.casename + "_agent_dict.json").read()
        dict_a = json.loads(lp)
        a_keys = list(dict_a['markets'].keys())
        a_keys.sort()
        c_keys = list(dict_a['controllers'].keys())
        c_keys.sort()
        print("\nMarket Dictionary:")
        print("ID Period Unit Init RefObj")
        for key in a_keys:
            row = dict_a['markets'][key]
            print (key, row['period'], row['unit'], row['init_price'], row['capacity_reference_object'])
        print("\nController Dictionary:")
        print("ID House Mode Ramp OffsetLimit PriceCap")
        for key in c_keys:
            row = dict_a['controllers'][key]
            print (key, row['houseName'], row['control_mode'], row['ramp'], row['offset_limit'], row['price_cap'])      
        
        # parse the substation metrics file first; there should just be one entity per time sample
        # each metrics file should have matching time points
        lp_s = open (self.casepath + "substation_" + self.casename + "_metrics.json").read()
        lst_s = json.loads(lp_s)
        print ("\nMetrics data starting", lst_s['StartTime'])
        
        # make a sorted list of the sample times in hours
        lst_s.pop('StartTime')
        meta_s = lst_s.pop('Metadata')
        times = list(map(int,list(lst_s.keys())))
        times.sort()
        print ("There are", len (times), "sample times at", times[1] - times[0], "second intervals")
        self.hrs = np.array(times, dtype=np.float)
        denom = 3600.0
        self.hrs /= denom
        
        time_key = str(times[0])
        
        self.time_interval_hours = (times[1] - times[0])/denom
        
        # parse the substation metadata for 2 things of specific interest
        print ("\nSubstation Metadata for", len(lst_s[time_key]), "objects")
        for key, val in meta_s.items():
            print (key, val['index'], val['units'])
            if key == 'real_power_avg':
                SUB_POWER_IDX = val['index']
                SUB_POWER_UNITS = val['units']
            elif key == 'real_power_losses_avg':
                SUB_LOSSES_IDX = val['index']
                SUB_LOSSES_UNITS = val['units']
        
        # create a NumPy array of all metrics for the substation
        data_s = np.empty(shape=(len(sub_keys), len(times), len(lst_s[time_key][sub_keys[0]])), dtype=np.float)
        print ("\nConstructed", data_s.shape, "NumPy array for Substations")
        j = 0
        for key in sub_keys:
                i = 0
                for t in times:
                        ary = lst_s[str(t)][sub_keys[j]]
                        data_s[j, i,:] = ary
                        i = i + 1
                j = j + 1
        
        # display some averages
        print ("Average power =", data_s[0,:,SUB_POWER_IDX].mean(), SUB_POWER_UNITS)
        print ("Average losses =", data_s[0,:,SUB_LOSSES_IDX].mean(), SUB_LOSSES_UNITS)
        
        # read the other JSON files; their times (hrs) should be the same
        lp_h = open (self.casepath + "house_" + self.casename + "_metrics.json").read()
        lst_h = json.loads(lp_h)
        lp_m = open (self.casepath + "billing_meter_" + self.casename + "_metrics.json").read()
        lst_m = json.loads(lp_m)
        lp_i = open (self.casepath + "inverter_" + self.casename + "_metrics.json").read()
        lst_i = json.loads(lp_i)
        lp_a = open (self.casepath + "auction_" + self.casename + "_metrics.json").read()
        lst_a = json.loads(lp_a)
        
        # houses
        lst_h.pop('StartTime')
        meta_h = lst_h.pop('Metadata')
        print("\nHouse Metadata for", len(lst_h[time_key]), "objects")
        for key, val in meta_h.items():
                print (key, val['index'], val['units'])
                if key == 'air_temperature_max':
                        HSE_AIR_MAX_IDX = val['index']
                        HSE_AIR_MAX_UNITS = val['units']
                elif key == 'air_temperature_min':
                        HSE_AIR_MIN_IDX = val['index']
                        HSE_AIR_MIN_UNITS = val['units']
                elif key == 'air_temperature_avg':
                        HSE_AIR_AVG_IDX = val['index']
                        HSE_AIR_AVG_UNITS = val['units']
                elif key == 'air_temperature_median':
                        HSE_AIR_MED_IDX = val['index']
                        HSE_AIR_MED_UNITS = val['units']
                elif key == 'air_temperature_deviation_cooling':
                        HSE_AIR_DEV_COOLING_IDX = val['index']
                        HSE_AIR_DEV_COOLING_UNITS = val['units']
                elif key == 'air_temperature_deviation_heating':
                        HSE_AIR_DEV_HEATING_IDX = val['index']
                        HSE_AIR_DEV_HEATING_UNITS = val['units']
                elif key == 'hvac_load_avg':
                        HSE_TOTAL_HVAC_LOAD_AVG_IDX = val['index']
                        HSE_TOTAL_HVAC_LOAD_AVG_UNITS = val['units']
                elif key == 'total_load_avg':
                        HSE_TOTAL_LOAD_AVG_IDX = val['index']
                        HSE_TOTAL_LOAD_AVG_UNITS = val['units']
        data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h[time_key][hse_keys[0]])), dtype=np.float)
        print ("\nConstructed", data_h.shape, "NumPy array for Houses")
        j = 0
        for key in hse_keys:
                i = 0
                for t in times:
                        ary = lst_h[str(t)][hse_keys[j]]
                        data_h[j, i,:] = ary
                        i = i + 1
                j = j + 1
        
        # Billing Meters - currently only Triplex Meters but eventually primary Meters as well
        lst_m.pop('StartTime')
        meta_m = lst_m.pop('Metadata')
        print("\nTriplex Meter Metadata for", len(lst_m[time_key]), "objects")
        for key, val in meta_m.items():
                print (key, val['index'], val['units'])
                if key == 'real_energy':
                        MTR_REAL_ENERGY_IDX = val['index']
                        MTR_REAL_ENERGY_UNITS = val['units']
                elif key == 'real_power_avg':
                        MTR_REAL_POWER_IDX = val['index']
                        MTR_REAL_POWER_UNITS = val['units']
                elif key == 'voltage_max':
                        MTR_VOLT_MAX_IDX = val['index']
                        MTR_VOLT_MAX_UNITS = val['units']
                elif key == 'voltage_min':
                        MTR_VOLT_MIN_IDX = val['index']
                        MTR_VOLT_MIN_UNITS = val['units']
                elif key == 'voltage12_max':
                        MTR_VOLT12_MAX_IDX = val['index']
                        MTR_VOLT12_MAX_UNITS = val['units']
                elif key == 'voltage12_min':
                        MTR_VOLT12_MIN_IDX = val['index']
                        MTR_VOLT12_MIN_UNITS = val['units']
                elif key == 'above_RangeA_Count':
                        MTR_VOLT_ABOVE_A_COUNT_IDX = val['index']
                        MTR_VOLT_ABOVE_A_COUNT_UNITS = val['units']
                elif key == 'above_RangeB_Count':
                        MTR_VOLT_ABOVE_B_COUNT_IDX = val['index']
                        MTR_VOLT_ABOVE_B_COUNT_UNITS = val['units']
                elif key == 'above_RangeA_Duration':
                        MTR_VOLT_ABOVE_A_DURATION_IDX = val['index']
                        MTR_VOLT_ABOVE_A_DURATION_UNITS = val['units']
                elif key == 'above_RangeB_Duration':
                        MTR_VOLT_ABOVE_B_DURATION_IDX = val['index']
                        MTR_VOLT_ABOVE_B_DURATION_UNITS = val['units']
                elif key == 'below_RangeA_Count':
                        MTR_VOLT_BELOW_A_COUNT_IDX = val['index']
                        MTR_VOLT_BELOW_A_COUNT_UNITS = val['units']
                elif key == 'below_RangeB_Count':
                        MTR_VOLT_BELOW_B_COUNT_IDX = val['index']
                        MTR_VOLT_BELOW_B_COUNT_UNITS = val['units']
                elif key == 'below_RangeA_Duration':
                        MTR_VOLT_BELOW_A_DURATION_IDX = val['index']
                        MTR_VOLT_BELOW_A_DURATION_UNITS = val['units']
                elif key == 'below_RangeB_Duration':
                        MTR_VOLT_BELOW_B_DURATION_IDX = val['index']
                        MTR_VOLT_BELOW_B_DURATION_UNITS = val['units']
                elif key == 'bill':
                        MTR_BILL_IDX = val['index']
                        MTR_BILL_UNITS = val['units']
        data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m[time_key][mtr_keys[0]])), dtype=np.float)
        print ("\nConstructed", data_m.shape, "NumPy array for Meters")
        j = 0
        for key in mtr_keys:
                i = 0
                for t in times:
                        ary = lst_m[str(t)][mtr_keys[j]]
                        data_m[j, i,:] = ary
                        i = i + 1
                j = j + 1
        
        # inverters
        lst_i.pop('StartTime')
        meta_i = lst_i.pop('Metadata')
        # Inverter object is not exsiting in some cases
        if lst_i[time_key] is not None:
            print("\nInverter Metadata for", len(lst_i[time_key]), "objects")
            for key, val in meta_i.items():
                    print (key, val['index'], val['units'])
                    if key == 'real_power_avg':
                            INV_P_AVG_IDX = val['index']
                            INV_P_AVG_UNITS = val['units']
                    elif key == 'reactive_power_avg':
                            INV_Q_AVG_IDX = val['index']
                            INV_Q_AVG_UNITS = val['units']             
            data_i = np.empty(shape=(len(inv_keys), len(times), len(lst_i[time_key][inv_keys[0]])), dtype=np.float)
            print ("\nConstructed", data_i.shape, "NumPy array for Inverters")
            j = 0
            for key in inv_keys:
                    i = 0
                    for t in times:
                            ary = lst_i[str(t)][inv_keys[j]]
                            data_i[j, i,:] = ary
                            i = i + 1
                    j = j + 1
                
        # Auctions
        lst_a.pop('StartTime')
        meta_a = lst_a.pop('Metadata')
        times = list(map(int,list(lst_a.keys())))
        times.sort()
        time_key = str(times[0])
        
        # parse the metadata for things of specific interest
        print ("\nAuction Metadata [Variable Index Units]")
        for key, val in meta_a.items():
            print (key, val['index'], val['units'])
            if key == 'clearing_price':
                CLEAR_IDX = val['index']
                CLEAR_UNITS = val['units']
        data_a = np.empty(shape=(len(a_keys), len(times), len(lst_a[str(times[0])][a_keys[0]])), dtype=np.float)
        print ("\nConstructed", data_a.shape, "NumPy array for Auctions")
        j = 0
        for key in a_keys:
                i = 0
                for t in times[0:-2]:
                        ary = lst_a[str(t)][a_keys[j]]
                        data_a[j, i,:] = ary
                        i = i + 1
                data_a[j, -1,:] = data_a[j, -2,:] # Since the auction agents do not have data for the last time step of the gld times, need to insert one here
                j = j + 1


        ## transform to a xarray dataset
        # billing_meter metrics
        self.meter_metrics = xr.Dataset({'Vmax': (['meterID', 'time'],  data_m[:, :, MTR_VOLT_MAX_IDX]),
                                         'Vmin':(['meterID', 'time'],  data_m[:, :, MTR_VOLT_MIN_IDX]),
                                         'VolatgeViolationCounts_aboveRangeA':(['meterID', 'time'], data_m[:, :, MTR_VOLT_ABOVE_A_COUNT_IDX]),
                                         'VolatgeViolationCounts_belowRangeA':(['meterID', 'time'], data_m[:, :, MTR_VOLT_BELOW_A_COUNT_IDX]),
                                         'VolatgeViolationCounts_aboveRangeB':(['meterID', 'time'], data_m[:, :, MTR_VOLT_ABOVE_B_COUNT_IDX]),
                                         'VolatgeViolationCounts_belowRangeB':(['meterID', 'time'], data_m[:, :, MTR_VOLT_BELOW_B_COUNT_IDX]),
                                         'Bill':(['meterID', 'time'], data_m[:, :, MTR_BILL_IDX]),
                                         'real_energy':(['meterID', 'time'], data_m[:, :, MTR_REAL_ENERGY_IDX]),
                                         'real_power_avg':(['meterID', 'time'], data_m[:, :, MTR_REAL_POWER_IDX]),
                                         },
                                        coords={'meterID':list(map(str,mtr_keys)),'time': self.hrs}, # or hrs
                                        attrs={"billingmeter_dict": dict['billingmeters']})

        # substation metrics
        self.subs_metrics = xr.Dataset({'Losses':(['substationID', 'time'], data_s[:, :, SUB_LOSSES_IDX]),
                                        'Real_power':(['substationID', 'time'],data_s[:,:,SUB_POWER_IDX]),
                                        }, 
                                       coords={'substationID':list(map(str,sub_keys)),'time': self.hrs}, # or hrs
                                       attrs={"Transformer_MVA": dict['transformer_MVA'],
                                                "Transmission_Bus" : dict['matpower_id'],
                                                "Feeder Dictionary": dict['feeders']})
        
        # house metrics 
        self.house_metrics = xr.Dataset({'Temperature':(['houseID', 'time'], data_h[:, :, HSE_AIR_AVG_IDX]),
                                         'Temperature_deviation':(['houseID', 'time'], data_h[:, :, HSE_AIR_DEV_COOLING_IDX]),
                                         'Total_HVACloads': (['houseID', 'time'], data_h[:, :, HSE_TOTAL_HVAC_LOAD_AVG_IDX]),
                                         'Total_load': (['houseID', 'time'], data_h[:, :, HSE_TOTAL_LOAD_AVG_IDX]),
                                        },
                                        coords={'houseID':list(map(str,hse_keys)),'time': self.hrs}, # or hrs
                                        attrs= {'houses_dict': dict['houses']})
        
        # Inverter metrics 
        times = list(map(int,list(lst_i.keys())))
        times.sort()
        time_key = str(times[0])
        if lst_i[time_key] is not None:
            self.inverter_metrics = xr.Dataset({'Real_power_avg':(['inverterID', 'time'], data_i[:,:,INV_P_AVG_IDX]),
                                                'Reactive_power_avg':(['inverterID', 'time'], data_i[:,:,INV_Q_AVG_IDX]),
                                                },
                                                coords={'inverterID':list(map(str,inv_keys)),
                                                        'time': self.hrs}, # or hrs
                                                attrs={'solar_inverter_ids': solar_id_array,'battery_inverter_ids': battery_id_array})
        
        # Auction metrics 
        self.auction_metrics = xr.Dataset({'Clearing_price':(['marketID', 'time'], data_a[:,:,CLEAR_IDX])},
                                            coords={'marketID':list(map(str,a_keys)),'time': self.hrs}, # or hrs
                                            attrs = {'market_dict': dict_a['markets']})        
        
        self.sub_keys = sub_keys
        self.inv_keys = inv_keys
        self.hse_keys = hse_keys
        self.mtr_keys = mtr_keys
    
    def loadSubstationMetricsFromNetCMFFile(self, bus_metrics_netCMF):
        self.subs_metrics = xr.open_dataset(bus_metrics_netCMF)

    def loadHouseMetricsFromNetCMFFile(self, house_metrics_netCMF):
        self.house_metrics = xr.open_dataset(house_metrics_netCMF)
        
    def loadMeterMetricsFromNetCMFFile(self, meter_metrics_netCMF):
        self.meter_metrics = xr.open_dataset(meter_metrics_netCMF)
        
    def loadInverterMetricsFromNetCMFFile(self, inverter_metrics_netCMF):
        self.inverter_metrics = xr.open_dataset(inverter_metrics_netCMF)

    def SaveSubstationMetricsToNetCMFFile(self,new_subs_metrics_netCMF):
        self.subs_metrics.to_netcdf(new_subs_metrics_netCMF)
        print('Substation related base metrics are save to : ',new_subs_metrics_netCMF)

    def SaveHouseMetricsToNetCMFFile(self, new_house_metrics_netCMF):
        self.house_metrics.to_netcdf(new_house_metrics_netCMF)
        print('House related base metrics are save to : ', new_house_metrics_netCMF)
        
    def SaveMeterMetricsToNetCMFFile(self,new_meter_metrics_netCMF):
        self.meter_metrics.to_netcdf(new_meter_metrics_netCMF)
        print('Meter related base metrics are save to : ',new_meter_metrics_netCMF)

    def SaveInverterMetricsToNetCMFFile(self, new_inverter_metrics_netCMF):
        self.inverter_metrics.to_netcdf(new_inverter_metrics_netCMF)
        print('Inverter related base metrics are save to : ', new_inverter_metrics_netCMF)


    ##----- substation metrics--------------------------------------------
    def get_subs_metrics(self):
        return self.subs_metrics

    # Input could be one ID string or an array of ID string
    def get_subs_metrics_byID(self,sub_id):
        return self.subs_metrics.sel(substationID = sub_id)

    def get_subs_metrics_at_time(self, a_time_instance):
        return self.subs_metrics.sel(time = a_time_instance)

    def get_subs_metrics_for_period(self, start_time, end_time):
        return self.subs_metrics.where(np.logical_and(self.subs_metrics.time >= start_time, self.subs_metrics.time < end_time), drop = True)

    def get_subs_realPower(self):
        return self.subs_metrics.Real_power
    
    def get_subs_electricity(self):
        # substation power unit is W
        return self.subs_metrics.Real_power/1000 * self.time_interval_hours

    ## ------house mertrics ---------------------------------------------
    def get_house_metrics(self):
        return self.house_metrics

    # Input could be one ID string or an array of ID string
    def get_house_metrics_byID(self, house_id):
        return self.house_metrics.sel(houseID = house_id)

    def get_house_metrics_at_time(self, a_time_instance):
        return self.house_metrics.sel(time=a_time_instance)

    def get_house_metrics_for_period(self, start_time, end_time):
        return self.house_metrics.where(np.logical_and(self.house_metrics.time >= start_time, self.house_metrics.time < end_time), drop = True)

    # get the house temperature deviation (dev= current temp - setpoint), return a dataSet
    def get_house_temp_deviation(self, house_id):
        if house_id == "":
            return self.house_metrics.sel(houseID = self.hse_keys[0]).Temperature_deviation
        else:
            return self.house_metrics.sel(houseID = house_id).Temperature_deviation

    # get the house HVAC energy consumption, return a dataSet
    def get_house_total_HVAC_electricity(self):
        return (self.house_metrics.Total_HVACloads * self.time_interval_hours).sum(dim = 'time')
    
    # get the house energy consumption, return a dataSet
    def get_house_total_electricity(self):
        return (self.house_metrics.Total_load * self.time_interval_hours).sum(dim = 'time')
    
    # get the house temperature, return a dataSet
    def get_house_temperature(self, house_id):
        if house_id == "":
            return self.house_metrics.sel(houseID = self.hse_keys[0]).Temperature
        else:
            return self.house_metrics.sel(houseID = house_id).Temperature

    # -------metering metrics-------------------------------------------
    def get_metering_metrics(self):
        return self.meter_metrics

    # Input could be one ID string or an array of ID string
    def get_metering_metrics_byID(self, meter_id):
        return self.meter_metrics.sel(meterID = meter_id)

    def get_metering_metrics_for_period(self, start_time, end_time):
        return self.meter_metrics.where(np.logical_and(self.meter_metrics.time >= start_time, self.meter_metrics.time < end_time), drop = True)

    # # sum of counts of voltage violation above Range A over the whole simulation period
    # print("\n\n Sum of voltage violation counts: ",mp_meter_metrics.VolatgeViolationCounts_aboveRangeA.sum(), "\n")
    def get_volt_violation_counts(self):
        count = self.meter_metrics.VolatgeViolationCounts_aboveRangeA.sum().values +\
                self.meter_metrics.VolatgeViolationCounts_belowRangeA.sum().values +\
                self.meter_metrics.VolatgeViolationCounts_aboveRangeB.sum().values + \
                self.meter_metrics.VolatgeViolationCounts_belowRangeB.sum().values
        return count

    def get_volt_violation_aboveRangeA_counts(self):
        count = self.meter_metrics.VolatgeViolationCounts_aboveRangeA.sum().values
        return count

    def get_volt_violation_belowRangeA_counts(self):
        count = self.meter_metrics.VolatgeViolationCounts_belowRangeA.sum().values

        return count

    def get_volt_violation_aboveRangeB_counts(self):
        count = self.meter_metrics.VolatgeViolationCounts_aboveRangeB.sum().values
        return count

    def get_volt_violation_belowRangeB_counts(self):
        count =  self.meter_metrics.VolatgeViolationCounts_belowRangeB.sum().values
        return count


    # bill of each house
    def get_eachhouse_bill(self):
        return self.meter_metrics.Bill.sum(dim='time')

    def get_house_avg_bill(self):
        return self.meter_metrics.Bill.sum(dim='time').mean().values

    # # sum of bill over the whole simulation period
    def get_allhouses_total_bill(self):
        return self.meter_metrics.Bill.sum().values

    ##-------inverter metrics --------------------------------------------

    def get_inverter_metrics(self):
        return self.inverter_metrics

    # Input could be one ID string or an array of ID string
    def get_inverter_metrics_byID(self, meter_id):
        return self.meter_metrics.sel(meterID=meter_id)

    def get_inverter_metrics_for_period(self, start_time, end_time):
        return self.inverter_metrics.where(
            np.logical_and(self.inverter_metrics.time >= start_time, self.inverter_metrics.time < end_time), drop=True)

    def get_PV_energy_output(self):
        PVOutput = self.inverter_metrics.sel_points(inverterID= self.inverter_metrics.attrs['solar_inverter_ids']).Real_power_avg * self.time_interval_hours/1000 # inverter unit is W
        print('\n\nPV energy :', PVOutput)
        return PVOutput
    
    # Calculating the battery revenue
    # Battery charging or discharging energy during each market clearing interval
    # discharging is positive while charging is negative
    def get_battery_energy_output(self):
        batteryOutput = self.inverter_metrics.sel_points(inverterID= self.inverter_metrics.attrs['battery_inverter_ids']).Real_power_avg * self.time_interval_hours/1000 # inverter unit is W
        print('\n\nbattery energy :', batteryOutput)
        return batteryOutput

    # print('\n\n solar inverter metrics: ', mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['solar_inverter_ids']).data_vars)
    #
    # print('\n\n battery inverter metrics: ', mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).data_vars)
    #
    #
    # # total solar generated energy
    # print('\n\n total solar energy [wh]: ', (mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['solar_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)
    #
    # # total battery output (power > 0) energy
    # print('\n\n total battery generated energy [wh]: ', (mp_inverter_metrics.where(mp_inverter_metrics.real_power_avg > 0).sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)
    #
    # # total batter charging (avg power < 0) energy
    # print('\n\n total battery charging energy [wh]: ', (mp_inverter_metrics.where(mp_inverter_metrics.real_power_avg < 0).sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)
    #
    # # total battery net energy
    # print('\n\n battery net energy [wh]: ', (mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)
    #
    #

    ##-----------Auction metrics --------------------
    def get_auction_metrics(self):
        return self.auction_metrics

    def get_auction_metrics_byMarketID(self,market_id):
        return self.auction_metrics.sel(marketID =market_id )


    # TODO for the next stage, we need a mapping between marketID and the feeder or battery
    def get_auction_clearing_price(self,market_id=""):
        if (market_id==""):
            return self.auction_metrics.Clearing_price
        else:
            return self.auction_metrics.sel(marketID=market_id).Clearing_price


    def get_PV_revenue_dataSet(self,feederID, start_time, end_time):
        PVOutput = self.inverter_metrics.where((self.inverter_metrics.time >= start_time) & (self.inverter_metrics.time <= end_time), drop = True).sel_points(inverterID= self.inverter_metrics.attrs['solar_inverter_ids']).Real_power_avg.values * self.time_interval_hours/1000 # inverter unit is W
        auctionPrice = self.auction_metrics.Clearing_price.where((self.auction_metrics.time >= start_time) & (self.auction_metrics.time <= end_time), drop = True).values
        PVRevenue = PVOutput * auctionPrice
        print('\n\nPV revenue [usd]:', PVRevenue)
        return PVRevenue


    def get_each_PV_revenue(self,feederID, start_time, end_time):
        return self.get_PV_revenue_dataSet("", start_time, end_time).sum(axis=1) # Axis 1 is the time axis


    def get_PV_total_revenue(self,feederID, start_time, end_time):
        return self.get_PV_revenue_dataSet("", start_time, end_time).sum(axis=1).sum()
    
    
    def get_battery_revenue_dataSet(self,feederID, start_time, end_time):
        batteryOutput = self.inverter_metrics.where((self.inverter_metrics.time >= start_time) & (self.inverter_metrics.time <= end_time), drop = True).sel_points(inverterID= self.inverter_metrics.attrs['battery_inverter_ids']).Real_power_avg.values * self.time_interval_hours/1000
        auctionPrice = self.auction_metrics.where((self.auction_metrics.time >= start_time) & (self.auction_metrics.time <= end_time), drop = True).Clearing_price.values
        batteryRevenue = batteryOutput * auctionPrice
#         batteryRevenue[batteryRevenue < 0] = 0.0 # Remove the charging cases
        print('\n\nbattery revenue [usd]:', batteryRevenue)
        return batteryRevenue


    def get_each_battery_revenue(self,feederID, start_time, end_time):
        return self.get_battery_revenue_dataSet("", start_time, end_time).sum(axis=1) # Axis 1 is the time axis


    def get_battery_total_revenue(self,feederID, start_time, end_time):
        return self.get_battery_revenue_dataSet("", start_time, end_time).sum(axis=1).sum()




# print("\n\nmeter metrics",mp_meter_metrics)
# #print(mp_meter_metrics.time)
# 
# # output the metrics for time at 300 sec
# print('\n\n metrics for time at 300 sec')
# print(mp_meter_metrics.sel(time = 300).data_vars)
# 
# print('\n\n metrics for time at 300, 900, 2400  sec')
# print(mp_meter_metrics.sel(time = [300,900,2400]).data_vars)
# 
# print('\n\n metrics for time Between 1 and 3000  sec')
# print(mp_meter_metrics.where(np.logical_and(mp_meter_metrics.time > 1,mp_meter_metrics.time < 3000)).data_vars)
# 
# print('\n\n metrics for time less than 1000 sec')
# print(mp_meter_metrics.where((mp_meter_metrics.time < 1000) , drop= True ).data_vars)
# 
# # output the metrics of one meter
# print('\n\n metrics for meter 1, time 300')
# print(mp_meter_metrics.sel(meterID = mtr_keys[0], time = 300).data_vars)
# 
# # print the voltage min and max over the whole simulation period
# print("\n\n Voltage maximum value:",mp_meter_metrics.Vmax.max(),"\n Voltage minimum value:",mp_meter_metrics.Vmin.min())
# 
# # sum of counts of voltage violation above Range A over the whole simulation period
# print("\n\n Sum of voltage violation counts: ",mp_meter_metrics.VolatgeViolationCounts_aboveRangeA.sum(), "\n")
# 
# # sum of bill over the whole simulation period
# print("\n\n Sum of bill: ",mp_meter_metrics.bill.sum(), "\n")
# 
# # ============================ substation metrics =============================================================
# mp_subs_metrics = xr.Dataset({
#                          'Losses':(['substationID', 'time'], data_s[:, :, SUB_LOSSES_IDX]),
#                          'Real_power':(['substationID', 'time'],data_s[:,:,SUB_POWER_IDX]),
#                          },
#                 coords={'substationID':list(map(str,sub_keys)),
#                         'time': times},# or hrs
#                  attrs={"Transformer_MVA": dict['transformer_MVA'],
#                         "Transmission_Bus" : dict['matpower_id'],
#                         "Feeder Dictionary": dict['feeders']})
# 
# 
# 
# 
# print("\n\nsubstation metrics: ",mp_subs_metrics)
# # print(mp_subs_metrics.time)
# 
# # output the metrics for time at 300 sec
# print('\n\n metrics for time at 300 sec')
# print(mp_subs_metrics.sel(time = 300).data_vars)
# 
# # ============================ house metrics =============================================================
# mp_house_metrics = xr.Dataset({
#                          'temperature':(['houseID', 'time'], data_h[:, :, HSE_AIR_AVG_IDX]),
#                         'temperature_deviation':(['houseID', 'time'], data_h[:, :, HSE_AIR_DEV_COOLING_IDX]),              
#                          },
#                 coords={'houseID':list(map(str,hse_keys)),
#                         'time': times}, # or hrs
#                 attrs= {'houses_dict': dict['houses']})
# 
# print("\n\n house metrics: ",mp_house_metrics)
# #print(mp_house_metrics.time)
# 
# # output the metrics for time at 300 sec
# print('\n\n house metrics for time at 300 sec')
# print(mp_house_metrics.sel(time = 300).data_vars)
# 
# 
# # ============================ PV and solar metrics =============================================================
# 
# # dict['inverters'][key]
# mp_inverter_metrics = xr.Dataset({
#                          'real_power_avg':(['inverterID', 'time'], data_i[:,:,INV_P_AVG_IDX]),
#                          'reactive_power_avg':(['inverterID', 'time'], data_i[:,:,INV_Q_AVG_IDX]),
#                          },
#                 coords={'inverterID':list(map(str,inv_keys)),
#                         'time': times}, # or hrs
#                 attrs={'solar_inverter_ids': solar_id_array,'battery_inverter_ids': battery_id_array }
#                 )
# 
# print('\n\ninverter metrics: ', mp_inverter_metrics)
# 
# # filter diffferent source types by where (inverterID in solar_dict)
# print('\nsolar inverter ids: ', mp_inverter_metrics.attrs['solar_inverter_ids'])
# print('\n\n solar inverter metrics: ', mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['solar_inverter_ids']).data_vars)
# 
# print('\n\n battery inverter metrics: ', mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).data_vars)
# 
# 
# # total solar generated energy
# print('\n\n total solar energy [wh]: ', (mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['solar_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)
# 
# # total battery output (power > 0) energy
# print('\n\n total battery generated energy [wh]: ', (mp_inverter_metrics.where(mp_inverter_metrics.real_power_avg > 0).sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)
# 
# # total batter charging (avg power < 0) energy
# print('\n\n total battery charging energy [wh]: ', (mp_inverter_metrics.where(mp_inverter_metrics.real_power_avg < 0).sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)
# 
# # total battery net energy
# print('\n\n battery net energy [wh]: ', (mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg*time_interval_hours).sum(dim = 'time').values)
# 
# 
# #TODO Yingying please help add the clearing prices to the inverters, then we can calculate the revenues of PV and battery
# 
# # battery revunue ( income from generated energy minus payment paid to charged energy
# # Since currently battery is not used as controlled agent, for battery revunue is calculated based on battery kW output and market clearing price
# # Auction data - the clearing price is used here for battery revenue calculation
# # Open auction dict files
# lp = open (casepath + casename + "_agent_dict.json").read()
# dict_a = json.loads(lp)
# a_keys = list(dict_a['markets'].keys())
# a_keys.sort()
# c_keys = list(dict_a['controllers'].keys())
# c_keys.sort()
# print("\nMarket Dictionary:")
# print("ID Period Unit Init RefObj")
# for key in a_keys:
#     row = dict_a['markets'][key]
#     print (key, row['period'], row['unit'], row['init_price'], row['capacity_reference_object'])
# print("\nController Dictionary:")
# print("ID House Mode Base RampHi RampLo RangeHi RangeLo")
# for key in c_keys:
#     row = dict_a['controllers'][key]
#     print (key, row['houseName'], row['control_mode'], row['base_setpoint'], row['ramp_high'], row['ramp_low'], row['range_high'], row['range_low'])
# 
# # Read the auction metrics file
# lp_a = open (casepath + "auction_" + casename + "_metrics.json").read()
# lst_a = json.loads(lp_a)
# print ("\nAuction Metrics data starting", lst_a['StartTime'])
# lst_a.pop('StartTime')
# meta_a = lst_a.pop('Metadata')
# # parse the metadata for things of specific interest
# print ("\nAuction Metadata [Variable Index Units]")
# for key, val in meta_a.items():
#     print (key, val['index'], val['units'])
#     if key == 'clearing_price':
#         CLEAR_IDX = val['index']
#         CLEAR_UNITS = val['units']
# 
# # create a NumPy array of all auction metrics
# data_a = np.empty(shape=(len(a_keys), len(times), len(lst_a[str(times[0])][a_keys[0]])), dtype=np.float)
# print ("\nConstructed", data_a.shape, "NumPy array for Auctions")
# j = 0
# for key in a_keys:
#         i = 0
#         for t in times[0:-2]:
#                 ary = lst_a[str(t)][a_keys[j]]
#                 data_a[j, i,:] = ary
#                 i = i + 1
#         data_a[j, -1,:] = data_a[j, -2,:] # Since the auction agents do not have data for the last time step of the gld times, need to insert one here
#         j = j + 1
#         
# # Creating auction metrics in x_array dataset      
# mp_auction_metrics = xr.Dataset({
#                          'clearing_price':(['marketID', 'time'], data_a[:,:,CLEAR_IDX]),
#                          },
#                 coords={'marketID':list(map(str,a_keys)),
#                         'time': times}, # or hrs
#                 )
# 
# # Calculating the battery revenue
# batteryOutput = mp_inverter_metrics.sel_points(inverterID = mp_inverter_metrics.attrs['battery_inverter_ids']).real_power_avg
# auctionPrice = mp_auction_metrics.clearing_price.values
# BatteryProfit = batteryOutput * auctionPrice
# print('\n\n Each battery revenue: ', BatteryProfit.sum(dim = 'time'))
# print('\n\n Total battery revenue: ', BatteryProfit.sum(dim = 'time').sum())

