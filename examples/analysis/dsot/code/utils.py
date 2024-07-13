"""Miscellaneous utility functions for pyvvo"""
import re
import math
import cmath
import subprocess
import logging
from datetime import datetime, timezone, date
import os
from functools import wraps
import numpy as np
import pandas as pd
import queue
try:
    import simplejson as json
except ModuleNotFoundError:
    import json
import signal
from contextlib import contextmanager

# Setup log.
LOG = logging.getLogger(__name__)

# Regular expressions for complex number parsing (from GridLAB-D).
RECT_EXP = re.compile(r'[+-]*([0-9])+(\.)*([0-9])*(e[+-]*([0-9])+)*[+-]'
                      + r'([0-9])+(\.)*([0-9])*(e[+-]([0-9])+)*j')
FIRST_EXP = re.compile(r'[+-]*([0-9])+(\.)*([0-9])*(e[+-]*([0-9])+)*')
SECOND_EXP = re.compile(r'[+-]*([0-9])+(\.)*([0-9])*(e[+-]*([0-9])+)*[dr]')

# Define directory
THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Timeout for the wait_for_lock function. May want to upgrade that to
# take inputs in the future.
LOCK_TIMEOUT = 60


def parse_complex_str(s):
    """Parse a string representing a complex number.

    Specifically designed to work with various types of output from
    GridLAB-D.

    Raises a ValueError if string cannot be cast to a complex number.

    :param s: string representing a complex number. Examples:
        +12.34-1.2j VA
        +15-20d V
        +12-3.14r I

    :returns: complex number, unit associated with it.
    """
    # Return a ValueError if the input is not a string.
    if not isinstance(s, str):
        raise ValueError('The input to parse_complex_str must be a string.')

    # First, strip whitespace, then split on whitespace to strip off the
    # unit
    t = s.strip().split()
    # Grab complex number part of the string.
    c = t[0]

    # Attempt to grab the unit.
    try:
        u = t[1]
    except IndexError:
        # There's no unit.
        u = None

    # Take action depending on whether or not the complex number is
    # already in rectangular form.
    if RECT_EXP.fullmatch(c):
        # If it's already in rectangular form, there's not much to do.
        n = complex(c)
    else:
        # Extract the first and second terms
        mag_match = FIRST_EXP.match(c)
        phase_match = SECOND_EXP.search(c)

        # If the number doesn't fit the form, raise exception.
        if (not mag_match) or (not phase_match):
            raise ValueError(('Inputs to getComplex must have a sign defined '
                              + 'for both components.\n'
                              + 'Decimals are optional.\n'
                              + 'Number must end in j, d, or r.'))

        # Grab the groups of matches
        mag_float = float(mag_match.group())
        phase_str = phase_match.group()

        # Extract the unit and phase from the phase string
        phase_unit = phase_str[-1]
        phase_float = float(phase_str[:-1])
        # If the unit is degrees, convert to radians
        if phase_unit == 'd':
            phase_float = math.radians(phase_float)

        # Convert to complex.
        n = (mag_float * cmath.exp(1j * phase_float))

    return n, u


def read_gld_csv(f):
    """Read a .csv file from a GridLAB-D recorder into a DataFrame.

    NOTE: No time parsing/indexing will be attempted, as this isn't
    presently needed.
    """
    # Read the file
    df = pd.read_csv(f, skiprows=8)

    # Rename the '# timestamp' column. Pretty hard-coded, but oh well.
    df.rename(columns={'# timestamp': 'timestamp'}, inplace=True)

    # Remove leading whitespace from columns. Unfortunately, the
    # GridLAB-D output is inconsistent with spaces, which makes pandas
    # unhappy.
    df.rename(mapper=str.strip, inplace=True, axis=1)

    # Loop over the columns, and attempt to convert the value to a
    # complex number. If we get a ValueError, we won't convert.
    for c in df.columns:
        # Grab the first element.
        item = df.iloc[0][c]

        try:
            parse_complex_str(item)
        except ValueError:
            # Move to the next column - this string can't be converted.
            continue

        # Create a Series with the complex numbers. Nobody is claiming
        # this is efficient: it doesn't have to be. PyVVO primarily uses
        # the MySQL recorders (which don't have this problem). We're
        # just using these .csv files for unit tests.
        s = pd.Series(0+1j*0, index=df.index)

        # Loop over the items in this column.
        for ind, item in df[c].iteritems():

            # Place the parsed complex number in the series.
            s.loc[ind] = parse_complex_str(item)[0]

        # Replace this column.
        df[c] = s

    return df


def list_to_string(in_list, conjunction):
    """Simple helper for formatting lists contaings strings as strings.

    This is intended for simple lists that contain strings. Input will
    not be checked.

    :param in_list: List to be converted to a string.
    :param conjunction: String - conjunction to be used (e.g. and, or).
    """
    return ", ".join(in_list[:-1]) + ", {} {}".format(conjunction, in_list[-1])


