clear;
define_constants;
mpc = loadcase ('rtmcase.m');
mpopt = mpoption ('verbose',0,'out.all',0);
res = rundcopf (mpc, mpopt, 'output.txt', 'solved.txt');
