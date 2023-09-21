# Copyright (C) 2023 Battelle Memorial Institute
# file: te30_usestore.py
""" 
Takes existing datastore made by running the te30 example and processes the results. This
demonstrates the prototype datastore capability in TESP.
"""


import json
import tesp_support.api.store as fle


def process_results():
    """
    Opens up datastore (.zip) and metadata (.json) to process results
    
    Assumes te30_store.zip and te30_store.json have been copied from ../te30 folder to
    the same folder as this script (examples/capabilities/datastore).
    """

	# Load in metadata to see what contents are in the TE30 store
	meta = json.loads('./te30_store.json')
	
	# List all the files in the store for inspection
	for item in meta['store']:
		print(item['name'])
		
	# Arbitrarily, let's look at the real power load at a specific billing meter
	# This data is coming from GridLAB-D (based on the TE30 documentation)
	
	# metadata table has the name of each parameters and "value" is the unit. 
	# Same order as what's in the index tables
	
	my_file.set_date_bycol(tables[1], columns[1])
    my_file.set_date_bycol(tables[2], columns[1])

if __name__ == "__main__":
    process_results()