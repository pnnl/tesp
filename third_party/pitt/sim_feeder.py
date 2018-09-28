# -*- coding: utf-8 -*-
"""
Created on Fri Aug 17 12:16:56 2018

@author: liub725
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 12:50:57 2018

@author: liub725
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 08:50:19 2018

@author: liub725
"""

import networkx as nx;
import re
import csv
import matplotlib.pyplot as plt
import os
import numpy as np
from numpy.linalg import inv
import cmath

def is_node_class(s):
    if s == 'node':
        return True
    if s == 'load':
        return True
    if s == 'meter':
        return True
    if s == 'triplex_node':
        return True
    if s == 'triplex_meter':
        return True
    return False

def is_edge_class(s):
    if s == 'switch':
        return True
    if s == 'fuse':
        return True
    if s == 'recloser':
        return True
    if s == 'regulator':
        return True
    if s == 'transformer':
        return True
    if s == 'overhead_line':
        return True
    if s == 'underground_line':
        return True
    if s == 'triplex_line':
        return True
    return False

def obj(parent,model,line,itr,oidh,octr):
    '''
    Store an object in the model structure
    Inputs:
        parent: name of parent object (used for nested object defs)
        model: dictionary model structure
        line: glm line containing the object definition
        itr: iterator over the list of lines
        oidh: hash of object id's to object names
        octr: object counter
    '''
    octr += 1
    # Identify the object type
    m = re.search('object ([^:{\s]+)[:{\s]',line,re.IGNORECASE)
    type = m.group(1)
    # If the object has an id number, store it
    n = re.search('object ([^:]+:[^{\s]+)',line,re.IGNORECASE)
    if n:
        oid = n.group(1)
    line = next(itr)
    # Collect parameters
    oend = 0
    oname = None
    params = {}
    if parent is not None:
        params['parent'] = parent
        # print('nested '+type)
    while not oend:
        m = re.match('\s*(\S+) ([^;{]+)[;{]',line)
        if m:
            # found a parameter
            param = m.group(1)
            val = m.group(2)
            intobj = 0
            if param == 'name':
                oname = val
            elif param == 'object':
                # found a nested object
                intobj += 1
                if oname is None:
                    print('ERROR: nested object defined before parent name')
                    quit()
                line,octr = obj(oname,model,line,itr,oidh,octr)
            elif re.match('object',val):
                # found an inline object
                intobj += 1
                line,octr = obj(None,model,line,itr,oidh,octr)
                params[param] = 'OBJECT_'+str(octr)
            else:
                params[param] = val
        if re.search('}',line):
            if intobj:
                intobj -= 1
                line = next(itr)
            else:
                oend = 1
        else:
            line = next(itr)
    # If undefined, use a default name
    if oname is None:
        oname = 'OBJECT_'+str(octr)
    oidh[oname] = oname
    # Hash an object identifier to the object name
    if n:
        oidh[oid] = oname
    # Add the object to the model
    if type not in model:
        # New object type
        model[type] = {}
    model[type][oname] = {}
    for param in params:
        model[type][oname][param] = params[param]
    # Return the 
    return line,octr




# %% get data from the full model  

def getV(model_name, simlistfile, V_datafile, new_Vdatafile):

    with open(V_datafile,'r') as f, open(new_Vdatafile,'w') as f1:
        next(f) # skip header line
        for line in f:
            f1.write(line)
    f2=open(new_Vdatafile, 'r')
    r=csv.DictReader(f2)
    node=[row['node_name'] for row in r]
    f2=open(new_Vdatafile, 'r')
    r1=csv.DictReader(f2)
    Va=dict(zip(node,[row['voltA_real'] for row in r1]))
    f2=open(new_Vdatafile, 'r')
    r2=csv.DictReader(f2)
    Vb=dict(zip(node,[row['voltB_real'] for row in r2]))
    f2=open(new_Vdatafile, 'r')
    r3=csv.DictReader(f2)
    Vc=dict(zip(node,[row['voltC_real'] for row in r3]))
    f2=open(new_Vdatafile, 'r')
    r4=csv.DictReader(f2)
    Vaimg=dict(zip(node,[row['voltA_imag'] for row in r4]))
    f2=open(new_Vdatafile, 'r')
    r5=csv.DictReader(f2)
    Vbimg=dict(zip(node,[row['voltB_imag'] for row in r5]))
    f2=open(new_Vdatafile, 'r')
    r6=csv.DictReader(f2)
    Vcimg=dict(zip(node,[row['voltC_imag'] for row in r6]))
    f2.close()
    # get the segment node from the nodelist file
    simlistkeys=['phase_name','i_node','f_node','junction','i_branch','f_branch','out_branch_1','out_branch_2','out_branch_3']
    global simlist
    with open (simlistfile,'r') as nodefile:            
        siminfo=nodefile.read().splitlines()
        siminfolist=[]
        for n in range(len(siminfo)):
            siminfolist.append(siminfo[n].split(','))
    # make a dict that contains the segment information
    simlist=[]
    for k in range(len(siminfolist)):
        simlist.append(dict(zip(simlistkeys,siminfolist[k])))    
    # read the voltage according to segment node
    global Via, Vib, Vic, Vfa, Vfb, Vfc
    Via=[]; Vib=[]; Vic=[]; Vfa=[]; Vfb=[]; Vfc=[]
    
    for n in range(len(simlist)):
    #    temp_node='R5-12-47-1_'+nodelist[n]['i_node']
        Via.append(complex(float(Va[model_name+'_node_'+simlist[n]['i_node']]),float(Vaimg[model_name+'_node_'+simlist[n]['i_node']])))
        Vib.append(complex(float(Vb[model_name+'_node_'+simlist[n]['i_node']]),float(Vbimg[model_name+'_node_'+simlist[n]['i_node']])))
        Vic.append(complex(float(Vc[model_name+'_node_'+simlist[n]['i_node']]),float(Vcimg[model_name+'_node_'+simlist[n]['i_node']])))
        Vfa.append(complex(float(Va[model_name+'_node_'+simlist[n]['f_node']]),float(Vaimg[model_name+'_node_'+simlist[n]['f_node']]))) 
        Vfb.append(complex(float(Vb[model_name+'_node_'+simlist[n]['f_node']]),float(Vbimg[model_name+'_node_'+simlist[n]['f_node']])))
        Vfc.append(complex(float(Vc[model_name+'_node_'+simlist[n]['f_node']]),float(Vcimg[model_name+'_node_'+simlist[n]['f_node']])))
        
