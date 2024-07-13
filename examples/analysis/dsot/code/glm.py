"""
This module is used to ingest a GridLAB-D model (extension .glm) into a
Python dictionary where the model can easily be modified. Then, the
modified model can be easily written to file.

A user of this module will likely only ever want to use the GLMManager
class (author: Brandon Thayer).

Original functions (modified) from Jacob and Ebony:
    parse(inputStr, filePath=True):
        Main function to parse in glm
    _tokenize_glm(inputStr, filePath=True):
        Helper function to parse glm
    _parse_token_list(tokenList):
        Helper function to parse glm
    sorted_write(inTree):
        Main function to write out glm
    _dict_to_string(inDict):
        Helper function to write out glm
    _gather_key_values(inDict, keyToAvoid):
        Helper function to write out glm


Adopted and modified August 30, 2018 by Brandon Thayer
    (brandon.thayer@pnnl.gov)
Modified March 28, 2017 by Jacob Hansen (jacob.hansen@pnnl.gov)
Created October 27, 2014 by Ebony Mayhorn (ebony.mayhorn@pnnl.gov)

Copyright (c) 2019 Battelle Memorial Institute.  The Government retains
a paid-up nonexclusive, irrevocable worldwide license to reproduce,
prepare derivative works, perform publicly and display publicly by or
for the Government, including the right to distribute to other
Government contractors.
"""

import re
import warnings
from functools import reduce
from datetime import datetime
import logging
import random
from string import ascii_letters, digits

# Create constants for drawing random digits and letters (used if we
# need to name a nested object).
LETTER_LIST = list(ascii_letters)
DIGIT_LIST = list(digits)
CHAR_LIST = LETTER_LIST + DIGIT_LIST

# 2019-09-01 - not renaming any more. It's not particularly
# maintainable, leads to hard to track down bugs, and doesn't do any
# good for PyVVO.
# List of object properties which will have '-' replaced with '_'
# RENAME = ['name', 'parent', 'from', 'to', 'configuration']

# List of classes in GridLAB-D's module, generators. NOTE: intentionally
# ordering this so the most likely to appear show up first.
# http://gridlab-d.shoutwiki.com/wiki/Generators_(module)
GEN_CLASSES = ['inverter', 'battery', 'diesel_dg', 'dc_dc_converter',
               'energy_storage', 'microturbine', 'power_electronics',
               'rectifier', 'solar', 'windturb_dg']

# List of valid phases for objects (not including the neutral.
PHASES = ('A', 'B', 'C')

# List of valid capacitor switch statuses.
CAP_STATUSES = ('OPEN', 'CLOSED')

# List of "settable" triplex_load parameters.
# http://gridlab-d.shoutwiki.com/wiki/Power_Flow_User_Guide#Triplex_Load
TRIPLEX_PARAMS = \
    ['base_power_1', 'base_power_2', 'base_power_12',
     'power_pf_1', 'power_pf_2', 'power_pf_12',
     'current_pf_1', 'current_pf_2', 'current_pf_12',
     'impedance_pf_1', 'impedance_pf_2', 'impedance_pf_12',
     'power_fraction_1', 'power_fraction_2', 'power_fraction_12',
     'current_fraction_1', 'current_fraction_2', 'current_fraction_12',
     'impedance_fraction_1', 'impedance_fraction_2', 'impedance_fraction_12'
     ]


def parse(input_str, file_path=True):
    """
    Parse a GLM into an omf.feeder tree. This is so we can walk the tree,
    change things in bulk, etc.

    Input can be a file path or GLM string.
    """

    tokens = _tokenize_glm(input_str, file_path)
    return _parse_token_list(tokens)


# noinspection RegExpRedundantEscape
def _tokenize_glm(input_str, file_path=True):
    """ Turn a GLM file/string into a linked list of tokens.

    E.g. turn a string like this:
    clock {clockey valley;};
    object house {name myhouse; object ZIPload {inductance bigind; power
        newpower;}; size 234sqft;};

    Into a Python list like this:
    ['clock','{','clockey','valley','}','object','house','{','name','myhouse',
        ';','object','ZIPload','{','inductance','bigind',';','power',
        'newpower','}','size','234sqft','}']
    """

    if file_path:
        with open(input_str, 'r') as glmFile:
            data = glmFile.read()

    else:
        data = input_str
    # Get rid of http for stylesheets because we don't need it and it conflicts
    # with comment syntax.
    data = re.sub(r'http:\/\/', '', data)
    # Strip comments.
    data = re.sub(r'\/\/.*(\s*)', '', data)
    # Also strip non-single whitespace because it's only for humans:
    data = data.replace('\r', '').replace('\t', ' ')
    # Tokenize around semicolons, braces, whitespace, and ${<stuff>}.
    tokenized = re.split(r'(;|\}|\{|\s|\$\{.*\})', data)
    # Get rid of whitespace strings.
    basic_list = [x for x in tokenized if x != '' and x != ' ']
    return basic_list


def _gen_rand_name(n=10):
    """Helper to generate a random name of n characters."""
    # Ensure the name starts with a letter.
    return ''.join([random.choice(LETTER_LIST)]
                   + random.choices(CHAR_LIST, k=n-1))


