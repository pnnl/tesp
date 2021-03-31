# -*- coding: utf-8 -*-
"""
Created on Fri Feb  5 08:21:30 2021

This module provides different metrics to
evaluate the overall communication for a given
power distribution system. We want to know how
well meters can communicate with each other.

For our analysis, we care about how far away meters
are from each other. We have developed different metrics
that capture things like how many meters are near a
central meter, how many meters are isolated, what is the
largest radius to envelope all meters in one circle, etc.

This module allows for performing this analysis on a
single model or multiple models. It has the abaility to
save these results for further analysis.

This module can be expanded to include more metrics
and/or plotting results.

@author: barn553
"""
import pandas as pd
import numpy as np
import itertools
import pyproj
import os
from joblib import Parallel, delayed
import logging
import logging.config
import json


# Creating a custom logger:
head, tail = os.path.split(os.getcwd())
config_file = os.path.join(
    head, 'results', 'gld', 'config.json')
with open(config_file, 'r') as file:
    config = json.load(file)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)


class EvaluateSystem:
    """Evaluates the power distribution system model.

    This class provides all the metrics for evaluating the
    overall communication abilities of a power distribution
    system. More information for each metric is provided
    in the documentation string of each function.

    Args:
        dataframe (pandas dataframe) - This is a pandas
        representation of the power distribution system
        model. It contains information like the name of the
        feeder, the names of the meters, and the meters'
        locations.

        meters (list) - List of the meters in a given
        power distribution system.

        pos_x (str) - The 'x' position of the meters'
        locations. For example, this might be the longitude
        value of a coordinate. This should be a column in
        the dataframe.

        pos_y (str) - The 'y' position of the meters'
        locations. For example, this might be the latitude
        value of a coordinate. This should be a column in
        the dataframe.

        unit (str) - The unit of measurement the positional
        information is currently in. For example, the GLD
        positional data is in 'feet', while the Santa Fe data
        is latitude-longitude pairs. This should be 'feet' or
        'geo', otherwise there will be an error.

    Returns:
        EvaluateSystem (obj) - An object that represents the
        MeterNetwork object of the power distribution model.
        This is the object that can be used for metric
        function calls.
    """

    def __init__(self, dataframe, meters, pos_x, pos_y, unit):
        """This initializes the class."""
        self.dataframe = dataframe
        assert 'model_name' in self.dataframe.columns,\
            'Make sure the name of the model is included.'
        self.model_name = self.dataframe['model_name'].unique()[0]
        assert 'feeder' in self.dataframe.columns,\
            'Make sure the feeder name is included in the dataframe.'
        self.feeder = self.dataframe['feeder'].unique()[0]
        logger.info(
            '----- An EvaluateSystem object has -----')
        logger.info(
            '----- been created for {} --'.format(self.feeder))
        self.meters = meters
        assert pos_x in self.dataframe.columns,\
            'Oops! {} is not in the dataframe'.format(pos_x)
        self.pos_x = pos_x
        assert pos_y in self.dataframe.columns,\
            'Oops! {} is not in the dataframe'.format(pos_y)
        self.pos_y = pos_y
        assert unit == 'feet' or unit == 'geo',\
            'Oops! "{}" is not valid; it must be "feet" or "geo"'.format(
                unit)
        self.unit = unit
        # NOTE: More descriptions of these attributes are provided
        # in the functions below.
        self.distance_dataframe = None
        self.perm_df = None
        self.dens_df = None
        self.range_df = None
        self.iso_df = None
        self.cont_df = None
        self.shc_df = None
        self.score_df = None
        self.composite_score = None

    def _modify_dataframe(self):
        """This funciton modifies the dataframe to speed up the
        get_distances function.

        It goes through all the permutations of abstact connections between
        any two meters in the system. Then, it grabs each "start" and
        "end" meters' positions. Then, it saves all this information
        as a dataframe, which can be accessed as an EvaluateSystem object's
        attribute.

        This allows for the ability to calculate the
        distance between these meter-pairs using pandas' array
        functionality (which is based on numpy's array functionality).
        This speeds up the calculation significantly.
        """
        # These are the original dataframe representation of the
        # model, the names of the positional data (i.e. 'lon', 'lat'),
        # and the unit of measurement the positional data is
        # currently in (e.g. feet or geospatial).
        df = self.dataframe
        pos_x = self.pos_x
        pos_y = self.pos_y
        unit = self.unit
        # For our analysis, we care about finding the distances
        # between ANY two meters in the system. That means
        # calculating the distance between ALL permutations of
        # pairs of meters. To speed up that calculation, we create
        # a tuple of (meter name, x-position, y-position). Then,
        # we find all the permutations of pairs of tuples. Next,
        # we grab the individual parts of the tuple. Lastly,
        # we create a dataframe of the "start" and "end" meters
        # and their positional information and save it as an
        # attribute to be called in the get_distances() function.
        #   NOTE: For the geospatial data, we use a separate
        #   function that can take the starting and ending
        #   positional data as arrays and returns an array of
        #   calculated distance between the meters. So, we make
        #   a dataframe with names and positional information only.
        #   The "feet" data calculates the change in x and change
        #   in y beforehand
        if unit == 'geo':
            # Creating the (meter name, x-position, y-position) tuple:
            df['location_tuple'] = [
                (n, df[df.name == n][pos_x].values[0],
                 df[df.name == n][pos_y].values[0])
                for n in df.name.unique()]
            # Getting all the permutations of pairs of tuples:
            perms = list(itertools.permutations(df.location_tuple, 2))
            # Grabbing the individual pieces of the tuples:
            start = [p[0][0] for p in perms]
            start_x = [p[0][1] for p in perms]
            start_y = [p[0][2] for p in perms]
            end = [p[1][0] for p in perms]
            end_x = [p[1][1] for p in perms]
            end_y = [p[1][2] for p in perms]
            # Saving the results as a dataframe to be used elsewhere:
            perm_df = pd.DataFrame(
                {'start': start, 'start_x': start_x, 'start_y': start_y,
                 'end': end, 'end_x': end_x, 'end_y': end_y},
                index=range(len(perms)))
            self.perm_df = perm_df
        elif unit == 'feet':
            # Creating the (meter name, x-position, y-position) tuple:
            df['location_tuple'] = [
                (n, df[df.name == n][pos_x].values[0],
                 df[df.name == n][pos_y].values[0])
                for n in df.name.unique()]
            # Getting all the permutations of pairs of tuples:
            perms = list(itertools.permutations(df.location_tuple, 2))
            # Grabbing the individual pieces of the tuples:
            start = [p[0][0] for p in perms]
            start_x = [p[0][1] for p in perms]
            start_y = [p[0][2] for p in perms]
            end = [p[1][0] for p in perms]
            end_x = [p[1][1] for p in perms]
            end_y = [p[1][2] for p in perms]
            # Calculating the change in x and y ahead of time:
            delta_x = [np.abs(ex - sx) for sx, ex in zip(end_x, start_x)]
            delta_y = [np.abs(ey - sy) for sy, ey in zip(end_y, start_y)]
            # Saving the results as a dataframe to be used elsewhere:
            perm_df = pd.DataFrame(
                {'start': start, 'start_x': start_x, 'start_y': start_y,
                 'end': end, 'end_x': end_x, 'end_y': end_y,
                 'delta_x': delta_x, 'delta_y': delta_y},
                index=range(len(perms)))
            self.perm_df = perm_df
        else:
            logger.error(
                '"{}" is invalid. It must be "feet" or "geo".'.format(
                    unit))

    def get_distances(self):
        """This function calculates the distances between all
        the meters in the system and saves the result as a
        dataframe to be used for further analysis.

        Args:
            (null)

        Returns:
            distance_dataframe (pandas dataframe) - This is a dataframe
            that has the calculated distance between all meters
            in a given meter network (aka model).
        """
        logger.info(
            '........................................')
        logger.info('calculating the distances between all the meters')
        if self.unit == 'geo':
            self._modify_dataframe()
            p_df = self.perm_df
            geodesic = pyproj.Geod(ellps='WGS84')
            # Calculating the distance using this function:
            #   NOTE: The default result of the calculated
            #   distance is in meters, so we multiply by 3.28084
            #   to convert it to feet. This can be expanded to
            #   provide the option of feet or meters.

            #   IMPORTANT: The longitude MUST be the first argument.
            #   So, it is important that the data read in has the
            #   the longitude values as the "x" values and latitude
            #   values as "y" values.
            p_df['distance'] = geodesic.inv(
                p_df.start_x, p_df.start_y,
                p_df.end_x, p_df.end_y)[-1] * 3.28084
            # Saving the result to be used for the different
            # metrics:
            distance_dataframe = p_df[['start', 'end', 'distance']]
            logger.info(
                '\tsaving the results to be used elsewhere')
            self.distance_dataframe = distance_dataframe
        elif self.unit == 'feet':
            self._modify_dataframe()
            p_df = self.perm_df
            # Calculating distance using the distance formula:
            p_df['distance'] = np.sqrt(
                np.square(np.array(p_df['delta_x']))
                + np.square(np.array(p_df['delta_y'])))
            # Saving the result to be used for the different
            # metrics:
            distance_dataframe = p_df[['start', 'end', 'distance']]
            logger.info(
                '\tsaving the results to be used elsewhere')
            self.distance_dataframe = distance_dataframe
        else:
            logger.error(
                '{} is an invalid option. It must be "feet" or "geo".'.format(
                    self.unit))
        logger.info('finished calculating the distances.')
        return distance_dataframe

    def meter_density(self, meter, radius):
        """This function returns the number of meters within
        a distance of x from the meter in question.

        For example, suppose we have a model of 10 meters
        ('meter1', 'meter2', ..., 'meter10'). Choose 'meter1'
        as the center. Suppose further our radius to test is
        100 feet. This function counts how many meters are within
        100 feet of 'meter1'.

        Args:
            meter (str) - The meter in question (aka the starting
            node in a graph).

            radius (float) - The distance to envelope the
            meters near the starting meter.

        Returns:
            total_meters (int) - The total number of meters within
            the radius.
        """
        logger.info(
            '........................................')
        logger.info(
            'Finding all the meters within {} (ft) of {}'.format(
                radius, meter))
        assert isinstance(radius, float),\
            'Oops, {} is not a float.'.format(radius)
        # Grabbing the dataframe that has all the calculated
        # distances between all the meters:
        dd = self.distance_dataframe
        reduced_dd = dd[(dd.start == meter) & (dd.distance <= radius)]
        # Counting the total number of meters within a certain
        # distance:
        total_meters = len(reduced_dd)
        logger.info(
            'The number of meters within {} (ft) of {} is {}.'.format(
                radius, meter, total_meters))
        return total_meters

    def meter_range(self, meter):
        """This function returns the radius, x, of the circle
        centered on a given meter encompasses all meters.


        For example, suppose we have a model of 10 meters
        (meter1, meter2, ... meter10). Choose meter1 as the
        center. This function finds the largest radius between
        meter1 and all the remaining meters.

        Args:
            meter (str) - The meter in question (aka the starting
            node in a graph).

        Returns:
            radius (float) - The maximum distance that envelopes all
            meters with a given meter as the center.
        """
        logger.info(
            '........................................')
        logger.info(
            'Finding the largest radius where {} is the center'.format(
                meter))
        # Grabbing the dataframe that has all the calculated
        # distances between all the meters:
        dd = self.distance_dataframe
        # Setting the given meter as the center:
        reduced_dd = dd[dd.start == meter]
        # Finding the maximum distance:
        radius = np.max(reduced_dd['distance'])
        logger.info(
            '{} (ft) captures all meters with {} as the center'.format(
                radius, meter))
        return radius

    def isolated_meter_count(self, radius):
        """This function returns how many meters have no other
        meters within x distance of them.


        For example, suppose we have a model of 10 meters
        (meter1, meter2, ... meter10). Suppose further meter2
        and meter3 are 300+ feet from each other and the
        remaining meters, and the remaining meters are 150
        feet or less from each other. Let the radius to test
        against be 200 feet. Then, this function would say there
        are two meters that are isolated from the other meters
        because their distances are greater than 200 feet.

        Args:
            radius (float) - A given distance to test whether
            or not meters are near each other.

        Returns:
            isolated_count (int) - The total number of meters that are
            isolated from others, given a specific distance.
        """
        assert isinstance(radius, float),\
            'Oops, {} is not a float.'.format(radius)
        logger.info(
            '........................................')
        logger.info(
            'Counting all the isolated meters within {} (ft)'.format(
                radius))
        # Grabbing the dataframe that has all the calculated
        # distances between all the meters:
        dd = self.distance_dataframe.copy()
        # Chekcing whether the calculated distances are
        # bigger than the given radius:
        bools = ['T' if d > radius else 'F' for d in dd.distance]
        dd['is_isolated'] = bools
        gpd = dd.groupby('start')
        # Counting all the isolated meters:
        gpd_df = gpd['is_isolated'].value_counts().to_frame(
            name='total_count').reset_index()
        isolated_count = len(gpd_df[
            (gpd_df.is_isolated == 'T') &
            (gpd_df.total_count == len(self.meters) - 1)]['start'].values[:])
        logger.info(
            '{} meters are isolated within {} (ft)'.format(
                isolated_count, radius))
        return isolated_count

    def meter_continuity(self, radius):
        """This function aims to see if any two meters can communicate
        with each other, either directly or indirectly, within
        a certain distance.

        For example, suppose we have a model of 10 meters
        (meter1, meter2, ... meter10). Suppose further meter2
        and meter3 are 300+ feet from each other, but they
        are 100 feet from the remaining meters. Let the radius
        to test against be 200 feet. Since meter2 and meter3
        are closer to the remaining meters (rather than each other),
        this function will say that there is continuity because
        there is an indirect path from meter2 to meter3 through
        any of the remaining meters.

        Args:
            radius (float) - A given distance to test whether
            or not a path exists between any two meters.

        Returns:
            continuity (bool) - Whether or not the meters are
            connected to each other.
        """
        logger.info(
            '........................................')
        logger.info(
            'Checking to see if paths exist between any {} {} {}'.format(
                'two meters within', radius, 'feet.'))
        assert isinstance(radius, float),\
            'Oops, {} is not a float.'.format(radius)
        # Grabbing the dataframe that has all the calculated
        # distances between all meters:
        dd = self.distance_dataframe.copy()
        # Reducing the dataframe to meters that have distances
        # less than or equal to the given radius:
        reduced_dd = dd[dd.distance <= radius]
        # Creating sets of the "start" and "end" meters:
        dd_set1 = set(dd.start.unique())
        dd_set2 = set(dd.end.unique())
        r_set1 = set(reduced_dd.start.unique())
        r_set2 = set(reduced_dd.end.unique())
        # If the reduced dataframe still has all the
        # "start" and "end" meters from the original
        # dataframe, then a path exists between any two
        # meters in the model because all their distances
        # are less than or equal to the given radius.
        # Otherwise, a path doesn't exist and the model
        # is not continuous.
        if dd_set1 == r_set1 and dd_set2 == r_set2:
            logger.info(
                '\tPaths exists between any two nodes.')
            logger.info(
                '\tThus, there is continuity across the network of meters.')
            continuity = True
        else:
            logger.info(
                '\tThere must not be a path between ANY two nodes.')
            continuity = False
        return continuity

    def single_hop_count(self, radius, y):
        """This function returns number of meters with y meters
        within x distance of them.

        For example, suppose we have a model of 10 meters
        (meter1, meter2, ... meter10). Let y = 2 and let
        radius = 200 feet. This functions counts how many
        of meter1 - meter10 have less than or equal to 2
        meters within 200 feet of them. Suppose meter1, meter2,
        and meter3 are all 150 feet from each other, while the
        remaining meters are 300+ feet from them and each other.
        This function will return 3 because meter1, meter2,
        and meter3 all have 2 meters or less within 200 feet.

        Args:
            radius (float) - A given distance to test whether
            or not a number of meters, y, are within a certain
            distance of a specified meter as the center.

            y (int) - Specific number of meters near a starting meters.

        Returns:
            single_hop_count (int) - The total number of meters
            with a certain number of meters near them within a given
            distance.
        """
        logger.info(
            '........................................')
        logger.info(
            'Counting how many meters have {} meters within {}'.format(
                y, radius))
        assert isinstance(radius, float),\
            'Oops! {} is not a float.'.format(radius)
        assert isinstance(y, int),\
            'Oops! {} is not an int.'.format(y)
        # Grabbing the dataframe that has all the calculated
        # distances between all meters:
        dd = self.distance_dataframe.copy()
        # Checking if the distance is less than or equal to
        # the given radius:
        bools = ['T' if d <= radius else 'F' for d in dd.distance]
        dd['within_radius'] = bools
        gpd = dd.groupby('start')
        # Counting how may meters have "y" meters
        # within a certain radius:
        gpd_df = gpd['within_radius'].value_counts().to_frame(
            name='total_count').reset_index()
        single_hop_count = len(gpd_df[
            (gpd_df.within_radius == 'T') &
            (gpd_df.total_count >= y)]['start'].values[:])
        logger.info(
            'There are {} meters that have {} meters within {} feet.'.format(
                single_hop_count, y, radius))
        return single_hop_count

    def all_densities(self, radii):
        """Calculates all densities for all meters for
        all radii.

        This function performs the same counting as
        the meter_density function. However, this is
        an iterative function, where it treats each of
        meters in the model as a center and counts how
        many meters are nearby within a given radius.
        Also, it does this counting over a range of
        radii, not just a single radius.

        Args:
            radii (list) - List of radii (in feet) to count the
            number of meters near a given meter.

        Returns:
            dens (list) - List of number of meters near a given
            meter within each of the radii.
        """
        logger.info(
            '........................................')
        logger.info(
            'Counting the number of meters nearby within each radius.')
        # Grabbing the dataframe that has all the calculated
        # distances between all meters:
        dd = self.distance_dataframe.copy()
        df_list = []
        for rad in radii:
            assert isinstance(rad, float),\
                'Oops! {} is not a float.'.format(rad)
            # Reducing the dataframe to meters with distances
            # less than or equal to the given radius:
            reduced_dd = dd[dd.distance <= rad]
            # Counting how many meters are within that radius
            # of each of the meters as the center:
            gpd_df = reduced_dd.groupby('start')['start'].count()\
                .to_frame(name='count').reset_index()
            gpd_df['radius'] = [rad] * len(gpd_df)
            df_list.append(gpd_df)
        # Creating a dataframe of the results to be used
        # elsewhere:
        dens_df = pd.concat(df_list, axis=0, ignore_index=True)
        density_dict = {
            'model_name': [self.model_name] * len(dens_df['radius']),
            'feeder': [self.feeder] * len(dens_df['radius']),
            'radius': dens_df['radius'],
            'count': dens_df['count']}
        dens = dens_df['count']
        # Saving the results as an attribute:
        self.dens_df = pd.DataFrame(
            density_dict, index=range(len(dens)))
        logger.info(
            'Finished counting the number of meters nearby.')
        return dens

    def all_ranges(self):
        """Calculates all the meter ranges for all meters
        as the center of each circle.

        This function performs the same calculation as
        the meter_range function. However, it performs
        this for all meters in the model where each meter
        is treated as the center.

        Args:
            (null)

        Returns:
            ranges (list) - List of the maximum radius to
            capture all the meters around a given meter
            as the center.
        """
        logger.info(
            '........................................')
        logger.info(
            'Getting all the maximum radii for each meter as the center.')
        # Grabbing the dataframe that has all the calculated
        # distances between all meters:
        dd = self.distance_dataframe.copy()
        # Finding the maximum distance to capture all
        # the meters in the circle around each meter
        # as the center:
        gpd_df = dd.groupby('start')['distance'].max().to_frame(
            name='radius').reset_index()
        gpd_df['model_name'] = [self.model_name] * len(gpd_df)
        gpd_df['feeder'] = [self.feeder] * len(gpd_df)
        ranges = gpd_df['radius']
        # Saving the results as an attribute to be used
        # elsewhere:
        self.range_df = gpd_df
        logger.info(
            'Finished getting all the maximum radii for each meter.')
        return ranges

    def all_isolates(self, radii):
        """Calculates isolated meter count for all meters for
        all radii.

        This function does the same counting as the
        isolated_meter_count function. However, it does
        this counting for a range of radii, not just
        a single radius.

        Args:
            radii (list) - List of radii (in feet) for
            counting all the isolated meters.

        Returns:
            iso (list) - List of all the isolated meter counts
            for each of the radii.
        """
        logger.info(
            '........................................')
        logger.info(
            'Getting the isolated meter count for all radii.')
        # Getting the isolated meter count for each radius:
        iso_tuples = [
            (rad, self.isolated_meter_count(rad)) for rad in radii]
        # Creating a dataframe to be used elsewhere:
        isolated_dict = {
            'model_name': [self.model_name] * len(iso_tuples),
            'feeder': [self.feeder] * len(iso_tuples),
            'radius': [tup[0] for tup in iso_tuples],
            'count': [tup[1] for tup in iso_tuples]}
        iso = [tup[1] for tup in iso_tuples]
        # Saving results as an attribute:
        self.iso_df = pd.DataFrame(
            isolated_dict, index=range(len(iso)))
        logger.info(
            'Finished getting the isolated meter count for all radii.')
        return iso

    def all_continuous(self, radii):
        """Calculates continuous count for all meters for
        all radii.

        This function does the same as the meter_continuity
        function. However, this performs the same analysis
        for a range of radii, not just a single radius.

        Args:
            radii (list) - List of radii (in feet) for finding
            if paths exist between any two meters for each of the
            radii.

        Returns:
            conts (list) - List of the booleans of whether or not
            paths exist between any two nodes within given radii.
        """
        logger.info(
            '........................................')
        logger.info(
            'Checking to see if paths exist between any two {}'.format(
                'nodes within each of the given radii.'))
        # Checking if the model is continuous across
        # all radii:
        conts_tuples = [
            (rad, self.meter_continuity(rad)) for rad in radii]
        # Creating a dataframe of the results to be used
        # elsewhere:
        continuity_dict = {
            'model_name': [self.model_name] * len(conts_tuples),
            'feeder': [self.feeder] * len(conts_tuples),
            'radius': [tup[0] for tup in conts_tuples],
            'continuous': [tup[1] for tup in conts_tuples]}
        conts = [tup[1] for tup in conts_tuples]
        # Saving the results as an attribute:
        self.cont_df = pd.DataFrame(
            continuity_dict, index=range(len(conts)))
        logger.info(
            'Finished seeing if paths exist within each of the radii.')
        return conts

    # (2021-03-10): range of y-values to test:
    # 1, 2, 3, 4, 5, 10
    def all_single_hops(self, radii):
        """Calculates single hop count for all meters for all
        radii.

        This function does the same counting as the
        single_hop_count function. However, it performs
        this counting for a range of radii, not just a
        single radius.

        Args:
            radii (list) - List of radii (in feet) for counting
            how many neters have a certain number of meters
            near them.

        Returns:
            shc (list) - List of all the single hop counts
            for all the radii.
        """
        # Reduced the number of meters nearby to speed up
        # the calculations:
        #   NOTE: In reality, it's not likely that
        #   ALL meters will be near each other. So,
        #   reducing the amount of values to test is
        #   for better analysis and realistic results.
        y_list = [1, 2, 3, 4, 5, 10]
        logger.info(
            '........................................')
        logger.info(
            'Counting the number of meters that have {}'.format(
                'a given number of meters nearby within each radius.'))
        # Grabbing the dataframe that has all the calculated
        # distances between all meters:
        dd = self.distance_dataframe.copy()
        df_list = []
        for rad in radii:
            assert isinstance(rad, float),\
                'Oops! {} is not a float.'.format(rad)
            # Reducing the dataframe to meters with distances
            # less than or equal to the given radius:
            reduced_dd = dd[dd.distance <= rad]
            # Counting how many meters are withing the given
            # radius near each of the meters as the center:
            gpd_df = reduced_dd.groupby('start')['start'].count()\
                .to_frame(name='total_count').reset_index()
            gpd_df['radius'] = [rad] * len(gpd_df)
            df_list.append(gpd_df)
        dens_df = pd.concat(df_list, axis=0, ignore_index=True)
        df_list2 = []
        for y in y_list:
            assert isinstance(y, int),\
                'Oops! {} is not an int.'.format(y)
            # Counting how many meters have at least y meters
            # nearby:
            r_df = dens_df[dens_df['total_count'] >= y]
            gpd_r_df = r_df.groupby('radius')['total_count'].count()\
                .to_frame(name='count').reset_index()
            gpd_r_df['y'] = [y] * len(gpd_r_df)
            df_list2.append(gpd_r_df)
        # Saving results as a dataframe to be used
        # elsewhere:
        shc_df = pd.concat(df_list2, axis=0, ignore_index=True)
        shc_df['model_name'] = [self.model_name] * len(shc_df)
        shc_df['feeder'] = [self.feeder] * len(shc_df)
        shc_df = shc_df.set_index(['model_name', 'feeder']).reset_index()
        # Saving results as an attribute:
        self.shc_df = shc_df
        shc = self.shc_df['count']
        logger.info('Finished getting all the single hop counts.')
        return shc

    def evaluate_system(self, radii):
        """This function performs all metrics for a given system
        and returns a weighted, overall score.

        The purpose of this function is to create an overall
        score to show how well meters can communicate with
        each other. It takes each of the results of the
        different metrics and creates a weighted value, similar
        to a weighted grade for a course in school.

        Weighted Values:
            Isolated Meter Counts:
                For our analysis, we want as few isolated meters
                as possible. The lower the isolated meter count,
                the better it is for the model. This will show
                that there are meters close enough to each other
                to communicate.

                To get the weighted isolated meter count, we find
                the average of all the isolated meter counts. Then,
                we divide that value by the total number of meters
                in the model. The worst case would be that the average
                is equal to the total number of meters in the system;
                in other words, all meters are isolated. The best case
                would be that there are no isolated meters. So, to
                turn this weighted score into a positive value to show
                that there are few isolated meters, we take 1 minus
                the weighted value. Thus, our weighted isolated meter
                count value is as follows:
                    iso = 1 - ((sum(counts) / len(counts)) / total_meters)

            Densities:
                For our analysis, we want as many meters near
                each other as possible. This will show that
                the meters can communicate well with each other.

                To get the weighted density count, we find the
                average of all the density counts. Then, we divide
                that value by the total number of meters minus 1.
                The best case is that the average of the density
                counts is equal to the total number of meters
                minus 1. That would mean our model is highly
                dense. The worst case would be the average is
                0, which would say that our model is not dense
                at all. So, our weighted density count values
                is as follows:
                    dens = (sum(counts) / len(counts)) / total_meters - 1

                2021-03-23: Dividing by maximum density value instead;
                will come back to this when we get more mony.

            Ranges:
                For our analysis, we need to know what the ranges
                for different meters as the center are. This will
                inform us how spread out the meters are from
                each other. For now, an extremely large range value
                is considered as based. However, it is important
                to note that it is quite possible that meters for
                a single feeder are spread out from each other in
                the real world.

                To get a weighted range value, we find the
                average of all the ranges. Then, we divide that
                value by the maximum range. The worse case is that
                the average is equal to the maximum. This tells
                us that the meters are very spread out from each
                other. The best case is that the average is very
                low compared to the maximum. To turn this value
                into a positive value to show that the meters
                aren't spread out from each other, we take 1 minus
                that weighted value. Thus, our weighted range value
                is as follows:
                    range = 1 - ((sum(ranges) / len(ranges)) / max(ranges))

            Continuous:
                For our analysis, we want to know if any two
                meters can communicate to each other, whether
                that is diretly or indirectly.

                To get a weighted continuity score, we find the
                average of the continuity scores. The best case
                is that the average continuity score would be
                equal to 1. That would tell us that all meters
                can communicate to each other, either directly
                or indirectly. The worst case would be that the
                average is equal to 0. That would tell us that
                all the meters cannot communicate to each other,
                either directly or indirectly. So, the weighted
                continuity score is as follows:
                    cont = sum(counts) / len(counts)

            Single Hop Counts:
                For our analysis, we need to know how many
                meters have a certain number of meters nearby.
                This is a form of density calculations. This
                will tell us, in a way, how many options are
                available for meters to communicate with other
                meters.

                To get a weighted single hop count score, we
                find the average of all single hop counts. Then,
                we divide by the total number of meters. The
                best case is when the average is equal to the
                total number of meters. In a similar vain, this
                tells us that our model is highly dense. The worst
                case is when the average is very low. So, our
                weight single hop count value is as follows:
                    shc = (sum(counts) / len(counts)) / total_meters

            Final Score:
                This is the overall score of a power distribution
                model. This score tells us how well the meters
                in the model can communicate with each other. The
                higher the score, the better the meters can
                communicate with each other. Right now, each
                metric is weighted evenly. After more analysis
                is performed, the weights on each metric will
                change.

                The score value is as follows:
                    score = 0.2 * (dens + iso + range + cont + shc)

        Args:
            radii (list or array) - List or array of radii for
            performing the metrics.

        Returns:
            score (float) - The weighted score of all the metrics
            for all meters for all radii. It is represented as a
            percent.
        """
        logger.info(
            '........................................')
        logger.info(
            'Caclulating the composite score for the meter network.')
        # Checking whether or the metric dataframes are empty or not:
        #   NOTE: If they are empty, then we call the functions to
        #   fill them out and grab the results. If they're not empty,
        #   then we just grab the results and perform the calculations.
        if (self.iso_df.empty or self.dens_df.empty
                or self.shc_df.empty or self.range_df.empty
                or self.cont_df.empty):
            fns = [self.all_isolates, self.all_single_hops,
                   self.all_continuous, self.all_densities]
            # This speeds up going through the functions by
            # parallelizing:
            delayed_fns = [delayed(fn)(radii) for fn in fns]
            results = Parallel(n_jobs=4, prefer='threads')(delayed_fns)
            isolates = results[0]
            single_hops = results[1]
            continuous = results[2]
            densities = results[3]
        else:
            isolates = self.iso_df['count'].values
            single_hops = self.shc_df['count'].values
            continuous = list(self.cont_df['continuous'].values)
            densities = self.dens_df['count'].values
            range_df = self.range_df
            ranges = range_df['radius']
        # Calculating the fractions:
        meters = self.meters
        iso_frac = 1 - ((np.sum(isolates) / len(isolates)) / len(meters))
        shc_frac = (np.sum(single_hops) / len(single_hops)) / len(meters)
        cont_frac = continuous.count(True) / len(continuous)
        # 2021-03-23: Trying to divide density by max density for now:
        dens_frac = (np.sum(densities) / len(densities)) / np.max(densities)
        # dens_frac = (np.sum(densities) / len(densities)) / (len(meters) - 1)
        range_frac = 1 - ((np.sum(ranges) / len(ranges)) / np.max(ranges))
        logger.info(
            '\tdensity score = {}, isolated score = {}'.format(
                dens_frac, iso_frac))
        logger.info(
            '\tcontinuous score = {}, single hop score = {}'.format(
                cont_frac, shc_frac))
        logger.info('\trange score = {}'.format(range_frac))
        # For now, evenly weighting each of the fractions:
        score = 0.2 * (dens_frac + iso_frac + shc_frac
                       + cont_frac + range_frac)
        logger.info(
            'The overall score for this network = {}{}'.format(
                score, '%'))
        # Saving the scores:
        self.composite_score = score
        self.score_df = pd.DataFrame(
            {'model_name': self.model_name,
             'feeder': self.feeder,
             'composite_score': self.composite_score,
             'density': dens_frac,
             'isolated': iso_frac,
             'single_hop': shc_frac,
             'continuous': cont_frac,
             'range': range_frac,
             'number_of_meters': len(self.meters)},
            index=range(0, 1))
        return score * 100.0


