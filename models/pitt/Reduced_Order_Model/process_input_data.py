# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 19:24:46 2020

@author: liubo
"""
import numpy as np
import torch
import torch.nn as nn

def process_data(input_rnn,output_rnn):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_dim = len(input_rnn[0,0,0,:])
    output_dim = len(output_rnn[0,0,0,:])
    
    input_max=np.zeros(input_dim)
    input_min=np.zeros(input_dim)
    input_rnn_norm=np.zeros(input_rnn.shape)
    for i in range(input_dim):
        input_max[i]=np.max(input_rnn[:,:,:,i])
        input_min[i]=np.min(input_rnn[:,:,:,i])
    #    input_rnn_norm[:,:,:,i] = input_rnn[:,:,:,i]/input_max[i]
        input_rnn_norm[:,:,:,i] = (input_rnn[:,:,:,i]-input_min[i])/(input_max[i]-input_min[i])    
    output_max=np.zeros(output_dim)
    output_min=np.zeros(output_dim)
    output_rnn_norm=np.zeros(output_rnn.shape)
    for i in range(output_dim):
        output_max[i]=np.max(output_rnn[:,:,:,i])
        output_min[i]=np.min(output_rnn[:,:,:,i])
    #    output_rnn_norm[:,:,:,i] = output_rnn[:,:,:,i]/output_max[i]
        output_rnn_norm[:,:,:,i] = (output_rnn[:,:,:,i]-output_min[i])/(output_max[i]-output_min[i])
       
    x_train = input_rnn_norm[:,0:21,:,:]
    x_test = input_rnn_norm[:,21:28,:,:]
    y_train = output_rnn_norm[:,0:21,:,:]
    y_test = output_rnn_norm[:,21:28,:,:]
    
    
    X=torch.tensor(input_rnn_norm).type(torch.FloatTensor).to(device)
    Y=torch.tensor(output_rnn_norm).type(torch.FloatTensor).to(device)
    
    X_=torch.tensor(x_test).type(torch.FloatTensor).to(device)
    Y_=torch.tensor(y_test).type(torch.FloatTensor).to(device)
    
    return X,Y,output_max,output_min,input_dim,input_max,input_min

def process_data1(input_rnn,output_rnn_p,output_rnn_l):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_dim = len(input_rnn[0,0,0,:])
    output_dim = len(output_rnn_p[0,0,0,:])
    
    input_max=np.zeros(input_dim)
    input_min=np.zeros(input_dim)
    input_rnn_norm=np.zeros(input_rnn.shape)
    for i in range(input_dim):
        input_max[i]=np.max(input_rnn[:,:,:,i])
        input_min[i]=np.min(input_rnn[:,:,:,i])
        input_rnn_norm[:,:,:,i] = (input_rnn[:,:,:,i]-input_min[i])/(input_max[i]-input_min[i])
        
    output_max_p=np.zeros(output_dim)
    output_min_p=np.zeros(output_dim)
    output_rnn_norm_p=np.zeros(output_rnn_p.shape)
    for i in range(output_dim):
        output_max_p[i]=np.max(output_rnn_p[:,:,:,i])
        output_min_p[i]=np.min(output_rnn_p[:,:,:,i])
        output_rnn_norm_p[:,:,:,i] = (output_rnn_p[:,:,:,i]-output_min_p[i])/(output_max_p[i]-output_min_p[i])

    output_max_l=np.zeros(output_dim)
    output_min_l=np.zeros(output_dim)
    output_rnn_norm_l=np.zeros(output_rnn_l.shape)
    for i in range(output_dim):
        output_max_l[i]=np.max(output_rnn_l[:,:,:,i])
        output_min_l[i]=np.min(output_rnn_l[:,:,:,i])
        output_rnn_norm_l[:,:,:,i] = (output_rnn_l[:,:,:,i]-output_min_l[i])/(output_max_l[i]-output_min_l[i])
        
    
    X=torch.tensor(input_rnn_norm).type(torch.FloatTensor).to(device)
    Yp=torch.tensor(output_rnn_norm_p).type(torch.FloatTensor).to(device)
    Yl=torch.tensor(output_rnn_norm_l).type(torch.FloatTensor).to(device)
    

    return X,Yp,Yl,output_max_p,output_min_p,output_max_l,output_min_l,input_dim,input_max,input_min

def process_data_cross(input_rnn,output_rnn,input_max,input_min,output_max,output_min):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_dim = len(input_rnn[0,0,0,:])
    output_dim = len(output_rnn[0,0,0,:])
    

    input_rnn_norm=np.zeros(input_rnn.shape)
    for i in range(input_dim):
        input_rnn_norm[:,:,:,i] = (input_rnn[:,:,:,i]-input_min[i])/(input_max[i]-input_min[i])    

    output_rnn_norm=np.zeros(output_rnn.shape)
    for i in range(output_dim):
        output_rnn_norm[:,:,:,i] = (output_rnn[:,:,:,i]-output_min[i])/(output_max[i]-output_min[i])
    
       
    X=torch.tensor(input_rnn_norm).type(torch.FloatTensor).to(device)
    Y=torch.tensor(output_rnn_norm).type(torch.FloatTensor).to(device)
      
    return X,Y

def process_data_norm(input_rnn,input_max,input_min):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    input_dim = len(input_rnn[0,0,0,:])

    input_rnn_norm=np.zeros(input_rnn.shape)
    for i in range(input_dim):
        input_rnn_norm[:,:,:,i] = (input_rnn[:,:,:,i]-input_min[i])/(input_max[i]-input_min[i])    
           
    X=torch.tensor(input_rnn_norm).type(torch.FloatTensor).to(device)     
    return X

def get_npy(house_num):
    
    if house_num <= 300:
        hn=300
    elif house_num <= 498:
        hn=498
    elif house_num <= 600:
        hn=600
    elif house_num <= 699:
        hn=699
    elif house_num <= 798:
        hn=798
    elif house_num <= 900:
        hn=900
    elif house_num <= 999:
        hn=999
    elif house_num <= 1098:
        hn=1098
    elif house_num <= 1200:
        hn=1200        
    elif house_num <= 1299:
        hn=1299
    else:
        hn=1500        
    return hn

def most_close_num(house_num):
    
    case=[300,498,600,699,798,900,999,1098,1200,1299,1500]
    temp_min = 1500
    for i in range(len(case)):
        diff = abs(house_num-case[i])
        if diff == 0:
            hn = house_num
            break
        elif diff < temp_min:
            temp_min = diff
            hn = case[i]
        else :
            pass           
    return hn

