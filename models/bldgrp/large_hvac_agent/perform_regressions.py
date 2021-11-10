import pandas as pd
from statsmodels.formula.api import ols
import process_plots as process_plots


def get_mass_flow_coefficients(y, x1, x2, x3, x4, ttl):
    df = pd.concat((x1, x2, x3, x4), axis=1)

    equation = "y ~ x1 + x2 +  x3 - 1"
    model = ols(equation, data=df).fit()
   # print(model.summary())
    coefficients = model.params
    return coefficients


def get_Twetbulb_bicubic_coefficients(y, df):

    equation = "y ~ x1 + x2 + x1_sq + x2_sq + x1_x2 + x1_sq_x2 + x2_sq_x1 + x1_cube + x2_cube"
    model = ols(equation, data=df).fit()
    # print(model.summary())
    coefficients = model.params

    return coefficients

def get_VAV_Power_Coefficient(y, df):

    equation = "y ~ x1 + x1_sq + x1_cube - 1"
    model = ols(equation, data=df).fit()
    # print(model.summary())
    coefficients = model.params

    return coefficients

def get_basement_cav_coefficient(y, df):

    equation = "y ~ x1 + x2 + x1_sq + x2_sq + x1_x2 + x1_sq_x2 + x2_sq_x1 + x1_cube + x2_cube"
    model = ols(equation, data=df).fit()
    # print(model.summary())
    coefficients = model.params
    return coefficients

def get_evaporator_load_chiller(y, df):

    equation = "y ~ x1 + x2 + x1_sq + x2_sq + x1_x2 + x1_sq_x2 + x2_sq_x1 + x1_cube + x2_cube"
    model = ols(equation, data=df).fit()
    # print(model.summary())
    coefficients = model.params
    return coefficients


def get_condenser_leaving_temp(y, df):

    equation = "y ~ x1 + x2 + x1_sq + x2_sq + x1_x2 + x1_sq_x2 + x2_sq_x1 + x1_cube + x2_cube"
    model = ols(equation, data=df).fit()
    # print(model.summary())
    coefficients = model.params
    return coefficients

def get_cooling_fan_power(y, df):
    equation = "y ~ x1 + x2 + x1_sq + x2_sq + x1_x2 + x1_sq_x2 + x2_sq_x1 + x1_cube + x2_cube"
    model = ols(equation, data=df).fit()
    # print(model.summary())
    coefficients = model.params
    return coefficients

def get_pump_power(y, df):
    equation = "y ~ x1 + x2 + x1_sq + x2_sq + x1_x2 + x1_sq_x2 + x2_sq_x1 + x1_cube + x2_cube"
    model = ols(equation, data=df).fit()
    # print(model.summary())
    coefficients = model.params
    return coefficients