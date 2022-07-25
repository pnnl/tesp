from TransmissionMetricsProcessor import TransmissionMetricsProcessor
import os
import matplotlib.pyplot as plt
import matplotlib 

plt.rc('xtick',labelsize=22)
plt.rc('ytick',labelsize=22)
plt.rc('legend',fontsize=22)
plt.rc('axes',labelsize=22)


d=r'''../SGIP1new'''
subdir = [os.path.join(d,o) for o in os.listdir(d) if os.path.isdir(os.path.join(d,o))]
print(subdir)

foldernames = [name for name in os.listdir(d) if os.path.isdir(os.path.join(d,name))]
print(foldernames)

all_bus_metrics = {}
all_gen_metrics = {}

all_bus_metrics_nonEventDay = {}
all_gen_metrics_nonEventDay = {}

all_bus_metrics_eventDay = {}
all_gen_metrics_eventDay = {}

colors = {0:'k', 1: 'b', 2:'r', 3: 'g',4: 'm',5:'y'}
time_interval_hours = 5/60

for i in range(0,len(subdir)):
    casepath = subdir[i]+"/"
    casename = foldernames[i]  # 'SGIP1a'
    tmp = TransmissionMetricsProcessor()

    tmp.loadAllMetricsFromJSONFiles(casename, casepath)
    if i ==0:
        time_interval_hours = 5/60  ##5 mins by default

        #print(tmp.get_bus_metrics())
    print('\n\n', casename)
    # print('\n',tmp.get_bus_metrics_at_bus(7).LMP_P.values)
    # print('\n', tmp.get_bus_metrics_at_bus(7).VMAG.values)
    # if(i<2):
    #     tmp.get_bus_metrics_at_bus(7).LMP_P.plot(ax = ax1, color = colors[i],label=casename)
    tmp.get_bus_metrics_at_bus(7).PD.plot( color=colors[i], label=casename)
    #(tmp.get_bus_metrics_at_bus(7).LMP_P*1000).plot(ax=ax1[i], color=colors[i], label=casename)
    #tmp.get_bus_metrics_at_bus(7).VMAG.plot(ax=axes[i])
    all_bus_metrics[casename] = tmp.get_bus_metrics()
    all_gen_metrics[casename] = tmp.get_gen_metrics()

    all_bus_metrics_nonEventDay[casename] = tmp.get_bus_metrics_for_period(0,24)
    all_gen_metrics_nonEventDay[casename] = tmp.get_gen_metrics_for_period(0,24)

    all_bus_metrics_eventDay[casename] = tmp.get_bus_metrics_for_period(24,48)
    all_gen_metrics_eventDay[casename] = tmp.get_gen_metrics_for_period(24,48)


fig1=plt.figure()
ax1 = fig1.add_subplot(211)

i = 0
for case in foldernames:
    #all_gen_metrics[case].sel(busNum = 4).PGEN.plot( ax = axes,color = colors[i],label=casename)
    plt.plot(all_bus_metrics_nonEventDay[case].sel(busNum = 7).time.values, all_bus_metrics_nonEventDay[case].sel(busNum = 7).PD.values,color = colors[i],label=case)
    i = i+1

ax1.legend(loc='best')
ax1.grid(True)
#ax1.set(title ='Bus LMP comparision', xlabel='Time (hours)',ylabel='LMP ($/kWh)')
ax1.set(title ='Bus 7 total load', xlabel='Time (hour)',ylabel='Load (MW)')


ax2 = fig1.add_subplot(212)
# axes.hold(True)
i = 0
for case in foldernames:
    plt.plot(all_bus_metrics_nonEventDay[case].sel(busNum = 7).time.values, all_bus_metrics_nonEventDay[case].sel(busNum = 7).LMP_P.values,color = colors[i],label=case)
    i = i+1

ax2.legend(loc='best')
ax2.set(xlabel = 'Time (hour)', ylabel='LMP ($/kWh)',title='LMP of bus 7')
ax2.grid(True)

fig1.suptitle("Non-event day")

##

