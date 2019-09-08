import pandas as pd

def approximate_bicubic(data, coeff):

    y_predict = coeff['Intercept'] + \
                coeff['x1'] * data['x1'].values + \
                coeff['x2'] * data['x2'].values + \
                coeff['x1_sq'] * data['x1_sq'].values + \
                coeff['x2_sq'] * data['x2_sq'].values + \
                coeff['x1_x2'] * data['x1_x2'].values + \
                coeff['x1_sq_x2'] * data['x1_sq_x2'].values + \
                coeff['x2_sq_x1'] * data['x2_sq_x1'].values + \
                coeff['x1_cube'] * data['x1_cube'].values + \
                coeff['x2_cube'] * data['x2_cube'].values

    return y_predict


def approximate_mass_flows(x1, x2, x3, x4, coeff, ttle):
    data = pd.concat((x1, x2, x3, x4), axis=1)
    # y_predict = coeff['Intercept'] + \
    y_predict = coeff['x1'] * data['x1'].values*data['x4'].values + \
                coeff['x2'] * data['x2'].values*data['x4'].values + \
                coeff['x3'] * data['x3'].values*data['x4'].values
                # coeff['x4'] * data['x4'].values
    y_predict[y_predict < 0] = 0
    # y_predict[y_predict < 0.2 * y_predict.max()] = 0

    return y_predict


def approximate_vav_power(data, coeff):

    # y_predict = coeff['Intercept'] + \
    #             coeff['x1'] * data['x1'].values + \
    #             coeff['x1_sq'] * data['x1_sq'].values + \
    #             coeff['x1_cube'] * data['x1_cube'].values

    y_predict = coeff['x1'] * data['x1'].values + \
                coeff['x1_sq'] * data['x1_sq'].values + \
                coeff['x1_cube'] * data['x1_cube'].values
    return y_predict


def approximate_cav_basement_coefficient(max_power, data, coeff):
    y_predict = coeff['Intercept'] + \
                coeff['x1'] * data['x1'].values + \
                coeff['x2'] * data['x2'].values + \
                coeff['x1_sq'] * data['x1_sq'].values + \
                coeff['x2_sq'] * data['x2_sq'].values + \
                coeff['x1_x2'] * data['x1_x2'].values + \
                coeff['x1_sq_x2'] * data['x1_sq_x2'].values + \
                coeff['x2_sq_x1'] * data['x2_sq_x1'].values + \
                coeff['x1_cube'] * data['x1_cube'].values + \
                coeff['x2_cube'] * data['x2_cube'].values
    y_predict[y_predict < 0] = 0

    y_predict[y_predict > max_power] = max_power
    y_predict[ (y_predict > max_power/2.0) & (y_predict < max_power)] = max_power
    y_predict[(y_predict == 0) & (y_predict < max_power/2.0) ] = max_power
    return y_predict


def approx_Evaporator_Load_Chiller(max_power, data, coeff):

    y_predict = coeff['Intercept'] + \
                coeff['x1'] * data['x1'].values + \
                coeff['x2'] * data['x2'].values + \
                coeff['x1_sq'] * data['x1_sq'].values + \
                coeff['x2_sq'] * data['x2_sq'].values + \
                coeff['x1_x2'] * data['x1_x2'].values + \
                coeff['x1_sq_x2'] * data['x1_sq_x2'].values + \
                coeff['x2_sq_x1'] * data['x2_sq_x1'].values + \
                coeff['x1_cube'] * data['x1_cube'].values + \
                coeff['x2_cube'] * data['x2_cube'].values
    y_predict[y_predict < 0] = 0
    y_predict[y_predict < 0.1*max_power] = 0
    y_predict[y_predict > max_power] = max_power
    return y_predict

def approx_Condenser_Leaving_Temp(max_temp, min_temp, data, coeff):
    y_predict = coeff['Intercept'] + \
                coeff['x1'] * data['x1'].values + \
                coeff['x2'] * data['x2'].values + \
                coeff['x1_sq'] * data['x1_sq'].values + \
                coeff['x2_sq'] * data['x2_sq'].values + \
                coeff['x1_x2'] * data['x1_x2'].values + \
                coeff['x1_sq_x2'] * data['x1_sq_x2'].values + \
                coeff['x2_sq_x1'] * data['x2_sq_x1'].values + \
                coeff['x1_cube'] * data['x1_cube'].values + \
                coeff['x2_cube'] * data['x2_cube'].values
    y_predict[y_predict < 0] = 0
    y_predict[y_predict > max_temp] = max_temp
    y_predict[y_predict < min_temp] = min_temp
    return y_predict

