from DistributionMetricsProcessor import DistributionMetricsProcessor
import os
import matplotlib
import matplotlib.pyplot as plt

d = r'''../SGIP1new'''
subdir = [os.path.join(d, o) for o in os.listdir(d) if os.path.isdir(os.path.join(d, o))]
print(subdir)

folder_names = [name for name in os.listdir(d) if os.path.isdir(os.path.join(d, name))]
print(folder_names)

time_interval_hours = {}
all_subs_metrics = {}
subsElectricity = {}
subsRealPower = {}
all_house_metrics = {}
all_meter_metrics = {}
voltageViolationCounts = {}
all_inverter_metrics = {}
BatteryRevenue_noEvent = {}
BatteryRevenue_Event = {}
PVRevenue_noEvent = {}
PVRevenue_Event = {}
PVRevenue = {}
BatteryRevenue = {}

colors = {0: 'k', 1: 'b', 2: 'r', 3: 'g', 4: 'm', 5: 'y'}

case_name = None
for i in range(0, len(subdir)):

    case_path = subdir[i] + "/"
    case_name = folder_names[i]  # 'SGIP1a'
    tmp = DistributionMetricsProcessor()

    tmp.loadAllMetricsFromJSONFiles(case_name, case_path)

    time_interval_hours[case_name] = tmp.time_interval_hours

    print('\n\n', case_name)

    # Substation metrics
    all_subs_metrics[case_name] = tmp.get_subs_metrics()
    subsElectricity[case_name] = tmp.get_subs_electricity()
    subsRealPower[case_name] = tmp.get_subs_realPower() / 1000

    # House metrics
    all_house_metrics[case_name] = tmp.get_house_metrics()

    # Meter metrics
    all_meter_metrics[case_name] = tmp.get_metering_metrics()
    voltageViolationCounts[case_name] = tmp.get_volt_violation_counts()

    # Inverter metrics
    all_inverter_metrics[case_name] = tmp.get_inverter_metrics()
    if all_inverter_metrics[case_name] is not None:
        BatteryRevenue_noEvent[case_name] = tmp.get_battery_total_revenue("", 0, 24)
        BatteryRevenue_Event[case_name] = tmp.get_battery_total_revenue("", 24, 48)
        PVRevenue_noEvent[case_name] = tmp.get_PV_total_revenue("", 0, 24)
        PVRevenue_Event[case_name] = tmp.get_PV_total_revenue("", 24, 48)
    else:
        BatteryRevenue_noEvent[case_name] = 0.0
        BatteryRevenue_Event[case_name] = 0.0
        PVRevenue_noEvent[case_name] = 0.0
        PVRevenue_Event[case_name] = 0.0
    if all_inverter_metrics[case_name] is not None:
        BatteryRevenue[case_name] = tmp.get_battery_total_revenue("", 0, 48)
        PVRevenue[case_name] = tmp.get_PV_total_revenue("", 0, 48)
    else:
        BatteryRevenue[case_name] = 0.0
        PVRevenue[case_name] = 0.0

# data for table
print('\ntotal feeder electricity (kWh), total feeder real power (kW), ' +
      'average customer real power (kW/customer), meter bills (USD), ' +
      'meter bills per customer (USD/customer), house energy consumption (kWh), ' +
      'house energy consumption per customer (kWh/customer), house HVAC consumption (kWh), ' +
      'house HVAC consumption per customer (kWh/customer):')
for case in folder_names:
    totalRealPower = subsRealPower[case].sum().values
    totalElectricity = subsElectricity[case].sum().values
    # Bill calculation from the meter metrics_collector is not correct
    # bills = all_meter_metrics[case].Bill.sum().values
    bills = totalElectricity * 0.1243
    house_energy = (all_house_metrics[case].Total_load * time_interval_hours[case]).sum(dim='time').sum().values
    house_num = all_house_metrics[case].houseID.size
    HVAC_energy = (all_house_metrics[case].Total_HVACloads * time_interval_hours[case]).sum(dim='time').sum().values
    print(case, ",", totalElectricity, ",", totalRealPower, ",", totalRealPower / house_num, ",", bills, ",",
          bills / house_num, ",", house_energy, ",", house_energy / house_num, ",", HVAC_energy, ",",
          HVAC_energy / house_num)

print('\ntotal voltage violation counts:')
for case in folder_names:
    print(case, ",", voltageViolationCounts)

