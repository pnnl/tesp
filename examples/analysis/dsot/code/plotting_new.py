from numpy import mean
import pandas as pd
import os
from pathlib import Path
import matplotlib.pyplot as plt

base_dir = r"C:\Rate Ananlysis Work\Rates_Scenario\Subscription\post"
subfolders =['mult0', 'mult0.2', 'mult0.4', 'mult0.6', 'mult0.8', 'mult1.0', 'mult1.2']
csv_filename = "Master_Customer_Dataframe.csv"
columns_of_interest = ['Customer ID', 'BillVolatility', 'tariff_class', 'Bills']

dfs = {}
for subfolder in subfolders:
    csv_path = os.path.join(base_dir, subfolder, csv_filename)
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        dfs[subfolder] = df[columns_of_interest]
        print(f"✓ Loaded: {subfolder} (shape: {dfs[subfolder].shape})")
    else:
        print(f"✗ Not found: {csv_path}")
    print(dfs[subfolder].head())
    dfs[subfolder] = dfs[subfolder][dfs[subfolder]['tariff_class'] == 'residential']

#Creating Pareto plot for Bill Volatility
plt.figure(figsize=(10, 6))
for subfolder, df in dfs.items():
    print("mean Bill Volatility:", mean(dfs[subfolder]['BillVolatility']))
    print("mean Bills:", mean(dfs[subfolder]['Bills']))
    plt.scatter(mean(dfs[subfolder]['BillVolatility']), mean(dfs[subfolder]['Bills']), label=subfolder, alpha=0.6)  
    plt.xlabel('Bill Volatility')
    plt.ylabel('Bills')     
    plt.title('Pareto Plot: Bill Volatility vs Bills')
    plt.legend()    
plt.grid(True)
plt.tight_layout()  
plt.show()

#Pareto Plot for bill voltaility and bill savings. bill savings = bills in flat rate - bills in subscription
flat_rate_csv = r"C:\Rate Ananlysis Work\Rates_Scenario\flat-rate\post\Master_Customer_Dataframe.csv"
if os.path.exists(flat_rate_csv):
    flat_rate_df = pd.read_csv(flat_rate_csv)
    flat_rate_df = flat_rate_df[columns_of_interest]
    flat_rate_df  = flat_rate_df[flat_rate_df['tariff_class'] == 'residential']
    print(f"✓ Loaded flat rate case (shape: {flat_rate_df.shape})")
else:
    print(f"✗ Flat rate case not found: {flat_rate_csv}")  
plt.figure(figsize=(10, 6))
for subfolder, df in dfs.items():    
    bill_savings = mean(flat_rate_df['Bills']) - mean(dfs[subfolder]['Bills'])
    print("mean Bill Volatility:", mean(dfs[subfolder]['BillVolatility']))
    print("mean Bill Savings:", bill_savings)
    plt.scatter(mean(dfs[subfolder]['BillVolatility']), bill_savings, label=subfolder, alpha=0.6)  
    plt.xlabel('Bill Volatility')
    plt.ylabel('Bill Savings')     
    plt.title('Pareto Plot: Bill Volatility vs Bill Savings')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()      
plt.show()