#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: load_less_solar.py
# Created 8/20/2020
# @author: hard312 (Trevor Hardy)
"""Creates a new 200-bus load profile that is the original load profile less
the distributed solar generation for that bus. For the hourly profile the
solar data that is used is the hourly forecast data. For the five-minute
profile the actual 5minute solar data is used. Users can select whether
they need to generate hourly or five-minute datasets.

An 8-bus aggregated profile is also created (hourly or five-minute)
automatically after the full 200-bus load dataset has been created.
"""

import argparse
import logging
import pprint
import os
import sys
from enum import Enum
from pathlib import Path
import datetime as dt
import matplotlib.pyplot as plt
import openpyxl as xl

# Setting up logging
logger = logging.getLogger(__name__)

# Adding custom logging level "DATA" to use for putting
#  all the simulation data on. "DATA" is between "DEBUG"
#  and "INFO" in terms of priority. 
DATA_LEVEL_NUM = 5
logging.addLevelName(DATA_LEVEL_NUM, "DATA")


def data(self, message, *args, **kws):
    if self.isEnabledFor(DATA_LEVEL_NUM):
        self._log(DATA_LEVEL_NUM, message, args, **kws)


logging.DATA = DATA_LEVEL_NUM
logging.Logger.data = data

# Setting up pretty printing, mostly for debugging.
pp = pprint.PrettyPrinter(indent=4, )


# Creating mode enumeration
class Mode(Enum):
    HOUR = 0
    FIVE_MINUTE = 1


def _open_file(file_path, type='r'):
    """ Utilty function to open file with reasonable error handling.


    Args:
        file_path (str) - Path to the file to be opened

        type (str) - Type of the open method. Default is read ('r')


    Returns:
        fh (file object) - File handle for the open file
    """
    try:
        fh = open(file_path, type)
    except IOError:
       logger.error('Unable to open {}'.format(file_path))
       sys.exit()
    else:
        return fh


def parse_DSO_metadata_Excel(dso_metadata_path_Excel, worksheet_name):
    """
    This function parses the DSO metadata which is contained in a
    JSON and Excel files. Most of the metadata is in the JSON but one
    crucial piece of information is in the Excel file: the mapping of
    the 200-node to 8-node buses.

    Sample of the bus-generator file: (Note the first columns is empty)
    	200 bus	8 bus
	    1	1
	    2	1
	    3	1
	    4	1
	    5	1
	    6	1
	    ...

    Args:
        dso_metadata_path_Excel (str) - Path to the Excel file
        containing the metadata to be parsed.

        worksheet_name (str) - Name of the worksheet in the Excel file
        containing the metadata


    Returns:
        dso_meta (list of dicts) - One dictionary per DSO with appropriate
        metadata captured.
    """
    # openpyxl doesn't use file handles so I just use my function to
    #   make sure the file is really there and then close it up to allo
    #   openpyxl to be able to grab it and do its thing.
    dso_fh = _open_file(dso_metadata_path_Excel)
    dso_fh.close()
    dso_meta = []
    wb = xl.load_workbook(dso_metadata_path_Excel)
    sheet = wb[worksheet_name]

    # Defining the location of the data I need to extract from each row
    #   of the spreadsheet
    header_idx = {}
    for header in sheet.iter_cols(min_row=1, max_row=1):
        if header[0].value == '200 bus':
            header_idx['200-bus'] = header[0].col_idx
        if header[0].value == '8 bus':
            header_idx['8-bus'] = header[0].col_idx

    # Now iterate over the rest of the file to pull in the metadata into
    #   my dictionary
    for row in sheet.rows:
        # Skip the header row and the spacer row beneath
        if row[0].row > 1:
            for item in row:
                if item.col_idx == header_idx['200-bus']:
                    bus_200 = item.value
                if item.col_idx == header_idx['8-bus']:
                    bus_8 = item.value
            dso_meta.append({'200-bus': bus_200,
                             '8-bus': bus_8})
    logger.info('Parsed DSO Excel metadata file {}'.format(
        dso_metadata_path_Excel))
    logger.info(pp.pformat(dso_meta))

    return dso_meta


