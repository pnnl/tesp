# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: fncs.py
""" Functions that provide access from Python to the FNCS library

Notes:
    Depending on the operating system, libfncs.dylib, libfncs.dll 
    or libfncs.so must already be installed. Besides the defined Python 
    wrapper functions, these pass-through library calls are always needed:

    - *fncs.finalize*: call after the simulation completes
    - *fncs.time_request (long long)*: request the next time step; blocks execution of this process until FNCS grants the requested time. Then, the process should check for messages from FNCS.

    These pass-through calls are also available, but not used in TESP:

    - *fncs.route*
    - *fncs.update_time_delta*
    - *fncs.get_id*
    - *fncs.get_simulator_count*
    - *fncs.get_events_size*
    - *fncs.get_keys_size*
    - *fncs.die*: stops FNCS and sends 'die' to other simulators

References:
    `ctypes <https://docs.python.org/3/library/ctypes.html>`_

    `FNCS <https://github.com/FNCS/fncs/>`_

Examples:
    - under tesp_support, see substation.py, precool.py and tso_PYPOWER_f.py
    - under examples, see loadshed/loadshed.py

"""
import ctypes
import platform

_libname = "libfncs.so"

if platform.system() == 'Darwin':
    _libname = "libfncs.dylib"
elif platform.system() == 'Windows':
    _libname = "libfncs"

try:
    _lib = ctypes.CDLL(_libname)

    _initialize = _lib.fncs_initialize
    _initialize.argtypes = []
    _initialize.restype = None

    _initialize_config = _lib.fncs_initialize_config
    _initialize_config.argtypes = [ctypes.c_char_p]
    _initialize_config.restype = None

    _agentRegister = _lib.fncs_agentRegister
    _agentRegister.argtypes = []
    _agentRegister.restype = None

    _agentRegisterConfig = _lib.fncs_agentRegisterConfig
    _agentRegisterConfig.argtypes = [ctypes.c_char_p]
    _agentRegisterConfig.restype = None

    _is_initialized = _lib.fncs_is_initialized
    _is_initialized.argtypes = []
    _is_initialized.restype = ctypes.c_int

    _time_request = _lib.fncs_time_request
    _time_request.argtypes = [ctypes.c_ulonglong]
    _time_request.restype = ctypes.c_ulonglong

    _publish = _lib.fncs_publish
    _publish.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    _publish.restype = None

    _publish_anon = _lib.fncs_publish_anon
    _publish_anon.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    _publish_anon.restype = None

    _agentPublish = _lib.fncs_agentPublish
    _agentPublish.argtypes = [ctypes.c_char_p]
    _agentPublish.restype = None

    _route = _lib.fncs_route
    _route.argtypes = [ctypes.c_char_p,
                      ctypes.c_char_p,
                      ctypes.c_char_p,
                      ctypes.c_char_p]
    _route.restype = None

    _die = _lib.fncs_die
    _die.argtypes = []
    _die.restype = None

    _finalize = _lib.fncs_finalize
    _finalize.argtypes = []
    _finalize.restype = None

    _update_time_delta = _lib.fncs_update_time_delta
    _update_time_delta.argtypes = [ctypes.c_ulonglong]
    _update_time_delta.restype = None

    _free = _lib._fncs_free
    _free.argtypes = [ctypes.c_void_p]
    _free.restype = None

    _get_events_size = _lib.fncs_get_events_size
    _get_events_size.argtypes = []
    _get_events_size.restype = ctypes.c_size_t

    _get_events = _lib.fncs_get_events
    _get_events.argtypes = []
    _get_events.restype = ctypes.POINTER(ctypes.POINTER(ctypes.c_char))

    _get_event_at = _lib.fncs_get_event_at
    _get_event_at.argtypes = [ctypes.c_size_t]
    _get_event_at.restype = ctypes.c_void_p

    _agentGetEvents = _lib.fncs_agentGetEvents
    _agentGetEvents.argtypes = []
    _agentGetEvents.restype = ctypes.c_void_p

    _get_value = _lib.fncs_get_value
    _get_value.argtypes = [ctypes.c_char_p]
    _get_value.restype = ctypes.c_void_p

    _get_values_size = _lib.fncs_get_values_size
    _get_values_size.argtypes = [ctypes.c_char_p]
    _get_values_size.restype = ctypes.c_size_t

    _get_values = _lib.fncs_get_values
    _get_values.argtypes = [ctypes.c_char_p]
    _get_values.restype = ctypes.POINTER(ctypes.POINTER(ctypes.c_char))

    _get_value_at = _lib.fncs_get_value_at
    _get_value_at.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    _get_value_at.restype = ctypes.c_void_p

    _get_keys_size = _lib.fncs_get_keys_size
    _get_keys_size.argtypes = []
    _get_keys_size.restype = ctypes.c_size_t

    _get_keys = _lib.fncs_get_keys
    _get_keys.argtypes = []
    _get_keys.restype = ctypes.POINTER(ctypes.POINTER(ctypes.c_char))

    _get_key_at = _lib.fncs_get_key_at
    _get_key_at.argtypes = [ctypes.c_size_t]
    _get_key_at.restype = ctypes.c_void_p

    _get_name = _lib.fncs_get_name
    _get_name.argtypes = []
    _get_name.restype = ctypes.c_void_p

    _get_id = _lib.fncs_get_id
    _get_id.argtypes = []
    _get_id.restype = ctypes.c_int

    _get_simulator_count = _lib.fncs_get_simulator_count
    _get_simulator_count.argtypes = []
    _get_simulator_count.restype = ctypes.c_int

    _get_version = _lib.fncs_get_version
    _get_version.argtypes = [ctypes.POINTER(ctypes.c_int),
                             ctypes.POINTER(ctypes.c_int),
                             ctypes.POINTER(ctypes.c_int)]
    _get_version.restype = None
