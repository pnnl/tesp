# -*- coding: utf-8 -*-
"""
Created on Mon May 25 12:03:48 2020
@author: mukh915
"""

import logging

import numpy as np
import numpy.matlib as npm
from scipy.interpolate import interp1d


# logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


# ----------------------------------------------------------------------------------------------------
# ------------------------- Laplacian of Chow's Fig 6, star topology ---------------------------------
# ----------------------------------------------------------------------------------------------------
def construct_Laplacian(N_agents):
    L = np.zeros((N_agents, N_agents))
    np.fill_diagonal(L, 1)
    L[:, 0] = -1
    L[0, :] = -1
    L[0, 0] = -1 * (N_agents - 1)
    D = np.absolute(L) / npm.repmat(np.sum(np.absolute(L), 1), N_agents, 1).T
    return D


# ---------------------------------------------------------------------------------------------------
# ---------------------------- Consensus Real Time (One Time Step)------------------------------------
# ----------------------------------------------------------------------------------------------------
def consensus_RT(P, Q, PD, PG_initial, Ramp_rates, is_Ramp=False):
    N_agents = P.shape[1]  # number of agents
    D = construct_Laplacian(N_agents)
    ###########################################################################
    # ################## Initialize dual variable \lambda #####################
    ###########################################################################
    lambda_initial = np.zeros(N_agents)
    for i in range(N_agents):
        f = interp1d(Q[:, i], P[:, i])
        lambda_initial[i] = f(PG_initial[i])

    # gamma0 = 4/np.sum(1/a)
    gamma0 = 0.0025
    rela_eps = 5e-2
    iter_max = 2000

    # Initialize dual variable \lambda
    lambda_c = np.zeros((N_agents, iter_max))
    PG = np.zeros((N_agents, iter_max))
    DeltaP = np.zeros((1, iter_max))
    lambda_c[:, 0] = lambda_initial
    PG[:, 0] = PG_initial
    DeltaP[:, 0] = PD - np.sum(PG[:, 0])

    ###########################################################################
    # ##################### Starting Consensus Algorthm #######################
    ###########################################################################
    # Select node 1 as the leader
    kk = 0
    jj = 0
    gamma_max = 15
    lambda_diff = 1
    lambda_diff2 = 1
    P_diff = max(abs(DeltaP[:, 0]))

    # while (abs(DeltaP[:,kk]) > rela_eps*abs(PD)) or (lambda_diff > 1e-06):
    while (abs(DeltaP[:, kk]) > rela_eps) or (lambda_diff > 1e-02):

        # ######## Adjusting gamma if consensus didn't converge ###########
        if kk + 1 >= iter_max:
            kk = 0
            jj = jj + 1
            print(jj)
            gamma0 = gamma0 / (jj ** 0.5)
        if jj > gamma_max:
            logging.warning('Failed to reach Consensus (Single-step) !!! On iteration {} for Gamma {}'.format(kk, jj))
            f = open("Consensus_reports.txt", "a+")
            f.write('Failed to reach Consensus (Single-step) !!!! On iteration {} for Gamma {}'.format(jj, kk))
            break

        # ############ Updating Lamda in each iteration ################
        lambda_c[:, kk + 1] = np.matmul(D, lambda_c[:, kk]) + ((gamma0 / ((kk + 1) * 0.9)) * DeltaP[:, kk]) * np.ones(
            N_agents)
        lambda_temp = lambda_c[:, kk + 1]
        lambda_temp = np.maximum(lambda_temp, P[0, :])  # The minimum value for lambda is b1=b2=1
        lambda_temp = np.minimum(lambda_temp, P[-1, :])  # The maximum value for lambda is 21 and 41

        # ######### Updating Agent Quantity in each iteration ###########
        for i in range(N_agents):
            P_agent, ind = np.unique(P[:, i], return_index=True)
            Q_agent = Q[ind, i]

            f_agent = interp1d(P_agent, Q_agent)
            PG[i, kk + 1] = f_agent(lambda_temp[i])

            # ######### Ramping Constraints (Temporary) ###########
            if is_Ramp and i < 5:
                if abs(PG[i, kk + 1]) > abs(Q_Previous[i] + Ramp_rates[i]):
                    PG[i, kk + 1] = (Q_Previous[i] + Ramp_rates[i])
                elif abs(PG[i, kk + 1]) < abs(Q_Previous[i] - Ramp_rates[i]):
                    PG[i, kk + 1] = (Q_Previous[i] - Ramp_rates[i])

            # ######### Bounding Constraints (Temporary) ###########
            if (PG[i, kk + 1]) > np.max((Q[:, i])) and i < 5:
                PG[i, kk + 1] = np.max((Q[:, i]))
                # print('hit Limit for agent',i, kk)
            elif (PG[i, kk + 1]) < np.min((Q[:, i])) and i < 5:
                PG[i, kk + 1] = np.min((Q[:, i]))
                # print('hit Limit for agent',i, kk)

        # ###### check the difference between dual variables #######
        lambda_temp = lambda_c[:, kk + 1]
        lambda_diff1 = 0
        lambda_diff2 = max(abs(lambda_c[:, kk + 1] - lambda_c[:, kk]))
        for i in range(N_agents):
            for j in range(i + 1, N_agents):
                lambda_diffTemp1 = lambda_diff1
                lambda_diffTemp2 = lambda_temp[i] - lambda_temp[j]
                lambda_diff1 = np.maximum(abs(lambda_diffTemp1), abs(lambda_diffTemp2))

        lambda_diff = lambda_diff1
        # ####### Updating  Quantity Mismatch in each iteration #########
        DeltaP[:, kk + 1] = PD - np.sum(PG[:, kk + 1])
        P_diff = max(abs(DeltaP[:, kk + 1] - DeltaP[:, kk]))
        kk = kk + 1

    price = lambda_c[:, kk]
    generation = PG[:, kk]
    print(jj, kk, DeltaP[:, kk], lambda_diff2)
    if jj < gamma_max:
        logging.info('Successfully Reached Consensus (Single-step) !!! On iteration {} for Gamma {}'.format(kk, jj))

    # ### Plotting Lamda convergence  ###
    # fig, ax = plt.subplots()
    # for i in range(N_agents):
    #     ax.plot(lambda_c[i,0:kk])
    # ax.set(xlabel='Iterations', ylabel='Lamda ($/kW)')
    # plt.show()

    return price, generation