fig2, axes = plt.subplots()
# axes.hold(True)
print('\ntotal Ancillary generation output (non-event day):')
i = 0
for case in foldernames:
    #all_gen_metrics[case].sel(busNum = 4).PGEN.plot( ax = axes,color = colors[i],label=casename)
    plt.plot(all_gen_metrics_nonEventDay[case].sel(busNum = 4).time.values, all_gen_metrics_nonEventDay[case].sel(busNum = 4).PGEN.values,color = colors[i],label=case)
    i = i+1

axes.legend(loc='best')
axes.set(xlabel = 'Time (hour)', ylabel='Power(MW)',title='Ancillary service generator output on non-event day (MW)')
axes.grid(True)



##

fig3, axes = plt.subplots()
# axes.hold(True)
i = 0
for case in foldernames:
    #all_gen_metrics[case].sel(busNum = 4).PGEN.plot( ax = axes,color = colors[i],label=casename)
    plt.plot(all_bus_metrics_nonEventDay[case].sel(busNum = 7).time.values, all_bus_metrics_nonEventDay[case].sel(busNum = 7).LMP_P.values,color = colors[i],label=case)
    i = i+1

axes.legend(loc='best')
axes.set(xlabel = 'Time (hour)', ylabel='LMP ($/kWh)',title='LMP of bus 7 (non-event day)')
axes.grid(True)

LMP_avg_nonEvent = []
LMP_max_nonEvent = []
LMP_min_nonEvent = []

## average, MAX AND MIN LMP
print('\n CASE, LMP AVG, LMP MAX, LMP MIN, (non-event day):')
for case in foldernames:
   avg= all_bus_metrics_nonEventDay[case].sel(busNum = 7).LMP_P.mean().values
   max =all_bus_metrics_nonEventDay[case].sel(busNum = 7).LMP_P.max().values
   min =all_bus_metrics_nonEventDay[case].sel(busNum = 7).LMP_P.min().values

   LMP_avg_nonEvent.append(avg)
   LMP_max_nonEvent.append(max)
   LMP_min_nonEvent.append(min)
   print(case, ",", avg, ",", max, ",", min)

print ('Baseline','Test','Impact')
print (LMP_avg_nonEvent[0],LMP_avg_nonEvent[1],LMP_avg_nonEvent[1]-LMP_avg_nonEvent[0])

gen_cost =[]
gen_revenue =[]
gen_profit =[]

##/// data for table
print('\ntotal gen cost, revenue, profit(non-event day):')
for case in foldernames:
    earning = all_gen_metrics_nonEventDay[case].REVENUE.sum().values
    cost = all_gen_metrics_nonEventDay[case].COST.sum().values
    profit = earning-cost

    gen_cost.append(cost)
    gen_revenue.append(earning)
    gen_profit.append(profit)

    print(case, ",", cost,",",earning,",",profit)

print('\ngen Cost')
print ('Baseline','Test','Impact')
print (gen_cost[0],gen_cost[1],gen_cost[1]-gen_cost[0])

em_co2 =[]
em_sox =[]
em_nox =[]

print('\ntotal gen emissions CO2, Sox, Nox (lb) (non-event day):')
for case in foldernames:
    co2 =  all_gen_metrics_nonEventDay[case].EMISSION_CO2.sum().values
    sox = all_gen_metrics_nonEventDay[case].EMISSION_SOX.sum().values
    nox = all_gen_metrics_nonEventDay[case].EMISSION_NOX.sum().values
    print(case, ",", co2, ",", sox, ",", nox)

    em_co2.append(co2)
    em_sox.append(sox)
    em_nox.append(nox)

print('\ngen emission CO2')
print ('Baseline','Test','Impact')
print (em_co2[0],em_co2[1],em_co2[1]-em_co2[0])

print('\ngen emission SOX')
print ('Baseline','Test','Impact')
print (em_sox[0],em_sox[1],em_sox[1]-em_sox[0])

print('\ngen emission NOX')
print ('Baseline','Test','Impact')
print (em_nox[0],em_nox[1],em_nox[1]-em_nox[0])