def read_load_file(load_path):
    """

    Args:
        load_path: Path to load file that is being read in

    Returns:
        load_data: list of lists with the headers and load data
    """
    # Read all load into memory since that is the common element that we
    #   are manipulating. Skipping last column as that is a cumulative
    #   value that needs to be manually calculated.
    load_fh = _open_file(load_path)
    logger.info(f'Reading in load data file {load_path}')
    load_data = []
    for idx, line in enumerate(load_fh):
        line_list = line.split(',')
        line_list = line_list[:-1]
        if idx > 0:
            line_list[1:] = [float(x) for x in line_list[1:]]
        load_data.append(line_list)
    logger.info('\tLoad data read in')
    load_fh.close()

    return load_data


def write_out_load_file(load_data, out_path):
    """
    Writes out load data to CSV file. Assumes a list of lists format.

    Args:
        load_data: Load data to be written to CSV.
        out_path: Path and filename of output file

    Returns:

    """
    logger.info(f'Writing out new load profile{out_path}')
    out_fh = _open_file(out_path, 'w')
    for row in load_data:
        out_str = ''
        for item in row:
            out_str = out_str + str(item) + ','
        # Remove very last comma and replace with a newline
        out_str = out_str[:-1]
        out_str = out_str + '\n'
        out_fh.write(out_str)
    out_fh.close()