def approx_cooling_Tower_Fan(max_power, data, coeff):
    y_predict = coeff['Intercept'] + \
                coeff['x1'] * data['x1'].values + \
                coeff['x2'] * data['x2'].values + \
                coeff['x1_sq'] * data['x1_sq'].values + \
                coeff['x2_sq'] * data['x2_sq'].values + \
                coeff['x1_x2'] * data['x1_x2'].values + \
                coeff['x1_sq_x2'] * data['x1_sq_x2'].values + \
                coeff['x2_sq_x1'] * data['x2_sq_x1'].values + \
                coeff['x1_cube'] * data['x1_cube'].values + \
                coeff['x2_cube'] * data['x2_cube'].values
    y_predict[y_predict < 0] = 0
    y_predict[y_predict > max_power] = max_power
    return y_predict

def approx_primary_pump_power(max_power, data, coeff):
    y_predict = coeff['Intercept'] + \
                coeff['x1'] * data['x1'].values + \
                coeff['x2'] * data['x2'].values + \
                coeff['x1_sq'] * data['x1_sq'].values + \
                coeff['x2_sq'] * data['x2_sq'].values + \
                coeff['x1_x2'] * data['x1_x2'].values + \
                coeff['x1_sq_x2'] * data['x1_sq_x2'].values + \
                coeff['x2_sq_x1'] * data['x2_sq_x1'].values + \
                coeff['x1_cube'] * data['x1_cube'].values + \
                coeff['x2_cube'] * data['x2_cube'].values
    y_predict[y_predict < 0] = 0
    y_predict[y_predict > max_power] = max_power
    y_predict[y_predict < 0.1*max_power] = 0

    return y_predict

def approx_Chiller1_Power(Agent):
    CAPFT = Agent.parameters_chiller_a0 \
            + Agent.parameters_chiller_a1_Tchws_1 * Agent.parameters_chiller_chilled_water_temp \
            + Agent.parameters_chiller_a2_Tchws_2 * Agent.parameters_chiller_chilled_water_temp ** 2 \
            + Agent.parameters_chiller_a3_Tcnds_1 * Agent.approx_Condenser_Leaving_Temperature_Chiller1.values \
            + Agent.parameters_chiller_a4_Tcnds_2 * Agent.approx_Condenser_Leaving_Temperature_Chiller1.values ** 2 \
            + Agent.parameters_chiller_a5_Tchws_Tcnds * Agent.approx_Condenser_Leaving_Temperature_Chiller1.values * Agent.parameters_chiller_chilled_water_temp

    P_avail = Agent.parameters_chiller_P_ref_chiller1_Watts * CAPFT
    PLR_chiller1 = Agent.approx_Evaporator_Load_Chiller1 / P_avail
    Cycling_ratio1 = PLR_chiller1 / 0.1
    Cycling_ratio1[PLR_chiller1 / 0.1 > 1] = 1
    PLR_chiller1[PLR_chiller1 > 1.03] = 1.03
    PLR_chiller1[PLR_chiller1 < 0.1] = 0.1
    EIRFT = Agent.parameters_chiller_b0 \
            + Agent.parameters_chiller_b1_Tchws_1 * Agent.parameters_chiller_chilled_water_temp \
            + Agent.parameters_chiller_b2_Tchws_2 * Agent.parameters_chiller_chilled_water_temp ** 2 \
            + Agent.parameters_chiller_b3_Tcnds_1 * Agent.approx_Condenser_Leaving_Temperature_Chiller1.values \
            + Agent.parameters_chiller_b4_Tcnds_2 * Agent.approx_Condenser_Leaving_Temperature_Chiller1.values ** 2 \
            + Agent.parameters_chiller_b5_Tchws_Tcnds * Agent.parameters_chiller_chilled_water_temp * Agent.approx_Condenser_Leaving_Temperature_Chiller1.values

    EIRFPLR_Chiller1 = Agent.parameters_chiller_c0 \
                       + Agent.parameters_chiller_c1_Tcnds_1 * Agent.approx_Condenser_Leaving_Temperature_Chiller1.values \
                       + Agent.parameters_chiller_c2_Tcnds_2 * Agent.approx_Condenser_Leaving_Temperature_Chiller1.values ** 2 \
                       + Agent.parameters_chiller_c3_PLR_1 * PLR_chiller1 \
                       + Agent.parameters_chiller_c4_PLR_2 * PLR_chiller1 ** 2 \
                       + Agent.parameters_chiller_c5_Tcnds_PLR * Agent.approx_Condenser_Leaving_Temperature_Chiller1.values * PLR_chiller1 \
                       + Agent.parameters_chiller_c6_PLR_3 * PLR_chiller1 ** 3
    y_predict = P_avail * EIRFT * EIRFPLR_Chiller1 * Cycling_ratio1 / Agent.parameters_chiller_COP_ref
    return y_predict

