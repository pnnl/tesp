#	Copyright (C) 2017 Battelle Memorial Institute
from TransmissionMetricsProcessor import TransmissionMetricsProcessor
import os
import matplotlib.pyplot as plt

# root = []
# for root, dirs, files in os.walk(r'''C:\Qiuhua\FY2016_Project_Transactive_system\Simulation_Year1\SGIP1\\'''):
#     # print(root)
#     print (dirs)
#     # print (files)

d=r'''C:\Qiuhua\FY2016_Project_Transactive_system\Simulation_Year1\SGIP1'''
subdir = [os.path.join(d,o) for o in os.listdir(d) if os.path.isdir(os.path.join(d,o))]
print(subdir)

foldernames = [name for name in os.listdir(d) if os.path.isdir(os.path.join(d,name))]
print(foldernames)

all_bus_metrics = {}
all_gen_metrics = {}
colors = {0:'k', 1: 'b', 2:'r', 3: 'g',4: 'm',5:'y'}

fig1,ax1 = plt.subplots()

for i in range(0,len(subdir)):
    casepath = subdir[i]+"\\"
    casename = foldernames[i]  # 'SGIP1a'
    tmp = TransmissionMetricsProcessor()

    tmp.loadAllMetricsFromJSONFiles(casename, casepath)

    #print(tmp.get_bus_metrics())
    print('\n\n', casename)
    # print('\n',tmp.get_bus_metrics_at_bus(7).LMP_P.values)
    # print('\n', tmp.get_bus_metrics_at_bus(7).VMAG.values)

    tmp.get_bus_metrics_at_bus(7).LMP_P.plot(ax = ax1, color = colors[i],label=casename)
    #tmp.get_bus_metrics_at_bus(7).VMAG.plot(ax=axes[i])
    all_bus_metrics[casename] = tmp.get_bus_metrics()
    all_gen_metrics[casename] = tmp.get_gen_metrics()

ax1.set(title ='Bus LMP comparision', xlabel='Time (hour)',ylabel='LMP ($/kWh)')


# fig2 = plt.figure(2)





##/// data for table
print('\ntotal gen cost, revenue, profit:')
for case in foldernames:
    earning = all_gen_metrics[case].REVENUE.sum().values
    cost = all_gen_metrics[case].COST.sum().values
    profit = earning-cost
    print(case, ",", cost,",",earning,",",profit)



print('\ntotal gen emissions CO2, Sox, Nox (lb):')
for case in foldernames:
    co2 =  all_gen_metrics[case].EMISSION_CO2.sum().values
    sox = all_gen_metrics[case].EMISSION_SOX.sum().values
    nox = all_gen_metrics[case].EMISSION_NOX.sum().values
    print(case, ",", co2, ",", sox, ",", nox)


fig2, axes = plt.subplots(nrows=len(foldernames))
print('\ntotal Ancillary generation output:')
i = 0
for case in foldernames:
    all_gen_metrics[case].sel(busNum = 1).PGEN.plot( ax = axes[i],color = colors[i],label=casename)
    i = i+1

plt.show()