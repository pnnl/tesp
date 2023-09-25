# Copyright (C) 2023 Battelle Memorial Institute
# file: te30_usestore.py
""" 
Takes existing datastore made by running the te30 example and processes the results. This
demonstrates the prototype datastore capability in TESP.
"""


import tesp_support.api.store as fle


def process_results(case_name):
    """
    Opens up datastore (.zip) and metadata (.json) to process results
    
    Assumes te30_store.zip and te30_store.json have been copied from ../te30 folder to
    the same folder as this script (examples/capabilities/datastore).
    """
    # Load in metadata to see what contents are in the TE30 store
    # fle.unzip(case_name)

    # example
    my_store = fle.Store(case_name)
    # this is a cvs file
    my_file = my_store.get_schema('weather')
    data = my_file.get_series_data('weather', '2013-07-01 00:00', '2013-07-02 00:00')
    tseries = [data]
    print(tseries)

    # List all the files in the store for inspection
    for item in my_store.get_schema():
        print(item)
		
    # Arbitrarily, let's look at the real power load at a specific billing meter
	# This data is coming from GridLAB-D (based on the TE30 documentation)
	
	# metadata table has the name of each parameter and "value" is the unit.
	# Same order as what's in the index tables


if __name__ == "__main__":
    process_results("te30_store")