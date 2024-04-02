# -*- coding: utf-8 -*-
"""
Created on Fri Mar 29 11:12:29 2024

@author: rame388
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# gen = pd.read_csv('./output/1b_Generator_realpower.csv', index_col=False)

# coal = gen['Gen2'] + gen['Gen3'] + gen['Gen4'] + gen['Gen5'] + gen['Gen6']+ gen['Gen7']+ gen['Gen8']+ gen['Gen9']+ gen['Gen10']+ gen['Gen11']+ gen['Gen12']+ gen['Gen14']+ gen['Gen15']+ gen['Gen17']+ gen['Gen18']+ gen['Gen19']
# coal = coal + gen['Gen20'] + gen['Gen21'] + gen['Gen24'] + gen['Gen25'] + gen['Gen26']+ gen['Gen27']+ gen['Gen28']+ gen['Gen30']+ gen['Gen35'] + gen['Gen36']+ gen['Gen37']

# NG = gen['Gen13'] + gen['Gen16']

# hydro = gen['Gen29']+ gen['Gen31']+ gen['Gen32']+ gen['Gen33']+ gen['Gen34']

# wind = gen['Gen38']+ gen['Gen39']+ gen['Gen40']+ gen['Gen41']+ gen['Gen42']+ gen['Gen43'] + gen['Gen44'] + gen['Gen45'] + gen['Gen46']+ gen['Gen47']+ gen['Gen48']

gen_emm = pd.read_csv('./output/gen_emission.csv', index_col=False)

fig = plt.figure()
ax1 = fig.add_subplot(3, 1, 1)
ax2 = fig.add_subplot(3, 1, 2)
ax3 = fig.add_subplot(3, 1, 3)
ax1.plot(gen_emm.index, gen_emm['coal'], "r--")
ax1.set_xlim([0, 25])
ax1.set_ylabel("Generation (MW)")
ax1.set_xlabel("Time [in hours]")

ax2.plot(gen_emm.index, gen_emm['wind'], "b--")
ax2.set_xlim([0, 25])
ax2.set_ylabel("Generation (MW)")
ax2.set_xlabel("Time [in hours]")

ax3.plot(gen_emm.index, gen_emm['emission'], "k--")
ax3.set_xlim([0, 25])
ax3.set_ylabel("CO_2 emission in short tons")
ax3.set_xlabel("Time [in hours]")


ax1.grid()
ax2.grid()
ax3.grid()
plt.tight_layout()
plt.savefig(f"./output/gen_emission_plot.png", dpi=200)