def create_load_less_solar(input_load_filename, output_load_filename, solar_dir, load_dir, mode):
    """

    Hourly data is used for the DA market and needs to subtract the
    distributed generation solar forecast. 5-minute data is RT and needs to
    subtract the actual solar production.


    Sample hourly load data:
        Hour_End,Bus0,Bus1,Bus2,Bus3,Bus4,Bus5,Bus6,...
        12/29/2015 0:00,3659.8,248.49,1652,4415.4,201.28,50.374,83.668,...
        12/29/2015 1:00,3659.8,248.49,1652,4415.4,201.28,50.374,83.668,...
        12/29/2015 2:00,3603.9,246.54,1626.8,4348,198.2,49.784,82.688,...
        12/29/2015 3:00,3577.2,246.19,1614.8,4315.8,196.74,49.431,...
        12/29/2015 4:00,3595.8,247.46,1623.1,4338.1,197.76,49.543,...
        12/29/2015 5:00,3666,249.03,1654.8,4422.9,201.62,50.085,83.188,...
        12/29/2015 6:00,3795.8,253.74,1713.4,4579.4,208.75,51.893,...
        12/29/2015 7:00,3931.7,260.87,1774.8,4743.5,216.23,53.583,...

    Sample hourly DSO distributed solar forecast data:
        0
        0
        0
        0
        0
        0
        0
        0
        1.079
        2.518
        3.499
        6.463


    Sample 5-minute load data:
        Seconds,Bus1,Bus2,Bus3,Bus4,Bus5,Bus6,Bus7,Bus8,
        0,3659.8,248.5,1652,4415.4,201.3,50.4,83.7,145.1
        300,3659.8,248.5,1652,4415.4,201.3,50.4,83.7,145.1
        600,3659.8,248.5,1652,4415.4,201.3,50.4,83.7,145.1
        900,3659.8,248.5,1652,4415.4,201.3,50.4,83.7,145.1
        1200,3659.8,248.5,1652,4415.4,201.3,50.4,83.7,145.1

    Sample 5-minute solar data:
        12/29/15 0:00,0
        12/29/15 0:05,0
        12/29/15 0:10,0
        12/29/15 0:15,0
        12/29/15 0:20,0
        12/29/15 0:25,0
        12/29/15 0:30,0
        12/29/15 0:35,0
        12/29/15 0:40,0
        12/29/15 0:45,0
        12/29/15 0:50,0
        12/29/15 0:55,0
        12/29/15 1:00,0


    Args:
        load_filename: Filename of input load data
        solar_dir: Directory of input solar data
        load_dir: Directory of input load data
    Returns:
        load_data: list of list of load data less solar
    """

    diagnostics = False


    load_path = os.path.join(load_dir, input_load_filename)
    load_data = read_load_file(load_path)

    Jan1 = dt.datetime(2016, 1, 1, 0, 0)
    LeapDay = dt.datetime(2016, 2, 29, 0, 0)
    LastDay = dt.datetime(2017, 1, 1, 0, 0)

    Jan1_s = 259200
    LeapDay_s = 5356800
    LastDay_s = 31881600

    if diagnostics:
        full_data = ''
    excess_solar = {}
    excess_solar_critical_value = 10

    # 'bus_idx' refers to the column index in load_data, 200 buses total.
    for bus_idx in range(1,201):
        if diagnostics:
            file_path=os.path.join(load_dir, f'DSO_{bus_idx}_load_less'
                                             f'_solar_diagnostics.csv')
            diag_fh = _open_file(file_path,'w')
            full_data = full_data + f'DSO {bus_idx}\n'
            full_data = full_data + f'Load (MW),Distributed Solar (MW),Load less solar (MW)\n'

        # Reading the solar data for the given DSO in
        if mode == mode.HOUR:
            solar_filename = f'DSO_{bus_idx}' \
                             f'_dist_hourly_forecast_power_profile.csv'
        else:
            solar_filename = f'DSO_{bus_idx}' \
                             f'_5_minute_dist_power.csv'
        solar_path = os.path.join(solar_dir, f'DSO_{bus_idx}', solar_filename)
        if os.path.isfile(solar_path):
            solar_fh = _open_file(solar_path)
            logger.info(f'Reading in solar data {solar_path}')
            solar_list = []
            for line_num, line in enumerate(solar_fh):
                if mode == Mode.HOUR:
                    # Data file just has data
                    solar_list.append(float(line.strip()))
                else:
                    # Data file is CSV with timestamp in first column
                    line_list = line.split(',')
                    solar_list.append(line_list[1].strip())
            solar_fh.close()

            for ts_idx, load_list in enumerate(load_data[1:]):
                if mode == mode.HOUR:
                    ts = dt.datetime.strptime(load_list[0],
                                     '%m/%d/%Y %H:%M')
                else:
                    ts = int(load_list[0])


                if (mode == Mode.HOUR and ts < Jan1) \
                        or (mode == Mode.FIVE_MINUTE and ts < Jan1_s):
                    # Since the solar data is only for 8760 hours and the first
                    #   two days are before Jan 1, for these days copy solar
                    #   data from Jan 1 and 2
                    solar_MW = solar_list[ts_idx]


                elif (mode == mode.HOUR and ts >= Jan1 and ts < LeapDay) or \
                    (mode == mode.FIVE_MINUTE and ts >= Jan1_s and ts < LeapDay_s):
                # From Jan 1 to Feb 29 use the solar data exactly from
                #   these dates where Jan 1 is the first entry in the list
                    solar_MW = solar_list[ts_idx - 72]

                elif (mode == mode.HOUR and ts >= LeapDay and ts < LastDay) \
                        or (mode == mode.FIVE_MINUTE and ts >= LeapDay_s and
                            ts < LastDay_s):
                    solar_MW = solar_list[ts_idx - 96]

                load = load_list[bus_idx]
                load_less_solar = load - float(solar_MW)
                if diagnostics:
                    full_data = full_data + f'{load},{solar_MW}' \
                                            f',{load_less_solar}\n'

                if load_less_solar < 0:
                    if abs(load_less_solar) > excess_solar_critical_value:
                        if bus_idx not in excess_solar:
                            excess_solar[bus_idx] = {'ts':[], 'excess solar':[]}
                        else:
                            excess_solar[bus_idx]['ts'].append(ts)
                            excess_solar[bus_idx]['excess solar'].append(
                                abs(load_less_solar))
                    logger.warning(
                        f'\tSolar power of {solar_MW} MW exceeds load of '
                        f'{load:.2f} MW by {load_less_solar:.2f} MW'
                        f' at bus {bus_idx} at timestamp {ts}')
                load_data[ts_idx + 1][bus_idx] = load_less_solar
            logger.info('\tSubtracted distributed solar profile load.')
            if diagnostics:
                diag_fh.write(full_data)
                diag_fh.close()
        else:
            logger.warning(f'No distributed solar profile found for bus '
                           f'{bus_idx}')

    # Adding data for ERCOT total in final column
    # First row is headers
    load_data[0].append('ERCOT')
    for ts, ts_data in enumerate(load_data[1:]):
        ercot_load = 0
        for bus_load in ts_data[1:]:
            ercot_load = ercot_load + bus_load
        load_data[ts + 1].append(ercot_load)


    color_list = ['black', 'dimgrey', 'silver', 'rosybrown', 'firebrick',
                  'maroon', 'chocolate', 'red', 'green', 'gold', 'yellow',
                  'orange', 'greenyellow', 'forestgreen', 'lime', 'aquamarine',
                  'turquoise', 'teal', 'cyan', 'deepskyblue', 'lightskyblue',
                  'steelblue', 'lavender', 'navy', 'slateblue',
                  'blue', 'lightcyan', 'darkorchid', 'plum',
                  'purple', 'fuchsia', 'deeppink', 'hotpink', 'crimson',
                  'indigo', 'black', 'dimgrey', 'silver', 'rosybrown',
                  'firebrick', 'maroon', 'chocolate', 'red', 'green', 'gold',
                  'yellow']
    marker_list = ['o', 'x', '^', 's', '*', 'D', 'v', '+',
                   'o', 'x', '^', 's', '*', 'D', 'v', '+',
                   'o', 'x', '^', 's', '*', 'D', 'v', '+',
                   'o', 'x', '^', 's', '*', 'D', 'v', '+',
                   'o', 'x', '^', 's', '*', 'D', 'v', '+',
                   'o', 'x', '^', 's', '*', 'D', 'v', '+',
                   'o', 'x', '^', 's', '*', 'D', 'v', '+']

    # Making excess solar graph
    if excess_solar:
        idx = 0
        for key in excess_solar:
            plt.scatter(excess_solar[key]['ts'],
                        excess_solar[key]['excess solar'],
                        label=f'Bus {key}, count = {len(excess_solar[key]["ts"])}',
                        s=16,
                        c = color_list[idx],
                        marker = marker_list[idx],
                        alpha = 0.5)
            idx = idx + 1
        plt.title(f'Instances of Solar Power in Excess of Nodal Load '
                  f'({excess_solar_critical_value} MW or Greater)')
        plt.xlabel('Date')
        plt.ylabel('Excess solar (MW)')
        plt.yscale('log')
        plt.legend()
        plt.show()


    # Writing out new load profile file
    out_path = os.path.join(load_dir, output_load_filename)
    write_out_load_file(load_data, out_path)

    return load_data