def getV_sim(model_name, simlistfile, V_datafile, new_Vdatafile):

    with open(V_datafile,'r') as f, open(new_Vdatafile,'w') as f1:
        next(f) # skip header line
        for line in f:
            f1.write(line)
    f2=open(new_Vdatafile, 'r')
    r=csv.DictReader(f2)
    node=[row['node_name'] for row in r]
    f2=open(new_Vdatafile, 'r')
    r1=csv.DictReader(f2)
    Va=dict(zip(node,[row['voltA_real'] for row in r1]))
    f2=open(new_Vdatafile, 'r')
    r2=csv.DictReader(f2)
    Vb=dict(zip(node,[row['voltB_real'] for row in r2]))
    f2=open(new_Vdatafile, 'r')
    r3=csv.DictReader(f2)
    Vc=dict(zip(node,[row['voltC_real'] for row in r3]))
    f2=open(new_Vdatafile, 'r')
    r4=csv.DictReader(f2)
    Vaimg=dict(zip(node,[row['voltA_imag'] for row in r4]))
    f2=open(new_Vdatafile, 'r')
    r5=csv.DictReader(f2)
    Vbimg=dict(zip(node,[row['voltB_imag'] for row in r5]))
    f2=open(new_Vdatafile, 'r')
    r6=csv.DictReader(f2)
    Vcimg=dict(zip(node,[row['voltC_imag'] for row in r6]))
    f2.close()

    # read the voltage according to segment node
    global Vias, Vibs, Vics, Vfas, Vfbs, Vfcs
    Vias=[]; Vibs=[]; Vics=[]; Vfas=[]; Vfbs=[];  Vfcs=[]
    
    for n in range(len(simlist)):
    #    temp_node='R5-12-47-1_'+nodelist[n]['i_node']
        Vias.append(complex(float(Va[model_name+'_node_'+simlist[n]['i_node']]),float(Vaimg[model_name+'_node_'+simlist[n]['i_node']])))
        Vibs.append(complex(float(Vb[model_name+'_node_'+simlist[n]['i_node']]),float(Vbimg[model_name+'_node_'+simlist[n]['i_node']])))
        Vics.append(complex(float(Vc[model_name+'_node_'+simlist[n]['i_node']]),float(Vcimg[model_name+'_node_'+simlist[n]['i_node']])))
        Vfas.append(complex(float(Va[model_name+'_node_'+simlist[n]['f_node']]),float(Vaimg[model_name+'_node_'+simlist[n]['f_node']]))) 
        Vfbs.append(complex(float(Vb[model_name+'_node_'+simlist[n]['f_node']]),float(Vbimg[model_name+'_node_'+simlist[n]['f_node']])))
        Vfcs.append(complex(float(Vc[model_name+'_node_'+simlist[n]['f_node']]),float(Vcimg[model_name+'_node_'+simlist[n]['f_node']])))

#***********************************************************************************************************
# get current from the full model
def getI(model_name, linelistfile, I_datafile,new_I_datafile):

    with open(I_datafile,'r') as f, open(new_I_datafile,'w') as f1:
        next(f) # skip header line
        for line in f:
            f1.write(line)
    f2=open(new_I_datafile, 'r')
    r=csv.DictReader(f2)
    link=[row['link_name'] for row in r]
    f2=open(new_I_datafile, 'r')
    r1=csv.DictReader(f2)
    Ia=dict(zip(link,[row['currA_real'] for row in r1]))
    f2=open(new_I_datafile, 'r')
    r2=csv.DictReader(f2)
    Ib=dict(zip(link,[row['currB_real'] for row in r2]))
    f2=open(new_I_datafile, 'r')
    r3=csv.DictReader(f2)
    Ic=dict(zip(link,[row['currC_real'] for row in r3]))
    f2=open(new_I_datafile, 'r')
    r4=csv.DictReader(f2)
    Iaimg=dict(zip(link,[row['currA_imag'] for row in r4]))
    f2=open(new_I_datafile, 'r')
    r5=csv.DictReader(f2)
    Ibimg=dict(zip(link,[row['currB_imag'] for row in r5]))
    f2=open(new_I_datafile, 'r')
    r6=csv.DictReader(f2)
    Icimg=dict(zip(link,[row['currC_imag'] for row in r6]))
    f2.close()
    
    global Iia, Iib, Iic, Ifa, Ifb, Ifc
    Iia=[]; Iib=[]; Iic=[]; Ifa=[]; Ifb=[]; Ifc=[]
    
    for n in range(len(simlist)):
        Iia.append(complex(float(Ia[simlist[n]['i_branch']]),float(Iaimg[simlist[n]['i_branch']])))
        Iib.append(complex(float(Ib[simlist[n]['i_branch']]),float(Ibimg[simlist[n]['i_branch']])))
        Iic.append(complex(float(Ic[simlist[n]['i_branch']]),float(Icimg[simlist[n]['i_branch']])))
        Ifa.append(complex(float(Ia[simlist[n]['f_branch']]),float(Iaimg[simlist[n]['f_branch']]))) 
        Ifb.append(complex(float(Ib[simlist[n]['f_branch']]),float(Ibimg[simlist[n]['f_branch']])))
        Ifc.append(complex(float(Ic[simlist[n]['f_branch']]),float(Icimg[simlist[n]['f_branch']])))

#***********************************************************************************************************
# get current for junction load aggreggation
        