def _parse_token_list(token_list):
    """
    Given a list of tokens from a GLM, parse those into a tree data structure.

    """

    def current_leaf_add(key_f, value, tree_f, guid_stack_f):
        # Helper function to add to the current leaf we're visiting.
        current = tree_f
        for x in guid_stack_f:
            current = current[x]

        # Try/except/else added by Brandon to avoid duplicate keys in
        # an object.
        try:
            # Simply try to access the field.
            current[key_f]
        except KeyError:
            # Field doesn't exist, simply add the value.
            current[key_f] = value
        else:
            # Trying to add to an existing key is no bueno.
            # TODO: Raise a different exception here.
            raise UserWarning('Multiple properties with the same name '
                              'encountered while parsing! Property: {},'
                              'Value: {}, Already parsed: {}'
                              .format(key_f, value, tree_f))

    def list_to_string(list_in):
        # Helper function to turn a list of strings into one string with some
        # decent formatting.
        if len(list_in) == 0:
            return ''
        else:
            # return reduce(lambda x, y: str(x) + ' ' + str(y), list_in[1:-1])
            if "#include" in list_in:
                return reduce(lambda x, y: str(x) + '' + str(y), list_in[1:-1])
            else:
                return reduce(lambda x, y: str(x) + ' ' + str(y), list_in[1:-1])

    # Tree variables.
    tree = {}
    guid = 0
    guid_stack = []

    # reverse the token list as pop() is way more efficient than pop(0)
    token_list = list(reversed(token_list))

    def get_full_token():
        nonlocal token_list
        # Pop, then keep going until we have a full token (i.e. 'object house',
        # not just 'object')
        ft = []
        while ft == [] or ft[-1] not in ['{', ';', '}', '\n', 'shape']:
            ft.append(token_list.pop())

        return ft

    # Initialize our "full_token" variable to make the nested function
    # below work without arguments.
    full_token = []

    def close_out_item():
        """Nested helper function to be used if the last element in the
        full_token == '}'
        """
        nonlocal tree
        nonlocal guid_stack
        nonlocal guid

        if len(full_token) > 1:
            current_leaf_add(full_token[0], list_to_string(full_token),
                             tree, guid_stack)
        guid_stack.pop()

    def add_item_definition():
        """Nested helper function to be used if the last element in the
        full_token == '{'
        """
        nonlocal guid
        nonlocal guid_stack
        nonlocal tree

        current_leaf_add(guid, {}, tree, guid_stack)
        guid_stack.append(guid)
        guid += 1

        # Wrapping this current_leaf_add is defensive coding so we don't
        # crash on malformed glm files.
        if len(full_token) > 1:
            # Do we have a clock/object or else an embedded configuration
            # object?
            if len(full_token) < 4:
                # Add the item definition.
                current_leaf_add(full_token[0], full_token[-2], tree,
                                 guid_stack)
            elif len(full_token) == 4:
                # We likely have an embedded/nested object.
                current_leaf_add('omfEmbeddedConfigObject',
                                 full_token[0] + ' ' +
                                 list_to_string(full_token), tree,
                                 guid_stack)
            else:
                # Something is wrong.
                raise UserWarning('Malformed GridLAB-D model. Token: {}'
                                  .format(' '.join(full_token)))

        # All done.

    # Loop over the tokens.
    while token_list:
        # Get full token.
        full_token = get_full_token()

        # Work with what we've collected.
        if full_token[0] == "#ifdef":
            pass

        if (full_token == ['\n']) or (full_token == [';']):
            # Nothing to do.
            continue
        elif full_token == ['}']:
            close_out_item()
        elif full_token[0] == '#set':
            if full_token[-1] == ';':
                tree[guid] = {'omftype': full_token[0],
                              'argument': list_to_string(full_token)}
            else:
                tree[guid] = {'#set': list_to_string(full_token)}
            guid += 1
        elif full_token[0] == '#include':
            if full_token[-1] == ';':
                tree[guid] = {'omftype': full_token[0],
                              'argument': list_to_string(full_token)}
            else:
                tree[guid] = {'#include': list_to_string(full_token)}
            guid += 1
        elif full_token[0] == 'shape':
            while full_token[-1] not in ['\n']:
                full_token.append(token_list.pop())
            full_token[-2] = ''
            current_leaf_add(full_token[0], list_to_string(full_token[0:-1]),
                             tree, guid_stack)
            guid += 1
        elif (len(guid_stack) == 1) and ('class' in tree[guid_stack[0]]) \
                and (len(full_token) > 1):
            # Intentionally narrow case for handling GridLAB-D classes.
            # Note this ONLY works for simple classes with property
            # definitions (e.g. "double consensus_iterations;").
            # Note this WILL NOT WORK for complex class definitions
            # which have anything other than simple properties. This is
            # because the complex classes have nested functions for
            # syncing, post-sync, etc. Not handling that here.
            # ALSO NOTE: This WILL NOT WORK for classes with
            # enumerations and sets, as those have curly braces...
            # http://gridlab-d.shoutwiki.com/wiki/Runtime_Class_User_Guide

            # Since we're just handling the simplest of class properties
            # here, do some assertions for safety.
            assert len(full_token) == 3, ('Malformed class token! Only simple'
                                          'classes are supported!')
            assert full_token[-1] == ';', ('Malformed class token! Only simple'
                                           'classes are supported!')

            # Add the type to the 'variable_types' field and add the
            # rest to the 'variable_names' field. Note this matches up
            # with how "sorted_write" will handle classes.
            v_type = full_token[0]
            v_name = full_token[1]
            tree_entry = tree[guid_stack[0]]
            try:
                tree_entry['variable_types'].append(v_type)
            except KeyError:
                tree_entry['variable_types'] = [v_type]

            try:
                tree_entry['variable_names'].append(v_name)
            except KeyError:
                tree_entry['variable_names'] = [v_name]

        elif full_token[-1] == '{':
            add_item_definition()
        elif full_token[-1] == '\n' or full_token[-1] == ';':

            if guid_stack == [] and full_token != ['\n'] and \
                    full_token != [';']:

                # Special case when we have zero-attribute items (like
                # #include, #set, module).
                if full_token[0] == "#endif":
                    tree[guid] = {'omftype': full_token[0],
                                  'argument': ""}
                else:
                    tree[guid] = {'omftype': full_token[0],
                                  'argument': list_to_string(full_token)}
                guid += 1
            elif len(full_token) > 1:
                # We process if it isn't the empty token (';')
                current_leaf_add(full_token[0], list_to_string(full_token),
                                 tree, guid_stack)
        elif full_token[0] == 'schedule':
            # Special code for those ugly schedule objects:
            if full_token[0] == 'schedule':
                while full_token[-1] not in ['}']:
                    full_token.append(token_list.pop())
                tree[guid] = {'object': 'schedule', 'name': full_token[1],
                              'cron': ' '.join(full_token[3:-2])}
                guid += 1

    # this section will catch old glm format and translate it. Not in the most
    # robust way but should work for now.
    # NOTE: In an ideal world, double-looping would be avoided by doing
    # the work below while looping through the token list. Oh well -
    # the point of borrowing someone else's work is to avoid doing it
    # yourself.
    _fix_old_syntax(tree)

    return tree


def _fix_old_syntax(tree):
    """Function for 'catching old glm format and translating it.'
    This is intended to work recursively to catch nested objects.
    """
    for key in list(tree.keys()):
        if 'object' in list(tree[key].keys()):
            # if no name is present and the object name is the old syntax we
            # need to be creative and pull the object name and use it
            if 'name' not in list(tree[key].keys()) and \
                    tree[key]['object'].find(':') >= 0:
                tree[key]['name'] = tree[key]['object'].replace(':', '_')

            # strip the old syntax from the object name
            tree[key]['object'] = tree[key]['object'].split(':')[0]

            # for the remaining syntax we will replace ':' with '_'
            for line in tree[key]:
                try:
                    tree[key][line] = tree[key][line].replace(':', '_')
                except AttributeError:
                    # If we've hit a dict, recurse.
                    if isinstance(tree[key][line], dict):
                        # Since dicts are mutable, and tree[key][line]
                        # is a dict, this should work just fine for
                        # updating in place.
                        _fix_old_syntax(tree={line: tree[key][line]})
                    else:
                        raise TypeError("Something weird is going on.")

            # if we are working with fuses let's set the mean replace time to 1
            # hour if not specified. Then we aviod a warning!
            if tree[key]['object'] == 'fuse' \
                    and 'mean_replacement_time' not in list(tree[key].keys()):
                tree[key]['mean_replacement_time'] = 3600.0

            # # FNCS is not able to handle names that include "-" so we will
            # # replace that with "_".
            # for prop in RENAME:
            #     try:
            #         # Attempt to fix the property.
            #         tree[key][prop] = tree[key][prop].replace('-', '_')
            #     except KeyError:
            #         # Property isn't present - move along.
            #         pass

    # No return, as we're modifying in place.
    return None


def sorted_write(in_tree):
    """
    Write out a GLM from a tree, and order all tree objects by their key.

    Sometimes GridLAB-D breaks if you rearrange a GLM.
    """

    sorted_keys = sorted(list(in_tree.keys()), key=int)
    output = ''
    try:
        for key in sorted_keys:
            output += _dict_to_string(in_tree[key]) + '\n'
    except ValueError:
        raise Exception
    return output


def _dict_to_string(in_dict):
    """
    Helper function: given a single dict representing a GLM object, concatenate
    it into a string.
    """

    # Handle the different types of dictionaries that are leafs of the tree
    # root:
    if 'omftype' in in_dict:
        return in_dict['omftype'] + ' ' + in_dict['argument'] + ';'
    elif 'module' in in_dict:
        return ('module ' + in_dict['module'] + ' {\n'
                + _gather_key_values(in_dict, 'module') + '}\n')
    elif 'clock' in in_dict:
        # return 'clock {\n' + gatherKeyValues(in_dict, 'clock') + '};\n'
        # This object has known property order issues writing it out explicitly
        clock_string = 'clock {\n'
        if 'timezone' in in_dict:
            clock_string = clock_string + '\ttimezone ' + in_dict[
                'timezone'] + ';\n'
        if 'starttime' in in_dict:
            clock_string = clock_string + '\tstarttime ' + in_dict[
                'starttime'] + ';\n'
        if 'stoptime' in in_dict:
            clock_string = clock_string + '\tstoptime ' + in_dict[
                'stoptime'] + ';\n'
        clock_string = clock_string + '}\n'
        return clock_string
    elif 'object' in in_dict and in_dict['object'] == 'schedule':
        return 'schedule ' + in_dict['name'] + ' {\n' + in_dict[
            'cron'] + '\n};\n'
    elif 'object' in in_dict:
        return ('object ' + in_dict['object'] + ' {\n'
                + _gather_key_values(in_dict, 'object') + '};\n')
    elif 'omfEmbeddedConfigObject' in in_dict:
        return in_dict['omfEmbeddedConfigObject'] + ' {\n' + \
               _gather_key_values(in_dict, 'omfEmbeddedConfigObject') + '};\n'
    elif '#include' in in_dict:
        return '#include ' + in_dict['#include']
    elif '#define' in in_dict:
        return '#define ' + in_dict['#define'] + '\n'
    elif '#set' in in_dict:
        return '#set ' + in_dict['#set']
    elif 'class' in in_dict:
        prop = 'class ' + in_dict['class'] + ' {\n'
        # this section will ensure we can get around the fact that you can't
        # have two key's with the same name!
        if 'variable_types' in list(
                in_dict.keys()) and 'variable_names' in list(
                in_dict.keys()) and len(in_dict['variable_types']) == len(
                in_dict['variable_names']):

            for x in range(len(in_dict['variable_types'])):
                prop += '\t' + in_dict['variable_types'][x] + ' ' + \
                        in_dict['variable_names'][x] + ';\n'

            prop += '}\n'
        else:
            prop += _gather_key_values(in_dict, 'class') + '}\n'

        return prop


