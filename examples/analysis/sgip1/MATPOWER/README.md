# MATPOWER models for co-simulation #

*Author: Laurentiu Dan Marinovici*
****************************************

## MATPOWER ##

MATPOWER is a package of MATLAB M-files for solving power flow and optimal power flow problems. To download the package in its latest version or previous ones follow this [link][link2MATPOWER]. The main documentation can be found [here][link2MATPOWERMan] [1], while a short description of its functionality is presented in this [paper][link2MATPOWERpaper] [2].

The main 3 steps of running a MATPOWER simulation are:
<ol>
  <li>Preparing the input data file known as the case file, which defines all the parameters relevant to the power system in question and the purpose of the problem;</li>
  <li>Invoking the appropriate function to solve the problem;</li>
  <li>Accessing, saving to output files or plotting the simulation results.</li>
</ol>

## MATPOWER case files ##

MATPOWER case files are MATLAB functions (``.m`` files) that specify a set of data matrices corresponding to each component of the studied power system, that is, buses, generators, lines/branches, etc. All these matrices are bundled in a MATLAB structure, referred to as a **M**AT**P**OWER **C**ase (MPC). For example, the 9-bus, 3-generator power system model is specified as:
```
function mpc = case9
% CASE9    Power flow data for 9 bus, 3 generator case.
%   Please see CASEFORMAT for details on the case file format.
%
%   Based on data from Joe H. Chow's book, p. 70.

%   MATPOWER
%   $Id: case9.m,v 1.11 2010/03/10 18:08:14 ray Exp $

%% MATPOWER Case Format : Version 2
mpc.version = '2';

%%-----  Power Flow Data  -----%%
%% system MVA base
mpc.baseMVA = 100;

%% bus data
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
%	bus	Pg	Qg	Qmax	Qmin	Vg	mBase	status	Pmax	Pmin	Pc1	Pc2	Qc1min	Qc1max	Qc2min	Qc2max	ramp_agc	ramp_10	ramp_30	ramp_q	apf
mpc.gen = [
1	0	0	300	-300	1	100	1	250	10	0	0	0	0	0	0	0	0	0	0	0;
2	163	0	300	-300	1	100	1	300	10	0	0	0	0	0	0	0	0	0	0	0;
3	85	0	300	-300	1	100	1	270	10	0	0	0	0	0	0	0	0	0	0	0;
];

%% branch data
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
%	area	refbus
mpc.areas = [
1	5;
];

%% generator cost data
%	1	startup	shutdown	n	x1	y1	...	xn	yn
%	2	startup	shutdown	n	c(n-1)	...	c0
mpc.gencost = [
2	1500	0	3	0.11	5	150;
2	2000	0	3	0.085	1.2	600;
2	3000	0	3	0.1225	1	335;
];
```

To facilitate the integration of MATPOWER within the FNCS environment, and its connection with distribution-side models, several additions have to be made to the case files to augment the MPC structure, that is:
<ol>
  <li>add vectors that specify the dimensions of each matrix in the MPC structure, defining every element of the power system; this helps with easily allocating the correct amount of memory in the C++ wrapper;</li>
  <li>add a FNCS communication interface that would facilitate the connection between the transmission simulator and the distribution simulator (GridLAB-D); at this stage, the following features are available:</li>
    <ol>
      <li>the total number of load buses where distribution sites are going to be connected to and their identification number;</li>
      <li>the total number of distribution sites that are getting attached to the transmission network, their id and the bus id where they are connected; keep in mind that multiple distribution sites could be connected to the same bus, and their power consumption is going to be aggregated;</li>
      <li>the total number and the id of the offline generators came in as part of creating scenarios that could affect increases in energy prices due to losing generation; they are application specific, so they could be left out;</li>
      <li>the amplification factor is meant to adjust the power consumption at the distribution level to an increased value, such that it makes a difference at the transmission level; if the distribution models provide enough load, then this factor could be set to 1.</li>
    </ol>
</ol>

The added MATLAB code line are shown below:
```
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
mpc.SubNumFNCS = 9;
%% Substation names, and the transmission network bus where it is connected to
mpc.SubNameFNCS = [
SUBSTATION1   7
SUBSTATION2   5
SUBSTATION3   9
SUBSTATION4   7
SUBSTATION5   5
SUBSTATION6   9
SUBSTATION7   5
SUBSTATION8   9
SUBSTATION9   7 ];
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
mpc.ampFactor = 100;
%% ======================================================================

mpc.busData = [ 9 13 ];
mpc.genData = [ 3 21 ];
mpc.branchData = [ 9 13 ];
mpc.areaData = [ 1 2 ];
mpc.costData = [ 3 7 ];
```
## References ##
[1] R. D. Zimmerman, C. E. Murillo-Sanchez, and R. J. Thomas, "*MATPOWER: Steady-State Operations, Planning and Analysis Tools for Power Systems Research and Education*," Power Systems, IEEE Transactions on, vol. 26, no. 1, pp. 12-19, Feb. 2011. Paper can be found [here][link2MATPOWERpaper].

[2] R. D. Zimmerman, C. E. Murillo-Sanchez, "*MATPOWER: User's Manual*". Download the manual [here][link2MATPOWERman]

[link2MATPOWER]: http://www.pserc.cornell.edu/matpower/ "MATPOWER site"
[link2MATPOWERMan]: http://www.pserc.cornell.edu/matpower/MATPOWER-manual.pdf "MATPOWER manual"
[link2MATPOWERpaper]: http://www.pserc.cornell.edu/matpower/MATPOWER-paper.pdf "MATPOWER paper"