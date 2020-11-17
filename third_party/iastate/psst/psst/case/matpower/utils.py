COLUMNS = {
        'bus': ['BUS_I', 'TYPE', 'PD', 'QD', 'GS', 'BS', 'AREA',
                'VM', 'VA', 'BASEKV', 'ZONE', 'VMAX', 'VMIN',
                'LAM_P', 'LAM_Q', 'MU_VMAX', 'MU_VMIN'],
        'gen': ['GEN_BUS', 'PG', 'QG', 'QMAX', 'QMIN', 'VG', 'MBASE', 'GEN_STATUS',
            'PMAX', 'PMIN', 'PC1', 'PC2', 'QC1MIN', 'QC1MAX', 'QC2MIN', 'QC2MAX',
            'RAMP_AGC', 'RAMP_10', 'RAMP_30', 'RAMP_Q', 'APF', 'MU_PMAX',
            'MU_PMIN', 'MU_QMAX', 'MU_QMIN'],
        'branch': ['F_BUS', 'T_BUS', 'BR_R', 'BR_X', 'BR_B', 'RATE_A', 'RATE_B',
            'RATE_C', 'TAP', 'SHIFT', 'BR_STATUS', 'ANGMIN', 'ANGMAX', 'PF', 'QF',
            'PT', 'QT', 'MU_SF', 'MU_ST', 'MU_ANGMIN', 'MU_ANGMAX'],
        'gencost': ['MODEL', 'STARTUP', 'SHUTDOWN', 'NCOST', 'COST'],
       }

ATTRIBUTES = ['version', 'baseMVA', 'areas', 'bus', 'gen', 'gencost', 'branch']
