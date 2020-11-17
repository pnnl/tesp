# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 19:43:37 2020

@author: liubo

"""
import torch
import numpy as np
from process_input_data import process_data_norm

class arl:
    '''
    Aggregate responsive load (ARL) agent
    Attributes：
    	(1) house_number : The number of hvac to be aggragted
    	(2) Bid RNN
    	(3) Response RNN
        
    Functions:
    1) Formulate bid RNN     
        Input：RNN input features (temp_rnn,schedule_rnn,limit_rnn,ramp_rnn,Hm_rnn,Ca_rnn,Cm_rnn,Ua_rnn) 
        historical input features    
        Output: bids 
    
    2) Response to the clearing price (adjust the aggregated load)       
        Input：RNN input features (price_rnn,temp_rnn,schedule_rnn,limit_rnn,ramp_rnn,Hm_rnn,Ca_rnn,Cm_rnn,Ua_rnn,tint_rnn,sqft_rnn) 
        Output: aggregate load 
    
    3) obtain clearing price
    
    4) set aggregated load
            
    Steps:
        arl agent formulated bid   submit to the auction
        obtain a cleared price from market               
        arl set the aggregated load 
           
    '''   

    def __init__(self,house_num,rnn1,rnn2,aucObj,hn):
        """Initializes the class
        """
        self.house_number = house_num
        self.bid_RNN = rnn1
        self.response_RNN = rnn2
        self.res_load = 0
        self.unres_load = 0
        self.agg_resp_max = 0    
        self.states = np.zeros(self.house_number)
        self.bid_q = np.zeros(self.house_number)
        self.bid_q.fill(0.5)
        self.chunk_num = 6
        self.std_dev = aucObj.std_dev
        self.mean = aucObj.clearing_price
        self.cleared_price = 0.019413
        self.day = 6
        self.step = 288
        self.input_num = 13
        self.max_num = 1500
        
        self.inputs = np.zeros((self.house_number,self.day,self.step,self.input_num))
        self.inputs[:,:,:,1] = np.tile(np.load('input\\inputs.npy',allow_pickle=True).item().get('temp'),(self.house_number,1,1))
        self.inputs[:,:,:,2] = np.load('input\\inputs.npy',allow_pickle=True).item().get('schedule')[:self.house_number]
        self.inputs[:,:,:,3] = np.tile(np.load('input\\inputs.npy',allow_pickle=True).item().get('limit').reshape(self.max_num,1,1),(1,self.day,self.step))[:self.house_number]
        self.inputs[:,:,:,4] = np.tile(np.load('input\\inputs.npy',allow_pickle=True).item().get('ramp').reshape(self.max_num,1,1),(1,self.day,self.step))[:self.house_number]
        self.inputs[:,:,:,5] = np.tile(np.load('input\\inputs.npy',allow_pickle=True).item().get('Hm').reshape(self.max_num,1,1),(1,self.day,self.step))[:self.house_number]     
        self.inputs[:,:,:,6] = np.tile(np.load('input\\inputs.npy',allow_pickle=True).item().get('Ca').reshape(self.max_num,1,1),(1,self.day,self.step))[:self.house_number]
        self.inputs[:,:,:,7] = np.tile(np.load('input\\inputs.npy',allow_pickle=True).item().get('Cm').reshape(self.max_num,1,1),(1,self.day,self.step))[:self.house_number]
        self.inputs[:,:,:,8] = np.tile(np.load('input\\inputs.npy',allow_pickle=True).item().get('Ua').reshape(self.max_num,1,1),(1,self.day,self.step))[:self.house_number]
        self.inputs[:,:,:,9] = np.full((self.house_number,self.day,self.step), self.house_number)
        self.inputs[:,:,:,10] = np.load('input\\inputs.npy',allow_pickle=True).item().get('p')[:self.house_number]
        self.inputs[:,:,:,11] = np.load('input\\inputs.npy',allow_pickle=True).item().get('h')[:self.house_number]
        self.inputs[:,:,:,12] = np.tile(np.load('input\\inputs.npy',allow_pickle=True).item().get('sqft').reshape(self.max_num,1,1),(1,self.day,self.step))[:self.house_number]
        
        self.unresponsive_load = (np.load('input\\aul.npy',allow_pickle=True).item().get(str(hn)))*(self.house_number/hn)   
        self.rnn_q=np.load('input\\rnn_q.npy',allow_pickle=True).item().get(str(hn))
        self.agg_un_tesp=self.unresponsive_load.reshape(self.day,self.step)
        self.unres_load_list = self.unresponsive_load     
        
        self.Y_bid_max = np.load('input\\minmax.npy',allow_pickle=True).item().get('outp_max')
        self.Y_bid_min = np.load('input\\minmax.npy',allow_pickle=True).item().get('outp_min')
        self.X_response_max = np.load('input\\minmax.npy',allow_pickle=True).item().get('inl_max')
        self.X_response_min = np.load('input\\minmax.npy',allow_pickle=True).item().get('inl_min')
        self.Y_response_max = np.load('input\\minmax.npy',allow_pickle=True).item().get('outl_max')
        self.Y_response_min = np.load('input\\minmax.npy',allow_pickle=True).item().get('outl_min')
        self.input_max = np.load('input\\input_max.npy')
        self.input_min = np.load('input\\input_min.npy')
           
        self.inputs_norm = process_data_norm(self.inputs,self.input_max,self.input_min)
        
    def inform_bid (self,price):
        """ Set the cleared_price attribute
        """
        self.cleared_price = price

#    def generate_bids(self,day,t,input_tensor,input_dim):
#        
#        input_tensor_day=input_tensor[:,day,0:t+1,:]
#        chunks= torch.chunk(input_tensor_day,self.chunk_num, dim=0)
#        out = np.zeros((self.chunk_num,(len(chunks[0])),2))
#        for k in range(self.chunk_num):
#            out[k,:len(chunks[k]),:] = self.bid_RNN(chunks[k][:,0:t+1,:])[:,t,:].cpu().detach().numpy()
#            
#        bid_pq_list=out.reshape(self.chunk_num*len(chunks[0]),2)[0:len(input_tensor),:]
#        bid_p_list=bid_pq_list[:,0]
#        bid_q_list=bid_pq_list[:,1]       
#        state= self.states
#        
#        return np.array([bid_p_list,bid_q_list,state])    

            
    def generate_bidsps(self,day,t):
      
        input_tensor_day=self.inputs_norm[:,day,0:t+1,1:11]
        chunks= torch.chunk(input_tensor_day,self.chunk_num, dim=0)
        outp = np.zeros((self.chunk_num,len(chunks[0])))

        for k in range(self.chunk_num):
            outp[k,:len(chunks[k])] = self.bid_RNN(chunks[k][:,0:t+1,:10])[:,t,0].cpu().detach().numpy()
            
        bid_p_list=outp.reshape(self.chunk_num*len(chunks[0]))[0:self.house_number]
#        bid_q_list=self.rnn_q[:self.house_number,day,t].ravel()
        bid_q_list=np.full((self.house_number,),self.rnn_q[day,t])
        state_list=self.states
        
        return np.array([bid_p_list,bid_q_list,state_list])  

    def set_hvac_load(self,day,t):
        
        input_tensor_day=self.inputs_norm[:,day,0:t+1,[0,1,2,3,4,5,6,7,8,12,9,11]]
        chunks= torch.chunk(input_tensor_day,self.chunk_num, dim=0)
        out = np.zeros((self.chunk_num,(len(chunks[0]))))
        for k in range(self.chunk_num):
            out[k,:len(chunks[k])] = self.response_RNN(chunks[k][:,0:t+1,:])[:,t,0].cpu().detach().numpy()

        load_list=out.reshape(self.chunk_num*len(chunks[0]))[0:self.house_number]   

        aggregate_load = np.sum(load_list)*self.Y_response_max            
        self.res_load = aggregate_load   
        
        for n in range(self.house_number):
            if load_list[n] > 0.25 : 
                self.states[n] = 1
            else:
                self.states[n] = 0                
                
        return load_list
    
    def update_unresposive_load(self,day,t):
    
        unres_t=self.unres_load_list[self.step*day+t]-150
        self.unres_load = unres_t
        












