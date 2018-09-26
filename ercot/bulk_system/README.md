8-Bus and 200-Bus ERCOT Bulk System Models
------------------------------------------

To regenerate the 8-Bus Model:

- Edit Buses8.csv, Lines8.csv and Units8.csv. No transformers are included.
- Run 'python make_case8.py'

To regenerate the 200-Bus Model:

- Edit RetainedBuses.csv, RetainedLines.csv, RetainedTransformers.csv and Units.csv.
- Run 'python make_case.py'

To run the 8-bus Model:

- Run 'python run_ERCOT.py' to spot check the PF and OPF solutions at peak load.
- Run 'python fncs_ERCOT.py' to run a time-stepping check with varying load.
- Run 'python process_pypower.py' to plot the results of fncs_ERCOT.py


