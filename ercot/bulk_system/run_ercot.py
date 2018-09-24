import numpy as np;
import pypower.api as pp;
import tesp_support.api as tesp;
import sys;

def rescale_case(ppc, scale):
    ppc['bus'][:,2] *= scale  # Pd
    ppc['bus'][:,3] *= scale  # Qd
    ppc['bus'][:,5] *= (scale * scale)  # Qs
    ppc['gen'][:,1] *= scale  # Pg

#ppc = tesp.load_json_case ('ercot_200.json')
ppc = tesp.load_json_case ('ercot_8.json')
#rescale_case (ppc, 0.4)
ppopt_regular = pp.ppoption(VERBOSE=1, 
                            OUT_SYS_SUM=1, 
                            OUT_BUS=1, 
                            OUT_GEN=0, 
                            OUT_BRANCH=1, 
                            PF_DC=0, 
                            PF_ALG=1)
rpf = pp.runpf (ppc, ppopt_regular)
pp.printpf (100.0,
            bus=rpf[0]['bus'],
            gen=rpf[0]['gen'],
            branch=rpf[0]['branch'],
            ppopt=ppopt_regular,
            fd=sys.stdout,
            et=rpf[0]['et'],
            success=rpf[0]['success'])

ppopt_market = pp.ppoption(VERBOSE=1, 
                            OUT_SYS_SUM=1, 
                            OUT_BUS=1, 
                            OUT_GEN=1, 
                            OUT_BRANCH=1, 
                            OUT_LINE_LIM=1, 
                            PF_DC=1, 
                            PF_ALG=1)
ropf = pp.runopf (ppc, ppopt_market)
pp.printpf (100.0,
            bus=ropf['bus'],
            gen=ropf['gen'],
            branch=ropf['branch'],
            ppopt=ppopt_market,
            fd=sys.stdout,
            et=ropf['et'],
            success=ropf['success'])

