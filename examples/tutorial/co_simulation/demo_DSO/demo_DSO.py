import math
import json
import numpy as np
import helics as h
import pandas as pd
from datetime import datetime, timedelta

def create_broker(simulators):
    initstring = "--federates=" + str(simulators) + " --name=mainbroker"
    broker = h.helicsCreateBroker("zmq", "", initstring)
    isconnected = h.helicsBrokerIsConnected(broker)
    if isconnected == 1:
        pass

    return broker

def get_storage_specs(wrapper_config):
    specs_path = '../src/storage_config.json'
    with open(specs_path, 'r') as f:
        specs = json.loads(f.read())
    return specs

def get_load_profiles(wrapper_config):

    load_profile_path = wrapper_config['matpower_most_data']['datapath'] + wrapper_config['matpower_most_data']['load_profile_info']['filename']
    input_resolution = wrapper_config['matpower_most_data']['load_profile_info']['resolution']
    input_data_reference_time =  datetime.strptime(wrapper_config['matpower_most_data']['load_profile_info']['starting_time'], '%Y-%m-%d %H:%M:%S')
    start_data_point = int((start_date - input_data_reference_time).total_seconds() / input_resolution)
    end_data_point   = int((end_date - input_data_reference_time).total_seconds() / input_resolution)
    load_profile_data = pd.read_csv(load_profile_path, skiprows = start_data_point+1, nrows=(end_data_point-start_data_point)+1, header=None)
    new_col_idx = load_profile_data.shape[1]
    load_profile_data[new_col_idx] = pd.date_range(start=start_date, end = end_date, freq='5min')
    load_profile_data.set_index(new_col_idx, inplace=True)
    sample_interval = str(wrapper_config['physics_powerflow']['interval'])+'s'
    load_profile_data_pf_interval = load_profile_data.resample(sample_interval).interpolate()

    return load_profile_data_pf_interval


def create_helics_configuration(helics_config, filename):
    Transmission_Sim_name = helics_config['name']
    helics_config['coreInit'] = '--federates=1'
    helics_config['coreName'] = 'DSO Federate'
    helics_config['name'] = 'DSOSim'
    helics_config['publications'] = [];
    helics_config['subscriptions'] = [];

    if wrapper_config['include_physics_powerflow']:
        
        for bus in wrapper_config['cosimulation_bus']:
            helics_config['publications'].append({'global': bool(True),
                                               'key': str(helics_config['name']+ '.pcc.' + str(bus) + '.pq'),
                                               'type': str('complex')
                                               })
            helics_config['subscriptions'].append({'required': bool(False),
                                               'key': str(Transmission_Sim_name + '.pcc.' + str(bus) + '.pnv'),
                                               'type': str('complex')
                                               })
                                               
    if wrapper_config['include_real_time_market']:   
        for bus in wrapper_config['cosimulation_bus']:                                        
            helics_config['publications'].append({'global': bool(True),
                                               'key': str(helics_config['name']+ '.pcc.' + str(bus) + '.rt_energy.bid'),
                                               'type': str('JSON')
                                               })
    
            helics_config['subscriptions'].append({'required': bool(False),
                                               'key': str(Transmission_Sim_name + '.pcc.' + str(bus) + '.rt_energy.cleared'),
                                               'type': str('JSON')
                                               })
    if wrapper_config['include_day_ahead_market']:   
        for bus in wrapper_config['cosimulation_bus']:                                        
            helics_config['publications'].append({'global': bool(True),
                                               'key': str(helics_config['name']+ '.pcc.' + str(bus) + '.da_energy.bid'),
                                               'type': str('JSON')
                                               })
    
            helics_config['subscriptions'].append({'required': bool(False),
                                               'key': str(Transmission_Sim_name + '.pcc.' + str(bus) + '.da_energy.cleared'),
                                               'type': str('JSON')
                                               })
    if wrapper_config['include_storage']:
        helics_config['publications'].append({'global': bool(True),
                                           'key': str(helics_config['name']+ '.pcc.' + 'storage'),
                                           'type': str('JSON')
                                           })


    out_file = open(filename, "w")
    json.dump(helics_config, out_file, indent=4)
    out_file.close()

    return

