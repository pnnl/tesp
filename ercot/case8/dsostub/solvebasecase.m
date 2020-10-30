clear;	
define_constants;	
mpc = loadcase ('basecase.m');	
mpopt = mpoption ('verbose',0,'out.all',0,'opf.dc.solver','GLPK');	
res = rundcopf (mpc, mpopt, 'output.txt', 'solved.txt');
