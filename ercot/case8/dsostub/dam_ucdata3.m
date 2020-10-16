function [xgd_table] = dam_ucdata3 (mpc)
xgd_table.colnames = {
    'CommitKey', ...
};

xgd_table.data = [  % 13 generators, possibly 5 wind, possibly 8 responsive load
    1;
    1;
    1;
    1;
    1;
    1;
    1;
    1;
    1;
    1;
    1;
    1;
    1;
% wind generation
% responsive loads
    2;
    2;
    2;
    2;
    2;
    2;
    2;
    2;
];
endfunction
