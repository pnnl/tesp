import json
import logging
import os

import helics as h
import numpy as np
import numpy.matlib as npm
from scipy.interpolate import interp1d

from tesp_support.dsot.helpers_dsot import MarketClearingType

P_price_DSO = np.array(([0.0247, 0.01974, 0.01889, 0.01797, 0.01724, 0.01713, 0.018, 0.01709, 0.0181,
                         0.02185, 0.02462, 0.03037, 0.04141, 0.04885, 0.06822, 0.09555, 0.14969, 0.11952,
                         0.08191, 0.05319, 0.04177, 0.03359, 0.02702, 0.02552]))
P_price_DSO = P_price_DSO * 5
P_price_DSO = np.hstack((P_price_DSO, P_price_DSO))

gamma = 0.0025
iter_max = 1600
microstep_interval = 0.010  # ##(in seconds)


# ----------------------------------------------------------------------------------------------------
# ------------------------- Laplacian of Chow's Fig 6, star topology ---------------------------------
# ----------------------------------------------------------------------------------------------------

# Laplacian of Chow's Fig 6, star topology
def construct_Laplacian(N_agents):
    L = np.zeros((N_agents, N_agents))
    np.fill_diagonal(L, 1)
    L[:, 0] = -1
    L[0, :] = -1
    L[0, 0] = -1 * (N_agents - 1)
    D = np.absolute(L) / npm.repmat(np.sum(np.absolute(L), 1), N_agents, 1).T
    return D