def _gather_key_values(in_dict, key_to_avoid):
    """
    Helper function: put key/value pairs for objects into the format GLD needs.
    """

    other_key_values = ''
    for key in in_dict:
        if type(key) is int:
            # WARNING: RECURSION HERE
            other_key_values += _dict_to_string(in_dict[key])
        elif key != key_to_avoid:
            if key == 'comment':
                other_key_values += (in_dict[key] + '\n')
            elif key == 'name' or key == 'parent':
                if len(in_dict[key]) <= 62:
                    other_key_values += (
                            '\t' + key + ' ' + str(in_dict[key]) + ';\n')
                else:
                    warnings.warn(
                        ("{:s} argument is longer that 64 characters. "
                         + " Truncating {:s}.").format(key, in_dict[key]),
                        RuntimeWarning)
                    other_key_values += ('\t' + key + ' '
                                         + str(in_dict[key])[0:62]
                                         + '; // truncated from {:s}\n'.format(
                                            in_dict[key]))
            else:
                other_key_values += ('\t' + key + ' ' + str(in_dict[key])
                                     + ';\n')
    return other_key_values


class GLMManager:
    """Class to manage a GridLAB-D model (.glm).

    Public methods:
        - write_model: Write model to file.
        - add_item: Given an item dict, add it to the model.
        - find_object: Lookup an object by type and name.
        - get_items_by_type: Lookup all items of a given type. Return a
            dictionary keyed by name.
        - modify_item: Update an item's properties (no renaming, though)
        - remove_properties_from_item: Delete certain properties from
            an item.
        - remove_item: Remove an item from the model
        - module_present: Test if a particular module is in the model.
        - get_objects_by_type: Return all objects of a given type as a
            list.
        - add_or_modify_clock: Add clock if not present, or update
            existing clock.
        - object_type_present: Check if a given object type exists in
            the model.
        - add_run_components: Helper for adding necessary pieces to get
            a model running when we're just given the "base" model from
            the GridAPPS-D platform. This "base" model is missing
            modules, a clock, etc.
        - add_substation_meter: Add a meter which monitors the
            swing bus (a substation object). All objects which were
            connected to the swing are modified to be connected to the
            new meter.
        - update_reg_taps: Update a regulator's tap positions, both in
            the regulator itself, and its corresponding configuration.
        - clear_all_triplex_loads: Clear out all parameters in
            TRIPLEX_PARAMS for all triplex_load objects in the model.
        - update_all_triplex_loads: Well, update all the triplex loads
            in the model. Self explanatory :) Check the docstring.
        - remove_all_solar: Remove all solar panels from the model.
        - set_inverter_v_and_i: Add V_In and I_In to inverters according
            to their rated power (essentially giving them a DC source).

    IMPORTANT NOTE ON MUTABILITY:
        As Python programmers should know, dictionaries are mutable, and
        thus pointers are effectively used. When using methods which 
        return a dictionary or collection of dictionaries representing
        model components (e.g. objects of type meter or the model's
        clock), this dictionary points directly to the same dictionary
        the GLMManager uses. Thus, these dictionaries SHOULD NOT BE 
        MODIFIED. While this hazard could be circumnavigated by 
        returning copies, that's simply not efficient and in my opinion,
        overkill. So, if you need to make modifications, make a copy. If
        you are intentionally modifying an object, use one of the public
        methods to do so. 

    A note on "items" vs. "objects":
        Any encapsulated element in a GridLAB-D model is considered an
        "item." E.g. a one-line module declaration or a mult-line
        object definition. "objects" are specifically GridLAB-D objects.
        E.g., their definition is like "object <object type> { ..."

    A note on "item_dict" inputs:
        item_dicts are Python dictionaries which represent GridLAB-D
        "items". This simplest case is a GridLAB-D object. The
        item_dict must have an "object" field, and the "object" field's
        value would be the object type. E.g. "recorder". All the
        remaining key-value pairs define the object's properties. Some
        examples follow:

        {'object': 'capacitor', 'name': '"my_cap"'}
        {'module': 'powerflow'}
        {'clock': 'clock', 'starttime': '\'2012-01-01 00:00:00\'',
         'stoptime': '\'2017-06-10 08:35:12\'', 'timezone': 'Pacific'}
        {'#define': 'VSOURCE=66395.28'}

    A note on nested items:
        Nested items (e.g. a recorder nested in an object or a
        transformer_configuration object nested within a transformer
        object) will be "un-nested." They'll be given name/parent
        attributes as necessary.

    Some notes on "class"es:
        The GLMManager (and this module, for that matter) currently
        ONLY supports simple classes with property definitions. If they
        have functions, that won't work.

        ALSO: Classes cannot have enumerations or sets, as this will
        break things.

        The reason for these short-comings is how the manager deals with
        nesting. Seeing curly braces within an object is how nesting is
        detected, and currently nested objects are "un-nested."

        Finally, not all the methods for accessing and modifying classes
        have been created yet.


    """
    # Date format for GridLAB-D models. See:
    #   http://gridlab-d.shoutwiki.com/wiki/Clock
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    # Define items we won't include in the model_map.
    NO_MAP = ('set', 'include', 'define')
    # Define non-object items.
    NON_OBJECTS = ('clock', 'module', 'include', 'set', 'define', 'omftype',
                   'class')

    def __init__(self, model, model_is_path=True):
        """Initialize by parsing given model.

        :param model: Path to or string of GridLAB-D model.
        :type model: str
        :param model_is_path: Specifies if model is path (True) or
               string of model (False)
        :type model_is_path: Boolean
        """
        # Setup logging.
        self.log = logging.getLogger(self.__class__.__name__)

        # Parse the model.
        self.model_dict = parse(model, model_is_path)

        # The model dict has increasing integer keys so the model can
        # later be written in order (since GridLAB-D cares sometimes).
        # Get the first and last keys.
        keys = list(self.model_dict.keys())
        # Set keys for adding items to beginning or end of model.
        self.append_key = max(keys) + 1
        self.prepend_key = min(keys) - 1

        # Initialize model_map.
        self.model_map = {'clock': [], 'module': {}, 'object': {}, 'class': {},
                          'object_unnamed': []}

        # Map objects in the model.
        parallel_dict = self._map_model_dict(self.model_dict, parallel_dict={})
        # Merge the nested items into the top-level dict.
        for k, v in parallel_dict.items():
            # NOTE: this check isn't efficient, but it brings peace of
            # mind.
            if k in self.model_dict:
                m = 'The key {} already exists in self.model_dict!'.format(k)
                raise ItemExistsError(m)
            else:
                self.model_dict[k] = v

        self.log.info('GridLAB-D model parsed and mapped.')

    def _update_append_key(self):
        """Add one to the append_key."""
        self.append_key += 1

    def _update_prepend_key(self):
        """Subtract one from the prepend_key."""
        self.prepend_key -= 1

    def _map_model_dict(self, model_dict, parallel_dict):
        """Generate mapping of model_dict by object type, and "un-nest"
            nested objects.

        Dictionary hierarchy will be as follows:
        <object type>
            <object name>
                <object properties>

        NOTE: each item will be stored as [model_key, item_dict] in the
            map.

        :param model_dict: dictionary with numeric mappings to
            dictionaries resembling GridLAB-D objects.
        :param parallel_dict: Same as model_dict, but used to build up
            dictionary of items to be "un-nested" after recursion is
            complete.

        :returns: parallel_dict: The contents of parallel_dict should be
            merged into the model_dict after the function nesting is
            complete.
        """

        # Loop over the model_dict.
        for model_key, item_dict in model_dict.items():

            # Get the item type.
            item_type = self._get_item_type(item_dict)

            # If it's an object, use the object function.
            if item_type == 'object':
                self._add_object_to_map(model_key, item_dict)

            elif item_type == 'clock':
                self._add_clock_to_map(model_key, item_dict)

            elif item_type == 'module':
                # Map by module name.
                self._add_module_to_map(model_key, item_dict)

            elif item_type == 'omftype':
                # Map (only if it's a module)
                if item_dict['omftype'] == 'module':
                    self._add_module_to_map(model_key, item_dict)

            elif item_type == 'class':
                # Map the class.
                self._add_class_to_map(model_key, item_dict)

            elif item_type in self.NO_MAP:
                # No mapping for now.
                pass

            else:
                # Unexpected type, raise warning.
                raise ValueError('Unimplemented item: {}'.format(item_dict))

            # If the item's dictionary contains a numeric key mapped to
            # a dictionary, we have a nested item which should be
            # mapped. This will be done recursively.
            to_pop = []
            to_add = []
            for k, v in item_dict.items():
                if isinstance(k, int):
                    if isinstance(v, dict):
                        # If we have 'omfEmbeddedConfigObject' we have
                        # a nested configuration which needs special
                        # handling.
                        try:
                            s = v['omfEmbeddedConfigObject'].split()
                        except KeyError:
                            # No extra work to do here. Mark that we'll
                            # use the 'parent' key.
                            parent = True
                        else:
                            # We do have an omfEmbeddedConfigObject.
                            assert len(s) == 3, ("Don't know how to handle "
                                                 "embedded config objects "
                                                 "like this: {}"
                                                 .format(v))

                            # Not using 'parent' in this case.
                            parent = False

                            # Attempt to get the name of the object up
                            # in the hierarchy.
                            try:
                                name = v['name']
                            except KeyError:
                                # This object doesn't have a name, but
                                # needs one since we're going to un-nest
                                # it.
                                try:
                                    prefix = item_dict['name']
                                except KeyError:
                                    # No name to use, make it random.
                                    prefix = _gen_rand_name(n=10)

                                # Create a name based on the type of object
                                # we're nesting. Example:
                                # s = ['conductor_1', 'object',
                                #      'triplex_line_conductor']
                                # So we're grabbing "conductor_1".
                                name = prefix + '_' + s[0]

                                # Add the name.
                                v['name'] = name

                            # Mark this as "to add" later (don't modify
                            # objects we're looping over)
                            to_add.append((s[0], name))

                            # Remove the 'omfEmbeddedConfigObject'
                            # notation.
                            del v['omfEmbeddedConfigObject']
                            # Add the object definition.
                            v[s[1]] = s[2]

                        # Recurse.
                        parallel_dict = \
                            self._map_model_dict(model_dict={k: v},
                                                 parallel_dict=parallel_dict)

                        # Mark that we need to pop this (can't pop
                        # while looping over the dict)
                        to_pop.append((k, parent))
                    else:
                        m = ('The model_dict has a numeric key that does not '
                             + 'map to a dictionary!')
                        raise TypeError(m)

            # Remove nested objects, move to top-level.
            for t in to_pop:
                k = t[0]
                parent = t[1]

                # Pop the object, and add the 'parent' property if
                # applicable.
                nested_item = item_dict.pop(k)
                if parent:
                    try:
                        nested_item['parent'] = item_dict['name']
                    except KeyError:
                        m = ('Nested item was nested within another item '
                             + 'that does not have a name!')
                        raise KeyError(m)

                # Put item in the parallel dictionary.
                parallel_dict[k] = nested_item

            # Add properties that were necessary due to our "un-nesting"
            for t in to_add:
                # t is a tuple like (key, value)
                item_dict[t[0]] = t[1]

        # Return the parallel dictionary.
        return parallel_dict

    def _add_clock_to_map(self, model_key, clock_dict):
        """Add clock to the model map.

        :param model_key: key to model_dict
        :param clock_dict: dictionary representing clock.
        :type clock_dict: dict
        """
        # Only allow one clock.
        if len(self.model_map['clock']) > 0:
            raise ItemExistsError('The model already has a clock!')

        # Map it.
        self.model_map['clock'] = [model_key, clock_dict]

    def _add_module_to_map(self, model_key, module_dict):
        """Add module to the model map by module name.

        :param model_key: key to model_dict
        :param module_dict: dictionary defining module.
        :type module_dict: dict
        """

        # Get the module name from the dict.
        if 'module' in module_dict:
            module_name = module_dict['module']
        elif 'omftype' in module_dict:
            module_name = module_dict['argument']
        else:
            # Bad dict.
            raise ValueError('Malformed module_dict: {}'.format(module_dict))

        # Ensure we aren't over-writing existing module.
        if module_name in self.model_map['module']:
            s = 'Module {} is already present!'.format(module_name)
            raise ItemExistsError(s)

        # Map it by name.
        self.model_map['module'][module_name] = [model_key, module_dict]

    def _add_object_to_map(self, model_key, object_dict):
        """Add object to the model_map.

        :param: object_dict: Dictionary of all object attributes.
        :type: object_dict: dict
        """
        # Grab reference to the object sub-dict.
        object_map = self.model_map['object']

        # Get type of object.
        obj_type = object_dict['object']

        # Define key object pair
        key_obj = [model_key, object_dict]

        # If this type isn't in the map, add it. NOTE: this can lead to
        # empty entries if the object isn't named.
        if obj_type not in object_map:
            object_map[obj_type] = {}

        try:
            # Never try to map an already existing named object.
            if object_dict['name'] in object_map[obj_type]:
                s = '{} already exists in the {} map!'
                raise ItemExistsError(s.format(object_dict['name'], obj_type))

        except KeyError:
            # Unnamed object. Add it to the unnamed list.
            self.model_map['object_unnamed'].append(key_obj)

        else:
            # Named object, map it.
            object_map[obj_type][object_dict['name']] = key_obj

        # No need to return; we're directly updating self.model_map

    def _add_class_to_map(self, model_key, class_dict):
        """Add a class to the model_map.

        :param model_key: key to model_dict.
        :param class_dict: dictionary of class attributes.
        """
        # Extract the class name.
        class_name = class_dict['class']

        try:
            # Attempt to access this class by name in the map.
            self.model_map['class'][class_name]
        except KeyError:
            # Class object does not exist. Map it.
            self.model_map['class'][class_name] = [model_key, class_dict]
        else:
            # This class name already exists, which will lead to
            # duplicates and failure.
            raise ItemExistsError('Class {} already exists in the map.'
                                  .format(class_name))

    def write_model(self, out_path):
        """Helper to write out the model_dict.

        :param out_path: Full path to write model out to. If None, a
            string will be returned.
        """

        # Get dictionary as a string.
        model_string = sorted_write(self.model_dict)

        if out_path is not None:
            # Write it.
            with open(out_path, 'w') as f:
                f.write(model_string)

            # We're done. explicitly return None.
            return None
        else:
            # Return the string.
            return model_string

    def add_item(self, item_dict):
        """Add and map a new item.

        :param item_dict:
        :type item_dict: dict
        """
        # Get type of item.
        item_type = self._get_item_type(item_dict)

        # Ensure all fields are strings, cast values to strings.
        for k in item_dict:
            # Check key.
            if not isinstance(k, str):
                raise TypeError('All keys must be strings!')

            # Make sure value is string.
            item_dict[k] = str(item_dict[k])

        if item_type == 'object':
            # Use _add_object method to map and add the object.
            self._add_object(item_dict)
        elif item_type in self.NON_OBJECTS:
            # Use _add_non_object method to map and add the item.
            self._add_non_object(item_type, item_dict)
        else:
            # From the docs, we should raise a TypeError:
            #
            # "This exception may be raised by user code to indicate
            # that an attempted operation on an object is not supported,
            # and is not meant to be."
            #
            # https://docs.python.org/3.7/library/exceptions.html#TypeError
            s = 'No add method for item type {}'.format(item_type)
            raise TypeError(s)

    def _add_object(self, object_dict):
        """Add and map object.

        :param object_dict:
        :type object_dict: dict
        """
        # Attempt to map the object first. This will raise an
        # ItemExistsError if a named object of the same type already
        # exists.
        self._add_object_to_map(self.append_key, object_dict)

        # Add the object to the end of the model.
        # TODO: which objects need added to the beginning?
        self.model_dict[self.append_key] = object_dict

        # Update append key.
        self._update_append_key()

    def find_object(self, obj_type, obj_name):
        """Find object by name in the model_map, if it exists.

        :param: obj_type: type of the object to look up.
        :type: obj_type: str
        :param: obj_name: name of the object to look up.
        :type: obj_name: str
        """
        try:
            # Simply look it up by type and name.
            obj = self.model_map['object'][obj_type][obj_name][1]
        except KeyError:
            # No dice. This object doesn't exist in the model.
            obj = None

        return obj

    def get_items_by_type(self, item_type, object_type=None):
        """Get data for all objects of the given type. At times, you
        may want to use this instead of get_objects_by_type since the
        return value is formatted differently.

        :param item_type: string, item type. At present (2019-07-03), 
            valid item types appear to be 'object', 'clock', 'module',
            or 'object_unnamed' by inspecting __init__ and
            _map_model_dict. 
        :param object_type: string, object type. Only used if item_type
               is 'object.' E.g. 'triplex_load'
        :return: Returns differ slightly by item_type. If the item_type 
            is not present in the model, None will be returned. The 
            other types are listed below:
                clock: Simply returns the clock dictionary.
                module: Returns a dictionary of dictionaries keyed by
                    module name.
                object: Dictionary of dictionaries keyed by object name.
                    NOTE: This is in contrast to get_objects_by_type 
                    which returns a list of dictionaries.
                object_unnamed: 
        """
        # Check to see if the item_type is in the map.
        try:
            dict_or_list = self.model_map[item_type]
        except KeyError:
            return None

        # If we're working with objects,
        if item_type == 'object':
            # See if we have this object_type.
            if object_type is not None:
                try:
                    object_dict = self.model_map[item_type][object_type]
                except KeyError:
                    return None
                
                # Loop over the map and create the return. In each list,
                # the first element is a key into the model_dict, and 
                # the user of this method doesn't care about that. Thus,
                # we grab v[1], which is the actual dictionary.
                out = {k: v[1] for k, v in object_dict.items()}
                
            else:
                # Require and object_type for item_type of 'object'
                raise ValueError("If item_type is 'object', then " +
                                 "object_type must not be None.")
        elif item_type == 'clock':
            # Simply return the clock dictionary. The first item in this 
            # list is the key into the model map.
            out = dict_or_list[1]
        elif item_type == 'module':
            # Return a dict of dicts keyed by module name.
            out = {k: v[1] for k, v in dict_or_list.items()}
        elif item_type == 'object_unnamed':
            # Return a list which doesn't include the keys into the 
            # model_dict.
            out = [i[1] for i in dict_or_list]
        else:
            # Hopefully we never get here, as the try/except at the
            # very beginning of this method will catch most cases.
            raise ValueError(
                'The given item_type, {}, is not supported.'.format(item_type))

        # We can get a 0 length if the given item type existed at one
        # point, but has then been removed. In this case, it exists in
        # the map, but is empty.
        if len(out) == 0:
            return None
        else:
            return out

    def _add_non_object(self, item_type, item_dict):
        """Add a non-object to the model.

        non-objects are listed in self.NON_OBJECTS.

        :param item_type: type of object to be added.
        :type item_type: str
        :param item_dict: dictionary with object properties
        :type item_dict: dict
        """

        # Map item.
        if item_type == 'clock':
            # Map clock.
            self._add_clock_to_map(self.prepend_key, item_dict)

        elif item_type == 'module':
            # Map module.
            self._add_module_to_map(self.prepend_key, item_dict)

        elif item_type == 'class':
            # Map class.
            self._add_class_to_map(self.prepend_key, item_dict)

        elif item_type in self.NO_MAP:
            # No mapping.
            pass

        else:
            s = 'No add method for {} item type.'.format(item_type)
            raise TypeError(s)

        # Add to beginning of model.
        self.model_dict[self.prepend_key] = item_dict

        # Update prepend key.
        self._update_prepend_key()

    def modify_item(self, item_dict):
        """Modify an item in the model. NOTE: The input item_dict will
        be modified.

        NOTE: this method CANNOT be used to change an object's name.

        :param item_dict: Dictionary with attributes used for both
            finding and modifying the item. E.g., for an object, both
            the 'object' and 'name' fields are required to locate the
            object. All other key/value pairs in the dictionary will
            then be used to modify the item.

        :raises ValueError: if item_dict contains the 'object' key but
            not the 'name' key.
        :raises KeyError: if an object/item cannot be found.
        :raises TypeError: if the type of the item cannot be identified
            or the type of the item is not supported for modification.
        :returns: None, the item in the model is modified directly.
        """
        # Get type.
        item_type = self._get_item_type(item_dict)

        if item_type == 'object':
            if 'name' not in item_dict:
                raise ValueError('To update an object, its name is needed.')
            # Look up object. Raises KeyError if not found.
            obj = self._lookup_object(object_type=item_dict.pop('object'),
                                      object_name=item_dict.pop('name'))

            # Successfully grabbed object. Update it.
            self._modify_item(obj, item_dict)

        elif item_type == 'clock':
            # No need to modify clock definition.
            item_dict.pop('clock')

            # Get clock.
            clock = self._lookup_clock()

            # Update the clock.
            self._modify_item(clock, item_dict)

        elif item_type == 'module':
            # Get module
            module = self._lookup_module(module_name=item_dict.pop('module'))

            # Modify it. Simple if it isn't an 'omftype' style module.
            if 'omftype' in module:
                # We need to change up this dictionary.
                module['module'] = module['argument']
                module.pop('omftype')
                module.pop('argument')

            # Modify it.
            self._modify_item(module, item_dict)

        else:
            s = 'Cannot modify item of type {}'.format(item_type)
            raise TypeError(s)

    @staticmethod
    def _modify_item(item, update_dict):
        """Simple helper to update an existing item.

        NOTE: We're casting everything to strings, so if the 'str()'
            method fails, this method fails :)

        Note that only properties from update_dict will be modified (or
            added)
        """
        for k in update_dict:
            item[k] = str(update_dict[k])

        return item

    def remove_properties_from_item(self, item_dict, property_list):
        """Remove properties from an item."""

        # Get type.
        item_type = self._get_item_type(item_dict)

        if item_type == 'object':
            # Check for name.
            if 'name' not in item_dict:
                raise ValueError('To update an object, its name is needed.')

            # Get object. Raises KeyError if not found.
            obj = self._lookup_object(object_type=item_dict['object'],
                                      object_name=item_dict['name'])

            # Remove properties.
            self._remove_from_item(obj, property_list)

        elif item_type == 'clock':
            # Get clock.
            clock = self._lookup_clock()

            # Remove properties.
            self._remove_from_item(clock, property_list)

        elif item_type == 'module':
            # Get module.
            module = self._lookup_module(module_name=item_dict['module'])

            self._remove_from_item(module, property_list)

        else:
            s = 'Cannot remove properties from items of type {}'.format(
                item_type)
            raise TypeError(s)

    def remove_item(self, item_dict):
        """Remove item from both the model_dict and model_map.

        :param item_dict: dictionary defining object to remove.
        """
        # Get type
        item_type = self._get_item_type(item_dict)

        if item_type == 'object':
            # Check for name (not currently supporting removal of
            # unnamed objects)
            try:
                obj_name = item_dict['name']
            except KeyError:
                s = 'Cannot remove unnamed objects!'
                raise KeyError(s)

            # Remove from model.
            obj_type = item_dict['object']
            self.model_dict.pop(self.model_map['object'][obj_type][
                                    obj_name][0])

            # Remove from the map.
            self.model_map['object'][obj_type].pop(obj_name)

        elif item_type == 'clock':
            # Ensure there's a clock to remove.
            self._lookup_clock()

            # Remove from model.
            self.model_dict.pop(self.model_map['clock'][0])

            # Remove from the map by resetting clock to empty list.
            self.model_map['clock'] = []

        elif item_type == 'module':
            # Ensure there's a module to remove.
            module_name = item_dict['module']
            self._lookup_module(module_name)

            # Remove from model.
            self.model_dict.pop(self.model_map['module'][module_name][0])

            # Remove from the map.
            self.model_map['module'].pop(module_name)
        else:
            s = 'Cannot remove item of type {}'.format(item_type)
            raise TypeError(s)

    def _lookup_object(self, object_type, object_name):
        # Simply look it up and update it.
        try:
            obj = self.model_map['object'][object_type][object_name][1]
        except KeyError:
            s = ('Object of type {} and name {} does not exist in the '
                 + 'model map!').format(object_type, object_name)
            raise KeyError(s)
        else:
            return obj

    def module_present(self, module_name):
        """Check if named module is present in the model.

        :param module_name: Name of module, must be a string.
        """
        # Check input.
        if not isinstance(module_name, str):
            raise TypeError('module_name must be a string.')

        # Lookup module, return True/False based on whether it's found.
        try:
            self._lookup_module(module_name)
        except KeyError:
            return False
        else:
            return True

    def _lookup_module(self, module_name):
        """Lookup named module."""
        try:
            module = self.model_map['module'][module_name][1]
        except KeyError:
            s = 'Module {} does not exist!'.format(module_name)
            raise KeyError(s)
        else:
            return module

    def _remove_from_item(self, item, remove_list):
        """Simple helper to remove fields from an item."""
        for k in remove_list:
            # Will raise KeyError if asked to remove non-existent item
            try:
                item.pop(k)
            except KeyError:
                # No worries removing non-existent item. Let's log it
                # just in case.
                self.log.debug('Unable to remove {} for the following item: '
                               '{}'.format(k, item))

        return item

    @staticmethod
    def _get_item_type(item_dict):
        """Determine type of given item."""

        if 'object' in item_dict:
            item_type = 'object'
        elif 'module' in item_dict:
            item_type = 'module'
        elif 'clock' in item_dict:
            item_type = 'clock'
        elif '#include' in item_dict:
            item_type = 'include'
        elif '#set' in item_dict:
            item_type = 'set'
        elif '#define' in item_dict:
            item_type = 'define'
        elif 'omftype' in item_dict:
            item_type = 'omftype'
        elif 'class' in item_dict:
            item_type = 'class'
        else:
            raise TypeError('Unknown type! Item: {}'.format(item_dict))

        return item_type

    def _lookup_clock(self):
        try:
            clock = self.model_map['clock'][1]
        except KeyError:
            raise KeyError('Clock does not exist!')
        except IndexError:
            raise IndexError('Clock does not exist!')
        else:
            return clock

    def loop_over_objects_helper(self, object_type, func, *args, **kwargs):
        """Helper for looping over objects of a given type and doing
        something with them.

        :param object_type: Type of object to loop over, e.g. 'switch'
        :param func: Function which each object will be passed to. The
            first positional input should take an object of the given
            type, which will be in dictionary format.
        :param args: Positional arguments to be passed to func.
        :param kwargs: Keyword arguments to be passed to func.
        :return: None
        :raises KeyError: if the given object_type is not present in
            the model.
        """
        # Grab the given object type from the model map. If the objects
        # are not present, raise a KeyError.
        try:
            object_dict = self.model_map['object'][object_type]
        except KeyError:
            m = f'The given object_type {object_type} is not in the model.'
            raise KeyError(m) from None
        else:
            if len(object_dict) == 0:
                m = f'The given object_type {object_type} is not in the model.'
                raise KeyError(m) from None

        # Loop over the objects.
        for obj in object_dict.values():
            # The dictionary representing the object itself is in
            # the position with index 1. Call the function.
            func(obj[1], *args, **kwargs)

    def get_objects_by_type(self, object_type):
        """Return a listing of objects by type, e.g. 'triplex_line.'

        These will simply be looked up in the model_map.

        :param object_type: string of desired object type to look up.
        :returns: object_list: list of dictionaries for the given object
                 type. Will return None if the object type isn't in the
                 model.
        """

        # Get dictionary of objects by type.
        try:
            object_dict = self.model_map['object'][object_type]
        except KeyError:
            # This object type isn't in the model map.
            return None

        # Extract the object dictionaries and put them in list for
        # return.
        out = [value[1] for value in object_dict.values()]

        # The 'out' list can be empty if the object type is mapped,
        # but all the objects have been removed.
        if len(out) == 0:
            return None
        else:
            return out

    def add_or_modify_clock(self, starttime=None,
                            stoptime=None, timezone='UTC0'):
        """Add clock to the model if it exists, otherwise modify clock.

        :param starttime: datetime.datetime object
        :param stoptime: datetime.datetime object
        :param timezone: string, should be valid timezone. See here:
            http://gridlab-d.shoutwiki.com/wiki/Timezone. If you do not
            wish to modify the timezone, set it to None.

        NOTE: Aside from type-checking, inputs are NOT validated.
        NOTE: This method has certainly not been optimized. However,
            I'm going for convenient and readable rather than efficient.
            Also avoiding over optimization for silly things.
        """
        # Initialize the item dictionary.
        clock = {'clock': 'clock'}

        # Check inputs.
        # NOTE: for the starttime/stoptime, I would prefer to use a
        # try/catch construct, attempting to use the strftime format.
        # However, if starttime/stoptime are not datetime objects
        # (e.g. date or time), we would get some unexpected times.
        if isinstance(starttime, datetime):
            clock['starttime'] = ("'" + starttime.strftime(self.DATE_FORMAT)
                                  + "'")
        elif starttime is not None:
            raise TypeError('starttime must be datetime.datetime or None.')

        if isinstance(stoptime, datetime):
            clock['stoptime'] = ("'" + stoptime.strftime(self.DATE_FORMAT)
                                 + "'")
        elif stoptime is not None:
            raise TypeError('stoptime must be datetime.datetime or None.')

        if isinstance(timezone, str):
            # NOTE: There isn't any validity check going on here...
            clock['timezone'] = timezone
        elif timezone is not None:
            raise TypeError('timezone must be a string or None.')

        # If all inputs are None, there's nothing to do. However, there
        # is no logical reason one would provide all three as None, so
        # raise an exception.
        if len(clock) == 1:
            raise ValueError('All inputs are None!')

        # Attempt to modify the clock first.
        try:
            self.modify_item(item_dict=clock)
        except (KeyError, IndexError):
            # No clock, add it instead. Note that the 'modify_item'
            # method 'popped' our 'clock' key.
            clock['clock'] = 'clock'
            # NOTE: A GridLAB-D clock MUST have starttime, stoptime, and
            # timezone defined.
            if len(clock) != 4:
                raise ValueError('To add a new clock, no input can be None. '
                                 + 'Be sure to define starttime, stoptime, '
                                 + 'and timezone.')
            self.add_item(item_dict=clock)

        # All done.
        return None

    def object_type_present(self, object_type):
        """Detect if a type of object (e.g. inverter) is present.

        Returns True if the object_type is found, False otherwise.

        NOTE: This only check in self.model_map['object'].

        :param object_type: string, object type to check for. Note
            the validity of the object type will not be checked.
        """
        # Check input.
        if not isinstance(object_type, str):
            raise TypeError('object_type must be a string.')

        # Lookup object type and return.
        return object_type in self.model_map['object']

    def add_run_components(self, starttime, stoptime, timezone='UTC0',
                           v_source=None, profiler=0,
                           minimum_timestep=60):
        """Add components to make model runnable. This is CIM-specific.

        When a .glm is requested from the platform (requested on the
        configuration topic, with the configuration type being
        'GridLAB-D Base GLM'), it doesn't have all the requisite
        components required to actually run the model. This function
        adds these components.

        :param starttime: datetime.datetime, gets passed directly to
            add_or_modify_clock
        :param stoptime: see starttime.
        :param timezone: string, gets passed directly to
            add_or_modify_clock.
        :param v_source: Voltage at swing bus. Must be number, string,
            or None. If None, the nominal_voltage from the 'substation'
            object will be used.
        :param profiler: Whether or not to use the model profiler. 0/1.
        :param minimum_timestep: Minimum simulation timestep for running
            the model. Should be an integer for simplicity.
        """
        # Handle inputs, starting with v_source.
        if v_source is None:
            # Use the nominal voltage from the substation object.
            substation = \
                self.find_object(obj_type='substation', obj_name='"sourcebus"')
            v_source = float(substation['nominal_voltage'])
        else:
            # Ensure input is valid to avoid surprises later.
            try:
                float(v_source)
            except ValueError:
                raise ValueError('v_source must be castable to a float.')

        # Profiler should be 0/1.
        if (profiler != 0) and (profiler != 1):
            m = 'profiler must be either 0 or 1.'
            if isinstance(profiler, int):
                raise ValueError(m)
            else:
                raise TypeError(m)

        # Minimum timestep should be an integer.
        if not isinstance(minimum_timestep, int):
            raise TypeError('minimum_timestep must be an integer.')

        # Add the source voltage.
        self.add_item({'#define': 'VSOURCE={}'.format(v_source)})

        # Ensure the powerflow module is included.
        self.add_item({'module': 'powerflow', 'solver_method': 'NR',
                       'line_capacitance': 'TRUE'})

        # If necessary, add the generators module.
        for gen in GEN_CLASSES:
            if self.object_type_present(gen):
                self.add_item({'module': 'generators'})
                break

        # In order to address
        # https://github.com/GRIDAPPSD/gridappsd-forum/issues/31#issue-499989979
        # we need to add the reliability module, a fault_check object,
        # and an eventgen object. I've been told this won't impact
        # radial models, but is needed to handle meshed systems like
        # the 9500 node model.
        self.add_item({'module': 'reliability'})
        self.add_item({'object': 'fault_check',
                       'name': 'fault_check_object',
                       'check_mode': 'ONCHANGE',
                       'eventgen_object': 'external_event_handler',
                       'strictly_radial': 'FALSE',
                       'grid_association': 'TRUE'})
        self.add_item({'object': 'eventgen',
                       'name': 'external_event_handler',
                       'use_external_faults': 'TRUE'})

        # Suppress repeating messages.
        self.add_item({'#set': 'suppress_repeat_messages=1'})

        # Relax naming rules.
        self.add_item({'#set': 'relax_naming_rules=1'})

        # Set profiler.
        self.add_item({'#set': 'profiler={}'.format(profiler)})

        # Minimum timestep of one minute.
        self.add_item({'#set': 'minimum_timestep={}'.format(minimum_timestep)})

        # Add the clock.
        self.add_or_modify_clock(starttime=starttime, stoptime=stoptime,
                                 timezone=timezone)

        # Done.
        return

    def add_substation_meter(self):
        """Helper to add a meter object to the substation.

        TODO: Handle multiple substations.
        TODO: Hard-coding the use of "substation" objects could get us
            into trouble.
        TODO: This looping to figure out what's connected is NASTY. This
            class should be augmented to include a graph representation
            of the model, such as from networkx.
        """
        # Get the substation object - for now, only handle a single one.
        sub = self.get_objects_by_type(object_type='substation')
        assert len(sub) == 1
        sub = sub[0]
        assert sub['bustype'] == 'SWING'

        sub_name = sub['name']

        # Create a name for the meter. We have to watch out for the
        # good old quotation marks. Note we're going to add the meter
        # to the model AFTER modifying objects connected to the
        # substation bus in order to keep our loop cleaner.
        if sub_name.endswith('"'):
            meter_name = sub_name[:-1] + '_meter"'
        else:
            meter_name = sub_name + '_meter'

        def check_and_modify(mgr, o, p, old_name, new_name):
            """Nested helper."""
            try:
                # Extract the property.
                p_val = o[p]
            except KeyError:
                # This object doesn't have this property.
                return
            else:
                # This object has the property, see if it matches.
                if p_val == old_name:
                    # Change the item to reference the new name.
                    mgr.modify_item({'object': o['object'],
                                     'name': o['name'],
                                     p: new_name})

        # Loop through ALL objects. This is terrible - we should have a
        # graph representation.
        for obj_type in self.model_map['object']:
            for obj_list in self.model_map['object'][obj_type].values():
                # Extract the object.
                obj = obj_list[1]

                # Check for parented objects.
                check_and_modify(mgr=self, o=obj, p='parent',
                                 old_name=sub_name, new_name=meter_name)

                # Check 'from'
                check_and_modify(mgr=self, o=obj, p='from',
                                 old_name=sub_name, new_name=meter_name)

                # Check 'to' (though this shouldn't be necessary, right?
                check_and_modify(mgr=self, o=obj, p='to',
                                 old_name=sub_name, new_name=meter_name)

        # Add the meter to the model.
        self.add_item({'object': 'meter',
                       'phases': sub['phases'],
                       'nominal_voltage': sub['nominal_voltage'],
                       'parent': sub['name'],
                       'name': meter_name})

        # All done.
        return meter_name

    def update_reg_taps(self, reg_name, pos_dict):
        """Update a regulator's tap positions, both in the regulator
        object itself, as well as its configuration.

        :param reg_name: Name of the regulator in question.
        :param pos_dict: Dictionary mapping phases to positions. E.g.,
            {'A': 12, 'B': 4, 'C': 16}. Not all phases must be present.
        """
        # Lookup the regulator.
        reg = self.find_object(obj_type='regulator', obj_name=reg_name)

        if reg is None:
            raise ValueError(
                'There is no regulator named {} in the model.'.format(reg_name)
            )

        # Lookup the regulator configuration.
        reg_conf = self.find_object(obj_type='regulator_configuration',
                                    obj_name=reg['configuration'])

        if reg_conf is None:
            raise ValueError('While the regulator {} exists, its '
                             'configuration, {}, does not.'.format(
                                reg_name, reg['configuration']))

        # Grab upper and lower bounds for the regulator.
        # http://gridlab-d.shoutwiki.com/wiki/Power_Flow_User_Guide#Regulator
        ub = int(reg_conf['raise_taps'])
        lb = -int(reg_conf['lower_taps'])

        # Loop and update. It's a tad dangerous to do this directly,
        # but it kills me to double-loop.
        for phase, tap in pos_dict.items():
            # Ensure phase is valid.
            if phase not in PHASES:
                raise ValueError(
                    "pos_dict's keys must be in {}".format(PHASES))

            # Ensure the given tap is valid.

            if not isinstance(tap, int):
                raise TypeError('Tap for phase {} is not an integer!'
                                .format(phase))

            if (tap > ub) or (tap < lb):
                raise ValueError('Given tap position, {}, for phase {} is out '
                                 'of bounds! It should be on interval [{}, {}]'
                                 .format(tap, phase, lb, ub))

            # Ensure this regulator has this phase.
            if phase not in reg['phases']:
                raise ValueError(
                    'Regulator {} does not have phase {}.'.format(reg_name,
                                                                  phase))

            # Update the regulator and its configuration. Check out the
            # _modify_item method, and notice that values are cast to
            # strings. This direct updating is dangerous, but avoids
            # double-looping.
            reg['tap_' + phase] = str(tap)
            reg_conf['tap_pos_' + phase] = str(tap)

        # That's it, we're done. Taps have been updated.

    def update_cap_switches(self, cap_name, phase_dict):
        """Update a capacitor's switch positions.

        :param cap_name: Name of the capacitor.
        :param phase_dict: Dictionary mapping of phases to states. E.g.,
            {'A': 'OPEN', 'B': 'CLOSED', 'C': 'OPEN}. Not all phases
            must be present.
        """
        # Lookup the capacitor.
        cap = self.find_object(obj_type='capacitor', obj_name=cap_name)

        if cap is None:
            raise ValueError(
                'There is no capacitor named {} in the model'.format(cap_name)
            )

        # Loop and update.
        for phase, status in phase_dict.items():
            # Ensure key is valid.
            if phase not in PHASES:
                raise ValueError(
                    "phase_dict's keys must be in {}".format(PHASES))

            # Ensure value is valid.
            if status not in CAP_STATUSES:
                raise ValueError(
                    'Capacitor status must be in {}'.format(CAP_STATUSES))

            # Ensure this capacitor has this phase.
            if phase not in cap['phases']:
                raise ValueError(
                    'Capacitor {} does not have phase {}.'.format(cap_name,
                                                                  phase)
                )

            # Update.
            cap['switch' + phase] = status

        # Done.

    def clear_all_triplex_loads(self):
        """For all triplex loads in the model, remove all properties
        in TRIPLEX_PARAMS constant.
        """
        # Start by getting all the triplex_load objects.
        tl_list = self.get_objects_by_type(object_type='triplex_load')

        # If there aren't any triplex loads, warn and return.
        if tl_list is None:
            self.log.warning('clear_all_triplex_loads called, but there '
                             'are not any triplex_loads in the model!')
            return

        # Clear 'em out!
        for tl in tl_list:
            self.remove_properties_from_item(item_dict=tl,
                                             property_list=TRIPLEX_PARAMS)

        # All done.

    def update_all_triplex_loads(self, triplex_loads):
        """Helper to update all the triplex loads in a model.

        :param triplex_loads: Dictionary of dictionaries, keyed by
            name of each triplex_load object. The sub-dictionaries must
            ONLY contain keys found in TRIPLEX_PARAMS. Note that the
            dictionaries will not be validated (for speed), so be
            careful.

        NOTE/TODO: With very minimal effort this could be generalized
            to work with any object type.
        """
        # Start by getting all the current triplex load objects.
        # Here, we'll use get_items_by_type instead of
        # get_objects_by_type so that we get a dictionary back, keyed
        # by name.
        current_tl = self.get_items_by_type(item_type='object',
                                            object_type='triplex_load')

        # Loop over the given triplex_loads.
        for tl_name, tl_dict in triplex_loads.items():
            # Attempt to modify the item.
            try:
                # We'll pop it so our search gets faster and faster as
                # we move along.
                to_modify = current_tl.pop(tl_name)
            except KeyError:
                raise KeyError('The triplex_load {} was not found in '
                               'the model!'.format(tl_name))

            # Modify it.
            self._modify_item(item=to_modify, update_dict=tl_dict)

        # All done.

    def remove_all_solar(self):
        """Remove all solar objects from the model.

        TODO: If desired, this could be made general for all object
            types.
        """
        # NOTE: This method could certainly be more efficient, but it's
        # simpler and more robust to just use the public methods the
        # class already has.

        # Get all solar objects.
        solar_list = self.get_objects_by_type(object_type='solar')

        if solar_list is None:
            self.log.warning('remove_all_solar was called, but there are no '
                             'solar objects in the model!')
        else:
            # Remove all the objects.
            for s in solar_list:
                self.remove_item(s)

            # Pretty easy, right?
            self.log.info('All solar objects removed from the model.')

        # Nothing to return.
        return None

    def set_inverter_v_and_i(self):
        """Set V_In and I_In for all inverters such that the DC supply
        is supplying the 110% inverter's rated power.
        """
        # NOTE: This method could be implemented in a more efficient
        # manner, but it's more readable and more robust to use the
        # public methods the class already has.

        # Define function to be used with the loop helper.
        def set_v_and_i(inv):
            # Attempt to get the rated power.
            try:
                s_str = inv['rated_power']
            except KeyError:
                # No rated power. Set arbitrary V and I in.
                self.log.warning(f"Inverter {inv['name']} does not have the "
                                 "rated_power attribute. Setting V_In=10000 "
                                 "I_In=10000.")

                self._modify_item(inv, {'V_In': 10000, 'I_In': 10000})
            else:
                # We have a rated power. Set values accordingly.
                s = float(s_str) * 1.1
                # Just use 1000.
                v = 1000
                i = s / v

                # Modify the inverter.
                self._modify_item(inv, {'V_In': v, 'I_In': i})

        # Loop over the inverter objects and call the helper.
        self.loop_over_objects_helper('inverter', set_v_and_i)

        self.log.info('All inverters have V_In and I_In set according to '
                      'their rated power.')
        # That's it.
        return None

    def convert_switch_status_to_three_phase(self, banked=False):
        """Ensure all multi-phase switches have their corresponding
        phase_<phase>_state properties set.

        Individual phase states will be based on the overall state
        from the "status" property. E.g., a switch with phases ABCN and
        a "status" of "CLOSED" will have phase_A_state "CLOSED" and the
        same for B and C. The "status" property will be removed.

        Additionally, switches will have their "operating_mode"
        attributed modified according to the "banked" input to this
        method.

        `GridLAB-D documentation
        <http://gridlab-d.shoutwiki.com/wiki/Power_Flow_User_Guide#Switch>`_

        :param banked: If True, set all switch "operating_mode"s to
            "BANKED." Else, set to "INDIVIDUAL."
        """
        # Simple set for valid phases.
        s_abc = set('ABC')

        # Determine operating_mode.
        if banked:
            operating_mode = 'BANKED'
        else:
            operating_mode = 'INDIVIDUAL'

        # Function to use with the loop helper.
        def fix_switch(switch):
            # Extract phases.
            p_set = set(switch['phases'])

            # We only care about A, B, and C.
            phases = p_set & s_abc

            # Grab and remove the status.
            try:
                status = switch.pop('status')
            except KeyError:
                self.log.warning(f"Switch {switch['name']} does not have the "
                                 '"status" attribute. It will be assumed '
                                 'to be closed.')
                status = 'CLOSED'

            # Add states for each phase.
            for p in phases:
                switch[f"phase_{p}_state"] = status

            # Set operating mode.
            switch['operating_mode'] = operating_mode

        # Call the loop helper.
        try:
            self.loop_over_objects_helper('switch', fix_switch)
        except KeyError:
            self.log.warning('convert_switch_status_to_three_phase was '
                             'called, but no switches are present in the '
                             'model.')
        else:
            self.log.info('All switches have had their states converted to '
                          'three phase notation.')


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class ItemExistsError(Error):
    """Raised when a GLMManager attempts to create a new item, but an
    instance of that item already exists and must be unique. E.g.,
    attempting to add a second clock to a model.
    """
    pass


def _test():
    import time
    start = time.time()
    model_manager = GLMManager('R2_12_47_2_AMI_5_min.glm')

    # Print first and last 20.
    for i in range(20):
        print(model_manager.model_dict[i])

    for i in range(model_manager.append_key - 1, (model_manager.append_key
                                                  - 21), -1):
        print(model_manager.model_dict[i])

    model_manager.write_model('R2_out.glm')
    '''
    # cProfile.run('re.compile("foo|bar")')
    # Location in docker container
    feeder_location = 'ieee8500_base.glm'
    feeder_dictionary = parse(feeder_location)
    # Map the model.
    model_map = map_dict(in_dict=feeder_dictionary)
    # print(feeder_dictionary)
    feeder_str = sorted_write(feeder_dictionary)
    glm_file = open('ieee8500_base_out.glm', 'w')
    glm_file.write(feeder_str)
    glm_file.close()
    '''
    end = time.time()
    print('successfully completed in {:0.1f} seconds'.format(end - start))


if __name__ == '__main__':
    _test()