print('\ntotal Solar PV outputs (kW), PV revenue (USD), battery outputs (kW), battery revenue (USD):')
for case in folder_names:
    PVOutput = 0
    BatteryOutput = 0
    if all_inverter_metrics[case] is not None:
        # inverter unit is W
        PVOutput = all_inverter_metrics[case].sel_points(
            inverterID=all_inverter_metrics[case].attrs['solar_inverter_ids']).Real_power_avg.sum().values / 1000
        BatteryOutput = all_inverter_metrics[case].sel_points(
            inverterID=all_inverter_metrics[case].attrs['battery_inverter_ids']).Real_power_avg.sum().values / 1000
        batteryNum = all_inverter_metrics[case].attrs['battery_inverter_ids'].__len__()
        PVNum = all_inverter_metrics[case].attrs['solar_inverter_ids'].__len__()
        print(PVNum, batteryNum)
    print(PVOutput, ",", PVRevenue[case], ",", BatteryOutput, ",", BatteryRevenue[case])

print('\n(non-event day) total feeder electricity (kWh), total meter bills (USD), ' +
      'average residential customer electricity (kWh/customer), ' +
      'meter bills per residential customer (USD/customer):')
for case in folder_names:
    totalElectricity = subsElectricity[case].where(
        (subsElectricity[case].time >= 0) & (subsElectricity[case].time <= 24)).sum().values
    bills = totalElectricity * 0.1243
    house_num = all_house_metrics[case].where(
        (all_house_metrics[case].time >= 0) & (all_house_metrics[case].time <= 24)).houseID.size
    eplusMeter = all_meter_metrics[case].where(all_meter_metrics[case].meterID == "R1_12_47_1_load_4_Eplus_meter4")
    eplusEnergy = eplusMeter.where((eplusMeter.time >= 0) & (eplusMeter.time <= 24),
                                   drop=True).real_energy.sum().values / 1000  # meter energy unit is Wh
    residentialEnergy = totalElectricity - eplusEnergy
    residentialBill = residentialEnergy * 0.1243
    print(case, ",", totalElectricity, ",", bills, ",", residentialEnergy / house_num, ",", residentialBill / house_num)

print('\n(event day) total feeder electricity (kWh), total meter bills (USD), ' +
      'average residential customer electricity (kWh/customer), ' +
      'meter bills per residential customer (USD/customer):')
for case in folder_names:
    totalElectricity = subsElectricity[case].where(
        (subsElectricity[case].time > 24) & (subsElectricity[case].time <= 48)).sum().values
    bills = totalElectricity * 0.1243
    house_num = all_house_metrics[case].where(
        (all_house_metrics[case].time > 24) & (all_house_metrics[case].time <= 48)).houseID.size
    eplusMeter = all_meter_metrics[case].where(all_meter_metrics[case].meterID == "R1_12_47_1_load_4_Eplus_meter4")
    eplusEnergy = eplusMeter.where((eplusMeter.time > 24) & (eplusMeter.time <= 48),
                                   drop=True).real_energy.sum().values / 1000  # meter energy unit is Wh
    residentialEnergy = totalElectricity - eplusEnergy
    residentialBill = residentialEnergy * 0.1243
    print(case, ",", totalElectricity, ",", bills, ",", residentialEnergy / house_num, ",", residentialBill / house_num)

print('\ntotal voltage violation counts:')
for case in folder_names:
    print(case, ",", voltageViolationCounts)

# Generate table results for 5 cases together
print('\n(non-event day) total feeder electricity (kWh), total meter bills (USD), ' +
      'average residential customer electricity (kWh/customer), ' +
      'meter bills per residential customer (USD/customer):')
for case in folder_names:
    totalElectricity = subsElectricity[case].where(
        (subsElectricity[case].time >= 0) & (subsElectricity[case].time <= 24)).sum().values
    bills = totalElectricity * 0.1243
    house_num = all_house_metrics[case].where(
        (all_house_metrics[case].time >= 0) & (all_house_metrics[case].time <= 24)).houseID.size
    eplusMeter = all_meter_metrics[case].where(all_meter_metrics[case].meterID == "R1_12_47_1_load_4_Eplus_meter4")
    eplusEnergy = eplusMeter.where((eplusMeter.time >= 0) & (eplusMeter.time <= 24),
                                   drop=True).real_energy.sum().values / 1000  # meter energy unit is Wh
    residentialEnergy = totalElectricity - eplusEnergy
    residentialBill = residentialEnergy * 0.1243
    print(case, ",", totalElectricity, ",", bills, ",", residentialEnergy / house_num, ",", residentialBill / house_num)

print('\n(event day) total feeder electricity (kWh), total meter bills (USD), ' +
      'average residential customer electricity (kWh/customer), ' +
      'meter bills per residential customer (USD/customer):')
