# -*- coding: utf-8 -*-
"""
Created on Sat Nov  9 21:54:27 2019

@author: liubo
"""

from DDPGa import Agent
import gym
import numpy as np
from utils import plotLearning

'''
DDPG agent  [action]
tesp_env  (house_name,time_step,state[],reward[],next_state[])

'''

env = gym.make('LunarLanderContinuous-v2')
agent = Agent(alpha=0.000025, beta=0.00025, input_dims=[8], tau=0.001, env=env,
              batch_size=64,  layer1_size=400, layer2_size=300, n_actions=1)

#agent.load_models()
np.random.seed(0)

score_history = []
for i in range(1000):
    obs = env.reset()                                                                                # obs =  hvac_number [T_set,T_room,LMP]
    done = False
    score = 0
    while not done:                                                                                 # t<t_step
        act = agent.choose_action(obs)                                                              # DDPG agent act=choose_action [T_set,T_room,LMP]      
        new_state, reward, done, info = env.step(act)                                                # new_state, reward, done = TESP.step(act)
        agent.remember(obs, act, reward, new_state, int(done))                                       # DDPG agent.remember(obs,act,new_state,int(done))
        agent.learn()                                                                               # DDPGagent. learn()
        score += reward                                                                             # score+=reward
        obs = new_state                                                                             # obs= new_state
        #env.render()
    score_history.append(score)

    if i % 25 == 0:
        agent.save_models()

    print('episode ', i, 'score %.2f' % score,
          'trailing 100 games avg %.3f' % np.mean(score_history[-100:]))

filename = 'LunarLander-alpha000025-beta00025-400-300.png'
plotLearning(score_history, filename, window=100)