def getI_agg(model_name, simlistfile, I_datafile, new_I_datafile):
    with open(I_datafile,'r') as f, open(new_I_datafile,'w') as f1:
        next(f) # skip header line
        for line in f:
            f1.write(line)
    f2=open(new_I_datafile, 'r')
    r=csv.DictReader(f2)
    link=[row['link_name'] for row in r]
    f2=open(new_I_datafile, 'r')
    r1=csv.DictReader(f2)
    Ia=dict(zip(link,[row['currA_real'] for row in r1]))
    f2=open(new_I_datafile, 'r')
    r2=csv.DictReader(f2)
    Ib=dict(zip(link,[row['currB_real'] for row in r2]))
    f2=open(new_I_datafile, 'r')
    r3=csv.DictReader(f2)
    Ic=dict(zip(link,[row['currC_real'] for row in r3]))
    f2=open(new_I_datafile, 'r')
    r4=csv.DictReader(f2)
    Iaimg=dict(zip(link,[row['currA_imag'] for row in r4]))
    f2=open(new_I_datafile, 'r')
    r5=csv.DictReader(f2)
    Ibimg=dict(zip(link,[row['currB_imag'] for row in r5]))
    f2=open(new_I_datafile, 'r')
    r6=csv.DictReader(f2)
    Icimg=dict(zip(link,[row['currC_imag'] for row in r6]))
    f2.close()

    global IiaJ, IibJ, IicJ, IoaJ, IobJ, IocJ
    IiaJ=[]; IibJ=[]; IicJ=[]; IoaJ=[]; IobJ=[]; IocJ=[]
    
    for n in range(len(simlist)):
        if simlist[n]['out_branch_1']=='' and simlist[n]['out_branch_2']=='' and simlist[n]['out_branch_3']=='':
            IiaJ.append(complex(float(Ia[simlist[n]['f_branch']]),float(Iaimg[simlist[n]['f_branch']])))
            IibJ.append(complex(float(Ib[simlist[n]['f_branch']]),float(Ibimg[simlist[n]['f_branch']])))
            IicJ.append(complex(float(Ic[simlist[n]['f_branch']]),float(Icimg[simlist[n]['f_branch']])))
            IoaJ.append(complex(float(0),float(0))) 
            IobJ.append(complex(float(0),float(0))) 
            IocJ.append(complex(float(0),float(0))) 
        elif simlist[n]['out_branch_1']!='' and simlist[n]['out_branch_2']=='' and simlist[n]['out_branch_3']=='':
            IiaJ.append(complex(float(Ia[simlist[n]['f_branch']]),float(Iaimg[simlist[n]['f_branch']])))
            IibJ.append(complex(float(Ib[simlist[n]['f_branch']]),float(Ibimg[simlist[n]['f_branch']])))
            IicJ.append(complex(float(Ic[simlist[n]['f_branch']]),float(Icimg[simlist[n]['f_branch']])))
            IoaJ.append(complex(float(Ia[simlist[n]['out_branch_1']]),float(Iaimg[simlist[n]['out_branch_1']]))) 
            IobJ.append(complex(float(Ib[simlist[n]['out_branch_1']]),float(Ibimg[simlist[n]['out_branch_1']])))
            IocJ.append(complex(float(Ic[simlist[n]['out_branch_1']]),float(Icimg[simlist[n]['out_branch_1']])))
        elif simlist[n]['out_branch_1']!='' and simlist[n]['out_branch_2']!='' and simlist[n]['out_branch_3']=='':
            IiaJ.append(complex(float(Ia[simlist[n]['f_branch']]),float(Iaimg[simlist[n]['f_branch']])))
            IibJ.append(complex(float(Ib[simlist[n]['f_branch']]),float(Ibimg[simlist[n]['f_branch']])))
            IicJ.append(complex(float(Ic[simlist[n]['f_branch']]),float(Icimg[simlist[n]['f_branch']])))
            IoaJ.append(complex(float(Ia[simlist[n]['out_branch_1']]),float(Iaimg[simlist[n]['out_branch_1']]))+complex(float(Ia[simlist[n]['out_branch_2']]),float(Iaimg[simlist[n]['out_branch_2']]))) 
            IobJ.append(complex(float(Ib[simlist[n]['out_branch_1']]),float(Ibimg[simlist[n]['out_branch_1']]))+complex(float(Ib[simlist[n]['out_branch_2']]),float(Ibimg[simlist[n]['out_branch_2']])))
            IocJ.append(complex(float(Ic[simlist[n]['out_branch_1']]),float(Icimg[simlist[n]['out_branch_1']]))+complex(float(Ic[simlist[n]['out_branch_2']]),float(Icimg[simlist[n]['out_branch_2']])))
        elif simlist[n]['out_branch_1']!='' and simlist[n]['out_branch_2']!='' and simlist[n]['out_branch_3']!='':
            IiaJ.append(complex(float(Ia[simlist[n]['f_branch']]),float(Iaimg[simlist[n]['f_branch']])))
            IibJ.append(complex(float(Ib[simlist[n]['f_branch']]),float(Ibimg[simlist[n]['f_branch']])))
            IicJ.append(complex(float(Ic[simlist[n]['f_branch']]),float(Icimg[simlist[n]['f_branch']])))
            IoaJ.append(complex(float(Ia[simlist[n]['out_branch_1']]),float(Iaimg[simlist[n]['out_branch_1']]))+complex(float(Ia[simlist[n]['out_branch_2']]),float(Iaimg[simlist[n]['out_branch_2']]))+complex(float(Ia[simlist[n]['out_branch_3']]),float(Iaimg[simlist[n]['out_branch_3']]))) 
            IobJ.append(complex(float(Ib[simlist[n]['out_branch_1']]),float(Ibimg[simlist[n]['out_branch_1']]))+complex(float(Ib[simlist[n]['out_branch_2']]),float(Ibimg[simlist[n]['out_branch_2']]))+complex(float(Ib[simlist[n]['out_branch_3']]),float(Ibimg[simlist[n]['out_branch_3']])))
            IocJ.append(complex(float(Ic[simlist[n]['out_branch_1']]),float(Icimg[simlist[n]['out_branch_1']]))+complex(float(Ic[simlist[n]['out_branch_2']]),float(Icimg[simlist[n]['out_branch_2']]))+complex(float(Ic[simlist[n]['out_branch_3']]),float(Icimg[simlist[n]['out_branch_3']])))