if __name__ == "__main__":
    
    
    
    json_path = '../TD_cosim_config.json'
    with open(json_path, 'r') as f:
        wrapper_config = json.loads(f.read())

    case_path = wrapper_config['matpower_most_data']['datapath'] + wrapper_config['matpower_most_data']['case_name']
    with open(case_path, 'r') as f:
        case = json.loads(f.read())



    start_date = datetime.strptime(wrapper_config['start_time'], '%Y-%m-%d %H:%M:%S')
    end_date   = datetime.strptime(wrapper_config['end_time'], '%Y-%m-%d %H:%M:%S')
    duration   = (end_date - start_date).total_seconds()
    include_helics = wrapper_config['include_helics']

    ##### Getting Load Profiles from input Matpower data #####
    load_profiles = get_load_profiles(wrapper_config)


    ##### Setting up HELICS Configuration #####
    print('DSO: HELICS Version {}'.format(h.helicsGetVersion()))
    helics_config_filename = 'demo_DSO.json'
    if include_helics:
        create_helics_configuration(wrapper_config['helics_config'], helics_config_filename)

        ##### Starting HELICS Broker #####
        # h.helicsBrokerDisconnect(broker)
        broker = create_broker(2)


        ##### Registering DSO Federate #####
        fed = h.helicsCreateCombinationFederateFromConfig(helics_config_filename)
        print('DSO: Registering {} Federate'.format(h.helicsFederateGetName(fed)))

        pubkeys_count = h.helicsFederateGetPublicationCount(fed)
        pub_keys = []
        for pub_idx in range(pubkeys_count):
            pub_object = h.helicsFederateGetPublicationByIndex(fed, pub_idx)
            pub_keys.append(h.helicsPublicationGetName(pub_object))
        print('DSO: {} Federate has {} Publications'.format(h.helicsFederateGetName(fed), pubkeys_count))
    
    
        subkeys_count = h.helicsFederateGetInputCount(fed)
        sub_keys = []
        for sub_idx in range(subkeys_count):
            sub_object = h.helicsFederateGetInputByIndex(fed, sub_idx)
            sub_keys.append(h.helicsSubscriptionGetTarget(sub_object))
        print('DSO: {} Federate has {} Inputs'.format(h.helicsFederateGetName(fed), subkeys_count))
    
        # print(pub_keys)
        # print(sub_keys)
    
        #####  Entering Execution for DSO Federate #####
        status = h.helicsFederateEnterExecutingMode(fed)
        print('DSO: Federate {} Entering execution'.format(h.helicsFederateGetName(fed)))
        
        if wrapper_config['include_storage']:
            temp_specs = get_storage_specs(wrapper_config)
            # ecap = [100,100,100]
            # pcap = [50,50,25]
            # storage_bus = [2,2,1]
            # eff = [1,1,1]
            # ecap_out = list(ecap)
            # pcap_out = list(pcap)
            # bus_out = list(storage_bus)
            # eff_out = list(eff)
            # storage_specs = dict()
            # storage_specs['ecap'] = ecap_out
            # storage_specs['pcap'] = pcap_out
            # storage_specs['bus'] = bus_out
            # storage_specs['eff'] = eff_out
            specs_raw = json.dumps(temp_specs)
            pub_key = [key for key in pub_keys  if ('pcc.' + 'storage') in key ]
            pub_object = h.helicsFederateGetPublication(fed, pub_key[0])
            status = h.helicsPublicationPublishString(pub_object, specs_raw)
            print('DSO: Published Storage Specifications')
            

    buffer = 0  ###### Buffer to sending out data before the Operational Cycle  ######
    tnext_physics_powerflow = wrapper_config['physics_powerflow']['interval']-buffer
    tnext_real_time_market  = wrapper_config['real_time_market']['interval']-buffer
    #tnext_day_ahead_market  = wrapper_config['day_ahead_market']['interval']-buffer
    #tnext_physics_powerflow = 0
    #tnext_real_time_market  = 0
    tnext_day_ahead_market  = 0

    # duration = 300
    time_granted = -1
    
    flexibility = .25
    flexibility_profile = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
    flexibility_profile = list(map(lambda x: x * flexibility, (i for i in flexibility_profile))) ##Multiply entire flex_profile by flex
    blocks = 10
    P_range = np.array([25, 60]) 
    
    while time_granted < duration:
        
        #next_helics_time = min([tnext_physics_powerflow, tnext_real_time_market, tnext_day_ahead_market]);
        next_helics_time = duration
        if wrapper_config['include_day_ahead_market']:
            next_helics_time = min([tnext_day_ahead_market,next_helics_time])
        if wrapper_config['include_real_time_market']:
            next_helics_time = min([tnext_real_time_market,next_helics_time])
        if wrapper_config['include_physics_powerflow']:
            next_helics_time = min([tnext_physics_powerflow,next_helics_time])
        
        if include_helics:
            #next_helics_time = min([tnext_physics_powerflow, tnext_real_time_market, tnext_day_ahead_market]);
            time_granted = h.helicsFederateRequestTime(fed, next_helics_time)
        else:
            time_granted = next_helics_time
            
        print('DSO: Requested {}s and got Granted {}s'.format(next_helics_time, time_granted))
        current_time = start_date + timedelta(seconds=time_granted)
        print('DSO: Current Time is {}'.format(current_time))

        ######## Day Ahead Market Intervals ########
        if time_granted >= tnext_day_ahead_market and wrapper_config['include_day_ahead_market'] and time_granted < duration:
            constant_load = np.zeros(len(flexibility_profile))
            flex_load = np.zeros(len(flexibility_profile))
            Q_values = np.zeros([len(flexibility_profile),blocks])
            Q_val_out = [[0]*blocks]*len(flexibility_profile)
            #Q_val_out = {}
            P_values = np.zeros([len(flexibility_profile),blocks])
            P_val_out = [[0]*blocks]*len(flexibility_profile)
            #P_val_out = {}
            DAM_start = current_time + timedelta(seconds=buffer)
            #DAM_start_idx = load_profiles.index[load_profiles.index == DAM_start]
            DAM_end = DAM_start + timedelta(seconds = wrapper_config['day_ahead_market']['interval'] - 60)
            #DAM_end_idx = load_profiles.index[load_profiles.index == DAM_end]
            DAM_profile_full = load_profiles.loc[DAM_start:DAM_end]
            DAM_profile = DAM_profile_full.resample('3600S').sum() / 60
            for cosim_bus in wrapper_config['cosimulation_bus']:
                load_data = DAM_profile.to_numpy()
                MW_MVAR_factor = case['bus'][cosim_bus-1][2] / case['bus'][cosim_bus-1][3]
                for t in range(len(flexibility_profile)):
                    constant_load[t] = load_data[t][cosim_bus] * (1-flexibility_profile[t])
                    flex_load[t] = load_data[t][cosim_bus] * flexibility_profile[t]
                    Q_values[t] = np.linspace(0,flex_load[t],blocks)
                    Q_val_out[t] = list(Q_values[t])
                    P_values[t] = np.linspace(max(P_range), min(P_range),blocks)
                    P_val_out[t] = list(P_values[t])
                    
                bid =  dict()
                bid['constant_MW'] = list(constant_load)
                bid['constant_MVAR'] = list(constant_load/MW_MVAR_factor)
                bid['P_bid'] = P_val_out
                bid['Q_bid'] = Q_val_out
                    
                    
                bid_raw = json.dumps(bid)
                    
                #####  Publishing current loads for Co-SIM Bus the ISO Simulator #####
                if include_helics:
                    pub_key = [key for key in pub_keys  if ('pcc.' + str(cosim_bus) + '.da_energy.bid') in key ]
                    pub_object = h.helicsFederateGetPublication(fed, pub_key[0])
                    status = h.helicsPublicationPublishString(pub_object, bid_raw)
                    print('DSO: Published Bids for Bus {}'.format(cosim_bus))
                
            tnext_day_ahead_market  = tnext_day_ahead_market + wrapper_config['day_ahead_market']['interval']-buffer

        ######## Real time Market Intervals ########
        if time_granted >= tnext_real_time_market and wrapper_config['include_real_time_market'] and time_granted < duration:
            
            profile_time = current_time + timedelta(seconds=buffer)
            data_idx = load_profiles.index[load_profiles.index == profile_time]
            current_load_profile = load_profiles.loc[data_idx]
            for cosim_bus in wrapper_config['cosimulation_bus']:
                base_kW = case['bus'][cosim_bus-1][2]
                base_kVAR = case['bus'][cosim_bus - 1][3]
                current_kW = current_load_profile[cosim_bus].values[0]
                constant_load = current_kW*(1-flexibility)
                flex_load = current_kW*(flexibility)
                Q_values = np.linspace(0, flex_load, blocks)
                P_values = np.linspace(max(P_range), min(P_range), blocks)
                
                
                current_load = complex(current_kW, current_kW*base_kVAR/base_kW)
                bid =  dict()
                bid['constant_MW'] = constant_load
                bid['constant_MVAR'] = constant_load*base_kVAR/base_kW
                bid['P_bid'] = list(P_values)
                bid['Q_bid'] = list(Q_values)
                
                
                bid_raw = json.dumps(bid)
                
                 #####  Publishing current loads for Co-SIM Bus the ISO Simulator #####
                if include_helics:
                    pub_key = [key for key in pub_keys  if ('pcc.' + str(cosim_bus) + '.rt_energy.bid') in key ]
                    pub_object = h.helicsFederateGetPublication(fed, pub_key[0])
                    status = h.helicsPublicationPublishString(pub_object, bid_raw)
                    print('DSO: Published Bids for Bus {}'.format(cosim_bus))
                
            if include_helics:                    
                time_request = time_granted+2
                while time_granted < time_request:
                    time_granted = h.helicsFederateRequestTime(fed, time_request)
    
                print('DSO: Requested {}s and got Granted {}s'.format(time_request, time_granted))
    
                for cosim_bus in wrapper_config['cosimulation_bus']:
                    sub_key = [key for key in sub_keys  if ('pcc.' + str(cosim_bus) + '.rt_energy.cleared') in key ]
                    sub_object = h.helicsFederateGetSubscription(fed, sub_key[0])
                    allocation_raw = h.helicsInputGetString(sub_object)
                    allocation =  json.loads(allocation_raw)
                    print('DSO: Received cleared values {} for Bus {}'.format(allocation, cosim_bus))

            tnext_real_time_market = tnext_real_time_market + wrapper_config['real_time_market']['interval']           
            
            
            
        ######## Power Flow Intervals ########
        if time_granted >= tnext_physics_powerflow and wrapper_config['include_physics_powerflow'] and time_granted < duration:
            
            profile_time = current_time + timedelta(seconds=buffer)
            data_idx = load_profiles.index[load_profiles.index == profile_time]
            current_load_profile = load_profiles.loc[data_idx]
            for cosim_bus in wrapper_config['cosimulation_bus']:
                base_kW = case['bus'][cosim_bus-1][2]
                base_kVAR = case['bus'][cosim_bus - 1][3]
                current_kW = current_load_profile[cosim_bus].values
                current_load = complex(current_kW, current_kW*base_kVAR/base_kW)

                #####  Publishing current loads for Co-SIM Bus the ISO Simulator #####
                pub_key = [key for key in pub_keys  if ('pcc.' + str(cosim_bus) + '.pq') in key ]
                pub_object = h.helicsFederateGetPublication(fed, pub_key[0])
                status = h.helicsPublicationPublishComplex(pub_object, current_load.real, current_load.imag)
                print('DSO: Published {} demand for Bus {}'.format(current_load, cosim_bus))

            time_request = time_granted+2
            while time_granted < time_request:
                time_granted = h.helicsFederateRequestTime(fed, time_request)

            print('DSO: Requested {}s and got Granted {}s'.format(time_request, time_granted))

            for cosim_bus in wrapper_config['cosimulation_bus']:
                sub_key = [key for key in sub_keys  if ('pcc.' + str(cosim_bus) + '.pnv') in key ]
                sub_object = h.helicsFederateGetSubscription(fed, sub_key[0])
                voltage = h.helicsInputGetComplex(sub_object)
                print('DSO: Received {} Voltage for Bus {}'.format(voltage, cosim_bus))

            tnext_physics_powerflow = tnext_physics_powerflow + wrapper_config['physics_powerflow']['interval']

    if include_helics:
        h.helicsFederateDisconnect(fed)
        h.helicsBrokerWaitForDisconnect(broker,-1)
        h.helicsCloseLibrary();
