from tesp_support.dsot.hvac_agent import HVACDSOT
import logging as log
from datetime import datetime, timedelta

logger = log.getLogger()
log.getLogger('pyomo.core').setLevel(log.ERROR)

def test():
    """
    Testing

    Makes a single hvac agent and run DA
    """
    hvac_properties = \
        {"feeder_id": "R4_25.00_1",
         "billingmeter_id": "R4_25_00_1_tn_107_mtr_1",
         "sqft": 1040.0,
         "stories": 2,
         "doors": 4,
         "thermal_integrity": "VERY_LITTLE",
         "cooling": "ELECTRIC",
         "heating": "GAS",
         "wh_gallons": 0,
         "house_class": "SINGLE_FAMILY",
         "Rroof": 20.07,
         "Rwall": 11.47,
         "Rfloor": 10.05,
         "Rdoors": 3.27,
         "airchange_per_hour": 0.68,
         "ceiling_height": 9,
         "thermal_mass_per_floor_area": 2.97,
         "aspect_ratio": 1.0,
         "exterior_wall_fraction": 1.0,
         "exterior_floor_fraction": 1.0,
         "exterior_ceiling_fraction": 1.0,
         "window_exterior_transmission_coefficient": 0.57,
         "glazing_layers": 2,
         "glass_type": 1,
         "window_frame": 1,
         "glazing_treatment": 1,
         "cooling_COP": 4.0,
         "over_sizing_factor": 0.2488,
         "fuel_type": "gas",
         "zip_skew": -1716.0,
         "zip_heatgain_fraction": {
             "constant": 1.0,
             "responsive_loads": 0.9,
             "unresponsive_loads": 0.9
         },
         "zip_scalar": {
             "constant": 0.0,
             "responsive_loads": 0.66,
             "unresponsive_loads": 0.65
         },
         "zip_power_fraction": {
             "constant": 1.0,
             "responsive_loads": 1.0,
             "unresponsive_loads": 0.4
         },
         "zip_power_pf": {
             "constant": 1.0,
             "responsive_loads": 1.0,
             "unresponsive_loads": 1.0
         }
         }
    hvac_dict = {
        "houseName": "R4_25_00_1_tn_107_hse_1",
        "meterName": "R4_25_00_1_tn_107_mtr_1",
        "houseClass": "SINGLE_FAMILY",
        "period": 300,
        "wakeup_start": 7.747,
        "daylight_start": 9.246,
        "evening_start": 19.877,
        "night_start": 20.573,
        "weekend_day_start": 9.842,
        "weekend_night_start": 21.93,
        "wakeup_set_cool": 100.0,
        "daylight_set_cool": 100.0,
        "evening_set_cool": 100.0,
        "night_set_cool": 100.0,
        "weekend_day_set_cool": 100.0,
        "weekend_night_set_cool": 100.0,
        "wakeup_set_heat": 60.0,
        "daylight_set_heat": 60.0,
        "evening_set_heat": 60.0,
        "night_set_heat": 60.0,
        "weekend_day_set_heat": 60.0,
        "weekend_night_set_heat": 60.0,
        "deadband": 2.427,
        "ramp_high_limit": 2.0,
        "ramp_low_limit": 2.0,
        "range_high_limit": 5.0,
        "range_low_limit": 3.0,
        "slider_setting": 0.3105,
        "price_cap": 1.0,
        "bid_delay": 45,
        "house_participating": True,
        "cooling_participating": True,
        "heating_participating": False
    }

    # ## Uncomment for testing logging functionality.
    # ## Supply these values (into WaterHeaterDSOT) when using the water
    # ## heater agent in the simulation.
    # model_diag_level = 11
    # helpers.enable_logging('DEBUG', model_diag_level, 'hvac_agent')
    start_time = '2016-08-12 05:59:00'
    time_format = '%Y-%m-%d %H:%M:%S'
    sim_time = datetime.strptime(start_time, time_format)
    obj = HVACDSOT(hvac_dict, hvac_properties, 'abc', 11, sim_time, 'ipopt')
    # obj.set_solargain_forecast(forecast_solargain)
    # if obj.change_basepoint(11, start_time):
    #     pass
    obj.DA_model_parameters(sim_time.minute, sim_time.hour, sim_time.weekday())

    obj.optimized_Quantity, obj.temp_room = obj.DA_optimal_quantities()

    # print(obj.temp_desired_48hour_cool)
    for i in range(10):
        sim_time = sim_time + timedelta(hours=1)
        obj.get_uncntrl_hvac_load(sim_time.minute, sim_time.hour, sim_time.weekday())

        # B_obj.Cinit = B_obj.capacity * 0.5#B_obj.set_SOC()

    # BID = [[-5.0, 6.0], [0.0, 5.0], [0.0, 4.0], [5.0, 3.0]]
    # fixed = B_obj1.RT_fix_four_points_range(BID, 0.0, 10.0)
    # print(fixed)
    # fixed = B_obj1.RT_fix_four_points_range(BID, -float('inf'), 0.0)
    # print(fixed)
    # fixed = B_obj1.RT_fix_four_points_range(BID, 0.0, float('inf'))
    # print(fixed)
    # fixed = B_obj1.RT_fix_four_points_range(BID, 0.5, 0.5)
    # print(fixed)
    # getQ = B_obj1.from_P_to_Q_battery(BID, 10)
    # print(getQ)
    # getQ = B_obj1.from_P_to_Q_battery(fixed, 10)
    # print(getQ)


if __name__ == "__main__":
    test()