#***********************************************************************************************************
# calculate impedance and load for simplified model
#%%
def calculate_Z_S():
    global Z, S, S_agg, dV, dV2, dI, dI2, Ii, Ii2, Zv, Zv2, S2, dIJ   
    #initiallize the arrays
    size=len(simlist)
    dV=np.empty((size,3,1),dtype=complex)
    dV2=np.empty((size,2,1),dtype=complex)      #variables for two phase segment need to be defined seperatly
    dI=np.empty((size,3,1),dtype=complex)
    dI2=np.empty((size,2,1),dtype=complex)
    Ii=np.empty((size,3,6),dtype=complex)
    Ii2=np.empty((size,2,3),dtype=complex)
    Zv=np.empty((size,6,1),dtype=complex)
    Zv2=np.empty((size,3,1),dtype=complex)
    Z=np.empty((size,3,3),dtype=complex)
    S=np.empty((size,3,1),dtype=complex)
    S2=np.empty((size,2,1),dtype=complex)
    dIJ=np.empty((size,3,1),dtype=complex)
    S_agg=np.empty((size,3,1),dtype=complex)
        
    for n in range(len(Via)):
        
        if simlist[n]['junction']=='junction':
            dIJ[n]=np.array([[IiaJ[n]-IoaJ[n]],[IibJ[n]-IobJ[n]],[IicJ[n]-IocJ[n]]])
            S_agg[n][0][0]=Vfa[n]*dIJ[n][0][0].conjugate()
            S_agg[n][1][0]=Vfb[n]*dIJ[n][1][0].conjugate()
            S_agg[n][2][0]=Vfc[n]*dIJ[n][2][0].conjugate()
        else:
            S_agg[n]=np.array([[0],[0],[0]]) 
        
        if simlist[n]['phase_name']=='ABC': # 3phase segment
            
            dV[n]=np.array([[Via[n]-Vfa[n]],[Vib[n]-Vfb[n]],[Vic[n]-Vfc[n]]])
            dI[n]=np.array([[Iia[n]-Ifa[n]],[Iib[n]-Ifb[n]],[Iic[n]-Ifc[n]]])
            
            Ii[n]=np.array([[Iia[n],Iib[n],Iic[n],0,0,0],[0,Iia[n],0,Iib[n],Iic[n],0],[0,0,Iia[n],0,Iib[n],Iic[n]]])
            Zv[n]=np.dot(np.dot(Ii[n].transpose().conjugate(),inv((np.dot(Ii[n],Ii[n].transpose().conjugate())))),dV[n])
            Z[n]=np.array([[Zv[n].item(0),Zv[n].item(1),Zv[n].item(2)],[Zv[n].item(1),Zv[n].item(3),Zv[n].item(4)],[Zv[n].item(2),Zv[n].item(4),Zv[n].item(5)]])
            if simlist[n]['i_branch']==simlist[n]['f_branch']:
                S[n]=np.array([[0],[0],[0]])
            else:
                S[n]=np.multiply(np.array([[Vfa[n]],[Vfb[n]],[Vfc[n]]]),dI[n].conjugate())
        elif simlist[n]['phase_name']=='AB':
        
            dV2[n]=np.array([[Via[n]-Vfa[n]],[Vib[n]-Vfb[n]]])
            dI2[n]=np.array([[Iia[n]-Ifa[n]],[Iib[n]-Ifb[n]]])
            
            Ii2[n]=np.array([[Iia[n],Iib[n],0],[0,Iia[n],Iib[n]]])
            Zv2[n]=np.dot(np.dot(Ii2[n].transpose().conjugate(),inv((np.dot(Ii2[n],Ii2[n].transpose().conjugate())))),dV2[n])
            Z[n]=np.array([[Zv2[n].item(0),Zv2[n].item(1),0],[Zv2[n].item(1),Zv2[n].item(2),0],[0,0,0]])
            S2[n]=np.multiply(np.array([[Vfa[n]],[Vfb[n]]]),dI2[n].conjugate())
            S[n]=np.array([[S2[n][0][0]],[S2[n][1][0]],[0]])
            if simlist[n]['i_branch']==simlist[n]['f_branch']:
                S[n]=np.array([[0],[0],[0]])
            else:
                S[n]=np.array([[S2[n][0][0]],[S2[n][1][0]],[0]])
        elif simlist[n]['phase_name']=='AC':
        
            dV2[n]=np.array([[Via[n]-Vfa[n]],[Vic[n]-Vfc[n]]])
            dI2[n]=np.array([[Iia[n]-Ifa[n]],[Iic[n]-Ifc[n]]])
            
            Ii2[n]=np.array([[Iia[n],Iic[n],0],[0,Iia[n],Iic[n]]])
            Zv2[n]=np.dot(np.dot(Ii2[n].transpose().conjugate(),inv((np.dot(Ii2[n],Ii2[n].transpose().conjugate())))),dV2[n])
            Z[n]=np.array([[Zv2[n].item(0),Zv2[n].item(1),0],[Zv2[n].item(1),Zv2[n].item(2),0],[0,0,0]])
            S2[n]=np.multiply(np.array([[Vfa[n]],[Vfc[n]]]),dI2[n].conjugate())
            if simlist[n]['i_branch']==simlist[n]['f_branch']:
                S[n]=np.array([[0],[0],[0]])
            else:
                S[n]=np.array([[S2[n][0][0]],[0],[S2[n][1][0]]])
        
        elif simlist[n]['phase_name']=='BC':
        
            dV2[n]=np.array([[Vib[n]-Vfb[n]],[Vic[n]-Vfc[n]]])
            dI2[n]=np.array([[Iib[n]-Ifb[n]],[Iic[n]-Ifc[n]]])
            
            Ii2[n]=np.array([[Iib[n],Iic[n],0],[0,Iib[n],Iic[n]]])
            Zv2[n]=np.dot(np.dot(Ii2[n].transpose().conjugate(),inv((np.dot(Ii2[n],Ii2[n].transpose().conjugate())))),dV2[n])
            Z[n]=np.array([[Zv2[n].item(0),Zv2[n].item(1),0],[Zv2[n].item(1),Zv2[n].item(2),0],[0,0,0]])
            S2[n]=np.multiply(np.array([[Vfb[n]],[Vfc[n]]]),dI2[n].conjugate())
            if simlist[n]['i_branch']==simlist[n]['f_branch']:
                S[n]=np.array([[0],[0],[0]])
            else:
                S[n]=np.array([[0],[S2[n][0][0]],[S2[n][1][0]]])
                
        elif simlist[n]['phase_name']=='A':
            
            dV[n]=np.array([[Via[n]-Vfa[n]],[0],[0]])
            dI[n]=np.array([[Iia[n]-Ifa[n]],[0],[0]])
            
            Z[n]=np.array([[np.dot(Via[n]-Vfa[n],(Iia[n])**(-1)),0,0],[0,0,0],[0,0,0]])
            if simlist[n]['i_branch']==simlist[n]['f_branch']:
                S[n]=np.array([[0],[0],[0]])
            else:
                S[n]=np.array([[np.multiply(Vfa[n],dI[n][0].conjugate())],[0],[0]])
        
        elif simlist[n]['phase_name']=='B':
        
            dV[n]=np.array([[0],[Vib[n]-Vfb[n]],[0]])
            dI[n]=np.array([[0],[Iib[n]-Ifb[n]],[0]])
            
            Z[n]=np.array([[0,0,0],[0,np.dot(Vib[n]-Vfb[n],(Iib[n])**(-1)),0],[0,0,0]])
            if simlist[n]['i_branch']==simlist[n]['f_branch']:
                S[n]=np.array([[0],[0],[0]])
            else:
                S[n]=np.array([[0],[np.multiply(Vfb[n],dI[n][1].conjugate())],[0]])
        
        elif simlist[n]['phase_name']=='C':
        
            dV[n]=np.array([[0],[0],[Vic[n]-Vfc[n]]])
            dI[n]=np.array([[0],[0],[Iic[n]-Ifc[n]]])
        
            Z[n]=np.array([[0,0,0],[0,0,0],[0,0,np.dot(Vic[n]-Vfc[n],(Iic[n])**(-1))]])
            if simlist[n]['i_branch']==simlist[n]['f_branch']:
                S[n]=np.array([[0],[0],[0]])
            else:
                S[n]=np.array([[0],[0],[np.multiply(Vfc[n],dI[n][2].conjugate())]])
                