# ----------------------------------------------------------------------------------------------------
# ------------------------------------- Day Ahead Distributed Market ---------------------------------
# ---------------------------------------------------------------------------------------------------
def Consenus_dist_DA(dso_market_obj, DA_horizon, fed, hour_of_day, time_granted, time_market_DA_complete):
    bid_size = 100
    P_agents_DA = np.zeros((DA_horizon, bid_size))
    Q_agents_DA = np.zeros((DA_horizon, bid_size))
    Q_initial_DA = np.zeros(DA_horizon)
    lambda_DA_initial = np.zeros(DA_horizon)
    P_uncontrol_DA = np.zeros(DA_horizon)

    ###########################################################################
    # ###################### Organizing Agent Bids ############################
    ###########################################################################
    for T in range(DA_horizon):
        Q_agents_DA[T, :] = np.linspace(0, dso_market_obj.generators['size'], bid_size)  # % in MW
        a = dso_market_obj.generators['a']
        b = dso_market_obj.generators['b']
        c = dso_market_obj.generators['c']
        P_agents_DA[T, :] = 2 * a * Q_agents_DA[T, :] + b

        Q_initial_DA[T] = dso_market_obj.cleared_q_da[T]
        Q_initial_DA[T] = np.minimum(Q_initial_DA[T], Q_agents_DA[T, 0])
        Q_initial_DA[T] = np.maximum(Q_initial_DA[T], Q_agents_DA[T, -1])
        f = interp1d(Q_agents_DA[T, :], P_agents_DA[T, :])
        lambda_DA_initial[T] = f(Q_initial_DA[T])

    ###########################################################################
    # ##################### Optimization Parameters ###########################
    ###########################################################################
    rela_eps = 5e-2 * np.ones(DA_horizon)
    gamma0 = gamma
    microstep = microstep_interval

    fed_name = h.helicsFederateGetName(fed)
    N_agents = len(dso_market_obj.market[fed_name]) + 1
    D = construct_Laplacian(N_agents)

    ###########################################################################
    # ################## Initialize dual variable \lambda #####################
    ###########################################################################
    lambda_c = np.zeros((DA_horizon, N_agents, iter_max))
    PG = np.zeros((DA_horizon, N_agents, iter_max))
    DeltaP = np.zeros((DA_horizon, iter_max))

    # ############### Starting Price and Quantity for Agent ###################
    agent_idx = 0
    lambda_c[:, agent_idx, 0] = lambda_DA_initial
    PG[:, agent_idx, 0] = Q_initial_DA
    DeltaP[:, 0] = P_uncontrol_DA - np.sum(PG[:, :, 0], axis=1)

    ###########################################################################
    # ########## Sending Starting Lamda and Quantity to all Agents ############
    ###########################################################################
    json_prices = json.dumps(lambda_c[:, agent_idx, 0].tolist(), indent=4, separators=(',', ': '))
    json_quantities = json.dumps(PG[:, agent_idx, 0].tolist(), indent=4, separators=(',', ': '))
    for key in dso_market_obj.market[fed_name]:
        key_price_bid = fed_name + '/' + key + '/cleared_price_DA'
        dest_price_bid = key + '/' + fed_name + '/cleared_price_DA'
        end_price_bid = h.helicsFederateGetEndpoint(fed, key_price_bid)
        status = h.helicsEndpointSendBytesTo(end_price_bid, json_prices, dest_price_bid)

        key_quantity_bid = fed_name + '/' + key + '/cleared_quantity_DA'
        dest_quantity_bid = key + '/' + fed_name + '/cleared_quantity_DA'
        end_quantity_bid = h.helicsFederateGetEndpoint(fed, key_quantity_bid)
        status = h.helicsEndpointSendBytesTo(end_quantity_bid, json_quantities, dest_quantity_bid)

    ###########################################################################
    # ##################### Starting Consensus Algorthm #######################
    ###########################################################################
    # Select node 1 as the leader
    kk = 0
    jj = 0
    gamma_max = 10
    logging.debug('Solving Multi Step Consensus for {} steps and  {} Agents'.format(DA_horizon, N_agents))

    time_market_da = time_granted
    while (np.any(abs(DeltaP[:, kk]) > rela_eps) or kk < 2) and time_granted < time_market_DA_complete:
        print(kk, np.max(np.abs(DeltaP[:, kk])))
        # ####### Adjusting gamma if consensus didn't converge ###########
        if kk + 1 >= iter_max:
            kk = 0
            jj = jj + 1
            print(jj)
            gamma0 = gamma0 / (jj ** 0.5)

        if jj > gamma_max:
            logging.warning('Failed to reach Consensus (Multi-step) !!!! On iteration {} for Gamma {}'.format(jj, kk))
            f = open("Consensus_reports.txt", "a+")
            f.write('Failed to reach Consensus (Multi-step) !!!! On iteration {} for Gamma {}'.format(jj, kk))
            break

        ###########################################################################
        # ################## MicroStepping Ahead in Time ##########################

        time_market_da = round(time_market_da + microstep, 3)
        while time_granted < time_market_da:
            time_granted = h.helicsFederateRequestTime(fed, time_market_da)

        ###########################################################################
        # ############ Receiving Lamda and Quantity from all Agents ###############
        # ############ Updating Lamda and Quantity from all Agents ################
        ###########################################################################
        other_agent_idx = 1
        for key in dso_market_obj.market[fed_name]:
            key_price_bid = fed_name + '/' + key + '/cleared_price_DA'
            end_price_bid = h.helicsFederateGetEndpoint(fed, key_price_bid)
            if h.helicsEndpointHasMessage(end_price_bid):
                price_msg_obj = h.helicsEndpointGetMessage(end_price_bid)
                temp_price = json.loads(h.helicsMessageGetString(price_msg_obj))
                lambda_c[:, other_agent_idx, kk] = np.asarray(temp_price)
            key_quantity_bid = fed_name + '/' + key + '/cleared_quantity_DA'
            end_quantity_bid = h.helicsFederateGetEndpoint(fed, key_quantity_bid)
            if h.helicsEndpointHasMessage(end_quantity_bid):
                quantity_msg_obj = h.helicsEndpointGetMessage(end_quantity_bid)
                temp_quantity = json.loads(h.helicsMessageGetString(quantity_msg_obj))
                PG[:, other_agent_idx, kk] = np.asarray(temp_quantity)
            other_agent_idx += 1

        # ###### Updating  Quantity Mismatch in each iteration #########
        DeltaP[:, kk + 1] = P_uncontrol_DA - np.sum(PG[:, :, kk], axis=1)

        ###########################################################################
        # #################### Updating Lamda in each iteration ###################
        ###########################################################################
        temp_value = np.zeros(DA_horizon)
        for n2 in range(N_agents):
            temp_value = temp_value + D[agent_idx, n2] * lambda_c[:, n2, kk]
        lambda_c[:, agent_idx, kk + 1] = temp_value + ((gamma0 / (0.9 * (kk + 1))) * DeltaP[:, kk + 1])

        lambda_temp = lambda_c[:, agent_idx, kk + 1]
        lambda_temp = np.maximum(lambda_temp, P_agents_DA[:, 0])
        lambda_temp = np.minimum(lambda_temp, P_agents_DA[:, -1])

        PG[:, :, kk + 1] = PG[:, :, kk]
        # ######## Updating Agent Quantity in each iteration ###########
        for T in range(DA_horizon):
            P_agent, ind = np.unique(P_agents_DA[T, :], return_index=True)
            Q_agent = Q_agents_DA[T, ind]
            f_agent = interp1d(P_agent, Q_agent)
            PG[T, agent_idx, kk + 1] = f_agent(lambda_temp[T])

            # ######## Bounding and Ramping Constraints (Temporary) ###########
            if 'DG' in fed_name:
                PG_max = np.max((Q_agents_DA[T, :]))
                PG_min = np.min((Q_agents_DA[T, :]))
                if abs(PG[T, agent_idx, kk + 1]) > PG_max:
                    PG[T, agent_idx, kk + 1] = PG_max
                    # print('hit Limit for agent',n, kk)
                elif abs(PG[T, agent_idx, kk + 1]) < PG_min:
                    PG[T, agent_idx, kk + 1] = PG_min

        # ######## Updating  Quantity Mismatch in each iteration #########
        # DeltaP[:, kk + 1] = P_uncontrol_DA - np.sum(PG[:, :, kk + 1], axis=1)

        kk = kk + 1

        ###########################################################################
        # ############## Sending Lamda and Quantity to all Agents #################
        ###########################################################################
        json_prices = json.dumps(lambda_c[:, agent_idx, kk].tolist(), indent=4, separators=(',', ': '))
        json_quantities = json.dumps(PG[:, agent_idx, kk].tolist(), indent=4, separators=(',', ': '))
        for key in dso_market_obj.market[fed_name]:
            key_price_bid = fed_name + '/' + key + '/cleared_price_DA'
            dest_price_bid = key + '/' + fed_name + '/cleared_price_DA'
            end_price_bid = h.helicsFederateGetEndpoint(fed, key_price_bid)
            status = h.helicsEndpointSendBytesTo(end_price_bid, json_prices, dest_price_bid)

            key_quantity_bid = fed_name + '/' + key + '/cleared_quantity_DA'
            dest_quantity_bid = key + '/' + fed_name + '/cleared_quantity_DA'
            end_quantity_bid = h.helicsFederateGetEndpoint(fed, key_quantity_bid)
            status = h.helicsEndpointSendBytesTo(end_quantity_bid, json_quantities, dest_quantity_bid)

    print(kk, np.max(np.abs(DeltaP[:, kk])))
    if jj < gamma_max:
        logging.info('Sucessfully Reached Consensus (Multi-step) !!!! On iteration {} for Gamma {}'.format(kk, jj))

    dso_market_obj.trial_cleared_quantity_DA = np.concatenate([PG[:, agent_idx, kk], PG[:, agent_idx, kk]]).tolist()
    dso_market_obj.Pwclear_DA = np.concatenate([lambda_c[:, agent_idx, kk], lambda_c[:, agent_idx, kk]]).tolist()
    dso_market_obj.trial_clear_type_DA = [MarketClearingType.UNCONGESTED] * dso_market_obj.windowLength

    while time_granted < time_market_DA_complete:
        time_granted = h.helicsFederateRequestTime(fed, time_market_DA_complete)

    for key in dso_market_obj.market[fed_name]:
        end_price_bid = h.helicsFederateGetEndpoint(fed, fed_name + '/' + key + '/cleared_price_DA')
        end_quantity_bid = h.helicsFederateGetEndpoint(fed, fed_name + '/' + key + '/cleared_quantity_DA')
        while h.helicsEndpointPendingMessageCount(end_price_bid) > 0:
            drop1 = h.helicsEndpointGetMessage(end_price_bid).data
        while h.helicsEndpointPendingMessageCount(end_quantity_bid) > 0:
            drop2 = h.helicsEndpointGetMessage(end_quantity_bid).data

    if not os.path.exists('convergence'):
        os.makedirs('convergence')
    np.savetxt("convergence/" + fed_name + "_lamda_DA_" + str(int(time_granted)) + ".csv", lambda_c[:, agent_idx, 0:kk],
               delimiter=",")
    np.savetxt("convergence/" + fed_name + "_PG_DA_" + str(int(time_granted)) + ".csv", PG[:, agent_idx, 0:kk],
               delimiter=",")

    return dso_market_obj, time_granted