# ----------------------------------------------------------------------------------------------------
# ---------------------------- Consensus Day Ahead (Multi Time Step) ---------------------------------
# ----------------------------------------------------------------------------------------------------
def consensus_DA(P_agents_Multi, Q_agents_Multi, P_uncontrol, Q_initial, Ramp_rates, is_Ramp=False):
    # ### Consensus for multiple timesteps
    time_steps = P_agents_Multi.shape[0]
    N_agents = P_agents_Multi.shape[2]  # number of agents
    D = construct_Laplacian(N_agents)

    ###########################################################################
    # ################### Initialize dual variable \lambda #####################
    ###########################################################################
    lambda_initial = np.zeros((time_steps, N_agents))
    for t in range(time_steps):
        for n in range(N_agents):
            f = interp1d(Q_agents_Multi[t, :, n], P_agents_Multi[t, :, n])
            lambda_initial[t, n] = f(Q_initial[t, n])

    # gamma0 = 4/np.sum(1/a)
    gamma0 = 0.0025
    rela_eps = 5e-2 * np.ones(time_steps)
    iter_max = 2500

    # Initialize dual variable \lambda
    lambda_c = np.zeros((time_steps, N_agents, iter_max))
    PG = np.zeros((time_steps, N_agents, iter_max))
    DeltaP = np.zeros((time_steps, iter_max))
    lambda_c[:, :, 0] = lambda_initial
    PG[:, :, 0] = Q_initial
    DeltaP[:, 0] = P_uncontrol - np.sum(PG[:, :, 0], axis=1)

    ###########################################################################
    # ###################### Starting Consensus Algorthm #######################
    ###########################################################################

    # Select node 1 as the leader
    kk = 0
    jj = 0
    gamma_max = 10
    lambda_diff = 1
    logging.debug('Solving Multi Step Consensus for {} steps and  {} Agents'.format(time_steps, N_agents))

    while np.any(abs(DeltaP[:, kk]) > rela_eps):

        # ######## Adjusting gamma if consensus didn't converge ###########
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

        # ############ Updating Lamda in each iteration ################
        for n1 in range(N_agents):
            temp_value = np.zeros(time_steps)
            for n2 in range(N_agents):
                temp_value = temp_value + D[n1, n2] * lambda_c[:, n2, kk]
            lambda_c[:, n1, kk + 1] = temp_value + ((gamma0 / (0.9 * (kk + 1))) * DeltaP[:, kk])

        lambda_temp = lambda_c[:, :, kk + 1]
        lambda_temp = np.maximum(lambda_temp, P_agents_Multi[:, 0, :])
        lambda_temp = np.minimum(lambda_temp, P_agents_Multi[:, -1, :])

        # ######### Updating Agent Quantity in each iteration ###########
        for t in range(time_steps):
            for n in range(N_agents):
                P_agent, ind = np.unique(P_agents_Multi[t, :, n], return_index=True)
                Q_agent = Q_agents_Multi[t, ind, n]
                f_agent = interp1d(P_agent, Q_agent)
                PG[t, n, kk + 1] = f_agent(lambda_temp[t, n])

                # ######### Bounding and Ramping Constraints (Temporary) ###########
                if n < 5 and t > 0:
                    if is_Ramp:
                        PG_max = np.min((np.max((Q_agents_Multi[t, :, n])), (PG[t - 1, n, kk + 1] + Ramp_rates[n])))
                        # PG_min = np.max((np.min((Q_agents_Multi[t,:,n])), (PG[t-1,n,kk+1] - Ramp_rates[n]) ))
                        PG_min = np.min((Q_agents_Multi[t, :, n]))
                    else:
                        PG_max = np.max((Q_agents_Multi[t, :, n]))
                        PG_min = np.min((Q_agents_Multi[t, :, n]))

                    if abs(PG[t, n, kk + 1]) > PG_max:
                        PG[t, n, kk + 1] = PG_max
                        # print('hit Limit for agent',n, kk)
                    elif abs(PG[t, n, kk + 1]) < PG_min:
                        PG[t, n, kk + 1] = PG_min
                        # print('hit Limit for agent',n, kk)

        # ## To do  ###
        # check the difference between dual variables 
        #        lambda_diff1 = 0
        #        for ni in range(N_agents):
        #            for nj in range(ni+1, N_agents):
        #                lambda_diffTemp1=lambda_diff1

        # ####### Updating  Quantity Mismatch in each iteration #########
        DeltaP[:, kk + 1] = P_uncontrol - np.sum(PG[:, :, kk + 1], axis=1)
        kk = kk + 1

    print(jj, kk, DeltaP[:, kk])
    if jj < gamma_max:
        logging.info('Successfully Reached Consensus (Multi-step) !!!! On iteration {} for Gamma {}'.format(kk, jj))

    price_Multi = lambda_c[:, :, kk]
    generation_Multi = PG[:, :, kk]

    # ## Plotting Lamda convergence  ###
    #    fig = plt.figure()
    #    ax = fig.gca(projection='3d')
    #    for t in range(time_steps):
    #        for i in range(N_agents):
    #            ax.plot( t*np.ones(kk), np.linspace(0, kk,kk), lambda_c[t,i,:kk])
    #    ax.set(xlabel='Time-steps', ylabel='Iterations',zlabel='Lamda ($/kW)')
    #    plt.show()

    return price_Multi, generation_Multi
