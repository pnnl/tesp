function mpc = case1
mpc.version = '2';
mpc.baseMVA = 100;
mpc.bus = [
	1	2	0	0	0	0	1	1	0	230	1	1.1	0.9;
	2	3	0	0	0	0	1	1	0	230	1	1.1	0.9;
];
mpc.gen = [
	1	0	0	0	-0	1	100	1	0	0	0	0	0	0	0	0	0	0	0	0	0;
];
mpc.branch = [
	1	2	0.00	0.0	0.00	00	00	00	0	0	1	-360	360;
];
mpc.gencost = [
	2	0	0	3	0.00   00	00000;
];