def create_8_node_load_less_solar(dso_meta, load_dir, input_load_filename, output_load_filename):
    """
    Using information in the dso_meta dictionary, this function aggregates
    the 200-bus load-less-solar values into the 8-bus values. The resulting
    dataset is written out to file.


    Args:
        dso_meta: DSO metadata defining how 200-node buses map to 8-node buses
        load_dir: Directory with input load data file
        input_load_filename: Filename only, no path
        output_load_filename: Filename only, no path

    Returns:
        (none)
    """
    load_path = os.path.join(load_dir, input_load_filename)
    load_data = read_load_file(load_path)
    out_path = os.path.join(load_dir, output_load_filename)

    dso_load = []
    for ts, ts_data in enumerate(load_data):
        ercot_load = 0
        if ts == 0:
            # Copy headers from source file. ERCOT column (final column)
            #   not read in by "read_load_file" so manually adding it.
            dso_load.append([load_data[0][0], load_data[0][1], load_data[0][2],
                           load_data[0][3], load_data[0][4], load_data[0][5],
                           load_data[0][6], load_data[0][7], load_data[0][8],
                           'ERCOT'])
        else:
            # Initialize to empty so load totals for each 8-bus DSO can
            #   be tabulated
            dso_load.append(['',0,0,0,0,0,0,0,0,0])
            # Allocate all 200-bus DSO loads to an 8-bus DSO load.
            #   Skip the last column because it is the ERCOT total
            for bus_idx, bus_load in enumerate(ts_data[:-1]):
                if bus_idx == 0:
                    dso_load[ts][bus_idx] = load_data[ts][0]
                else:
                    eight_bus_num = dso_meta[bus_idx]['8-bus']
                    dso_load[ts][eight_bus_num] = \
                        dso_load[ts][eight_bus_num] + bus_load
                    ercot_load = ercot_load + bus_load

            dso_load[ts][-1] = ercot_load

    write_out_load_file(dso_load, out_path)