class Results:
    """This class collects and saves the results from more
    than one power distribution system evaluation.

    For our analysis, we not only care about the communication
    between meters for a single model, but many models. This class
    is for collecting ALL the results from ALL models tested
    for analysis.
    """

    def __init__(self):
        """This initializes the class."""
        logger.info(
            '########### Created a Results object for saving data ###########')
        self.systems = []

    def add(self, system):
        """This function adds the systems to the Results class.

        Since each system that gets added is an object, all
        of its attributes are saved (and added) as well.

        Args:
            system (object) - An EvaluateSystem object that
            has meter network information and calculated
            results from metrics performed.

        Returns:
            (null)
        """
        logger.info(
            'Added {} to the Results object'.format(system.feeder))
        self.systems.append(system)

    def save(self, output_path, output_name):
        """This function saves all the results as an hdf5 file.

        Args:
            output_path (path) - The path to send the results file.

            output_name (str) - The name of the results file.

        Returns:
            (null)
        """
        path = os.path.join(output_path, output_name)
        # Grabbing all the dataframes from all the systems:
        densities = [s.dens_df for s in self.systems]
        ranges = [s.range_df for s in self.systems]
        isos = [s.iso_df for s in self.systems]
        continuous = [s.cont_df for s in self.systems]
        shcs = [s.shc_df for s in self.systems]
        scores = [s.score_df for s in self.systems]
        logger.info('\t Creating an HDF5 file')
        # Creating an HDF% store:
        #   NOTE: This will allow us to save the
        #   results from all the dataframes into
        #   one file without running into file size
        #   issues.
        store = pd.HDFStore(path)
        # Combining all the results into single dataframes:
        dens_df = pd.concat(densities, axis=0, ignore_index=True)
        range_df = pd.concat(ranges, axis=0, ignore_index=True)
        iso_df = pd.concat(isos, axis=0, ignore_index=True)
        cont_df = pd.concat(continuous, axis=0, ignore_index=True)
        shc_df = pd.concat(shcs, axis=0, ignore_index=True)
        scores_df = pd.concat(scores, axis=0, ignore_index=True)
        logger.info('Saving all the results to the file')
        # Adding the dataframes to the HDF5 file:
        store['density'] = dens_df
        store['range'] = range_df
        store['isolated'] = iso_df
        store['continuous'] = cont_df
        store['single_hop'] = shc_df
        store['scores'] = scores_df
        store.close()
        logger.info('Finished saving the results to file')
        logger.info(
            '########### Finished system evaluation calculations. ###########')