except:
    pass

def time_request(time):
    """ FNCS time request

    Args:
        time (int): requested time.
    """
    return _time_request(time)

def initialize(config=None):
    """ Initialize the FNCS configuration

    Args:
        config (str): a ZPL file. If None (default), provide YAML file in FNCS_CONFIG_FILE environment variable.
    """
    if config:
        _initialize_config(config)
    else:
        _initialize()

def agentRegister(config=None):
    """ Initialize the FNCS configuration for the agent interface

    Args:
        config (str): a ZPL file. If None (default), provide YAML file in FNCS_CONFIG_FILE environment variable.
    """
    if config:
        _agentRegisterConfig(config)
    else:
        _agentRegister()

def is_initialized():
    """ Determine whether the FNCS library has been initialized

    Returns:
        Boolean: True if initialized, False if not.
    """
    return 1 == _is_initialized()

def publish(key, value):
    """ Publish a value over FNCS, under the simulator name

    Args:
        key (str): topic under the simulator name
        value (str): value
    """
    _publish(str(key).encode('utf-8'), str(value).encode('utf-8'))

def publish_anon(key, value):
    """ Publish a value over FNCS, under the 'anonymous' simulator name

    Args:
        key (str): topic under 'anonymous'
        value (str): value
    """
    _publish_anon(str(key).encode('utf-8'), str(value).encode('utf-8'))

def agentPublish(value):
    """ Publish a value over FNCS, under the configured simulator name / agent name

    Args:
        value (str): value
    """
    _agentPublish(str(value).encode('utf-8'))

def route(sender, receiver, key, value):
    """ Route a value over FNCS from sender to receiver

    Args:
        sender (str): simulator routing the message
        receiver (str): simulator to route the message to
        key (str): topic under the simulator name
        value (str): value
    """
    _route(str(sender).encode('utf-8'), str(receiver).encode('utf-8'), str(key).encode('utf-8'), str(value).encode('utf-8'))

def get_events():
    """ Retrieve FNCS messages after time_request returns

    Returns:
        list: tuple of decoded FNCS events
    """
    _events = _get_events()
    size = get_events_size()
    events_tmp = [ctypes.cast(_events[i], ctypes.c_char_p).value for i in range(size)]
    events = [x.decode() for x in events_tmp]
    for i in range(size):
        _free(_events[i])
    _free(_events)
    return events