def approx_Chiller2_Power(Agent):
    CAPFT = Agent.parameters_chiller_a0 \
            + Agent.parameters_chiller_a1_Tchws_1 * Agent.parameters_chiller_chilled_water_temp \
            + Agent.parameters_chiller_a2_Tchws_2 * Agent.parameters_chiller_chilled_water_temp ** 2 \
            + Agent.parameters_chiller_a3_Tcnds_1 * Agent.approx_Condenser_Leaving_Temperature_Chiller2.values \
            + Agent.parameters_chiller_a4_Tcnds_2 * Agent.approx_Condenser_Leaving_Temperature_Chiller2.values ** 2 \
            + Agent.parameters_chiller_a5_Tchws_Tcnds * Agent.approx_Condenser_Leaving_Temperature_Chiller2.values * Agent.parameters_chiller_chilled_water_temp

    P_avail = Agent.parameters_chiller_P_ref_chiller2_Watts * CAPFT
    PLR_Chiller2 = Agent.approx_Evaporator_Load_Chiller2 / P_avail
    Cycling_ratio1 = PLR_Chiller2 / 0.1
    Cycling_ratio1[PLR_Chiller2 / 0.1 > 1] = 1
    PLR_Chiller2[PLR_Chiller2 > 1.03] = 1.03
    PLR_Chiller2[PLR_Chiller2 < 0.1] = 0.1
    EIRFT = Agent.parameters_chiller_b0 \
            + Agent.parameters_chiller_b1_Tchws_1 * Agent.parameters_chiller_chilled_water_temp \
            + Agent.parameters_chiller_b2_Tchws_2 * Agent.parameters_chiller_chilled_water_temp ** 2 \
            + Agent.parameters_chiller_b3_Tcnds_1 * Agent.approx_Condenser_Leaving_Temperature_Chiller2.values \
            + Agent.parameters_chiller_b4_Tcnds_2 * Agent.approx_Condenser_Leaving_Temperature_Chiller2.values ** 2 \
            + Agent.parameters_chiller_b5_Tchws_Tcnds * Agent.parameters_chiller_chilled_water_temp * Agent.approx_Condenser_Leaving_Temperature_Chiller2.values

    EIRFPLR_Chiller2 = Agent.parameters_chiller_c0 \
                       + Agent.parameters_chiller_c1_Tcnds_1 * Agent.approx_Condenser_Leaving_Temperature_Chiller2.values \
                       + Agent.parameters_chiller_c2_Tcnds_2 * Agent.approx_Condenser_Leaving_Temperature_Chiller2.values ** 2 \
                       + Agent.parameters_chiller_c3_PLR_1 * PLR_Chiller2 \
                       + Agent.parameters_chiller_c4_PLR_2 * PLR_Chiller2 ** 2 \
                       + Agent.parameters_chiller_c5_Tcnds_PLR * Agent.approx_Condenser_Leaving_Temperature_Chiller2.values * PLR_Chiller2 \
                       + Agent.parameters_chiller_c6_PLR_3 * PLR_Chiller2 ** 3
    y_predict = P_avail * EIRFT * EIRFPLR_Chiller2 * Cycling_ratio1 / Agent.parameters_chiller_COP_ref
    return y_predict
