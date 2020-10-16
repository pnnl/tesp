clear;
define_constants;

mpopt = mpoption('verbose', 0, 'out.all', 0);
%mpopt = mpoption ('verbose',1,'out.all',1,'opf.dc.solver','GLPK');
%mpopt = mpoption(mpopt, 'most.dc_model', 0); % use model with no network

mpc = loadcase ('rtmcase3.m');
xgd = loadxgendata(dam_ucdata3, mpc);
profiles = getprofiles('dam_loads3.m');
profiles = getprofiles('dam_loads4.m', profiles);

nt = size(profiles(1).values, 1); % number of periods
mdi = loadmd(mpc, nt, xgd, [], [], profiles);

mdo = most(mdi, mpopt);
ms = most_summary(mdo);
save('-text', 'msout.txt', 'ms')