for case in folder_names:
    totalElectricity = subsElectricity[case].where(
        (subsElectricity[case].time > 24) & (subsElectricity[case].time <= 48)).sum().values
    bills = totalElectricity * 0.1243
    house_num = all_house_metrics[case].where(
        (all_house_metrics[case].time > 24) & (all_house_metrics[case].time <= 48)).houseID.size
    eplusMeter = all_meter_metrics[case].where(all_meter_metrics[case].meterID == "R1_12_47_1_load_4_Eplus_meter4")
    eplusEnergy = eplusMeter.where((eplusMeter.time > 24) & (eplusMeter.time <= 48),
                                   drop=True).real_energy.sum().values / 1000  # meter energy unit is Wh
    residentialEnergy = totalElectricity - eplusEnergy
    residentialBill = residentialEnergy * 0.1243
    print(case, ",", totalElectricity, ",", bills, ",", residentialEnergy / house_num, ",", residentialBill / house_num)

print('\n(non-event day) total Solar PV outputs (kW), PV output energy (kWh), ' +
      'PV output energy per unit (kWh/unit), PV revenue (USD), battery outputs (kW), ' +
      'battery discharge energy (kWh), battery charge energy (kWh), ' +
      'battery discharge energy per unit (kWh/unit), ' +
      'battery charge energy per unit (kWh/unit), battery revenue (USD):')
for case in folder_names:
    PVOutput = 0
    PVOutputEnergy = 0
    BatteryOutput = 0
    BatteryDischargeEnergy = 0
    BatteryChargeEnergy = 0
    revenue_p = 0
    revenue_b = 0
    PVOutputEnergyPerUnit = 0
    BatteryDischargeEnergyPerUnit = 0
    BatteryChargeEnergyPerUnit = 0
    if all_inverter_metrics[case] is not None:
        # inverter unit is W
        # PV inverter
        PVOutputVals = all_inverter_metrics[case].where(
            (all_house_metrics[case].time >= 0) & (all_house_metrics[case].time <= 24), drop=True).sel_points(
            inverterID=all_inverter_metrics[case].attrs['solar_inverter_ids']).Real_power_avg.values / 1000
        PVOutput = PVOutputVals.sum()
        PVOutputEnergy = (PVOutputVals * time_interval_hours[case_name]).sum()
        # Battery
        BatteryOutputVals = all_inverter_metrics[case].where(
            (all_house_metrics[case].time >= 0) & (all_house_metrics[case].time <= 24), drop=True).sel_points(
            inverterID=all_inverter_metrics[case].attrs['battery_inverter_ids']).Real_power_avg.values / 1000
        BatteryOutput = BatteryOutputVals.sum()
        BatteryDischargeEnergy = (BatteryOutputVals[BatteryOutputVals > 0] * time_interval_hours[case_name]).sum()
        BatteryChargeEnergy = (BatteryOutputVals[BatteryOutputVals < 0] * time_interval_hours[case_name]).sum()
        # Just to confirm the numbers here
        batteryNum = all_inverter_metrics[case].where(
            (all_house_metrics[case].time >= 0) & (all_house_metrics[case].time <= 24)).attrs[
            'battery_inverter_ids'].__len__()
        PVNum = all_inverter_metrics[case].where(
            (all_house_metrics[case].time >= 0) & (all_house_metrics[case].time <= 24)).attrs[
            'solar_inverter_ids'].__len__()
        # Per unit electricity calculation
        PVOutputEnergyPerUnit = PVOutputEnergy / PVNum
        BatteryDischargeEnergyPerUnit = BatteryDischargeEnergy / batteryNum
        BatteryChargeEnergyPerUnit = BatteryChargeEnergy / batteryNum
    print(PVOutput, ",", PVOutputEnergy, ",", PVOutputEnergyPerUnit, ",", PVRevenue_noEvent[case], ",", BatteryOutput,
          ",", BatteryDischargeEnergy, ",", BatteryChargeEnergy, ",", BatteryDischargeEnergyPerUnit, ",",
          BatteryChargeEnergyPerUnit, ",", BatteryRevenue_noEvent[case])

print('\n(event day) total Solar PV outputs (kW), PV output energy (kWh), ' +
      'PV output energy per unit (kWh/unit), PV revenue (USD), battery outputs (kW), ' +
      'battery discharge energy (kWh), battery charge energy (kWh), ' +
      'battery discharge energy per unit (kWh/unit), ' +
      'battery charge energy per unit (kWh/unit), battery revenue (USD):')
