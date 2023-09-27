#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: PSM_download.py
# Created 4/28/2020
# @author: hard312 (Trevor Hardy)
"""Simple script to download PSM weather files and convert them to DAT files.

In the name of expediency, this script contains two functions that were
copy and pasted from dsot_solar.py. I wish that those functions had been
better abstracted when I wrote them but, it's not worth the time and effort
to do so now. This script will likely ever only be run a few times as it
is just creating input files and is not a part of the co-sim runtime.

The script does make use of PSMvstoDAT.py as a function, though. I had to
make minor edits to that function as it was slightly non-abstracted and
not completely stand-alone.
"""

import argparse
import logging
import os
import pprint
import sys
from pathlib import Path

import openpyxl as xl

import tesp_support.weather.PSMv3toDAT as PSM

# spec = importlib.util.spec_from_file_location("PSMv3toDAT", "../PSMv3toDAT.py")
# PSM = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(PSM)

# Setting up logging
logger = logging.getLogger(__name__)

# Setting up pretty printing, mostly for debugging.
pp = pprint.PrettyPrinter(indent=4, )


def _open_file(file_path, typ='r'):
    """ Utilty function to open file with reasonable error handling.


    Args:
        file_path (str) - Path to the file to be opened

        typ (str) - Type of the open method. Default is read ('r')


    Returns:
        fh (file object) - File handle for the open file
    """
    try:
        fh = open(file_path, typ)
    except IOError:
        logger.error('Unable to open {}'.format(file_path))
    else:
        return fh


def parse_DSO_location(dso_metadata_path, worksheet_name):
    """ This function parses the DSO metadata which is contained in an Excel spreadsheet

    Args:
        dso_metadata_path (str): Path to the Excel file containing the  metadata to be parsed.
        worksheet_name (str): Name of the worksheet in the Excel file containing the metadata
    Returns:
        list<dict>: One dictionary per DSO with appropriate metadata captured.
    """

    # openpyxl doesn't use file handles so, I just use my function to
    #   make sure the file is really there and then close it up to allow
    #   openpyxl to be able to grab it and do its thing.
    dso_fh = _open_file(dso_metadata_path)
    dso_fh.close()
    dso_meta = []
    wb = xl.load_workbook(dso_metadata_path)
    sheet = wb[worksheet_name]

    # Defining the location of the data I need to extract from each row
    #   of the spreadsheet
    header_idx = {}
    for header in sheet.iter_cols(min_row=1, max_row=1):
        if header[0].value == 'Latitude':
            header_idx['lat'] = header[0].col_idx
        if header[0].value == 'Longitude':
            header_idx['long'] = header[0].col_idx
        if header[0].value == 'Bus':
            header_idx['200-bus'] = header[0].col_idx

    # Now iterate over the rest of the file to pull in the metadata into
    #   my dictionary
    for row in sheet.rows:
        # Skip the header row and the spacer row beneath
        if row[0].row > 2:
            for item in row:
                if item.col_idx == header_idx['lat']:
                    lat = item.value
                if item.col_idx == header_idx['long']:
                    long = item.value
                if item.col_idx == header_idx['200-bus']:
                    bus_200 = item.value
            dso_meta.append({'lat': lat,
                             'long': long,
                             '200-bus': bus_200})
    logger.info('Parsed DSO metadata file {}'.format(dso_metadata_path))
    logger.info(pp.pformat(dso_meta))
    return dso_meta


