clear;
define_constants;
mpopt = mpoption('verbose', 0);
mpc = loadcase('ex_case3b');
xgd = loadxgendata('ex_xgd_uc', mpc);
[iwind, mpc, xgd] = addwind('ex_wind_uc', mpc, xgd);
profiles = getprofiles('ex_wind_profile_d', iwind);
profiles = getprofiles('ex_load_profile', profiles);
nt = size(profiles(1).values, 1); % number of periods
mpc_full = mpc;
xgd_full = xgd;
mpc.gencost(:, [STARTUP SHUTDOWN]) = 0; % remove startup/shutdown costs
xgd.MinUp(2) = 1; % remove min up-time constraint
xgd.PositiveLoadFollowReserveQuantity(3) = 250; % remove ramp reserve
xgd.PositiveLoadFollowReservePrice(3) = 1e-6; % constraint and costs
xgd.NegativeLoadFollowReservePrice(3) = 1e-6;

mpopt = mpoption(mpopt, 'most.dc_model', 0); % use model with no network
mdi = loadmd(mpc, nt, xgd, [], [], profiles);
mdo = most(mdi, mpopt);
ms = most_summary(mdo);

EPg = mdo.results.ExpectedDispatch;
Elam = mdo.results.GenPrices;