def gld_installed(env=None):
    """Test if GridLAB-D is installed or not."""
    # Attempt to run GridLAB-D.
    result = subprocess.run("gridlabd --version", shell=True,
                            stderr=subprocess.STDOUT,
                            stdout=subprocess.PIPE, env=env)

    LOG.debug('"gridlabd --version" result:\n{}'.format(result.stdout))

    if result.returncode == 0:
        return True
    else:
        return False


def run_gld(model_path, env=None):
    """Helper to run a GRIDLAB-D model. The GridLAB-D executable will be
    run from the same directory as the model.

    If needed, run options can be added in the future.

    :param model_path: path (preferably full path) to GridLAB-D model.
    :param env: used to override the environment for subprocess. Leave
        this as None.

    :returns: A subprocess.CompletedProcess object corresponding to the
        GridLAB-D run.
    """
    cwd = os.path.dirname(model_path)
    if len(cwd) == 0:
        cwd = None

    result = subprocess.run("gridlabd {}".format(model_path), shell=True,
                            stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                            env=env, cwd=cwd)

    if result.returncode == 0:
        LOG.debug('GridLAB-D model {} ran successfully.'.format(model_path))
    else:
        m = ('GridLAB-D model {} failed to run.\n\tstdout:{}\n\t'
             + 'stderr:{}').format(model_path, result.stdout, result.stderr)
        LOG.error(m)

    return result


def dt_to_us_from_epoch(dt):
    """Convert datetime.datetime object to microseconds since the epoch.

    :param dt: datetime.datetime object.

    :returns: microseconds since the epoch as a string.
    """
    return '{:.0f}'.format(dt.timestamp() * 1e6)


def dt_to_s_from_epoch(dt):
    """Convert datetime.datetime object to seconds since the epoch as
    a string.
    :param dt: Python datetime.datetime object.

    :returns: seconds since the epoch as a string.
    """
    return '{:.0f}'.format(dt.timestamp())


def platform_header_timestamp_to_dt(timestamp):
    """Convert timestamp (milliseconds from epoch) to datetime object.
    This is specifically built for reading the 'timestamp' field of the
    header which comes in from the GridAPPS-D platform.

    :param timestamp: Integer or float. Milliseconds since
        1970-01-01 00:00:00.000. Assumed to be in UTC.

    :returns: dt: timezone aware (UTC) datetime.datetime object.
    """
    return datetime.fromtimestamp(timestamp / 1000, timezone.utc)


def simulation_output_timestamp_to_dt(timestamp):
    """Convert timestamp (seconds from epoch) to datetime object.
    This is specifically built for reading the 'timestamp' field of the
    message object which comes from the GridAPPS-D simulator output.

    :param timestamp: Integer or float. Seconds since
        1970-01-01 00:00:00.000. Assumed to be in UTC.

    :returns: dt: timezone aware (UTC) datetime.datetime object.
    """
    return datetime.fromtimestamp(timestamp, timezone.utc)


# noinspection PyShadowingBuiltins
def map_dataframe_columns(map, df, cols):
    """Helper to apply a map to specified columns in a pandas DataFrame.

    :param map: valid input to pandas.Series.map.
    :param df: pandas DataFrame.
    :param cols: list of columns in 'df' to apply 'map' to.
    """
    # Check inputs (but allow pandas to check the map).
    if not isinstance(df, pd.DataFrame):
        raise TypeError('df input must be a pandas DataFrame.')

    if not isinstance(cols, list):
        raise TypeError('cols input must be a list.')

    for col in cols:
        try:
            df[col] = df[col].map(map)
        except KeyError:
            # If we're trying to map a column which doesn't exist,
            # warn.
            LOG.warning('Column {} does not exist in DataFrame.'.format(col))

    return df


def power_factor(s: np.ndarray) -> np.ndarray:
    """Given a numpy array of complex values, compute power factor.
    If the power factor is lagging, a positive value will be returned.
    If the power factor is leading, a negative value will be returned.

    Reference:

    Power System Analysis and Design, 5th Edition, by Glover, Sarma, and
    Overbye

    In Section 2.2, power factor is defined as
    :math:`\\cos (\\delta - \\beta)` where :math:`\\delta - \\beta` is
    the angle between the voltage and current. If
    :math:`\\beta < \\delta`, then the power factor is lagging. If
    :math:`\\beta > \\delta`, then the power factor is leading.
    The power factor is positive by convention. If
    :math:`|\\delta - \\beta| > \\pi/2`, then the reference direction
    for the current may be reversed, resulting in a positive value of
    :math:`\\cos (\\delta - \\beta)`.

    In the case where the reference direction of current is reversed,
    we'll simply rotate our complex number by 180 degrees.

    Note that any 0-valued power factors will be converted to np.nan
    and a warning will be logged.

    :param s: numpy.ndarray of complex values representing apparent
        power (VA).

    :returns: An array of power factor values. Value will be negative
        if leading, positive if lagging. Any 0's will be changed to
        np.nan.
    """
    # Extract the angle.
    angle = np.angle(s, deg=False)
    # Find where the magnitude of the angle is > 90 degrees
    g_90 = np.abs(angle) > (np.pi / 2)

    if g_90.any():
        # Change the current reference by multiplying s by -1.
        # Recall that S = VI*. If we change the reference direction for
        # the current, we're replacing I* with (-I)*, which is
        # equivalent to multiplying S by -1.
        neg_s = s[g_90] * -1
        angle[g_90] = np.angle(neg_s)

    # Now compute the power factor, and change sign to meet our
    # convention that positive is lagging, negative is leading.
    # Note this conflicts with the "GSO" books convention
    # that power factor is always positive.
    pf = np.cos(angle) * np.sign(angle)

    # Cast any zeros to NaNs.
    zero_mask = pf == 0
    if zero_mask.any():
        LOG.warning('Zero power factor values found, casting to np.nan.')
        pf[zero_mask] = np.nan

    # And we're done.
    return pf


