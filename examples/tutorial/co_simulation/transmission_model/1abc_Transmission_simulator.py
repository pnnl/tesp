# -*- coding: utf-8 -*-
"""
Created on Thu Oct 11 10:08:26 2018

@author: monish.mukherjee
"""
import scipy.io as spio
from pypower.api import case118, ppoption, runpf, runopf
import math
import numpy
import matplotlib.pyplot as plt
import time
#import helics as h
import random
import logging
import argparse
import json 
import pandas as pd
import copy

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)



def destroy_federate(fed):
    grantedtime = h.helicsFederateRequestTime(fed, h.HELICS_TIME_MAXTIME)
    status = h.helicsFederateDisconnect(fed)
    h.helicsFederateDestroy(fed)
    logger.info("Federate finalized")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-c', '--case_num',
                        help='Case number, must be either "1b" or "1c"',
                        nargs=1)
    args = parser.parse_args()

    #################################  Registering  federate from json  ########################################
    case_num = '1b'
    # fed = h.helicsCreateValueFederateFromConfig(f"{case_num}_Transmission_config.json")
    # #h.helicsFederateRegisterInterfaces(fed, "1a_Transmission_config.json")
    # federate_name = h.helicsFederateGetName(fed)
    # logger.info("HELICS Version: {}".format(h.helicsGetVersion()))
    # logger.info("{}: Federate {} has been registered".format(federate_name, federate_name))
    # pubkeys_count = h.helicsFederateGetPublicationCount(fed)
    # subkeys_count = h.helicsFederateGetInputCount(fed)
    # ######################   Reference to Publications and Subscription form index  #############################
    # pubid = {}
    # subid = {}
    # for i in range(0, pubkeys_count):
        # pubid["m{}".format(i)] = h.helicsFederateGetPublicationByIndex(fed, i)
        # pubtype = h.helicsPublicationGetType(pubid["m{}".format(i)])
        # pubname = h.helicsPublicationGetName(pubid["m{}".format(i)])
        # logger.info("{}: Registered Publication ---> {}".format(federate_name, pubname))
    # for i in range(0, subkeys_count):
        # subid["m{}".format(i)] = h.helicsFederateGetInputByIndex(fed, i)
        # h.helicsInputSetDefaultComplex(subid["m{}".format(i)], 0, 0)
        # sub_key = h.helicsSubscriptionGetTarget(subid["m{}".format(i)])
        # logger.info("{}: Registered Subscription ---> {}".format(federate_name, sub_key))

    ######################   Entering Execution Mode  ##########################################################
    #h.helicsFederateEnterInitializingMode(fed)
    #status = h.helicsFederateEnterExecutingMode(fed)

    # Pypower Processing (inputs)
    hours = 24
    total_inteval = int(60 * 60 * hours)
    grantedtime = -1
    pf_interval    = 5 * 60  # in seconds (minimim_resolution) ## Adjust this to change PF intervals
    acopf_interval = 15 * 60  # in seconds (minimim_resolution) ## Adjust this to change ACOPF intervals
    random.seed(0)

    peak_demand = []
    ppc = []
    #case_format = case118()
    #peak_demand = case_format["bus"][:, 2][:].copy()
    #ppc = case_format.copy()
    
    f = open("c118swf.json")
    json_string = f.read()
    json_data = json.loads(json_string) 
    
    case_format = json_data
    case_format["bus"] = numpy.array(case_format["bus"])
    case_format["gen"] = numpy.array(case_format["gen"])
    case_format["gencost"] = numpy.array(case_format["gencost"])
    
    peak_demand = copy.deepcopy(case_format["bus"][:, 2][:])
    ppc = copy.deepcopy(case_format)
    #ppc["gen"][48:52,8:10] = 0.0

    ######################   creating fixed load profiles for each bus based on PF interval #############################

    # load profiles (inputs)
    profiles = spio.loadmat(
        "normalized_load_data_1min_ORIGINAL.mat", squeeze_me=True, struct_as_record=False
    )
    load_profiles_1min = profiles["my_data"]
    resolution_load = int(total_inteval / pf_interval)
    points = numpy.floor(numpy.linspace(0, len(load_profiles_1min) - 1, resolution_load + 1))
    time_pf = numpy.linspace(0, total_inteval, resolution_load + 1)
    load_profiles = load_profiles_1min[points.astype(int), :]

    ###################   Creating a fixed profile for buses    ##################

    bus_profiles_index = []
    profile_number = 0
    for i in range(len(ppc["bus"])):
        bus_profiles_index.append(profile_number)
        if profile_number == 8:
            profile_number = 0
        else:
            profile_number = profile_number + 1
    ###################   Asserting Profiles to buses    ############################

    # bus_profiles_index = numpy.random.random_integers(0,load_profiles.shape[1]-1,len(ppc['bus']))
    bus_profiles = load_profiles[:, bus_profiles_index]
    time_opf = numpy.linspace(0, total_inteval, int(total_inteval / acopf_interval) + 1)

    ###########################   Cosimulation Bus and Load Amplification Factor #########################################

    # Co-sim Bus  (inputs)
    Cosim_bus_number = 118
    cosim_bus = Cosim_bus_number - 1  ## Do not change this line
    load_amplification_factor = 15

    # power_flow
    fig = plt.figure()
    ax1 = fig.add_subplot(2, 1, 1)
    ax2 = fig.add_subplot(2, 1, 2)
    voltage_plot = []
    x = 0
    k = 0
    voltage_cosim_bus = (ppc["bus"][cosim_bus, 7] * ppc["bus"][cosim_bus, 9]) * 1.043

    #########################################   Starting Co-simulation  ####################################################

    for t in range(0, total_inteval, pf_interval):

        ############################   Publishing Voltage to GridLAB-D #######################################################

        voltage_gld = complex(voltage_cosim_bus * 1000)
        # logger.info("{}: Substation Voltage to the Distribution System = {} kV".format(federate_name, round(abs(voltage_gld)/1000, 2)))
        # for i in range(0, pubkeys_count):
            # pub = pubid["m{}".format(i)]
            # status = h.helicsPublicationPublishComplex(pub, voltage_gld.real, voltage_gld.imag)
        # # status = h.helicsEndpointSendEventRaw(epid, "fixed_price", 10, t)

        # logger.info("{} - {}".format(grantedtime, t))
        # while grantedtime < t:
            # grantedtime = h.helicsFederateRequestTime(fed, t)
        grantedtime = t               

        #############################   Subscribing to Feeder Load from to GridLAB-D ##############################################

        # for i in range(0, subkeys_count):
            # sub = subid["m{}".format(i)]
            # demand = h.helicsInputGetComplex(sub)
            # rload = demand.real;
            # iload = demand.imag;
        rload = 2980
        iload = 2980*math.tan(math.acos(0.85))                                                  
        #logger.info("{}: Federate Granted Time = {}".format(federate_name,grantedtime))
        #logger.info("{}: Substation Load from Distribution System = {} kW".format(federate_name, complex(round(rload,2), round(iload,2)) / 1000))
        # print(voltage_plot,real_demand)

        actual_demand = peak_demand * bus_profiles[x, :]
        ppc["bus"][:, 2] = actual_demand
        ppc["bus"][:, 3] = actual_demand * math.tan(math.acos(0.85))
        # ppc["bus"][cosim_bus, 2] = rload * load_amplification_factor / 1000000
        # ppc["bus"][cosim_bus, 3] = iload * load_amplification_factor / 1000000
        ppopt = ppoption(PF_ALG=1, OUT_ALL=0, VERBOSE=1)

        #logger.info("{}: Current AC-PF TIme is {} and Next AC-OPF time is {}".format(federate_name, time_pf[x], time_opf[k]))

        ############################  Running OPF For optimal power flow intervals   ##############################

        if time_pf[x] == time_opf[k]:
            results_opf = runopf(ppc, ppopt)
            if results_opf["success"]:
                ppc["bus"] = results_opf["bus"]
                ppc["gen"] = results_opf["gen"]
                if k == 0:
                    LMP_solved = results_opf["bus"][:, 13]
                else:
                    LMP_solved = numpy.vstack((LMP_solved, results_opf["bus"][:, 13]))
                    opf_time = time_opf[0 : k + 1] / 3600
            k = k + 1

        ################################  Running PF For optimal power flow intervals   ##############################

        solved_pf = runpf(ppc, ppopt)
        results_pf = solved_pf[0]
        ppc["bus"] = results_pf["bus"]
        ppc["gen"] = results_pf["gen"]

        if results_pf["success"] == 1:
            if x == 0:
                voltages = results_pf["bus"][:, 7]
                real_demand = results_pf["bus"][:, 2]
                gen_op = results_pf["gen"][:, 1]
                distribution_load = [rload / 1000000]
            else:
                voltages = numpy.vstack((voltages, results_pf["bus"][:, 7]))
                real_demand = numpy.vstack((real_demand, results_pf["bus"][:, 2]))
                gen_op = numpy.vstack((gen_op, results_pf["gen"][:, 1]))
                distribution_load.append(rload / 1000000)
                pf_time = time_pf[0 : x + 1] / 3600

            voltage_cosim_bus = results_pf["bus"][cosim_bus, 7] * results_pf["bus"][cosim_bus, 9]
            voltage_plot.append(voltage_cosim_bus)

        ######################### Plotting the Voltages and Load of the Co-SIM bus ##############################################

        if x > 0:
            ax1.clear()
            ax1.plot(pf_time, voltage_plot, "r--")
            ax1.set_xlim([0, 25])
            ax1.set_ylabel("Voltage [in kV]")
            ax1.set_xlabel("Time [in hours]")
            ax2.clear()
            ax2.plot(pf_time, real_demand[:, cosim_bus], "k")
            ax2.set_xlim([0, 25])
            ax2.set_ylabel("Load from distribution [in MW]")
            ax2.set_xlabel("Time [in hours]")
            ax1.grid()
            ax2.grid()
            plt.show(block=False)
            plt.pause(0.01)
        x = x + 1
        
        if t == (total_inteval - pf_interval):
            plt.tight_layout()
            plt.savefig(f"./output/{case_num}_transmission_plot.png", dpi=200)

    ##########################   Creating headers and Printing results to CSVs #####################################

    head = str("Time(in Hours)")
    for i in range(voltages.shape[1]):
        head = head + "," + ("Bus" + str(i + 1))

    numpy.savetxt(
        f"./output/{case_num}_Transmission_Voltages.csv",
        numpy.column_stack((pf_time, voltages)),
        delimiter=",",
        fmt="%s",
        header=head,
        comments="",
    )
    numpy.savetxt(
        f"./output/{case_num}_Transmission_MW_demand.csv",
        numpy.column_stack((pf_time, real_demand)),
        delimiter=",",
        fmt="%s",
        header=head,
        comments="",
    )
    numpy.savetxt(
        f"./output/{case_num}_Transmission_LMP.csv",
        numpy.column_stack((opf_time, LMP_solved)),
        delimiter=",",
        fmt="%s",
        header=head,
        comments="",
    )
    Gen_head = str("Time(in Hours)")
    for i in range(gen_op.shape[1]):
        Gen_head = Gen_head + "," + ("Gen" + str(i + 1))

    numpy.savetxt(
        f"./output/{case_num}_Generator_realpower.csv",
        numpy.column_stack((pf_time, gen_op)),
        delimiter=",",
        fmt="%s",
        header=Gen_head,
        comments="",
    )

    ##############################   Terminating Federate   ########################################################
    t = 60 * 60 * 24
    # while grantedtime < t:
        # grantedtime = h.helicsFederateRequestTime(fed, t)
    # logger.info("{}: Destroying federate".format(federate_name))
    # destroy_federate(fed)
    # logger.info("{}: Done!".format(federate_name))
