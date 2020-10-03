## Author: tom <tom@uvm>
## Created: 2020-10-02
function loadprofile = dam_loads
%% define constants
[CT_LABEL, CT_PROB, CT_TABLE, CT_TBUS, CT_TGEN, CT_TBRCH, CT_TAREABUS, ...
    CT_TAREAGEN, CT_TAREABRCH, CT_ROW, CT_COL, CT_CHGTYPE, CT_REP, ...
    CT_REL, CT_ADD, CT_NEWVAL, CT_TLOAD, CT_TAREALOAD, CT_LOAD_ALL_PQ, ...
    CT_LOAD_FIX_PQ, CT_LOAD_DIS_PQ, CT_LOAD_ALL_P, CT_LOAD_FIX_P, ...
    CT_LOAD_DIS_P, CT_TGENCOST, CT_TAREAGENCOST, CT_MODCOST_F, ...
    CT_MODCOST_X] = idx_ct;

loadprofile = struct( ...
    'type', 'mpcData', ...
    'table', CT_TLOAD, ...
    'rows', 0, ...
    'col', CT_LOAD_ALL_PQ, ...
    'chgtype', CT_REL, ...
    'values', [] );
scale = 0.5;
loadprofile.values(:, 1, 1) = [
scale;%        0.6704;
scale;%        0.6303;
scale;%        0.6041;
scale;%        0.5902;
scale;%        0.5912;
scale;%        0.6094;
scale;%        0.6400;
scale;%        0.6725;
scale;%        0.7207;
scale;%        0.7584;
scale;%        0.7905;
scale;%        0.8171;
scale;%        0.8428;
scale;%        0.8725;
scale;%        0.9098;
scale;%        0.9480;
scale;%        0.9831;
scale;%        1.0000;
scale;%        0.9868;
scale;%        0.9508;
scale;%        0.9306;
scale;%        0.8999;
scale;%        0.8362;
scale;%        0.7695;
];

endfunction
