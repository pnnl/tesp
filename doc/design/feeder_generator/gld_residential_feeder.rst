============================
Residential Feeder Generator 
============================

This residential feeder generator module (gld_residential_feeder.py) takes a model feeder.glm (GridLAB-D readable format), identifies existing transformers on the feeder with downstream load, determines how many houses each transformer can support based on the average house load in kVA, and adds that many houses. This process can also be used to add commercial buildings as well as small ZIP loads. The newly populated feeder is saved as a separate .glm, which can be used for subsequent analysis in GridLAB-D.

Before proceeding, please be sure you have successfully installed TESP.

Pre-req: Get Required Data Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before using gld_residential_feeder.py, we need the required metadata. Start by downloading the supporting data that is not stored in the repository due to its size and static nature. This will add a “data” folder alongside the existing “code” folder from the repository. ::

    cd tesp/repository/tesp/examples/analysis/dsot/code`

    ./dsotData.sh`

Config
~~~~~~

Feeder Configuration
--------------------

The feeder_config.json5 file contains the required configurations read in by the ``Config`` class and used by the rest of gld_residential_feeder.py. The config file is organized into sections for readability.::

- general: contains the basic requirements to build the .glm, such as input and output file names, and simulation time information. Much of this information is used by the ``preamble`` function to add the required .glm modules.
- input files: contains the file paths to the required metadata for the ``Residential_Build``, ``Commercial_Build``, ``Battery``, ``Electric_Vehicle``, and ``Solar`` classes. 
- dso: contains the DSO-specific information, such as location, weather files, and customer mix.
- RECS Data: contains the information required to populate the RECS metadata for the user case.
- electric vehicle definitions: contains EV-specific parameters
- solar definitions: contains solar-specific parameters
- simulation parameters: details whether to use HELICS or FNCS for any cosimulation and whether to build upon an existing taxonomy feeder instead of a user-defined ``in_file_glm`` defined in 'general'.
- else: additional requirements, such as the GridLAB-D region assignment and the average house and commercial load size.
- add schedules: sets ``includes`` to contain standard appliance, water heater, and thermostat setpoint schedules.
- add sets: sets any .glm specific parameters such as logging level.
- add defines: sets any .glm defines.
- DSOT Case Config: contains required DSOT config parameters such as ``case_type`` and participation rates of individual DERs.


Define Residential Population
-----------------------------

The 2020 Residential Energy Consumption Survey data are the backbone of how TESP creates a realistic distribution of residential housing stock on the feeder. The recs_gld_house_parameters.py script responsible for creating the residential metadata file (RECS_residential_metadata.json) fetches this metadata based on ``state``, ``housing_density``, and ``income_level``.

For our test case, those parameters are:::

    "state": "VT"
    "housing_density": ['No_DSO_Type']
    "income_level": ['Low', 'Middle', 'Upper']

This information is used by the ``generate_and_load_recs`` function to assign the default commercial, residential, battery, solar, and ev metadata.

Residential_Build
~~~~~~~~~~~~~~~~~

This primary function of this class is to ``add_houses`` to the feeder. The dependent functions of ``add_houses`` are also contained in this class, such as functions to set the thermal properties, heating and cooling setpoints, and income level of the houses, based on RECS and ``Config``. This class is also responsible for adding small ZIP loads to the houses. 


Commercial_Build
~~~~~~~~~~~~~~~~

The primary function of this class is to scan loads assigned with a 'C' class by the ``buildingTypeLabel`` function within the ``Residential_Build`` class and replace those with commercial building loads. This class also defines functions to add commercial zones and additional commercial buildings and ZIP loads.

Battery
~~~~~~~

This class is primarily a placeholder for battery functionality.

Solar
~~~~~

This primary function of this class is to define the solar inverter settings.

Electric_Vehicle
~~~~~~~~~~~~~~~~

This primary function of this class is to define the EVs to be added to the feeder as well as their driving and charging behavior. This is achieved by first reading available driving data from the NHTS survey via ``processs_nhts_data`` and matching that data with a reaslistic driving schedule via ``match_driving_schedule`` based on the daily miles driven, departure, and arrival times. This class contains an additional check to ensure that the driving schedules have realistic timings, via ``is_drive_time_valid``.

Feeder
~~~~~~

This class pulls everything together to read the input feeder (``readBackboneModel``) and populate it with the residential, commercial, battery, solar, and electric vehicle loads defined in the previous classes. This is primarily achieved via the ``GLMModifier()`` module, called with the shorthand ``self.glm`` throughout. Existing transformer configurations are modified to accomodate the new loads and then the feeder is populated. For reporting purposes, this class also defines ``identify_xfmr_houses`` to report to the user the number of houses and small loads that have been added. 


Running gld_residential_feeder.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run the feeder generator, the ``Config`` class must first be initialized with the user-defined config file, after which ``Feeder`` reads that config, as such.::

    def _test1():
    config = Config("./feeder_config.json5")
    feeder = Feeder(config)   


    if __name__ == "__main__":
        _test1()

