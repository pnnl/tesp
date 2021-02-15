# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 18:28:40 2020

@author: liubo
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class RNN(nn.Module):
    def __init__(self,input_size,hidden_size,output_size):
        super(RNN, self).__init__()

        self.rnn = nn.LSTM(    
            input_size,      
            hidden_size,    
            num_layers=3,       
            batch_first=True,   #   e.g. (batch, time_step, input_size)
        )
        self.out = nn.Linear(hidden_size, output_size)    

    def forward(self, x):
        
        r_out, (h_n, h_c) = self.rnn(x, None)   
        out = self.out(r_out).to(device)
#        return out
        return torch.sigmoid(out)
#    
class RNNl(nn.Module):
    def __init__(self,input_size,hidden_size,output_size):
        super(RNNl, self).__init__()

        self.rnn = nn.LSTM(     
            input_size,      
            hidden_size,     
            num_layers=3,       
            batch_first=True,  
        )
#        self.ln = nn.LayerNorm([288,1]) #shijian
#        self.bn = nn.BatchNorm1d(288) #batch
        self.out = nn.Linear(hidden_size, output_size)   

    def forward(self, x):

        r_out, (h_n, h_c) = self.rnn(x, None)  
        out = self.out(r_out).to(device)

        return torch.sigmoid(out)
    
#class RNNs(nn.Module):
#    def __init__(self,input_size,hidden_size,output_size):
#        super(RNNs, self).__init__()
#
#        self.rnn = nn.LSTM(     
#            input_size,      
#            hidden_size,     
#            num_layers=3,       
#            batch_first=True,   
#        )
#        self.out = nn.Linear(hidden_size, output_size)   
#
#    def forward(self, x):
#        
#        r_out, (h_n, h_c) = self.rnn(x, None)   
#        out = self.out(r_out).to(device)
#        return F.sigmoid(out)