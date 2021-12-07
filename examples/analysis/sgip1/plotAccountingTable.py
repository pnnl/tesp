# @Author: Allison Campbell <camp426>
# @Date:   2021-11-12T15:21:15-08:00
# @Email:  allison.m.campbell@pnnl.gov
# @Last modified by:   camp426
# @Last modified time: 2021-11-12T15:32:14-08:00



import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import lca_standard_graphs as lsg
import pandas as pd
import numpy as np

base_dir = '/Users/camp426/TESP Virtual Machine'
accounting_table_final = pd.read_csv(base_dir+'/SGIP1_accounting_table.csv')
new_table = accounting_table_final.iloc[:,:11].copy()

for i in ['a','b','c','d','e']:
    temp = new_table['SGIP1'+i+' Day 1'] + new_table['SGIP1'+i+' Day 2']
    new_table['SGIP1'+i+' Day 2'] = temp.values

day1 = new_table.loc[:,[i[-1:] == '1' for i in new_table.columns]]
day2 = new_table.loc[:,[i[-1:] == '2' for i in new_table.columns]]
day1.index = new_table['Metric Description']
day2.index = new_table['Metric Description']
day1.columns = [i[:6] for i in day1.columns]
day2.columns = [i[:6] for i in day2.columns]

day1_emissions = day1.iloc[-3:].T
day1_emissions.columns=['CO2 [1e3]','SOx','NOx']

day2_emissions = day2.iloc[-3:].T
day2_emissions.columns=['CO2 [1e3]','SOx','NOx']

comp = lsg.build_comparison_table([day2_emissions, day1_emissions],['Day 1','Day 2'], fillna=0.0)

ax, fig = lsg.plot_grouped_stackedbars(comp, ix_categories='Criteria', \
        ix_entities_compared='Scenarios', norm=None ,yaxis_label='kg of emissions per day', \
        xaxis_label='Day 1 (left, dark) vs Day 2 (right, light)',\
        width=0.4, figsize=(10, 8),saveplot='Emissions.png')

plt.show()



PV_energy = pd.concat([day1.T['Average PV energy transacted (kWh/day)'],
                day2.T['Average PV energy transacted (kWh/day)']],axis=1)
PV_energy.columns = ['Day 1','Day 2']
PV_revenue = pd.concat([day1.T['Average PV energy revenue ($/day)'],
                day2.T['Average PV energy revenue ($/day)']],axis=1)
PV_revenue.columns = ['Day 1','Day 2']
ES_energy = pd.concat([day1.T['Average ES energy transacted (kWh/day)'],
                day2.T['Average ES energy transacted (kWh/day)']],axis=1)
ES_energy.columns = ['Day 1','Day 2']
ES_revenue = pd.concat([day1.T['Average ES energy net revenue'],
                day2.T['Average ES energy net revenue']],axis=1)
ES_revenue.columns = ['Day 1','Day 2']
testfeeder_MWh = pd.concat([day1.T['Wholesale electricity purchases for test feeder (MWh/d)'],
                day2.T['Wholesale electricity purchases for test feeder (MWh/d)']],axis=1)
testfeeder_MWh.columns = ['Day 1','Day 2']
testfeeder_cost = pd.concat([day1.T['Wholesale electricity purchase cost for test feeder ($/day)'],
                day2.T['Wholesale electricity purchase cost for test feeder ($/day)']],axis=1)
testfeeder_cost.columns = ['Day 1','Day 2']
generator_revenue = pd.concat([day1.T['Total wholesale generation revenue ($/day)'],
                day2.T['Total wholesale generation revenue ($/day)']],axis=1)
generator_revenue.columns = ['Day 1','Day 2']

plot_type = ['PV Energy Transacted','PV Average Revenue','ES Energy Transacted','ES Average Revenue', \
             'Wholesale Energy Purchased at Test Feeder','Wholesale Energy Cost at Test Feeder', \
             'Total Generator Revenue']
plot_units = ['kWh per day','$ per day','kWh per day','$ per day', \
             'MWh per day','$ per day','$ per day']
tables = [PV_energy,PV_revenue,ES_energy,ES_revenue, \
          testfeeder_MWh,testfeeder_cost,generator_revenue]
c = ['#021A7D','#4D71AE']
format_dollars = [False,True,False,True, \
                  False,True,True]

for tbl,title,yaxis_label,fd in zip(tables,plot_type,plot_units,format_dollars):
    x = np.arange(len(tbl.index))
    tbl_day1 = tbl['Day 1']
    tbl_day2 = tbl['Day 2']
    width = 0.4
    fig, ax = plt.subplots(figsize=(10, 8),facecolor='white')
    rects1 = ax.bar(x - width/2, tbl_day1, width, label='Day 1',color=c[0], edgecolor='k')
    rects2 = ax.bar(x + width/2, tbl_day2, width, label='Day 2',color=c[1], edgecolor='k')
    ax.set_title(title,fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(tbl.index,fontsize=16,rotation=90)
    if fd:
        formatter = ticker.StrMethodFormatter('${x:,.0f}')
        ax.yaxis.set_major_formatter(formatter)
    ax.grid(which='major', axis='y', linestyle='--', zorder=0)
    #ax.set_xlabel(xaxis_label,fontsize=16)
    ax.set_ylabel(yaxis_label,fontsize=16)
    ax.tick_params(labelsize=14)
    ax.legend(fontsize=16)
    ax.autoscale()
    fig.tight_layout()
    filename = title.replace(' ','_')+'.png'
    plt.savefig(filename)
    plt.show()
