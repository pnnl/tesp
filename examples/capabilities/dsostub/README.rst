The dsostub example demonstrates TESP's ability to replicate the power system and market behavior of a distribution system without doing the detailed modeling that is often done for transactive studies such as in GridLAB-D. dsostub replicates the behavior in aggregate, allowing the computation burden in assessing transactive systems under development to be dramatically reduced.

dsostub supports a real-time and day-ahead double-auction energy market implementation. The bulk power system physics and market models are run by PSST with the CBC solver used for solving the security constrained unit commitment problem as part of clearing the day-ahead market. PSST with CBC also solves a security-constrained economic dispatch problem to clear the five-minute real-time energy market.

Almost of the parameters for the models used in this dsostub example are defined in the "case_config.json" file; this includes the transmission and generation system model. The "dsostub.py" script has a price-responsive curve hard-coded into the real-time market bidding.

This TESP capability was published in the IEEE Power and Energy Society General Meeting in July of 2021 and the publication can be found in :cite:`Hanif:2021aa` (https://doi.org/10.1109/PESGM46819.2021.9638030). 


Running the demonstration
.........................

::

    ./runstub.sh dsostub_case
    cd dsostub_case
    ./run.sh
    
    

File Directory:
...............

* *case_config.json*: configuration data co-simulation including bulk-power system definition, source data file references, and general configuration and metadata
* *data*: folder containing time-series data used by various actors in the co-simulation
* *dsoStub.py*: Minimal representation of the distribution system providing identical interface as other TESP examples but requires dramatically reduced computation load as compared to full modeling traditionally done in GridLAB-D.
* *runstub.sh*: prepares co-simulation and launches it