for case in folder_names:
    PVOutput = 0
    PVOutputEnergy = 0
    BatteryOutput = 0
    BatteryDischargeEnergy = 0
    BatteryChargeEnergy = 0
    revenue_p = 0
    revenue_b = 0
    PVOutputEnergyPerUnit = 0
    BatteryDischargeEnergyPerUnit = 0
    BatteryChargeEnergyPerUnit = 0
    if all_inverter_metrics[case] is not None:
        # inverter unit is W
        # PV inverter
        PVOutputVals = all_inverter_metrics[case].where(
            (all_house_metrics[case].time > 24) & (all_house_metrics[case].time <= 48), drop=True).sel_points(
            inverterID=all_inverter_metrics[case].attrs['solar_inverter_ids']).Real_power_avg.values / 1000
        PVOutput = PVOutputVals.sum()
        PVOutputEnergy = (PVOutputVals * time_interval_hours[case_name]).sum()
        # Battery
        BatteryOutputVals = all_inverter_metrics[case].where(
            (all_house_metrics[case].time > 24) & (all_house_metrics[case].time <= 48), drop=True).sel_points(
            inverterID=all_inverter_metrics[case].attrs['battery_inverter_ids']).Real_power_avg.values / 1000
        BatteryOutput = BatteryOutputVals.sum()
        BatteryDischargeEnergy = (BatteryOutputVals[BatteryOutputVals > 0] * time_interval_hours[case_name]).sum()
        BatteryChargeEnergy = (BatteryOutputVals[BatteryOutputVals < 0] * time_interval_hours[case_name]).sum()
        # Just to confirm the numbers here
        batteryNum = \
            all_inverter_metrics[case].where((all_house_metrics[case].time > 24) & (all_house_metrics[case].time <= 48),
                                             drop=True).attrs['battery_inverter_ids'].__len__()
        PVNum = all_inverter_metrics[case].where(
            (all_house_metrics[case].time > 24) & (all_house_metrics[case].time <= 48)).attrs[
            'solar_inverter_ids'].__len__()
        # Per unit electricity calculation
        PVOutputEnergyPerUnit = PVOutputEnergy / PVNum
        BatteryDischargeEnergyPerUnit = BatteryDischargeEnergy / batteryNum
        BatteryChargeEnergyPerUnit = BatteryChargeEnergy / batteryNum
    print(PVOutput, ",", PVOutputEnergy, ",", PVOutputEnergyPerUnit, ",", PVRevenue_Event[case], ",", BatteryOutput,
          ",", BatteryDischargeEnergy, ",", BatteryChargeEnergy, ",", BatteryDischargeEnergyPerUnit, ",",
          BatteryChargeEnergyPerUnit, ",", BatteryRevenue_Event[case])

# data for plots
fig1, axes1 = plt.subplots()
plt.grid(True)
axes1.hold(True)
print('\n(non-event day) Total feeder generation output plotted')
i = 0
for case in folder_names:
    plt.plot(all_subs_metrics[case].where((all_subs_metrics[case].time >= 0) & (all_subs_metrics[case].time <= 24),
                                          drop=True).time.values,
             all_subs_metrics[case].where((subsRealPower[case].time >= 0) & (subsRealPower[case].time <= 24),
                                          drop=True).sel(substationID="network_node").Real_power.values / 1000,
             color=colors[i], label=case)
    plt.grid(True)
    i = i + 1
axes1.set(xlabel='Time (hour)', ylabel='Real Power (kW)', title='(non-event day) Total feeder generation output')
plt.xlim([0, 24])
axes1.legend(loc='best')
fig1.suptitle("Non-event day")

fig2, axes2 = plt.subplots()
plt.grid(True)
axes2.hold(True)
print('\n(Event day) Total feeder generation output plotted')
i = 0
for case in folder_names:
    plt.plot(all_subs_metrics[case].where((all_subs_metrics[case].time > 24) & (all_subs_metrics[case].time <= 48),
                                          drop=True).time.values,
             all_subs_metrics[case].where((subsRealPower[case].time > 24) & (subsRealPower[case].time <= 48),
                                          drop=True).sel(substationID="network_node").Real_power.values / 1000,
             color=colors[i], label=case)
    plt.grid(True)
    i = i + 1
axes2.set(xlabel='Time (hour)', ylabel='Real Power (kW)', title='(Event day) Total feeder generation output')
plt.xlim([24, 48])
axes2.legend(loc='best')
fig2.suptitle("Event day")

fig3, axes3 = plt.subplots()
plt.grid(True)
axes3.hold(True)
print('\ntotal feeder generation output:')
i = 0
for case in folder_names:
    plt.plot(all_subs_metrics[case].time.values,
             all_subs_metrics[case].sel(substationID="network_node").Real_power.values / 1000, color=colors[i],
             label=case[-1])
    plt.grid(True)
    i = i + 1
axes3.set_ylabel("kW")
axes3.set_xlabel("time (hour)")
axes3.set_title("Total feeder generation output")
axes3.legend(loc='best')

matplotlib.rcParams.update({'font.size': 22})
plt.show()