def _auto_run(args):
    """
    This function executes when the script is called as a stand-alone
    executable.

    A more complete description of this code can be found in the
    docstring at the beginning of this file.

    Args:
        '-a' or '--auto_run_dir' - Path of the auto_run folder
        that contains examples of the files used in this script. Used
        for development purposes as well as models/examples/documentation
        of the format and contents expected in said files

    Returns:
        (none)
    """
    if args.mode == 'hourly':
        mode = Mode.HOUR
    else:
        mode = Mode.FIVE_MINUTE
    logging.info(f'Mode is {args.mode}')

    if mode == Mode.HOUR:
        input_load_filename = '2016_ERCOT_200Bus_Hourly_Load_Data.csv'
        output_load_filename = '2016_ERCOT_200Bus_Hourly_Load_Less_Dist_Solar.csv'
    else:
        input_load_filename = '2016_ERCOT_200Bus_5min_Load_Data.csv'
        output_load_filename ='2016_ERCOT_200Bus_5min_Load_Less_Dist_Solar.csv'

    dso_meta = parse_DSO_metadata_Excel(args.dso_metadata_Excel,
                                                args.Excel_worksheet_name)

    load_data = create_load_less_solar( input_load_filename,
                                        output_load_filename,
                                        args.solar_dir,
                                        args.load_dir,
                                        mode)
    if args.eight_node == 'y':
        if mode == Mode.HOUR:
            input_load_filename = \
                '2016_ERCOT_200Bus_Hourly_Load_Less_Dist_Solar.csv'
            output_load_filename = \
                '2016_ERCOT_8Bus_Hourly_Load_Less_Dist_Solar.csv'
        else:
            input_load_filename = \
                '2016_ERCOT_200Bus_5min_Load_Less_Dist_Solar.csv'
            output_load_filename = \
                '2016_ERCOT_8Bus_5min_Load_Less_Dist_Solar.csv'


        create_8_node_load_less_solar(dso_meta, args.load_dir,
                                      input_load_filename,
                                      output_load_filename)

    logging.critical('Script done')


if __name__ == '__main__':
    # TDH: This slightly complex mess allows lower importance messages
    # to be sent to the log file and ERROR messages to additionally
    # be sent to the console as well. Thus, when bad things happen
    # the user will get an error message in both places which,
    # hopefully, will aid in trouble-shooting.
    fileHandle = logging.FileHandler("dsot_load_less_solar.log", mode='w')
    fileHandle.setLevel(logging.DEBUG)
    streamHandle = logging.StreamHandler(sys.stdout)
    streamHandle.setLevel(logging.ERROR)
    logging.basicConfig(level=logging.INFO,
                        handlers=[fileHandle, streamHandle])

    parser = argparse.ArgumentParser(description='Subtract solar PV from load')
    # TDH: Have to do a little bit of work to generate a good default
    # path for the auto_run folder (where the development test data is
    # held.
    script_path = os.path.dirname(os.path.realpath(__file__))
    auto_run_dir = os.path.join(script_path, 'auto_run')
    parser.add_argument('-a',
                        '--auto_run_dir',
                        nargs='?',
                        default=auto_run_dir)
    script_path = Path(script_path)
    tesp_root = script_path.parents[3]
    dsot_data_path = os.path.join(tesp_root, 'examples', 'data')
    solar_dir = os.path.join(dsot_data_path,
                             'solar_data',
                             'solar_pv_power_profiles')
    parser.add_argument('-s',
                        '--solar_dir',
                        nargs='?',
                        default=solar_dir)
    load_dir = dsot_data_path
    parser.add_argument('-l',
                        '--load_dir',
                        nargs='?',
                        default=load_dir)
    parser.add_argument('-m',
                        '--mode',
                        nargs='?',
                        default='five_minute')
    parser.add_argument('-e',
                        '--eight_node',
                        nargs='?',
                        default='y')
    dso_file_Excel = os.path.join(dsot_data_path, 'bus_generators.xlsx')
    parser.add_argument('-x',
                        '--dso_metadata_Excel',
                        nargs='?',
                        default=dso_file_Excel)
    parser.add_argument('-w',
                        '--Excel_worksheet_name',
                        nargs='?',
                        default='Bus mapping')
    args = parser.parse_args()
    _auto_run(args)
