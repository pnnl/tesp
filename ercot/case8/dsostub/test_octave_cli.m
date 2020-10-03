clear;
define_constants;
mpopt = mpoption('verbose',0); % ,'opf.dc.solver','GLPK'); % 'out.all',0,
%mpc = loadcase('respload.m');
mpc = loadcase('rtmcase.m');
rundcopf (mpc, mpopt)

