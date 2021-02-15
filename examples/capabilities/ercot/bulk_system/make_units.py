import json
import math 

unitparameters = [
	{'fuel':'Conventional Steam Coal', 'c2': 0.005, 'c1':19.0, 'Pminpu': 0.5, 'Pmaxpu': 1.0, 'MinLagPF': 0.95, 'MinLeadPF': 0.95, 'count': 0, 'total': 0.0},
	{'fuel':'Natural Gas Fired Combined Cycle', 'c2': 0.005, 'c1':40.0, 'Pminpu': 0.1, 'Pmaxpu': 1.0, 'MinLagPF': 0.95, 'MinLeadPF': 0.95, 'count': 0, 'total': 0.0},
	{'fuel':'Natural Gas Fired Combustion Engine', 'c2': 0.005, 'c1':40.0, 'Pminpu': 0.1, 'Pmaxpu': 1.0, 'MinLagPF': 0.95, 'MinLeadPF': 0.95, 'count': 0, 'total': 0.0},
	{'fuel':'Natural Gas Internal Combustion Engine', 'c2': 0.005, 'c1':40.0, 'Pminpu': 0.1, 'Pmaxpu': 1.0, 'MinLagPF': 0.95, 'MinLeadPF': 0.95, 'count': 0, 'total': 0.0},
	{'fuel':'Natural Gas Steam Turbine', 'c2': 0.005, 'c1':40.0, 'Pminpu': 0.1, 'Pmaxpu': 1.0, 'MinLagPF': 0.95, 'MinLeadPF': 0.95, 'count': 0, 'total': 0.0},
	{'fuel':'Nuclear', 'c2': 0.00019, 'c1':8.0, 'Pminpu': 0.9, 'Pmaxpu': 1.0, 'MinLagPF': 0.95, 'MinLeadPF': 0.95, 'count': 0, 'total': 0.0},
	{'fuel':'Onshore Wind Turbine', 'c2': 0.00001, 'c1':0.01, 'Pminpu': 0.1, 'Pmaxpu': 1.0, 'MinLagPF': 0.95, 'MinLeadPF': 0.95, 'count': 0, 'total': 0.0},
	{'fuel':'Solar Photovoltaic', 'c2': 0.00001, 'c1':0.01, 'Pminpu': 0.1, 'Pmaxpu': 1.0, 'MinLagPF': 0.95, 'MinLeadPF': 0.95, 'count': 0, 'total': 0.0}
	]

def find_unit_parameters (tok):
	for row in unitparameters:
		if tok == row['fuel']:
			return row
	return None

if __name__ == '__main__':
	lp = open ('200NodesData.json').read()
	busdict = json.loads(lp)

	fp = open ('Units.csv', 'w')
	print('idx', 'bus', 'mvabase', 'pmin', 'qmin', 'qmax', 'c2', 'c1', 'c0', sep=',', file=fp)
	idx = 0
	for row in busdict:
		n = int(row['bus'])
		if 'weightdict' in row:
			for val in row['weightdict']:
				for row in unitparameters:
					tok = row['fuel']
					if tok in val:
						gen = float (val[tok])
						if gen > 0.0:
							ln = find_unit_parameters (tok)
							ln['count'] = ln['count'] + 1
							ln['total'] = ln['total'] + gen
							pf = ln['MinLeadPF']
							qmin = -gen * math.sqrt (1.0 - pf * pf)
							pf = ln['MinLagPF']
							qmax = gen * math.sqrt (1.0 - pf * pf)
							print (idx, n, gen, '{:.2f}'.format(gen*ln['Pminpu']), '{:.2f}'.format(qmin), 
										 '{:.2f}'.format(qmax), ln['c2'], ln['c1'], 0.0, sep=',', file=fp)
							idx = idx + 1
	fp.close ()

	gen = 0.0
	idx = 0
	for row in unitparameters:
		print (row['fuel'], 'totals', '{:.2f}'.format(row['total']), 'in', row['count'], 'units')
		gen = gen + row['total']
		idx = idx + row['count']
	print ('Total', '{:.2f}'.format(gen), 'MW in', idx, 'units')