#***********************************************************************************************************               
# %%write new gld model 
def CreateNode(modelname,seg_number,glmfile):
    f=open(glmfile,'a')
    f.write('object node {\n')
    f.write('	  name '+modelname+'_node_'+simlist[seg_number]['f_node']+';\n')
    f.write('     phases '+simlist[seg_number]['phase_name']+'N;\n')
    f.write('	  nominal_voltage '+str(v_base)+';\n')
    f.write('	    voltage_A '+va+';\n')
    f.write('	    voltage_B '+vb+';\n')
    f.write('	    voltage_C '+vc+';\n')
    f.write('    }\n')
    return
    
# create line configurations
def CreateLineConfig(seg_number,glmfile):
    f=open(glmfile,'a')
    if simlist[seg_number]['phase_name']=='ABC':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')  
        f.write('    z11 '+np.array2string(Z[seg_number][0][0])+';\n') 
        f.write('    z12 '+np.array2string(Z[seg_number][0][1])+';\n') 
        f.write('    z13 '+np.array2string(Z[seg_number][0][2])+';\n') 
        f.write('    z21 '+np.array2string(Z[seg_number][1][0])+';\n') 
        f.write('    z22 '+np.array2string(Z[seg_number][1][1])+';\n') 
        f.write('    z23 '+np.array2string(Z[seg_number][1][2])+';\n') 
        f.write('    z31 '+np.array2string(Z[seg_number][2][0])+';\n') 
        f.write('    z32 '+np.array2string(Z[seg_number][2][1])+';\n') 
        f.write('    z33 '+np.array2string(Z[seg_number][2][2])+';\n') 
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='AB':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')  
        f.write('    z11 '+np.array2string(Z[seg_number][0][0])+';\n') 
        f.write('    z12 '+np.array2string(Z[seg_number][0][1])+';\n') 
        f.write('    z21 '+np.array2string(Z[seg_number][1][0])+';\n') 
        f.write('    z22 '+np.array2string(Z[seg_number][1][1])+';\n')         
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='AC':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')  
        f.write('    z11 '+np.array2string(Z[seg_number][0][0])+';\n')         
        f.write('    z13 '+np.array2string(Z[seg_number][0][1])+';\n')         
        f.write('    z31 '+np.array2string(Z[seg_number][1][0])+';\n') 
        f.write('    z33 '+np.array2string(Z[seg_number][1][1])+';\n') 
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='BC':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')          
        f.write('    z22 '+np.array2string(Z[seg_number][0][0])+';\n') 
        f.write('    z23 '+np.array2string(Z[seg_number][0][1])+';\n') 
        f.write('    z32 '+np.array2string(Z[seg_number][1][0])+';\n') 
        f.write('    z33 '+np.array2string(Z[seg_number][1][1])+';\n') 
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='A':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')  
        f.write('    z11 '+np.array2string(Z[seg_number][0][0])+';\n') 
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='B':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')  
        f.write('    z22 '+np.array2string(Z[seg_number][1][1])+';\n') 
        f.write('    }\n')        
    elif simlist[seg_number]['phase_name']=='C':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')  
        f.write('    z33 '+np.array2string(Z[seg_number][2][2])+';\n') 
        f.write('    }\n')
    return