def get_complex(r, phi, degrees=True):
    """Given polar coordinates, return complex numbers.

    :param r: radius/magnitude. Scalar or numpy array.
    :param phi: angle. Scalar or numpy array. Assumed to be in degrees
        if degrees=True, otherwise assumed to be in radians.
    :param degrees: boolean, True for degrees, False for radians.
    """
    if degrees:
        return r * np.exp(1j * np.radians(phi))
    else:
        return r * np.exp(1j * phi)


def read_config():
    """Simpler helper to read the PyVVO configuration file."""
    with open(os.path.join(THIS_DIR, 'pyvvo_config.json'), 'r') as f:
        config = json.load(f)

    return config


def add_timedelta_to_time(t, td):
    """Add a timedelta object to a time object using a dummy datetime.

    :param t: datetime.time object.
    :param td: datetime.timedelta object.

    :returns: datetime.time object, representing the result of t + td.

    NOTE: Using a gigantic td may result in an overflow. You've been
    warned.
    """
    # Create a dummy date object.
    dummy_date = date(year=100, month=1, day=1)

    # Combine the dummy date with the given time.
    dummy_datetime = datetime.combine(date=dummy_date, time=t, tzinfo=t.tzinfo)

    # Add the timedelta to the dummy datetime.
    new_datetime = dummy_datetime + td

    # Return the resulting time, including timezone information.
    return new_datetime.timetz()


class Error(Exception):
    """Top level exception for utils."""
    pass


class FunctionTimeoutError(Error):
    """Exception raised by the time_limit context manager."""
    pass


@contextmanager
def time_limit(seconds: int, msg: str = None):
    """Context manager to run code with a timeout.

    Source: https://stackoverflow.com/a/601168/11052174

    Caveats:
        - Some S.O. users have noted that signals and threads don't
            mix well.
        - Not all functions can be interrupted by signals:
            https://stackoverflow.com/a/34895076/11052174
        - If alarms are being used elsewhere, this may be a problem.

    :param seconds: Integer number of seconds allowed before a
        FunctionTimeoutError is raised.
    :param msg: Message to provide if a FunctionTimeoutError is
        raised.

    :raises FunctionTimeoutError: Raised if code doesn't complete within
        seconds.
    """
    if msg is None:
        msg = "Timed out!"

    # noinspection PyUnusedLocal
    def signal_handler(signum, frame):
        raise FunctionTimeoutError(msg)

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Disable the alarm.
        signal.alarm(0)


class LockTimeoutError(Error):
    """Raised if a call to a threading.Lock object's acquire method
    time out. Specifically, this is raised in wait_for_lock.
    """
    pass


def wait_for_lock(method):
    """Decorator for class methods which use a Lock object from the
    threading module. The attribute must be named _lock.

    The SimOutRouter (gridappsd_platform) uses this to avoid collisions
    due to multi-threading.

    https://stackoverflow.com/a/36944992/11052174
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        # Block.
        acquired = self._lock.acquire(blocking=True, timeout=LOCK_TIMEOUT)

        if not acquired:
            raise LockTimeoutError('Failed to acquire lock within {} seconds'
                                   .format(LOCK_TIMEOUT))

        # Execute the method
        try:
            result = method(self, *args, **kwargs)
        finally:
            # Always indicate we're done.
            self._lock.release()

        return result

    return wrapper


def dump_queue(q, i):
    """Helper to empty a queue into a list.

    :param q: A queue.Queue like object (e.g.
        multiprocessing.JoinableQueue)
    :param i: A list object, for which items from q will be appended to.

    :returns: i. While this isn't necessary, it's explicit.
    """
    while True:
        try:
            i.append(q.get_nowait())
        except queue.Empty:
            return i


def drain_queue(q):
    """Helper to simply clear out a queue. The items in the queue will
    be discarded. If the queue is joinable (has a task_done() method),
    it will be called for each get_nowait() call.

    :param q: A queue.Queue lik object (e.g.
        multiprocessing.JoinableQueue)

    :returns: None
    """
    while True:
        try:
            q.get(block=True, timeout=0.1)
            try:
                q.task_done()
            except AttributeError:
                pass

        except queue.Empty:
            break