print('\n Distribution utility (at bus 7) expense (non-event day):')
i = 0
for case in foldernames:
    # plt.plot( kind = 'bar', (all_bus_metrics[case].sel(busNum = 7).LMP_P*all_bus_metrics[case].sel(busNum = 7).PD).sum().values , color = colors[i],label=case)
    fee = (all_bus_metrics_nonEventDay[case].sel(busNum = 7).LMP_P*1000.0*time_interval_hours*all_bus_metrics_nonEventDay[case].sel(busNum = 7).PD).sum().values
    print(case, ",", )
    i = i+1

print('\ngen emission NOX')
print ('Baseline','Test','Impact')
print (em_nox[0],em_nox[1],em_nox[1]-em_nox[0])

###==============================================Event day ========================================================================

fig1=plt.figure()
ax1 = fig1.add_subplot(211)

i = 0
for case in foldernames:
    #all_gen_metrics[case].sel(busNum = 4).PGEN.plot( ax = axes,color = colors[i],label=casename)
    plt.plot(all_bus_metrics_eventDay[case].sel(busNum = 7).time.values, all_bus_metrics_eventDay[case].sel(busNum = 7).PD.values,color = colors[i],label=case)
    i = i+1

ax1.legend(loc='best')
ax1.grid(True)
#ax1.set(title ='Bus LMP comparision', xlabel='Time (hours)',ylabel='LMP ($/kWh)')
ax1.set(title ='Bus 7 total load', xlabel='Time (hour)',ylabel='Load (MW)')


ax2 = fig1.add_subplot(212)
# axes.hold(True)
i = 0
for case in foldernames:
    plt.plot(all_bus_metrics_eventDay[case].sel(busNum = 7).time.values, all_bus_metrics_eventDay[case].sel(busNum = 7).LMP_P.values,color = colors[i],label=case)
    i = i+1

ax2.legend(loc='best')
ax2.set(xlabel = 'Time (hour)', ylabel='LMP ($/kWh)',title='LMP of bus 7')
ax2.grid(True)
fig1.suptitle("Event day")

fig2, axes = plt.subplots()
# axes.hold(True)
print('\ntotal Ancillary generation output (event day):')
i = 0
for case in foldernames:
    #all_gen_metrics[case].sel(busNum = 4).PGEN.plot( ax = axes,color = colors[i],label=casename)
    plt.plot(all_gen_metrics_eventDay[case].sel(busNum = 4).time.values, all_gen_metrics_eventDay[case].sel(busNum = 4).PGEN.values,color = colors[i],label=case)
    i = i+1

axes.legend(loc='best')
axes.set(xlabel = 'Time (hour)', ylabel='Power(MW)',title='Ancillary service generator output on event day (MW)')
axes.grid(True)

fig3, axes = plt.subplots()
# axes.hold(True)
i = 0
for case in foldernames:
    #all_gen_metrics[case].sel(busNum = 4).PGEN.plot( ax = axes,color = colors[i],label=casename)
    plt.plot(all_bus_metrics_eventDay[case].sel(busNum = 7).time.values, all_bus_metrics_eventDay[case].sel(busNum = 7).LMP_P.values,color = colors[i],label=case)
    i = i+1

axes.legend(loc='best')
axes.set(xlabel = 'Time (hour)', ylabel='LMP ($/kWh)',title='LMP of bus 7 (event day)')
axes.grid(True)

fig4, axes = plt.subplots()
# axes.hold(True)
i = 0
for case in foldernames:
    #all_gen_metrics[case].sel(busNum = 4).PGEN.plot( ax = axes,color = colors[i],label=casename)
    plt.plot(all_bus_metrics[case].sel(busNum = 7).time.values, all_bus_metrics[case].sel(busNum = 7).LMP_P.values,color = colors[i],label=case)
    i = i+1

axes.legend(loc='best')
axes.set(xlabel = 'Time (hour)', ylabel='LMP ($/kWh)',title='LMP of bus 7')
axes.grid(True)