# ----------------------------------------------------------------------------------------------------
# ------------------------------------- Real Time Distributed Market ---------------------------------
# ---------------------------------------------------------------------------------------------------

def Consenus_dist_RT(dso_market_obj, fed, hour_of_day, time_granted, time_market_RT_complete):
    bid_size = len(dso_market_obj.curve_DSO_RT.prices)
    P_agent_RT = np.zeros(bid_size)
    Q_agent_RT = np.zeros(bid_size)
    ###########################################################################
    # ##################### Organizing Agent Bids #############################
    ###########################################################################
    P_uncontrol = 0
    Q_agent_RT = np.linspace(0, dso_market_obj.generators['size'], bid_size)  # % in MW
    a = dso_market_obj.generators['a']
    b = dso_market_obj.generators['b']
    c = dso_market_obj.generators['c']
    P_agent_RT = 2 * a * Q_agent_RT + b

    Q_initial_RT = dso_market_obj.cleared_q_rt
    Q_initial_RT = np.minimum(Q_initial_RT, Q_agent_RT[0])
    Q_initial_RT = np.maximum(Q_initial_RT, Q_agent_RT[-1])
    f = interp1d(Q_agent_RT, P_agent_RT)
    lambda_RT_initial = f(Q_initial_RT)

    ###########################################################################
    # ##################### Optimization Parameters ###########################
    ###########################################################################
    rela_eps = 5e-2
    gamma0 = gamma
    microstep = microstep_interval

    fed_name = h.helicsFederateGetName(fed)
    N_agents = len(dso_market_obj.market[fed_name]) + 1
    D = construct_Laplacian(N_agents)

    ###########################################################################
    # ################## Initialize dual variable \lambda #####################
    ###########################################################################
    lambda_c = np.zeros((N_agents, iter_max))
    PG = np.zeros((N_agents, iter_max))
    DeltaP = np.zeros((1, iter_max))

    # ############### Starting Price and Quantity for Agent ###################
    agent_idx = 0
    lambda_c[agent_idx, 0] = lambda_RT_initial
    PG[agent_idx, 0] = Q_initial_RT
    DeltaP[agent_idx, 0] = P_uncontrol - np.sum(PG[:, 0])

    ###########################################################################
    # ########## Sending Starting Lamda and Quantity to all Agents ############
    ###########################################################################
    price = str(lambda_c[agent_idx, 0])
    quantity = str(PG[agent_idx, 0])
    for key in dso_market_obj.market[fed_name]:
        key_price_bid = fed_name + '/' + key + '/cleared_price_RT'
        dest_price_bid = key + '/' + fed_name + '/cleared_price_RT'
        end_price_bid = h.helicsFederateGetEndpoint(fed, key_price_bid)
        status = h.helicsEndpointSendBytesTo(end_price_bid, price, dest_price_bid)

        key_quantity_bid = fed_name + '/' + key + '/cleared_quantity_RT'
        dest_quantity_bid = key + '/' + fed_name + '/cleared_quantity_RT'
        end_quantity_bid = h.helicsFederateGetEndpoint(fed, key_quantity_bid)
        status = h.helicsEndpointSendBytesTo(end_quantity_bid, quantity, dest_quantity_bid)

    ###########################################################################
    # ##################### Starting Consensus Algorthm #######################
    ###########################################################################
    # Select node 1 as the leader
    kk = 0
    jj = 0
    gamma_max = 10
    temp_price = 0
    temp_quantity = 0

    logging.debug('Solving Single Step Consensus for {} Agents'.format(N_agents))

    time_market_rt = time_granted
    while ((abs(DeltaP[:, kk]) > rela_eps) or kk < 2) and time_granted < time_market_RT_complete:
        # print(kk, np.max(np.abs(DeltaP[:, kk])))
        # ####### Adjsuting gamma if consenus didn't converge ###########
        if kk + 1 >= iter_max:
            kk = 0
            jj = jj + 1
            print(jj)
            gamma0 = gamma0 / (jj ** 0.5)

        if jj > gamma_max:
            logging.warning('Failed to reach Consensus (Multi-step) !!!! On iteration {} for Gamma {}'.format(jj, kk))
            f = open("Consensus_reports.txt", "a+")
            f.write('Failed to reach Consensus (Multi-step) !!!! On iteration {} for Gamma {}'.format(jj, kk))
            break

        ###########################################################################
        # ################## MicroStepping Ahead in Time ##########################

        time_market_rt = round(time_market_rt + microstep, 3)
        while time_granted < time_market_rt:
            time_granted = h.helicsFederateRequestTime(fed, time_market_rt)

        ###########################################################################
        # ############ Receiving Lamda and Quantity from all Agents ###############
        # ############ Updating Lamda and Quantity from all Agents ################
        ###########################################################################
        other_agent_idx = 1
        for key in dso_market_obj.market[fed_name]:
            key_price_bid = fed_name + '/' + key + '/cleared_price_RT'
            end_price_bid = h.helicsFederateGetEndpoint(fed, key_price_bid)
            if h.helicsEndpointHasMessage(end_price_bid):
                price_msg_obj = h.helicsEndpointGetMessage(end_price_bid)
                temp_price = float(h.helicsMessageGetString(price_msg_obj))
                lambda_c[other_agent_idx, kk] = temp_price
            else:
                lambda_c[other_agent_idx, kk] = lambda_c[other_agent_idx, kk - 1]
            key_quantity_bid = fed_name + '/' + key + '/cleared_quantity_RT'
            end_quantity_bid = h.helicsFederateGetEndpoint(fed, key_quantity_bid)
            if h.helicsEndpointHasMessage(end_quantity_bid):
                quantity_msg_obj = h.helicsEndpointGetMessage(end_quantity_bid)
                temp_quantity = float(h.helicsMessageGetString(quantity_msg_obj))
                PG[other_agent_idx, kk] = temp_quantity
            else:
                PG[other_agent_idx, kk] = PG[other_agent_idx, kk - 1]
            other_agent_idx += 1

        # ###### Updating  Quantity Mismatch in each iteration #########
        DeltaP[:, kk + 1] = P_uncontrol - np.sum(PG[:, kk])  # ## (before local updates of lamda and PG)

        ###########################################################################
        # #################### Updating Lamda in each iteration ###################
        ###########################################################################
        temp_value = 0
        for n2 in range(N_agents):
            temp_value = temp_value + D[agent_idx, n2] * lambda_c[n2, kk]
        lambda_c[agent_idx, kk + 1] = temp_value + ((gamma0 / (0.9 * (kk + 1))) * DeltaP[:, kk + 1])

        lambda_temp = lambda_c[agent_idx, kk + 1]
        lambda_temp = np.maximum(lambda_temp, P_agent_RT[0])
        lambda_temp = np.minimum(lambda_temp, P_agent_RT[-1])

        PG[:, kk + 1] = PG[:, kk]
        # ######## Updating Agent Quantity in each iteration ###########
        P_agent, ind = np.unique(P_agent_RT, return_index=True)
        Q_agent = Q_agent_RT[ind]
        f_agent = interp1d(P_agent, Q_agent)
        PG[agent_idx, kk + 1] = f_agent(lambda_temp)

        # ######## Bounding and Ramping Constraints (Temporary) ###########
        if 'DG' in fed_name:
            PG_max = np.max(Q_agent_RT)
            PG_min = np.min(Q_agent_RT)
            if abs(PG[agent_idx, kk + 1]) > PG_max:
                PG[agent_idx, kk + 1] = PG_max
                # print('hit Limit for agent',n, kk)
            elif abs(PG[agent_idx, kk + 1]) < PG_min:
                PG[agent_idx, kk + 1] = PG_min

        # ######## Updating  Quantity Mismatch in each iteration #########
        # DeltaP[:, kk + 1] = P_uncontrol - np.sum(PG[:, kk + 1])

        kk = kk + 1
        # logging.info("current price {} and quantity {}".format(lambda_c[agent_idx, kk], PG[agent_idx, kk]))
        ###########################################################################
        # ############## Sending Lamda and Quantity to all Agents #################
        ###########################################################################
        price = str(lambda_c[agent_idx, kk])
        quantity = str(PG[agent_idx, kk])
        for key in dso_market_obj.market[fed_name]:
            key_price_bid = fed_name + '/' + key + '/cleared_price_RT'
            dest_price_bid = key + '/' + fed_name + '/cleared_price_RT'
            end_price_bid = h.helicsFederateGetEndpoint(fed, key_price_bid)
            status = h.helicsEndpointSendBytesTo(end_price_bid, price, dest_price_bid)

            key_quantity_bid = fed_name + '/' + key + '/cleared_quantity_RT'
            dest_quantity_bid = key + '/' + fed_name + '/cleared_quantity_RT'
            end_quantity_bid = h.helicsFederateGetEndpoint(fed, key_quantity_bid)
            status = h.helicsEndpointSendBytesTo(end_quantity_bid, quantity, dest_quantity_bid)

    print(kk, np.max(np.abs(DeltaP[:, kk])))
    if jj < gamma_max:
        logging.info('Sucessfully Reached Consensus (Single-step) !!!! On iteration {} for Gamma {}'.format(kk, jj))

    dso_market_obj.trial_cleared_quantity_RT = PG[agent_idx, kk]
    dso_market_obj.Pwclear_RT = lambda_c[agent_idx, kk]
    dso_market_obj.trial_clear_type_RT = MarketClearingType.UNCONGESTED

    while time_granted < time_market_RT_complete:
        time_granted = h.helicsFederateRequestTime(fed, time_market_RT_complete)

    for key in dso_market_obj.market[fed_name]:
        end_price_bid = h.helicsFederateGetEndpoint(fed, fed_name + '/' + key + '/cleared_price_RT')
        end_quantity_bid = h.helicsFederateGetEndpoint(fed, fed_name + '/' + key + '/cleared_quantity_RT')
        while h.helicsEndpointPendingMessageCount(end_price_bid) > 0:
            drop1 = h.helicsEndpointGetMessage(end_price_bid).data
        while h.helicsEndpointPendingMessageCount(end_quantity_bid) > 0:
            drop2 = h.helicsEndpointGetMessage(end_quantity_bid).data

    if not os.path.exists('convergence'):
        os.makedirs('convergence')
    np.savetxt("convergence/" + fed_name + "_lamda_RT_" + str(int(time_granted)) + ".csv", lambda_c[agent_idx, 0:kk],
               delimiter=",")
    np.savetxt("convergence/" + fed_name + "_PG_RT_" + str(int(time_granted)) + ".csv", PG[agent_idx, 0:kk],
               delimiter=",")

    return dso_market_obj, time_granted