def download_nsrdb_data(dso_meta, output_path):
    """ This function queries the NSRDB database over the web and pulls down and does a conversion.

    Function pulls down the solar data down calls PSMv3toDAT to convert them to appropriate format.

    Args:
        dso_meta (list): List of dicts with metadata associated with each DSO, specifically the site information
        output_path (str) - Location to write out solar data from the NSRDB.
    """

    # Change directory to parent file location of output path to enable
    #   the use of PSMv3toDAT.py.
    os.chdir(output_path)

    for idx, dso in enumerate(dso_meta):
        lat = dso['lat']
        long = dso['long']
        dso_num = dso['200-bus']

        year = 2016

        # You must request an NSRDB api key from https://developer.nrel.gov/signup/
        api_key = 'replace me with the NSRDB API key (string)'
        # Set the attributes to extract (e.g., dhi, ghi, etc.), separated by commas.
        attributes = 'dhi,dni,wind_speed,relative_humidity,air_temperature,surface_pressure'
        # Set leap year to true or false. True will return leap day data if present, false will not.
        leap_year = 'false'
        # Set time interval in minutes, i.e., '30' is half hour intervals. Valid intervals are 30 & 60.
        interval = '30'
        # Specify Coordinated Universal Time (UTC),
        #   'true' will use UTC, 'false' will use the local time zone of the data.
        # NOTE: In order to use the NSRDB data in SAM, you must specify UTC as 'false'.
        # SAM requires the data to be in the local time zone.
        utc = 'false'
        # Your full name, use '+' instead of spaces.
        your_name = 'Trevor+Hardy'
        # Your reason for using the NSRDB.
        reason_for_use = 'research'
        # Your affiliation
        your_affiliation = 'PNNL'
        # Your email address
        your_email = 'trevor.hardy@pnnl.gov'
        # Please join our mailing list so, we can keep you up-to-date on new developments.
        mailing_list = 'false'

        # Declare url string for the requests
        url = 'http://developer.nrel.gov/api/solar/nsrdb_psm3_download.csv?wkt=POINT({lon}%20{lat})&names={year}&leap_day={leap}&interval={interval}&utc={utc}&full_name={name}&email={email}&affiliation={affiliation}&mailing_list={mailing_list}&reason={reason}&api_key={api}&attributes={attr}'.format(
            year=year, lat=lat, lon=long, leap=leap_year, interval=interval,
            utc=utc, name=your_name, email=your_email, mailing_list=mailing_list,
            affiliation=your_affiliation, reason=reason_for_use, api=api_key, attr=attributes)

        # Check to see if file exists (indicating we downloaded it before
        # and don't need to do so again). If file does exist, we load
        # it and add it to the list of dataframes.
        filename = 'DSO_{}_{}_{}_weather_data.csv'.format(dso_num, lat, long)
        output_file = os.path.join(output_path, filename)

        # r = requests.get(url, allow_redirects=True)
        # csv_fh = open(output_file, 'wb')
        # csv_fh.write(r.content)
        # csv_fh.close()
        logger.info('Downloaded data for DSO {} and...'.format(dso_num))

        # We've already moved to the correct folder at the top of this
        #   function and all that is needed is the filename.
        file, ext = os.path.splitext(filename)
        PSM.weatherdat(file,
                       'Bus_{}'.format(dso_num + 1),
                       '{}_{}'.format(lat, long))
        logger.info('\t...converted PSM to DAT for DSO {}'.format(dso_num))


def _auto_run(args):
    """ This function executes when the script is called as a stand-alone executable.

    Args:
        '-a' or '--auto_run_dir': Path of the auto_run folder
            that contains examples of the files used in this script. Used
            for development purposes as well as models/examples/documentation
            of the format and contents expected in said files
        '-d' or '--dso_metadata': Path to .xlsx file with all DSO
            metadata file is part of the DSO+T planning/documentation
            dataset and should not need to be manually created or edited.
        '-n' or '--nsrdb_path': Location to save downloaded solar files
        '-x' or '--dso_metadata_worksheet_name': Name of worksheet in
            file specified by dso_metdata that contains the location metadata.
    """

    # Must parse solar metadata file first as it contains the name of the
    #   Excel worksheet that contains the values for the DSO metadata.
    dso_meta = parse_DSO_location(args.dso_metadata, args.dso_metadata_worksheet_name)
    download_nsrdb_data(dso_meta, args.nsrdb_output_path)
    logger.info('Download and conversion for all weather files complete.')


if __name__ == '__main__':
    # TDH: This slightly complex mess allows lower importance messages
    # to be sent to the log file and ERROR messages to additionally
    # be sent to the console as well. Thus, when bad things happen
    # the user will get an error message in both places which,
    # hopefully, will aid in troubleshooting.
    fileHandle = logging.FileHandler("dsot_weather_download.log", mode='w')
    fileHandle.setLevel(logging.DEBUG)
    streamHandle = logging.StreamHandler(sys.stdout)
    streamHandle.setLevel(logging.ERROR)
    logging.basicConfig(level=logging.INFO,
                        handlers=[fileHandle, streamHandle])

    parser = argparse.ArgumentParser(description='Download NSRDB data.')
    # TDH: Have to do a bit of work to generate a good default
    # path for the auto_run folder where the development test data is held.
    script_path = os.path.dirname(os.path.realpath(__file__))
    auto_run_dir = os.path.join(script_path, 'auto_run')
    parser.add_argument('-a',
                        '--auto_run_dir',
                        nargs='?',
                        default=auto_run_dir)

    dso_file = os.path.join(auto_run_dir, '200busmappingv5.xlsx')
    parser.add_argument('-d',
                        '--dso_metadata',
                        nargs='?',
                        default=dso_file)

    p = Path(auto_run_dir).parents[4]
    nsrdb_output_path = os.path.join(str(p),
                                     'support',
                                     'weather',
                                     '200-node data',
                                     'PSM source weather files')
    parser.add_argument('-n',
                        '--nsrdb_output_path',
                        nargs='?',
                        default=nsrdb_output_path)

    parser.add_argument('-x',
                        '--dso_metadata_worksheet_name',
                        nargs='?',
                        default='200BusValues')

    args = parser.parse_args()

    _auto_run(args)