def get_event_at(i):
    """ Retrieve FNCS message by index number after time_request returns

    Returns:
        str: one decoded FNCS event
    """
    _event = _get_event_at(i)
    event_tmp = ctypes.string_at(ctypes.cast(_event, ctypes.c_char_p).value)
    event = event_tmp.decode()
    _free(_event)
    return event

def agentGetEvents():
    """ Retrieve FNCS agent messages

    Returns:
        str: concatenation of agent messages
    """
    _event = _agentGetEvents()
    event_tmp = ctypes.string_at(ctypes.cast(_event, ctypes.c_char_p).value)
    event = event_tmp.decode()
    _free(_event)
    return event

def get_value(key):
    """ Extract value from a FNCS message

    Args:
        key (str): the topic

    Returns:
        str: decoded value
    """
    _value = _get_value(key.encode('utf-8'))
    value_tmp = ctypes.string_at(ctypes.cast(_value, ctypes.c_char_p).value)
    value = value_tmp.decode()
    _free(_value)
    return value

def get_values_size(key):
    """ For list publications, find how many values were published

    Args:
        key (str): the topic

    Returns:
        int: the number of values for this topic
    """
    return _get_values_size(key.encode('utf-8'))

def get_values(key):
    """ For list publications, get the list of values

    Args:
        key (str): the topic

    Returns:
        [str]: decoded values
    """
    _key = key.encode('utf-8')
    _values = _get_values(_key)
    size = get_values_size(_key)
    values_tmp = [ctypes.cast(_values[i], ctypes.c_char_p).value for i in range(size)]
    values = [x.decode() for x in values_tmp]
    for i in range(size):
        _free(_values[i])
    _free(_values)
    return values

def get_value_at(key, i):
    """ For list publications, get the value by index

    Args:
        key (str): the topic
        i (int): the list index number

    Returns:
        str: decoded value
    """
    _value = _get_value_at(key.encode('utf-8'), i)
    value_tmp = ctypes.string_at(ctypes.cast(_value, ctypes.c_char_p).value)
    value = value_tmp.decode()
    _free(_value)
    return value

def get_keys():
    """ Find the list of topics

    Returns:
        [str]: decoded topic names
    """
    _keys = _get_keys()
    size = get_keys_size()
    keys_tmp = [ctypes.cast(_keys[i], ctypes.c_char_p).value for i in range(size)]
    keys = [x.decode() for x in keys_tmp]
    for i in range(size):
        _free(_keys[i])
    _free(_keys)
    return keys

def get_key_at(i):
    """ Get the topic by index number

    Args:
        i (int): the index number

    Returns:
        str: decoded topic name
    """
    _key = _get_key_at(i)
    key_tmp = ctypes.string_at(ctypes.cast(_key, ctypes.c_char_p).value)
    key = key_tmp.decode()
    _free(_key)
    return key

def get_name():
    """ Find the FNCS simulator name

    Returns:
        str: the name of this simulator as provided in the ZPL or YAML file
    """
    _name = _get_name()
    name_tmp = ctypes.string_at(ctypes.cast(_name, ctypes.c_char_p).value)
    name = name_tmp.decode()
    _free(_name)
    return name

def get_version():
    """ Find the FNCS version

    Returns:
        int, int, int: major, minor and patch numbers
    """
    major = ctypes.c_int()
    minor = ctypes.c_int()
    patch = ctypes.c_int()
    _get_version(ctypes.byref(major),
                 ctypes.byref(minor),
                 ctypes.byref(patch))
    return (major.value, minor.value, patch.value)

def die():
    """ Call FNCS die because of simulator error

    """
    _die()

def finalize():
    """ Call FNCS finalize to end connection with broker

    """
    _finalize()

def update_time_delta(delta):
    """ Update simulator time delta value

    Args:
        delta (int): time delta.
    """
    _update_time_delta(delta)

def get_events_size():
    """ Get the size of the event queue

    """
    return _get_events_size()

def get_keys_size():
    """ Get the size of the keys

    """
    return _get_keys_size()

def get_simulator_count():
    """ Find the FNCS simulator count

    """
    return _get_simulator_count()

def get_id():
    """ Find the FNCS ID

    """
    return _get_id()