# Create lines
def CreateLine(model_name,seg_number,glmfile):
    f=open(glmfile,'a')
    f.write('object overhead_line {\n')    
    f.write('    name line_seg_'+str(seg_number)+';\n') 
    if simlist[seg_number]['phase_name']=='ABC':
        f.write('	 phases ABC;\n')
    elif simlist[seg_number]['phase_name']=='A':
        f.write('    phases A;\n')
    elif simlist[seg_number]['phase_name']=='B':
        f.write('    phases B;\n')
    elif simlist[seg_number]['phase_name']=='C':
        f.write('    phases C;\n')
    elif simlist[seg_number]['phase_name']=='AB':
        f.write('    phases AB;\n')
    elif simlist[seg_number]['phase_name']=='AC':
        f.write('    phases AC;\n')
    elif simlist[seg_number]['phase_name']=='BC':
        f.write('    phases BC;\n')
    f.write('    from '+model_name+'_node_'+simlist[seg_number]['i_node']+';\n') 
    f.write('    to '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
    f.write('	 length 5280 ft;\n')
    f.write('	 configuration line_config_seg_'+str(seg_number)+';\n')
    f.write('    }\n')
    return

# Creat Meters to attached the loads    
def CreateMeter(model_name,seg_number,glmfile):
    f=open(glmfile,'a')
    f.write('object meter {\n')
    f.write('    name meter_seg_'+str(seg_number)+';\n')
    f.write('    parent '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
    f.write('    }\n')
    return
      
# Create loads   
def CreateLoad(model_name,seg_number,glmfile):
    f=open(glmfile,'a')
    if simlist[seg_number]['phase_name']=='ABC':
        f.write('object load {\n')
        f.write('   parent '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
        f.write('   name load_seg_'+str(seg_number)+';\n')
        f.write('   phases ABCN;\n')
        f.write('   nominal_voltage 7970.0;\n')        # can't specefy voltage for different phases 
        f.write('   load_class U;\n')
        f.write('   constant_power_A '+np.array2string(S[seg_number][0][0])+';\n')
        f.write('   constant_power_B '+np.array2string(S[seg_number][1][0])+';\n')
        f.write('   constant_power_C '+np.array2string(S[seg_number][2][0])+';\n')
        f.write('	    voltage_A 7970.0+0.0j;\n')
        f.write('	    voltage_B -3985.00-6902.22j;\n')
        f.write('	    voltage_C -3985.00+6902.22j;\n')
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='AB':
        f.write('object load {\n')
        f.write('   parent '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
        f.write('   name load_seg_'+str(seg_number)+';\n')
        f.write('   phases ABN;\n')
        f.write('   nominal_voltage 7970.0;\n')        # can't specefy voltage for different phases 
        f.write('   load_class U;\n')
        f.write('   constant_power_A '+np.array2string(S[seg_number][0][0])+';\n')
        f.write('   constant_power_B '+np.array2string(S[seg_number][1][0])+';\n')
        f.write('	    voltage_A 7970.0+0.0j;\n')
        f.write('	    voltage_B -3985.00-6902.22j;\n')
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='AC':
        f.write('object load {\n')
        f.write('   parent '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
        f.write('   name load_seg_'+str(seg_number)+';\n')
        f.write('   phases ACN;\n')
        f.write('   nominal_voltage 7970.0;\n')        # can't specefy voltage for different phases
        f.write('   load_class U;\n')
        f.write('   constant_power_A '+np.array2string(S[seg_number][0][0])+';\n')
        f.write('   constant_power_C '+np.array2string(S[seg_number][2][0])+';\n')
        f.write('	    voltage_A 7970.0+0.0j;\n')
        f.write('	    voltage_C -3985.00+6902.22j;\n')
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='BC':
        f.write('object load {\n')
        f.write('   parent '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
        f.write('   name load_seg_'+str(seg_number)+';\n')
        f.write('   phases BCN;\n')
        f.write('   nominal_voltage 7970.0;\n')        # can't specefy voltage for different phases 
        f.write('   load_class U;\n')
        f.write('   constant_power_B '+np.array2string(S[seg_number][1][0])+';\n')
        f.write('   constant_power_C '+np.array2string(S[seg_number][2][0])+';\n')
        f.write('	    voltage_B -3985.00-6902.22j;\n')
        f.write('	    voltage_C -3985.00+6902.22j;\n')
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='A':
        f.write('object load {\n')
        f.write('   parent '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
        f.write('   name load_seg_'+str(seg_number)+';\n')
        f.write('	   phases AN;\n')
        f.write('   nominal_voltage 7970.0;\n')        # can't specefy voltage for different phases
        f.write('   load_class U;\n')
        f.write('	   constant_power_A '+np.array2string(S[seg_number][0][0])+';\n')
        f.write('	    voltage_A 7970.0+0.0j;\n')
        f.write('	    voltage_B -3985.00-6902.22j;\n')
        f.write('	    voltage_C -3985.00+6902.22j;\n')
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='B':
        f.write('object load {\n')
        f.write('   parent '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
        f.write('   name load_seg_'+str(seg_number)+';\n')
        f.write('	   phases BN;\n')
        f.write('   nominal_voltage 7970.0;\n')        # can't specefy voltage for different phases 
        f.write('   load_class U;\n')
        f.write('	   constant_power_B '+np.array2string(S[seg_number][1][0])+';\n')
        f.write('	    voltage_B -3985.00-6902.22j;\n')
        f.write('    }\n')
    elif simlist[seg_number]['phase_name']=='C':
        f.write('object load {\n')
        f.write('   parent '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
        f.write('   name load_seg_'+str(seg_number)+';\n')
        f.write('	   phases CN;\n')
        f.write('   nominal_voltage 7970.0;\n')        # can't specefy voltage for different phases 
        f.write('   load_class U;\n')
        f.write('	   constant_power_C '+np.array2string(S[seg_number][2][0])+';\n')
        f.write('	    voltage_C -3985.00+6902.22j;\n')
        f.write('    }\n')
    return

def CreateLoad_agg(model_name,seg_number,glmfile):
    f=open(glmfile,'a')
    if simlist[seg_number]['junction']=='junction':
        f.write('object load {\n')
        f.write('   parent '+model_name+'_node_'+simlist[seg_number]['f_node']+';\n')
        f.write('   name load_junction_seg_'+str(seg_number)+';\n')
        f.write('   phases '+simlist[seg_number]['phase_name']+'N;\n')
        f.write('   nominal_voltage 7970.0;\n')        # can't specefy voltage for different phases 
        f.write('   load_class U;\n')
        f.write('   constant_power_A '+np.array2string(S_agg[seg_number][0][0])+';\n')
        f.write('   constant_power_B '+np.array2string(S_agg[seg_number][1][0])+';\n')
        f.write('   constant_power_C '+np.array2string(S_agg[seg_number][2][0])+';\n') 
        f.write('	    voltage_A 7970.0+0.0j;\n')
        f.write('	    voltage_B -3985.00-6902.22j;\n')
        f.write('	    voltage_C -3985.00+6902.22j;\n')
        f.write('    }\n')
    return

#*********************************************
def CreateHeader(glmfile,modelname,swingbus,v_base,v1,v2,v3,reg_band_center,reg_band_width):
    f=open(glmfile,'a')
    f.write('//********************************\n')
    f.write('//Simplified feeder model\n')
#    f.write('// created by: Boming Liu\n')
    f.write('//\n')
    f.write('\n')
    f.write('clock{\n')
    f.write("   timezone EST+5EDT;\n")
    f.write("	timestamp '2000-01-01 0:00:00';\n")
    f.write("	stoptime '2000-01-01 1:00:00';\n")
    f.write("}\n")
    f.write("#set profiler=1\n\n")
    #create the module section
    f.write("\n")  
    f.write('module tape;\n')
    f.write('module powerflow{\n')
    f.write("	solver_method NR;\n")
    f.write("	default_maximum_voltage_error 1e-6;\n};\n\n")
    
    #swing bus node define
    f.write('object node {\n')
    f.write('    name '+modelname+'_node_'+swingbus+';\n')
    f.write('    phases ABCN;\n')
    f.write('	    nominal_voltage '+v_base+';\n')
    f.write('    bustype SWING;\n')
    f.write('	    voltage_A '+v1+';\n')
    f.write('	    voltage_B '+v2+';\n')
    f.write('	    voltage_C '+v3+';\n')
    f.write('    }\n')
    
    f.write('object regulator_configuration {\n')
    f.write('	   name feeder_reg_cfg;\n')
    f.write('    Control OUTPUT_VOLTAGE;\n')
    f.write('	    band_center '+reg_band_center+';\n')
    f.write('	    band_width '+reg_band_width+';\n')
    f.write('	    connect_type WYE_WYE;\n')
    f.write('	    time_delay 30;\n')
    f.write('	    raise_taps 16;\n')
    f.write('	    lower_taps 16;\n')
    f.write('	    regulation 0.10;\n')
    f.write('	    tap_pos_A 0;\n')
    f.write('	    tap_pos_B 0;\n')
    f.write('	    tap_pos_C 0;\n')
    f.write('    }\n')
    
    
    f.write('object meter {\n')
    f.write('	   name '+modelname+'_meter_head;\n')
    f.write('    phases ABCN;\n')
    f.write('	    nominal_voltage '+v_base+';\n')
    f.write('	    voltage_A '+v1+';\n')
    f.write('	    voltage_B '+v2+';\n')
    f.write('	    voltage_C '+v3+';\n')
    f.write('    }\n')
    
    f.write('object regulator {\n')
    f.write('	   name feeder_reg_1;\n')
    f.write('    from '+modelname+'_node_'+swingbus+';\n')
    f.write('	    to '+modelname+'_meter_head;\n')
    f.write('	    phases ABCN;\n')
    f.write('	    configuration feeder_reg_cfg;\n')
    f.write('    }\n')

    # bus node
    f.write('object node {\n')
    f.write('	   parent '+modelname+'_meter_head;\n')
    f.write('    name '+modelname+'_node_'+simlist[0]['i_node']+';\n')
    f.write('    phases ABCN;\n')
    f.write('	    nominal_voltage '+v_base+';\n')
    f.write('	    voltage_A '+v1+';\n')
    f.write('	    voltage_B '+v2+';\n')
    f.write('	    voltage_C '+v3+';\n')
    f.write('    }\n')
#create voltdump objects
#*********************************************
def CreateVoltdump(glmfile,outputfileName1):
    f=open(glmfile,'a')
    f.write("object voltdump {\n")
    f.write("	filename "+outputfileName1+";\n")
    f.write("}\n\n")
#    f=open(glmfile,'a')
#    f.write("object voltdump {\n")
#    f.write("	filename "+outputfileName2+";\n")
#    f.write('mode polar;\n')
#    f.write("}\n\n")
    return
#******************************************
#create voltdump objects
#*********************************************
def CreateCurrdump(glmfile,outputfileName,):
    f=open(glmfile,'a')
    f.write("object currdump {\n")
    f.write("	filename "+outputfileName+";\n")
    f.write("}\n\n")
    return
def errorplot(baseV):
    global errora
    global errorb
    global errorc 
    global errormean
    errora=[]
    errorb=[]
    errorc=[]
    for n in range(len(Vfa)):
        if Vfas[n]!=0j:      
            errora.append(abs((abs(Vfa[n])-abs(Vfas[n])))/baseV*100)
        else:            
            n=n+1
    for n in range(len(Vfb)):
        if Vfbs[n]!=0j:      
            errorb.append(abs((abs(Vfb[n])-abs(Vfbs[n])))/baseV*100)
        else:            
            n=n+1
    for n in range(len(Vfc)):
        if Vfcs[n]!=0j:      
            errorc.append(abs((abs(Vfc[n])-abs(Vfcs[n])))/baseV*100)
        else:            
            n=n+1
    errormean=errora+errorb+errorc
    errormean=np.mean(errormean)
    indexa = np.arange(len(errora))
    indexb = np.arange(len(errorb))
    indexc = np.arange(len(errorc))
    plt.subplot(311)
    plt.bar(indexc,errorc,0.3,color='r',align="center")
    plt.title('Phase A error')
    plt.ylabel('V Error [p.u.]')
    plt.subplots_adjust(hspace=0.5)
    plt.subplot(312)
    plt.bar(indexa,errora,0.3,color='b',align="center")
    plt.title('Phase B error')
    plt.ylabel('V Error [p.u.]')
    plt.subplot(313)
    plt.bar(indexb,errorb,0.3,color='g',align="center")
    plt.title('Phase C error')
    plt.ylabel('V Error [p.u.]')
    plt.show()
    return



#%% begin to simplify feeder model
def _tests():
    tax       = [['R1-12.47-1',12470.0, 7200.0, 4000.0, 20000.0],
                 ['R1-12.47-2',12470.0, 7200.0, 4500.0, 30000.0],
                 ['R1-12.47-3',12470.0, 7200.0, 8000.0, 15000.0],
                 ['R1-12.47-4',12470.0, 7200.0, 4000.0, 15000.0],
                 ['R1-25.00-1',24900.0,14400.0, 6000.0, 25000.0],
                 ['R2-12.47-1',12470.0, 7200.0, 7000.0, 20000.0],
                 ['R2-12.47-2',12470.0, 7200.0,15000.0, 25000.0],
                 ['R2-12.47-3',12470.0, 7200.0, 5000.0, 30000.0],
                 ['R2-25.00-1',24900.0,14400.0, 6000.0, 15000.0],
                 ['R2-35.00-1',34500.0,19920.0,15000.0, 30000.0],
                 ['R3-12.47-1',12470.0, 7200.0,12000.0, 40000.0],
                 ['R3-12.47-2',12470.0, 7200.0,14000.0, 30000.0],
                 ['R3-12.47-3',12470.0, 7200.0, 7000.0, 15000.0],
                 ['R4-12.47-1',13800.0, 7970.0, 9000.0, 30000.0],
                 ['R4-12.47-2',12470.0, 7200.0, 6000.0, 20000.0],
                 ['R4-25.00-1',24900.0,14400.0, 6000.0, 20000.0],
                 ['R5-12.47-1',13800.0, 7970.0, 6500.0, 20000.0,'266','8300','132'], #16
                 ['R5-12.47-2',12470.0, 7200.0, 4500.0, 15000.0,'317','7500','120'], #17
                 ['R5-12.47-3',13800.0, 7970.0, 4000.0, 15000.0],  # rural
                 ['R5-12.47-4',12470.0, 7200.0, 6000.0, 30000.0,'675','7500','60'], #19
                 ['R5-12.47-5',12470.0, 7200.0, 4500.0, 25000.0,'1100','7500','60'], #20
                 ['R5-25.00-1',22900.0,13200.0, 3000.0, 20000.0,'953','13773','220'],
                 ['R5-35.00-1',34500.0,19920.0, 6000.0, 25000.0,'339','20748','332'],
                 ['GC-12.47-1',12470.0, 7200.0, 8000.0, 13000.0]]
   
#   index of feeder model   16,17,19,20 is avaliable
    k=16
    fname='new_'+tax[k][0]+'.glm' 
    mname=tax[k][0].replace('.','-')
    sim_fname='sim_'+tax[k][0]+'.glm'
    #caluculate Vbase
    global va, vb, vc, v_base
    v_base=tax[k][2]
    va1,va2=cmath.polar(v_base); va=cmath.rect(va1,va2)
    va1,va2=cmath.polar(v_base); vb=cmath.rect(va1,-2.094395257234013)
    va1,va2=cmath.polar(v_base); vc=cmath.rect(va1,2.094395257234013)
    v_base=str(v_base)

    va=str(va).replace('(',''); va=va.replace(')','');
    vb=str(vb).replace('(',''); vb=vb.replace(')','');
    vc=str(vc).replace('(',''); vc=vc.replace(')','');
    
    
    CreateVoltdump(fname,mname+'_voltage.csv')
    CreateCurrdump(fname,mname+'_current.csv')
    
    os.system('gridlabd '+fname)
    if os.path.exists('sim_'+tax[k][0]+'.glm'):
        os.remove('sim_'+tax[k][0]+'.glm')

   
    # read the model
    ip = open (fname, 'r')
    lines = []
    line = ip.readline()
    while line is not '':
        while re.match('\s*//',line) or re.match('\s+$',line):
            # skip comments and white space
            line = ip.readline()
        lines.append(line.rstrip())
        line = ip.readline()
    ip.close()
    
    octr = 0;
    model = {}
    h = {}		# OID hash
    itr = iter(lines)
    for line in itr:
        if re.search('object',line):
            line,octr = obj(None,model,line,itr,h,octr)
    
    # construct a graph of the model, starting with known links
    G = nx.Graph()
    for t in model:
        if is_edge_class(t):
            for o in model[t]:
                n1 = model[t][o]['from']
                n2 = model[t][o]['to']
                G.add_edge(n1,n2,eclass=t,ename=o,edata=model[t][o])
    
    # add the parent-child node links
    for t in model:
        if is_node_class(t):
            for o in model[t]:
                if 'parent' in model[t][o]:
                    p = model[t][o]['parent']
                    G.add_edge(o,p,eclass='parent',ename=o,edata={})
    
    # now we backfill node attributes
    for t in model:
        if is_node_class(t):
            for o in model[t]:
                if o in G.nodes():
                    G.nodes()[o]['nclass'] = t
                    G.nodes()[o]['ndata'] = model[t][o]
                else:
                    print('orphaned node', t, o)
    
#    swing_node = ''
#    for n1, data in G.nodes(data=True):
#        if 'nclass' in data:
#            if 'bustype' in data['ndata']:
#                if data['ndata']['bustype'] == 'SWING':
#                    swing_node = n1   


    getV(mname,mname+'_sim_list.csv',mname+'_voltage.csv',mname+'_voltage1.csv')
    
    
    # creat the list with given node : get branch name by networkx 
    i_branch=[]
    f_branch=[]
    segment_node=[]
    for n in range(len(simlist)): 
        segment_node=nx.shortest_path(G, source=mname+'_node_'+simlist[n]['i_node'], target=mname+'_node_'+simlist[n]['f_node'])
        i_branch.append(G.edges[segment_node[0],segment_node[1]]['ename'])
        f_branch.append(G.edges[segment_node[-2],segment_node[-1]]['ename'])
    for n in range(len(simlist)):    
        simlist[n]['i_branch']=i_branch[n]
        simlist[n]['f_branch']=f_branch[n]
    
    
    
    for n in range(len(simlist)): 
        if simlist[n]['junction']=='junction':
            count=-1
            junction_outbranch=['','','']
            for m in range(len(simlist)):
                if simlist[m]['i_node']==simlist[n]['f_node']:
                    count+=1
                    junction_outbranch[count]=(simlist[m]['i_branch'])
                simlist[n]['out_branch_1']=junction_outbranch[0]
                simlist[n]['out_branch_2']=junction_outbranch[1]
                simlist[n]['out_branch_3']=junction_outbranch[2]    
        else:
            junction_outbranch=['','','']
            simlist[n]['out_branch_1']=junction_outbranch[0]
            simlist[n]['out_branch_2']=junction_outbranch[1]
            simlist[n]['out_branch_3']=junction_outbranch[2]    
    
    #
    getI(mname,mname+'_sim_list.csv',mname+'_current.csv',mname+'_current1.csv')
    getI_agg(mname,mname+'_sim_list.csv',mname+'_current.csv',mname+'_current1.csv')
    calculate_Z_S()
    
    CreateHeader(sim_fname,mname,tax[k][5],v_base,va,vb,vc,tax[k][6],tax[k][7])
    for n in range(len(simlist)):
         CreateNode(mname,n,sim_fname)
    for n in range(len(simlist)):
         CreateLineConfig(n,sim_fname)
    for n in range(len(simlist)):        
        CreateLine(mname,n,sim_fname)
#    for n in range(len(nodelist)):        
#        CreateMeter('R5-12-47-1',n,'R5_s1.glm')
    for n in range(len(simlist)):        
        CreateLoad(mname,n,sim_fname)
    for n in range(len(simlist)):  
        CreateLoad_agg(mname,n,sim_fname)
    CreateVoltdump(sim_fname,mname+'_node_voltage_sim.csv')
    CreateCurrdump(sim_fname,mname+'_branch_current_sim.csv')
# run the simplified feeder model
    os.system('gridlabd '+sim_fname)
    getV_sim(mname,mname+'_sim_list.csv',mname+'_node_voltage_sim.csv',mname+'_node_voltage_sim1.csv')
    errorplot(7970)
    print()
    print()
    print()
    print()
    print('Reduced order model of '+fname+' is written in '+sim_fname)
    print('Average error is '+str(errormean))

    
if __name__ == '__main__':
    _tests()
    

