# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 08:50:19 2018

@author: liub725
"""

import networkx as nx
import re
import csv
import matplotlib.pyplot as plt
import os
import subprocess
import numpy as np
from numpy.linalg import inv
import cmath
import math

'''
switch line 68 to line 69 for feeder #16 #17 #19 #20
'''


min_load_size = 10.0

# GridLAB-D name should not begin with a number, or contain '-' for FNCS
def gld_strict_name(val):
    """Sanitizes a name for GridLAB-D publication to FNCS

    Args:
        val (str): the input name

    Returns:
        str: val with all '-' replaced by '_', and any leading digit replaced by 'gld\_'
    """
    if val[0].isdigit():
        val = 'gld_' + val
    return val.replace ('-','_')

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
    """
    Store an object in the model structure
    Inputs:
        parent: name of parent object (used for nested object defs)
        model: dictionary model structure
        line: glm line containing the object definition
        itr: iterator over the list of lines
        oidh: hash of object id's to object names
        octr: object counter
    """
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

    base_name = gld_strict_name (model_name)

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
        Via.append(complex(float(Va[base_name+'_node_'+simlist[n]['i_node']]),float(Vaimg[base_name+'_node_'+simlist[n]['i_node']])))
        Vib.append(complex(float(Vb[base_name+'_node_'+simlist[n]['i_node']]),float(Vbimg[base_name+'_node_'+simlist[n]['i_node']])))
        Vic.append(complex(float(Vc[base_name+'_node_'+simlist[n]['i_node']]),float(Vcimg[base_name+'_node_'+simlist[n]['i_node']])))
        Vfa.append(complex(float(Va[base_name+'_node_'+simlist[n]['f_node']]),float(Vaimg[base_name+'_node_'+simlist[n]['f_node']])))
        Vfb.append(complex(float(Vb[base_name+'_node_'+simlist[n]['f_node']]),float(Vbimg[base_name+'_node_'+simlist[n]['f_node']])))
        Vfc.append(complex(float(Vc[base_name+'_node_'+simlist[n]['f_node']]),float(Vcimg[base_name+'_node_'+simlist[n]['f_node']])))

def getV_sim(model_name, simlistfile, V_datafile, new_Vdatafile):
    base_name = gld_strict_name (model_name)
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
        Vias.append(complex(float(Va[base_name+'_node_'+simlist[n]['i_node']]),float(Vaimg[base_name+'_node_'+simlist[n]['i_node']])))
        Vibs.append(complex(float(Vb[base_name+'_node_'+simlist[n]['i_node']]),float(Vbimg[base_name+'_node_'+simlist[n]['i_node']])))
        Vics.append(complex(float(Vc[base_name+'_node_'+simlist[n]['i_node']]),float(Vcimg[base_name+'_node_'+simlist[n]['i_node']])))
        Vfas.append(complex(float(Va[base_name+'_node_'+simlist[n]['f_node']]),float(Vaimg[base_name+'_node_'+simlist[n]['f_node']])))
        Vfbs.append(complex(float(Vb[base_name+'_node_'+simlist[n]['f_node']]),float(Vbimg[base_name+'_node_'+simlist[n]['f_node']])))
        Vfcs.append(complex(float(Vc[base_name+'_node_'+simlist[n]['f_node']]),float(Vcimg[base_name+'_node_'+simlist[n]['f_node']])))

#***********************************************************************************************************
# get current from the full model
def getI(model_name, linelistfile, I_datafile,new_I_datafile):

    base_name = gld_strict_name (model_name)
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
    base_name = gld_strict_name (model_name)
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
        if  simlist[n]['out_branch_4']!='':
            IiaJ.append(complex(float(Ia[simlist[n]['f_branch']]),float(Iaimg[simlist[n]['f_branch']])))
            IibJ.append(complex(float(Ib[simlist[n]['f_branch']]),float(Ibimg[simlist[n]['f_branch']])))
            IicJ.append(complex(float(Ic[simlist[n]['f_branch']]),float(Icimg[simlist[n]['f_branch']])))
            IoaJ.append(complex(float(Ia[simlist[n]['out_branch_1']]),float(Iaimg[simlist[n]['out_branch_1']]))+complex(float(Ia[simlist[n]['out_branch_2']]),float(Iaimg[simlist[n]['out_branch_2']]))+complex(float(Ia[simlist[n]['out_branch_3']]),float(Iaimg[simlist[n]['out_branch_3']]))+complex(float(Ia[simlist[n]['out_branch_4']]),float(Iaimg[simlist[n]['out_branch_4']])))
            IobJ.append(complex(float(Ib[simlist[n]['out_branch_1']]),float(Ibimg[simlist[n]['out_branch_1']]))+complex(float(Ib[simlist[n]['out_branch_2']]),float(Ibimg[simlist[n]['out_branch_2']]))+complex(float(Ib[simlist[n]['out_branch_3']]),float(Ibimg[simlist[n]['out_branch_3']]))+complex(float(Ib[simlist[n]['out_branch_4']]),float(Ibimg[simlist[n]['out_branch_4']])))
            IocJ.append(complex(float(Ic[simlist[n]['out_branch_1']]),float(Icimg[simlist[n]['out_branch_1']]))+complex(float(Ic[simlist[n]['out_branch_2']]),float(Icimg[simlist[n]['out_branch_2']]))+complex(float(Ic[simlist[n]['out_branch_3']]),float(Icimg[simlist[n]['out_branch_3']]))+complex(float(Ic[simlist[n]['out_branch_4']]),float(Icimg[simlist[n]['out_branch_4']])))
#a=inv((np.dot(Ii[10],Ii[10].transpose().conjugate())))

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
    base_name = gld_strict_name (modelname)
    f=open(glmfile,'a')
    f.write('object meter { // node {\n')
    f.write('   name '+base_name+'_node_'+simlist[seg_number]['f_node']+';\n')
    f.write('   phases '+simlist[seg_number]['phase_name']+'N;\n')
    f.write('   nominal_voltage '+str(v_base)+';\n')
    f.write('   voltage_A '+va+';\n')
    f.write('   voltage_B '+vb+';\n')
    f.write('   voltage_C '+vc+';\n')
    f.write('}\n')
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
        f.write('}\n')
    elif simlist[seg_number]['phase_name']=='AB':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')
        f.write('    z11 '+np.array2string(Z[seg_number][0][0])+';\n')
        f.write('    z12 '+np.array2string(Z[seg_number][0][1])+';\n')
        f.write('    z21 '+np.array2string(Z[seg_number][1][0])+';\n')
        f.write('    z22 '+np.array2string(Z[seg_number][1][1])+';\n')
        f.write('}\n')
    elif simlist[seg_number]['phase_name']=='AC':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')
        f.write('    z11 '+np.array2string(Z[seg_number][0][0])+';\n')
        f.write('    z13 '+np.array2string(Z[seg_number][0][1])+';\n')
        f.write('    z31 '+np.array2string(Z[seg_number][1][0])+';\n')
        f.write('    z33 '+np.array2string(Z[seg_number][1][1])+';\n')
        f.write('}\n')
    elif simlist[seg_number]['phase_name']=='BC':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')
        f.write('    z22 '+np.array2string(Z[seg_number][0][0])+';\n')
        f.write('    z23 '+np.array2string(Z[seg_number][0][1])+';\n')
        f.write('    z32 '+np.array2string(Z[seg_number][1][0])+';\n')
        f.write('    z33 '+np.array2string(Z[seg_number][1][1])+';\n')
        f.write('}\n')
    elif simlist[seg_number]['phase_name']=='A':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')
        f.write('    z11 '+np.array2string(Z[seg_number][0][0])+';\n')
        f.write('}\n')
    elif simlist[seg_number]['phase_name']=='B':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')
        f.write('    z22 '+np.array2string(Z[seg_number][1][1])+';\n')
        f.write('}\n')
    elif simlist[seg_number]['phase_name']=='C':
        f.write('object line_configuration {\n')
        f.write('    name line_config_seg_'+str(seg_number)+';\n')
        f.write('    z33 '+np.array2string(Z[seg_number][2][2])+';\n')
        f.write('}\n')
    return

# Create lines
def CreateLine(model_name,seg_number,glmfile):
    base_name = gld_strict_name (model_name)
    f=open(glmfile,'a')
    f.write('object overhead_line {\n')
    f.write('    name line_seg_'+str(seg_number)+';\n')
    if simlist[seg_number]['phase_name']=='ABC':
        f.write('    phases ABC;\n')
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
    f.write('    from '+base_name+'_node_'+simlist[seg_number]['i_node']+';\n')
    f.write('    to '+base_name+'_node_'+simlist[seg_number]['f_node']+';\n')
    f.write('    length 5280 ft;\n')
    f.write('    configuration line_config_seg_'+str(seg_number)+';\n')
    f.write('}\n')
    return

# Creat Meters to attached the loads
def CreateMeter(model_name,seg_number,glmfile):
    base_name = gld_strict_name (model_name)
    f=open(glmfile,'a')
    f.write('object meter {\n')
    f.write('    name meter_seg_'+str(seg_number)+';\n')
    f.write('    parent '+base_name+'_node_'+simlist[seg_number]['f_node']+';\n')
    f.write('}\n')
    return

def parse_kva(cplx):
    toks = re.split('[\+j]',cplx)
    p = float(toks[0])
    q = float(toks[1])
    return 0.001 * math.sqrt(p*p + q*q)

def accumulate_load_kva(data):
    kva = 0.0
    cls = 'R' # this is the default for triplex nodes
    if 'constant_power_A' in data:
        kva += parse_kva(data['constant_power_A'])
        cls = 'U' # default for primary nodes
    if 'constant_power_B' in data:
        kva += parse_kva(data['constant_power_B'])
        cls = 'U' # default for primary nodes
    if 'constant_power_C' in data:
        kva += parse_kva(data['constant_power_C'])
        cls = 'U' # default for primary nodes
    if 'constant_power_1' in data:
        kva += parse_kva(data['constant_power_1'])
    if 'constant_power_2' in data:
        kva += parse_kva(data['constant_power_2'])
    if 'constant_power_12' in data:
        kva += parse_kva(data['constant_power_12'])
    if 'power_1' in data:
        kva += parse_kva(data['power_1'])
    if 'power_2' in data:
        kva += parse_kva(data['power_2'])
    if 'power_12' in data:
        kva += parse_kva(data['power_12'])
    if 'load_class' in data:  # explicitly specified
        cls = data['load_class']
    return kva, cls

def CreateOneClassLoad (parent_name, load_name, phase_name, cls, p0, p1, p2, f):
    f.write('object load {\n')
    f.write('   parent ' + parent_name + ';\n')
    f.write('   name ' + load_name + ';\n')
    f.write('   nominal_voltage '+str(v_base)+';\n')
    f.write('   load_class ' + cls + ';\n')
    if np.absolute(p0) > 0.1:
        str_a = np.array2string(p0,precision=2)
    else:
        str_a = '0+0j'
    if np.absolute(p1) > 0.1:
        str_b = np.array2string(p1,precision=2)
    else:
        str_b = '0+0j'
    if np.absolute(p2) > 0.1:
        str_c = np.array2string(p2,precision=2)
    else:
        str_c = '0+0j'
    if phase_name == 'ABC':
        f.write('   phases ABCN;\n')
        f.write('   constant_power_A ' + str_a + ';\n')
        f.write('   constant_power_B ' + str_b + ';\n')
        f.write('   constant_power_C ' + str_c + ';\n')
        f.write('   voltage_A '+va+';\n')
        f.write('   voltage_B '+vb+';\n')
        f.write('   voltage_C '+vc+';\n')
    elif phase_name == 'AB':
        f.write('   phases ABN;\n')
        f.write('   constant_power_A ' + str_a + ';\n')
        f.write('   constant_power_B ' + str_b + ';\n')
        f.write('   voltage_A '+va+';\n')
        f.write('   voltage_B '+vb+';\n')
    elif phase_name == 'AC':
        f.write('   phases ACN;\n')
        f.write('   constant_power_A ' + str_a + ';\n')
        f.write('   constant_power_C ' + str_c + ';\n')
        f.write('   voltage_A '+va+';\n')
        f.write('   voltage_C '+vc+';\n')
    elif phase_name == 'BC':
        f.write('   phases BCN;\n')
        f.write('   constant_power_B ' + str_b + ';\n')
        f.write('   constant_power_C ' + str_c + ';\n')
        f.write('   voltage_B '+vb+';\n')
        f.write('   voltage_C '+vc+';\n')
    elif phase_name == 'A':
        f.write('   phases AN;\n')
        f.write('   constant_power_A ' + str_a + ';\n')
        f.write('   voltage_A '+va+';\n')
    elif phase_name == 'B':
        f.write('   phases BN;\n')
        f.write('   constant_power_B ' + str_b + ';\n')
        f.write('   voltage_B '+vb+';\n')
    elif phase_name == 'C':
        f.write('   phases CN;\n')
        f.write('   constant_power_C ' + str_c + ';\n')
        f.write('   voltage_C '+vc+';\n')
    f.write('}\n')
    return

# Create loads
def CreateLoad(model_name,seg_number,glmfile,class_factors):
    base_name = gld_strict_name (model_name)
    parent_name = base_name+ '_node_' + simlist[seg_number]['f_node']
    load_name = 'load_seg_' + str(seg_number)
    phase_name = simlist[seg_number]['phase_name']
    p0 = S[seg_number][0][0]
    p1 = S[seg_number][1][0]
    p2 = S[seg_number][2][0]
    if p0+p1+p2 < min_load_size:
#        print ('skipping near-zero load', load_name, 'at', parent_name)
        return
    f=open(glmfile,'a')

    # look for the original load class allocations from f_node, then i_node if not found
    class_factor_node = parent_name
    if class_factor_node not in class_factors:
        class_factor_node = base_name + '_node_' + simlist[seg_number]['i_node']
    if class_factor_node in class_factors:
#        print (class_factor_node, class_factors[class_factor_node])
        for cls in ['A', 'I', 'C', 'R', 'U']:
            if class_factors[class_factor_node][cls] > 0.0:
                CreateOneClassLoad (parent_name, load_name + '_' + cls, phase_name, cls,
                                    class_factors[class_factor_node][cls] * p0,
                                    class_factors[class_factor_node][cls] * p1,
                                    class_factors[class_factor_node][cls] * p2, f)
                simple_kva[cls] += class_factors[class_factor_node][cls] * np.absolute(p0 + p1 + p2)
    else:
        print ('Defaulting to class U for load at', parent_name)
        CreateOneClassLoad (parent_name, load_name + '_U', phase_name, 'U', p0, p1, p2, f)
        simple_kva['U'] += np.absolute(p0 + p1 + p2)
    return

def CreateLoad_agg(model_name,seg_number,glmfile,class_factors):
    base_name = gld_strict_name (model_name)
    parent_name = base_name+ '_node_' + simlist[seg_number]['f_node']
    load_name = 'load_junction_seg_' + str(seg_number)
    phase_name = simlist[seg_number]['phase_name']
    p0 = S_agg[seg_number][0][0]
    p1 = S_agg[seg_number][1][0]
    p2 = S_agg[seg_number][2][0]
    if simlist[seg_number]['junction'] != 'junction':
#        print ('skipping non-junction aggregate load at', parent_name)
        return
    if p0+p1+p2 < min_load_size:
#        print ('skipping near-zero aggregate load', load_name, 'at', parent_name)
        return

    f=open(glmfile,'a')

    # look for the original load class allocations from f_node, then i_node if not found
    class_factor_node = parent_name
    if class_factor_node not in class_factors:
        class_factor_node = base_name + '_node_' + simlist[seg_number]['i_node']
    if class_factor_node in class_factors:
#        print (class_factor_node, class_factors[class_factor_node])
        for cls in ['A', 'I', 'C', 'R', 'U']:
            if class_factors[class_factor_node][cls] > 0.0:
                CreateOneClassLoad (parent_name, load_name + '_' + cls, phase_name, cls,
                                    class_factors[class_factor_node][cls] * p0,
                                    class_factors[class_factor_node][cls] * p1,
                                    class_factors[class_factor_node][cls] * p2, f)
                simple_kva[cls] += class_factors[class_factor_node][cls] * np.absolute(p0 + p1 + p2)
    else:
        print ('Defaulting to class U for aggregate load at', parent_name)
        CreateOneClassLoad (parent_name, load_name + '_U', phase_name, 'U', p0, p1, p2, f)
        simple_kva['U'] += np.absolute(p0 + p1 + p2)
    return

#*********************************************
def CreateHeader(glmfile,modelname,swingbus,v_base,v1,v2,v3,reg_band_center,reg_band_width):
    base_name = gld_strict_name (modelname)
    f=open(glmfile,'a')
    f.write('//********************************\n')
    f.write('//Simplified feeder model\n')
    f.write('\n')
    f.write('clock{\n')
    f.write("  timezone EST+5EDT;\n")
    f.write("  timestamp '2000-01-01 0:00:00';\n")
    f.write("  stoptime '2000-01-01 1:00:00';\n")
    f.write("}\n")
    f.write("#set profiler=1\n\n")
    #create the module section
    f.write("\n")
    f.write('module tape;\n')
    f.write('module powerflow{\n')
    f.write("  solver_method NR;\n")
    f.write("  default_maximum_voltage_error 1e-6;\n};\n\n")

    #swing bus node define
    f.write('object node {\n')
    f.write('    name '+base_name+'_node_'+swingbus+';\n')
    f.write('    phases ABCN;\n')
    f.write('    nominal_voltage '+v_base+';\n')
    f.write('    bustype SWING;\n')
    f.write('    voltage_A '+v1+';\n')
    f.write('    voltage_B '+v2+';\n')
    f.write('    voltage_C '+v3+';\n')
    f.write('}\n')

    f.write('object regulator_configuration {\n')
    f.write('    name feeder_reg_cfg;\n')
    f.write('    Control OUTPUT_VOLTAGE;\n')
    f.write('    band_center '+reg_band_center+';\n')
    f.write('    band_width '+reg_band_width+';\n')
    f.write('    connect_type WYE_WYE;\n')
    f.write('    time_delay 30;\n')
    f.write('    raise_taps 16;\n')
    f.write('    lower_taps 16;\n')
    f.write('    regulation 0.10;\n')
    f.write('    tap_pos_A 0;\n')
    f.write('    tap_pos_B 0;\n')
    f.write('    tap_pos_C 0;\n')
    f.write('}\n')

    f.write('object meter {\n')
    f.write('    name '+base_name+'_meter_head;\n')
    f.write('    phases ABCN;\n')
    f.write('    nominal_voltage '+v_base+';\n')
    f.write('    voltage_A '+v1+';\n')
    f.write('    voltage_B '+v2+';\n')
    f.write('    voltage_C '+v3+';\n')
    f.write('}\n')

    f.write('object regulator {\n')
    f.write('    name feeder_reg_1;\n')
    f.write('    from '+base_name+'_node_'+swingbus+';\n')
    f.write('    to '+base_name+'_meter_head;\n')
    f.write('    phases ABCN;\n')
    f.write('    configuration feeder_reg_cfg;\n')
    f.write('}\n')

    # bus node
    f.write('object node {\n')
    f.write('    parent '+base_name+'_meter_head;\n')
    f.write('    name '+base_name+'_node_'+simlist[0]['i_node']+';\n')
    f.write('    phases ABCN;\n')
    f.write('    nominal_voltage '+v_base+';\n')
    f.write('    voltage_A '+v1+';\n')
    f.write('    voltage_B '+v2+';\n')
    f.write('    voltage_C '+v3+';\n')
    f.write('}\n')
#create voltdump objects
#*********************************************
def CreateVoltdump(glmfile,outputfileName1):
    f=open(glmfile,'a')
    f.write("object voltdump {\n")
    f.write("	 filename "+outputfileName1+";\n")
    f.write("}\n\n")
    return
#******************************************
#create currdump objects
#*********************************************
def CreateCurrdump(glmfile,outputfileName,):
    f=open(glmfile,'a')
    f.write("object currdump {\n")
    f.write("	 filename "+outputfileName+";\n")
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
            errora.append(abs((abs(Vfa[n])-abs(Vfas[n])))/baseV)
        else:
            n=n+1
    for n in range(len(Vfb)):
        if Vfbs[n]!=0j:
            errorb.append(abs((abs(Vfb[n])-abs(Vfbs[n])))/baseV)
        else:
            n=n+1
    for n in range(len(Vfc)):
        if Vfcs[n]!=0j:
            errorc.append(abs((abs(Vfc[n])-abs(Vfcs[n])))/baseV)
        else:
            n=n+1
    errormean=errora+errorb+errorc
    errormean=np.mean(errormean)
    indexa = np.arange(len(errora))
    indexb = np.arange(len(errorb))
    indexc = np.arange(len(errorc))
    plt.subplot(311)
    plt.bar(indexc,errorc,0.3,color='r',align="center")
    plt.title('Phase C error')
    plt.ylabel('V Error [p.u.]')
    plt.subplots_adjust(hspace=0.5)
    plt.subplot(312)
    plt.bar(indexa,errora,0.3,color='b',align="center")
    plt.title('Phase A error')
    plt.ylabel('V Error [p.u.]')
    plt.subplot(313)
    plt.bar(indexb,errorb,0.3,color='g',align="center")
    plt.title('Phase B error')
    plt.ylabel('V Error [p.u.]')
    plt.show()
    return

#%% begin to simplify feeder model
tax       = [['R1-12.47-1',12470.0, 7200.0, 4000.0, 20000.0,'617','7520','120'],#0 larger error; 0.006 pu
             ['R1-12.47-2',12470.0, 7200.0, 4500.0, 30000.0,'338','7520','120'],#1 larger error; 0.003 pu
             ['R1-12.47-3',12470.0, 7200.0, 8000.0, 15000.0,'53','7500','120'],#2
             ['R1-12.47-4',12470.0, 7200.0, 4000.0, 15000.0,'305','7520','120'],#3
             ['R1-25.00-1',24900.0,14400.0, 6000.0, 25000.0,'324','14975','240'],#4
             ['R2-12.47-1',12470.0, 7200.0, 7000.0, 20000.0,'488','7500','120'],#5
             ['R2-12.47-2',12470.0, 7200.0,15000.0, 25000.0,'253','7500','120'],#6
             ['R2-12.47-3',12470.0, 7200.0, 5000.0, 30000.0,'832','7500','120'],#7
             ['R2-25.00-1',24900.0,14400.0, 6000.0, 15000.0,'324','14975','240'],#8
             ['R2-35.00-1',34500.0,19920.0,15000.0, 30000.0,'1039','20748','332'],#9
             ['R3-12.47-1',12470.0, 7200.0,12000.0, 40000.0,'634','7500','120'],#10
             ['R3-12.47-2',12470.0, 7200.0,14000.0, 30000.0,'267','7500','120'],#11
             ['R3-12.47-3',12470.0, 7200.0, 7000.0, 15000.0,'2001','7520','120'],#12
             ['R4-12.47-1',13800.0, 7970.0, 9000.0, 30000.0,'572','8300','133'],#13
             ['R4-12.47-2',12470.0, 7200.0, 6000.0, 20000.0,'273','7518','120'],#14
             ['R4-25.00-1',24900.0,14400.0, 6000.0, 20000.0,'231','14975','240'],#15
             ['R5-12.47-1',13800.0, 7970.0, 6500.0, 20000.0,'266','8300','132'], #16
             ['R5-12.47-2',12470.0, 7200.0, 4500.0, 15000.0,'317','7500','120'], #17
             ['R5-12.47-3',13800.0, 7970.0, 4000.0, 15000.0,'1469','8300','131'],#18 larger error; 0.005 pu
             ['R5-12.47-4',12470.0, 7200.0, 6000.0, 30000.0,'675','7500','60'], #19
             ['R5-12.47-5',12470.0, 7200.0, 4500.0, 25000.0,'1100','7500','60'], #20
             ['R5-25.00-1',22900.0,13200.0, 3000.0, 20000.0,'953','13773','220'],#21
             ['R5-35.00-1',34500.0,19920.0, 6000.0, 25000.0,'339','20748','332'],#22
             ['GC-12.47-1',12470.0, 7200.0, 8000.0, 13000.0,'28','7500','120']]#23

def get_base_gld_path (root):
    return os.path.expandvars('$TESPDIR/data/feeders/') + root + '.glm'

def _one_test(k):
    fname = get_base_gld_path (tax[k][0])
    mname=tax[k][0].replace('.','-')
    base_name = gld_strict_name (mname)
    sim_fname='sim_'+tax[k][0]+'.glm'
    #calculate Vbase
    global va, vb, vc, v_base
    v_base=tax[k][2]
    vb = '{:.2f}'.format(-0.5 * v_base) + '-{:.2f}'.format(math.sqrt(0.75) * v_base) + 'j'
    vc = '{:.2f}'.format(-0.5 * v_base) + '+{:.2f}'.format(math.sqrt(0.75) * v_base) + 'j'
    v_base='{:.2f}'.format(v_base)
    va = v_base

    cmdline = 'gridlabd -D WANT_VI_DUMP=1 '+fname
    pw0 = subprocess.Popen (cmdline, shell=True)
    pw0.wait()

    if os.path.exists('sim_'+tax[k][0]+'.glm'):
        os.remove('sim_'+tax[k][0]+'.glm')

    # read the model
    ip = open (fname, 'r')
    lines = []
    line = ip.readline()
    while line != '':
        while re.match('\s*//', line) or re.match('\s+$', line):
            # skip comments and white space
            line = ip.readline()
        lines.append(line.rstrip())
        line = ip.readline()
    ip.close()

    octr = 0
    model = {}
    h = {}		# OID hash
    itr = iter(lines)
    for line in itr:
        if re.search('object',line):
            line,octr = obj(None,model,line,itr,h,octr)

    # construct a graph of the model, starting with known links
    global G
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

    getV(mname,
         mname+'_sim_list.csv',
         'Voltage_Dump_' + mname + '.csv', # mname+'_voltage.csv',
         mname+'_voltage1.csv')

    # create the list with given node : get branch name by networkx 
    i_branch=[]
    f_branch=[]
    segment_node=[]
    for n in range(len(simlist)):
        segment_node=nx.shortest_path(G, source=base_name+'_node_'+simlist[n]['i_node'], target=base_name+'_node_'+simlist[n]['f_node'])
        i_branch.append(G.edges[segment_node[0],segment_node[1]]['ename'])
        f_branch.append(G.edges[segment_node[-2],segment_node[-1]]['ename'])
    for n in range(len(simlist)):
        simlist[n]['i_branch']=i_branch[n]
        simlist[n]['f_branch']=f_branch[n]

    for n in range(len(simlist)):
        if simlist[n]['junction']=='junction':
            count=-1
            junction_outbranch=['','','','']
            for m in range(len(simlist)):
                if simlist[m]['i_node']==simlist[n]['f_node']:
                    count+=1
                    junction_outbranch[count]=(simlist[m]['i_branch'])
                simlist[n]['out_branch_1']=junction_outbranch[0]
                simlist[n]['out_branch_2']=junction_outbranch[1]
                simlist[n]['out_branch_3']=junction_outbranch[2]
                simlist[n]['out_branch_4']=junction_outbranch[3]
        else:
            junction_outbranch=['','','','']
            simlist[n]['out_branch_1']=junction_outbranch[0]
            simlist[n]['out_branch_2']=junction_outbranch[1]
            simlist[n]['out_branch_3']=junction_outbranch[2]
            simlist[n]['out_branch_4']=junction_outbranch[3]

    #
    getI(mname,
         mname+'_sim_list.csv',
         'Current_Dump_' + mname + '.csv',  # mname+'_current.csv',
         mname+'_current1.csv')
    getI_agg(mname,
             mname+'_sim_list.csv',
             'Current_Dump_' + mname + '.csv',  # mname+'_current.csv',
             mname+'_current1.csv')
    calculate_Z_S()

    # we need the load connected to each primary node, by load_class
    swing_node = ''
    for n1, data in G.nodes(data=True):
        if 'nclass' in data:
            if data['nclass'] == 'node':
                data['ndata']['class_load'] = {'A':0,'I':0,'C':0,'R':0,'U':0}
            if 'bustype' in data['ndata']:
                if data['ndata']['bustype'] == 'SWING':
                    swing_node = n1
    print ('swing node is', swing_node)
    retained_nodes = set()
    retained_nodes.add(swing_node)
    for n in simlist:
        retained_nodes.add(base_name + '_node_' + n['i_node'])
        retained_nodes.add(base_name + '_node_' + n['f_node'])
#    print (retained_nodes)

    total_kva = {}
    class_count = {}
    for cls in ['A', 'I', 'C', 'R', 'U']:
        total_kva[cls] = 0.0
        class_count[cls] = 0
    for n1, data in G.nodes(data=True):
        if 'ndata' in data:
            (kva, load_class) = accumulate_load_kva (data['ndata'])
            if kva > 0:
                total_kva[load_class] += kva
                class_count[load_class] += 1
                nodes = nx.shortest_path(G, n1, swing_node)
                # assign this class load to the closest upstream primary node that's in the retained set
                for x in nodes:
                    n2 = G.nodes[x]
                    if 'nclass' in n2:
                        if n2['nclass'] == 'node':
                            if x in retained_nodes:
#                               if load_class == 'C':
#                                   print ('assigning C load', kva, 'at', n1, 'to', x)
#                                   for y in nodes:
#                                       print ('  ', y)
#                                       if y == x:
#                                           break
                                n2['ndata']['class_load'][load_class] += kva
                                break
    count_summary = 0
    class_factors = {}
    for o in model['node']:
        cls_ld = G.nodes[o]['ndata']['class_load']
        cls_a = cls_ld['A']
        cls_i = cls_ld['I']
        cls_c = cls_ld['C']
        cls_r = cls_ld['R']
        cls_u = cls_ld['U']
        cls_sum = cls_a + cls_i + cls_c + cls_r + cls_u
        if cls_sum > 0.0:
            count_summary += 1
#            print ('Node Summary for', o, 'A={:.2f} I={:.2f} C={:.2f} R={:.2f} U={:.2f}'.format (cls_a, cls_i, cls_c, cls_r, cls_u))
            class_factors[o] = {'A':cls_a/cls_sum, 'I':cls_i/cls_sum, 'C':cls_c/cls_sum, 'R':cls_r/cls_sum, 'U':cls_u/cls_sum}
    print ('summarized load class allocation factors at', count_summary, 'retained primary nodes')

    global simple_kva
    simple_kva = {'A':0, 'I': 0, 'C': 0, 'R': 0, 'U': 0}
    CreateHeader(sim_fname,mname,tax[k][5],v_base,va,vb,vc,tax[k][6],tax[k][7])
    for n in range(len(simlist)):
        CreateNode(mname,n,sim_fname)
    for n in range(len(simlist)):
        CreateLineConfig(n,sim_fname)
    for n in range(len(simlist)):
        CreateLine(mname,n,sim_fname)
    for n in range(len(simlist)):
        CreateLoad(mname,n,sim_fname,class_factors)
    for n in range(len(simlist)):
        CreateLoad_agg(mname,n,sim_fname,class_factors)
    CreateVoltdump(sim_fname,mname+'_node_voltage_sim.csv')
    CreateCurrdump(sim_fname,mname+'_branch_current_sim.csv')

    for cls in ['A', 'I', 'C', 'R', 'U']:
        print ('class', cls, class_count[cls], 'customers = {:.2f} kva'.format(total_kva[cls]),
            'simplified to {:.2f} kva'.format(0.001 * simple_kva[cls]))
# run the simplified feeder model
    os.system('gridlabd '+sim_fname)
    getV_sim(mname,mname+'_sim_list.csv',mname+'_node_voltage_sim.csv',mname+'_node_voltage_sim1.csv')
    errorplot(tax[k][2])
    print()
    print()
    print()
    print()
    print('Reduced order model of '+fname+' is written in '+sim_fname)
    print('Average error is '+str(errormean))

if __name__ == '__main__':
#    print (simlist)

#    _one_test(7)
#    quit()

    for k in range (len(tax)):
        _one_test(k)

##locate the error segment

#for i in range(45):
#    
#    inv((np.dot(Ii[i],Ii[i].transpose().conjugate())))