fig5, axes = plt.subplots()
i = 0
for case in foldernames:
    #all_gen_metrics[case].sel(busNum = 4).PGEN.plot( ax = axes,color = colors[i],label=casename)
    plt.plot(all_bus_metrics[case].sel(busNum = 7).time.values, all_bus_metrics[case].sel(busNum = 7).PD.values,color = colors[i],label=case)
    i = i+1

axes.legend(loc='best')
axes.grid(True)
axes.set(title ='Bus 7 total load', xlabel='Time (hour)',ylabel='Load (MW)')



## average, MAX AND MIN LMP
print('\n CASE, LMP AVG, LMP MAX, LMP MIN, (event day):')
for case in foldernames:
   avg= all_bus_metrics_eventDay[case].sel(busNum = 7).LMP_P.mean().values
   max =all_bus_metrics_eventDay[case].sel(busNum = 7).LMP_P.max().values
   min =all_bus_metrics_eventDay[case].sel(busNum = 7).LMP_P.min().values
   print(case, ",", avg, ",", max, ",", min)

##/// data for table
print('\ntotal gen cost, revenue, profit(event day):')
for case in foldernames:
    earning = all_gen_metrics_eventDay[case].REVENUE.sum().values
    cost = all_gen_metrics_eventDay[case].COST.sum().values
    profit = earning-cost
    print(case, ",", cost,",",earning,",",profit)



print('\ntotal gen emissions CO2, Sox, Nox (lb) (event day):')
for case in foldernames:
    co2 =  all_gen_metrics_eventDay[case].EMISSION_CO2.sum().values
    sox = all_gen_metrics_eventDay[case].EMISSION_SOX.sum().values
    nox = all_gen_metrics_eventDay[case].EMISSION_NOX.sum().values
    print(case, ",", co2, ",", sox, ",", nox)



print('\n Distribution utility (at bus 7) expense (event day):')
i = 0
for case in foldernames:
    # plt.plot( kind = 'bar', (all_bus_metrics[case].sel(busNum = 7).LMP_P*all_bus_metrics[case].sel(busNum = 7).PD).sum().values , color = colors[i],label=case)
    print(case, ",", (all_bus_metrics_eventDay[case].sel(busNum = 7).LMP_P*1000.0*time_interval_hours*all_bus_metrics_eventDay[case].sel(busNum = 7).PD).sum().values)
    i = i+1

###==============================================Both day ========================================================================

## average, MAX AND MIN LMP
LMP_avg = []
LMP_max = []
LMP_min = []

print('\n CASE, LMP AVG, LMP MAX, LMP MIN, (both day):')
for case in foldernames:
   avg= all_bus_metrics[case].sel(busNum = 7).LMP_P.mean().values
   max =all_bus_metrics[case].sel(busNum = 7).LMP_P.max().values
   min =all_bus_metrics[case].sel(busNum = 7).LMP_P.min().values

   LMP_avg.append(avg)
   LMP_max.append(max)
   LMP_min.append(min)
   print(case, ",", avg, ",", max, ",", min)

print ('Baseline','Test','Impact')
print (LMP_avg[0],LMP_avg[1],LMP_avg[1]-LMP_avg[0])

##/// data for table
print('\ntotal gen cost, revenue, profit:')
for case in foldernames:
    earning = all_gen_metrics[case].REVENUE.sum().values
    cost = all_gen_metrics[case].COST.sum().values
    profit = earning-cost
    print(case, ",", cost,",",earning,",",profit)
    
print('\ntotal gen emissions CO2, Sox, Nox (lb) (both day):')
for case in foldernames:
    co2 =  all_gen_metrics[case].EMISSION_CO2.sum().values
    sox = all_gen_metrics[case].EMISSION_SOX.sum().values
    nox = all_gen_metrics[case].EMISSION_NOX.sum().values
    print(case, ",", co2, ",", sox, ",", nox)

# this is for displaying all the plots
# matplotlib.rcParams.update({'font.size': 50})
plt.show()


