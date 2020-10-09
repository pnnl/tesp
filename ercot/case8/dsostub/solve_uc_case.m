clear;
define_constants;
mpc = loadcase ('rtmcase2.m');
mpopt = mpoption('verbose', 0);
% mpopt = mpoption ('verbose',0,'out.all',1,'opf.dc.solver','GLPK');
xgd = loadxgendata(dam_ucdata2, mpc);
%nt = 4; % 24;
%profiles = [];
profiles = getprofiles('dam_loads2.m');
nt = size(profiles(1).values, 1); % number of periods
mdi = loadmd(mpc, nt, xgd, [], [], profiles);
mdo = most(mdi, mpopt);
EPg = mdo.results.ExpectedDispatch;
Elam = mdo.results.GenPrices;
most_summary(mdo);
