import sys
import json
import tkinter as tk
import tkinter.ttk as ttk

root = tk.Tk()
root.title('Transactive Energy Simulation Platform: Case Configuration')
nb = ttk.Notebook(root)
nb.pack(fill='both', expand='yes')

StartTime = "2013-07-01 00:00:00"
EndTime = "2013-07-03 00:00:00"
#Tmax = 2 * 24 * 3600

varsTM = [['Start Time',StartTime,''],
					['End Time',EndTime,''],
					['Market Clearing Period',300,'s'],
					['GridLAB-D Time Step',15,'s'],
					['Energy+ Time Step',60,'s'],
					['Agent Time Step',5,'s'],
					['GridLAB-D Base File','Taxonomy.glm',''],
					['Energy+ Base File','Sample.idf',''],
					['PYPOWER Base File','PPCase.py',''],
					['Weather Type','TMY3','TMY3/CSV'],
					['Weather Source','File or URL','s'],
					['Airport Code','YKM',''],
					['Working Directory','Case Name','']
					];
varsFD = [['Billing Mode','TIERED',''],
					['Monthly Fee',13,'$'],
					['Price',0.102013,'$/kwh'],
					['Tier 1 Energy',500,'kwh'],
					['Tier 1 Price',0.117013,'$/kwh'],
					['Tier 2 Energy',1000,'kwh'],
					['Tier 2 Price',0.122513,'$/kwh'],
					['Tier 3 Energy',0,'kwh'],
					['Tier 3 Price',0,'$/kwh'],
					['Electric Cooling Penetration',90,'%'],
					['HVAC Participation',50,'%'],
					['HVAC Set Daytime',80,'degF'],
					['HVAC Set Nighttime',72,'degF'],
					['HVAC Deadband',2,'degF'],
					['HVAC Std Dev',2,'degF'],
					['Solar Penetration',20,'%'],
					['Battery Penetration',10,'%'],
					['Eplus Bus','Eplus_load',''],
					['Eplus Service Voltage',480,'V'],
					['Eplus Transformer Size',150,'kVA']
					];
varsPP = [['OPF Type','DC','AC/DC'],
					['GLD Bus',7,''],
					['GLD Scale',400,''],
					['Unit Out',2,''],
					['Unit Outage Start','2013-07-02 06:00:00',''],
					['Unit Outage End','2013-07-02 20:00:00',''],
					['Branch Out','',''],
					['Branch Outage Start','',''],
					['Branch Outage End','','']
					];
varsEP = [['Base Price',0.02,'$'],
					['Ramp',25,'degF/$'],
					['Max Delta',4,'degF']
					];
varsAC = [['Initial Price',0.02078,'$'],
					['Std Dev Price',0.00361,'$'],
					['Price Cap',3.78,'$']
					];
varsHS = [['Ramp Lo: Mean',2.0,'$(std dev)/degF'],
					['Ramp Lo: Band',0.5,'$(std dev)/degF'],
					['Ramp Hi: Mean',2.0,'$(std dev)/degF'],
					['Ramp Hi: Band',0.0,'$(std dev)/degF'],
					['Range Lo: Mean',-3.0,'degF'],
					['Range Lo: Band',1.0,'degF'],
					['Range Hi: Mean',2.0,'degF'],
					['Range Hi: Band',0.0,'degF'],
					['Base Cooling: Mean',78.0,'degF'],
					['Base Cooling: Band',2.0,'degF'],
					['Bid Delay',60,'s']
					];

def AttachFrame(tag, vars):
	f = ttk.Frame(nb, name=tag)
	lab = ttk.Label(f, text='Parameter', relief=tk.RIDGE)
	lab.grid(row=0, column=0, sticky=tk.NSEW)
	lab = ttk.Label(f, text='Value', relief=tk.RIDGE)
	lab.grid(row=0, column=1, sticky=tk.NSEW)
	lab = ttk.Label(f, text='Units', relief=tk.RIDGE)
	lab.grid(row=0, column=2, sticky=tk.NSEW)
	for i in range(len(vars)):
		lab = ttk.Label(f, text=vars[i][0], relief=tk.RIDGE)
		lab.grid(row=i+1, column=0, sticky=tk.NSEW)
		ent = ttk.Entry(f)
		ent.insert(0, vars[i][1])
		ent.grid(row=i+1, column=1, sticky=tk.NSEW)
		lab = ttk.Label(f, text=vars[i][2], relief=tk.RIDGE)
		lab.grid(row=i+1, column=2, sticky=tk.NSEW)
	return f

def GenerateFiles():
	print('TODO: write all files to case working directory')

f1 = AttachFrame ('varsTM', varsTM)
f2 = AttachFrame ('varsFD', varsFD)
f3 = AttachFrame ('varsPP', varsPP)
f4 = AttachFrame ('varsEP', varsEP)
f5 = AttachFrame ('varsAC', varsAC)
f6 = AttachFrame ('varsHS', varsHS)

#ttk.Style().configure('TButton', background='blue')
ttk.Style().configure('TButton', foreground='blue')
btn = ttk.Button(f1, text='Generate', command=GenerateFiles)
btn.grid(row=len(varsTM) + 1, column=1, sticky=tk.NSEW)

nb.add(f1, text='Main', underline=0, padding=2)
nb.add(f2, text='Feeder', underline=0, padding=2)
nb.add(f3, text='PYPOWER', underline=0, padding=2)
nb.add(f4, text='Energy+', underline=0, padding=2)
nb.add(f5, text='Auction', underline=0, padding=2)
nb.add(f6, text='Controllers', underline=0, padding=2)

while True:
	try:
		root.mainloop()
		break
	except UnicodeDecodeError:
		pass
