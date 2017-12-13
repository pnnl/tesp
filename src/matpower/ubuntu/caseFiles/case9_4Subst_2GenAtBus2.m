function mpc = case9
%CASE9    Power flow data for 9 bus, 3 generator case.
%   Please see CASEFORMAT for details on the case file format.
%
%   Based on data from Joe H. Chow's book, p. 70.

%   MATPOWER
%   $Id: case9.m,v 1.11 2010/03/10 18:08:14 ray Exp $

%% MATPOWER Case Format : Version 2
mpc.version = '2';

%% ======================================================================
%% FNCS communication interface
%% This has been added to simplify the set-up process
%% ======================================================================
% Number of buses where distribution networks are going to be connected to
mpc.BusFNCSNum = 3;
% Buses where distribution networks are going to be connected to
mpc.BusFNCS = [
               7;
               5;
               9];
% Number of distribution feeders (GridLAB-D instances)
mpc.SubNumFNCS = 4;
%% Substation names, and the transmission network bus where it is connected to
mpc.SubNameFNCS = [
                 SUBSTATION1   7
                 SUBSTATION2   5
                 SUBSTATION3   9
                 SUBSTATION4   7
%                SUBSTATION5   5
%                SUBSTATION6   9
%                SUBSTATION7   5
%                SUBSTATION8   9
%                SUBSTATION9   7 ];
%                SUBSTATION10  5 ];
%                SUBSTATION11  9 
                ];
%% ======================================================================
%% For creating scenarios for visualization
%% Setting up the matrix of generators that could become off-line
% Number of generators that might be turned off-line
mpc.offlineGenNum = 0;
% Matrix contains the bus number of the corresponding off-line generators
mpc.offlineGenBus = [
                  3 ];       

%% ======================================================================
%% An amplification factor is used to simulate a higher load at the feeder end
mpc.ampFactor = 1;
%% ======================================================================

%%-----  Power Flow Data  -----%%
%% system MVA base
mpc.baseMVA = 100;

%% bus data
mpc.busData = [ 9 13 ];
%	bus_i	type	Pd	Qd	Gs	Bs	area	Vm	Va	baseKV	zone	Vmax	Vmin
mpc.bus = [
	1	3	0	0	0	0	1	1	0	345	1	1.1	0.9;
	2	2	0	0	0	0	1	1	0	345	1	1.1	0.9;
	3	2	0	0	0	0	1	1	0	345	1	1.1	0.9;
	4	1	0	0	0	0	1	1	0	345	1	1.1	0.9;
	5	1	90	30	0	0	1	1	0	345	1	1.1	0.9;
	6	1	0	0	0	0	1	1	0	345	1	1.1	0.9;
	7	1	100	35	0	0	1	1	0	345	1	1.1	0.9;
	8	1	0	0	0	0	1	1	0	345	1	1.1	0.9;
	9	1	125	50	0	0	1	1	0	345	1	1.1	0.9;
];

%% generator data
mpc.genData = [ 5 21 ];
%	bus	Pg	Qg	Qmax	Qmin	Vg	mBase	status	Pmax	Pmin	Pc1	Pc2	Qc1min	Qc1max	Qc2min	Qc2max	ramp_agc	ramp_10	ramp_30	ramp_q	apf
mpc.gen = [
	1  	0	0	300	-300	1	100	1	250	10	0	0	0	0	0	0	  0	  0	  0	  0	0;
	2	163	0	300	-300	1	100	1	300	10	0	0	0	0	0	0	  0	  0	  0	  0	0;
	2	120	0	300	-300	1	100	1	300	10	0	0	0	0	0	0	  0	  0	  0	  0	0;
	3	 85	0	300	-300	1	100	1	270	10	0	0	0	0	0	0	  0	  0	  0	  0	0;
	5   0 0   0    0  0 100 0   0  0  0 0 0 0 0 0 Inf Inf Inf Inf 0;
];

%% branch data
% branch  5-6 (row 3) column 6 (rateA) has been reduced from 150 to 45 to have the line congested and result in different LMPs from DC OPF
mpc.branchData = [ 9 13 ];
%	fbus	tbus	r	x	b	rateA	rateB	rateC	ratio	angle	status	angmin	angmax
mpc.branch = [
	1	4	0	0.0576	0	250	250	250	0	0	1	-360	360;
	4	5	0.017	0.092	0.158	250	250	250	0	0	1	-360	360;
	5	6	0.039	0.17	0.358	150	150	150	0	0	1	-360	360;
	3	6	0	0.0586	0	300	300	300	0	0	1	-360	360;
	6	7	0.0119	0.1008	0.209	150	150	150	0	0	1	-360	360;
	7	8	0.0085	0.072	0.149	250	250	250	0	0	1	-360	360;
	8	2	0	0.0625	0	250	250	250	0	0	1	-360	360;
	8	9	0.032	0.161	0.306	250	250	250	0	0	1	-360	360;
	9	4	0.01	0.085	0.176	250	250	250	0	0	1	-360	360;
];

%%-----  OPF Data  -----%%
%% area data
mpc.areaData = [ 1 2 ];
%	area	refbus
mpc.areas = [
	1	5;
];

%% generator cost data
mpc.gencostData = [ 5 7 ];
%	1	startup	shutdown	n	x1	y1	...	xn	yn
%	2	startup	shutdown	n	c(n-1)	...	c0
mpc.gencost = [
	2	1500	0	3	0.11	  5	  150;
	2	2000	0	3	0.085  	1.2	600;
	2	2000	0	3	0.085  	1.2	600;
	2	3000	0	3	0.1225	1	  335;
	2    0  0 3 0       0     0;
];
