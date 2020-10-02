function mpc = basecase
%% MATPOWER base case from PNNL TESP, fncsTSO2.py, model name ercot_8
mpc.version = '2';
mpc.baseMVA = 100;
%% bus_i  type  Pd  Qd  Gs  Bs  area  Vm  Va  baseKV  zone  Vmax  Vmin
mpc.bus = [
 1.0  3.0  15167.5  3079.9  0.0  5000.0  1.0  1.0  0.0  345.0  2.0  1.1  0.9  0.0  0.0;
 2.0  2.0  14875.0  3020.5  0.0  4000.0  1.0  1.0  0.0  345.0  1.0  1.1  0.9  0.0  0.0;
 3.0  2.0  331.6  67.3  0.0  70.0  1.0  1.0  0.0  345.0  4.0  1.1  0.9  0.0  0.0;
 4.0  2.0  3634.4  739.0  0.0  2500.0  1.0  1.0  0.0  345.0  4.0  1.1  0.9  0.0  0.0;
 5.0  2.0  7603.6  1544.0  0.0  3500.0  1.0  1.0  0.0  345.0  3.0  1.1  0.9  0.0  0.0;
 6.0  2.0  427.5  86.8  0.0  80.0  1.0  1.0  0.0  345.0  3.0  1.1  0.9  0.0  0.0;
 7.0  2.0  5646.0  1146.5  0.0  1100.0  1.0  1.0  0.0  345.0  3.0  1.1  0.9  0.0  0.0;
 8.0  1.0  113.8  23.1  0.0  -100.0  1.0  1.0  0.0  345.0  4.0  1.1  0.9  0.0  0.0
];
%% bus  Pg  Qg  Qmax  Qmin  Vg  mBase status  Pmax  Pmin  Pc1 Pc2 Qc1min  Qc1max  Qc2min  Qc2max  ramp_agc  ramp_10 ramp_30 ramp_q  apf
mpc.gen = [
 1.0  0.0  0.0  6567.0  -6567.0  1.0  19978.8  1.0  19978.8  1998.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 1.0  0.0  0.0  3834.0  -3834.0  1.0  11664.8  1.0  11664.8  5832.4  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 1.0  0.0  0.0  798.7  -798.7  1.0  2430.0  1.0  2430.0  1215.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 2.0  2076.0  0.0  6824.0  -6824.0  1.0  20761.7  1.0  20761.7  2076.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 2.0  1595.0  0.0  1048.6  -1048.6  1.0  3190.3  1.0  3190.3  1595.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 2.0  1354.3  0.0  890.3  -890.3  1.0  2708.6  1.0  2708.6  1354.3  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 3.0  8.0  0.0  26.3  -26.3  1.0  80.0  1.0  80.0  8.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 3.0  360.0  0.0  236.7  -236.7  1.0  720.0  1.0  720.0  360.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 4.0  343.8  0.0  1130.1  -1130.1  1.0  3438.2  1.0  3438.2  343.8  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 5.0  1059.0  0.0  3480.7  -3480.7  1.0  10589.7  1.0  10589.7  1059.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 5.0  2864.0  0.0  1882.7  -1882.7  1.0  5728.1  1.0  5728.1  2864.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 7.0  3692.5  0.0  2427.3  -2427.3  1.0  7385.0  1.0  7385.0  3692.5  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 7.0  311.2  0.0  204.6  -204.6  1.0  622.4  1.0  622.4  311.2  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 1.0  0.0  0.0  550.6  -550.6  1.0  1675.0  0.0  1675.0  167.5  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 3.0  1014.9  0.0  737.0  -737.0  1.0  2242.2  0.0  2242.2  224.2  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 4.0  3951.5  0.0  2869.5  -2869.5  1.0  8730.3  0.0  8730.3  873.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 6.0  45.2  0.0  32.8  -32.8  1.0  99.8  0.0  99.8  10.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 7.0  1612.3  0.0  1170.8  -1170.8  1.0  3562.2  0.0  3562.2  356.2  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 1.0  0.0  0.0  0.0  0.0  1.0  250.0  1.0  0.0  -5.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 2.0  0.0  0.0  0.0  0.0  1.0  250.0  1.0  0.0  -5.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 3.0  0.0  0.0  0.0  0.0  1.0  250.0  1.0  0.0  -5.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 4.0  0.0  0.0  0.0  0.0  1.0  250.0  1.0  0.0  -5.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 5.0  0.0  0.0  0.0  0.0  1.0  250.0  1.0  0.0  -5.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 6.0  0.0  0.0  0.0  0.0  1.0  250.0  1.0  0.0  -5.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 7.0  0.0  0.0  0.0  0.0  1.0  250.0  1.0  0.0  -5.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0;
 8.0  0.0  0.0  0.0  0.0  1.0  250.0  1.0  0.0  -5.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0  0.0
];
%% bus  tbus  r x b rateA rateB rateC ratio angle status  angmin  angmax
mpc.branch = [
 5.0  6.0  0.0042376  0.0358982  2.483257  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 4.0  5.0  0.0024809  0.0210167  13.0845006  6504.0  6504.0  6504.0  0.0  0.0  1.0  -360.0  360.0;
 4.0  6.0  0.00597922  0.05065251  3.50388768  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 1.0  2.0  0.006158677  0.05217279  3.6090528  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 2.0  7.0  0.006215203  0.052651649  3.6421779  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 1.0  5.0  0.00585052  0.04956227  3.42847  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 4.0  8.0  0.0063891224  0.0541249945  3.7440965856  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 6.0  7.0  0.005946527  0.05037558  3.484730861  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 2.0  5.0  0.001472827  0.012476948  7.76783579  6504.0  6504.0  6504.0  0.0  0.0  1.0  -360.0  360.0;
 1.0  4.0  0.00787911  0.06674734  4.617247  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 3.0  4.0  0.00439238  0.037209735  2.573983474  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 5.0  7.0  0.00496783  0.04208459  2.91120165  2168.0  2168.0  2168.0  0.0  0.0  1.0  -360.0  360.0;
 1.0  3.0  0.004216212  0.03571734  5.55918  3252.0  3252.0  3252.0  0.0  0.0  1.0  -360.0  360.0
];
%% either 1 startup shutdown n x1 y1  ... xn  yn
%%   or 2 startup shutdown n c(n-1) ... c0
mpc.gencost = [
 2.0  0.0  0.0  3.0  0.0  35.0  0.0;
 2.0  0.0  0.0  3.0  0.0  19.0  0.0;
 2.0  0.0  0.0  3.0  0.0  8.0  0.0;
 2.0  0.0  0.0  3.0  0.0  56.5  0.0;
 2.0  0.0  0.0  3.0  0.0  19.0  0.0;
 2.0  0.0  0.0  3.0  0.0  8.0  0.0;
 2.0  0.0  0.0  3.0  0.0  57.03  0.0;
 2.0  0.0  0.0  3.0  0.0  19.0  0.0;
 2.0  0.0  0.0  3.0  0.0  57.03  0.0;
 2.0  0.0  0.0  3.0  0.0  45.0  0.0;
 2.0  0.0  0.0  3.0  0.0  19.0  0.0;
 2.0  0.0  0.0  3.0  0.0  50.0  0.0;
 2.0  0.0  0.0  3.0  0.0  19.0  0.0;
 2.0  0.0  0.0  3.0  0.0  0.01  0.0;
 2.0  0.0  0.0  3.0  0.0  0.01  0.0;
 2.0  0.0  0.0  3.0  0.0  0.01  0.0;
 2.0  0.0  0.0  3.0  0.0  0.01  0.0;
 2.0  0.0  0.0  3.0  0.0  0.01  0.0;
 2.0  0.0  0.0  3.0  0.0  0.0  0.0;
 2.0  0.0  0.0  3.0  0.0  0.0  0.0;
 2.0  0.0  0.0  3.0  0.0  0.0  0.0;
 2.0  0.0  0.0  3.0  0.0  0.0  0.0;
 2.0  0.0  0.0  3.0  0.0  0.0  0.0;
 2.0  0.0  0.0  3.0  0.0  0.0  0.0;
 2.0  0.0  0.0  3.0  0.0  0.0  0.0;
 2.0  0.0  0.0  3.0  0.0  0.0  0.0
];