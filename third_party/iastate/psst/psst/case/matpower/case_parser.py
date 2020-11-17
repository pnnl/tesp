# -*- coding: utf-8 -*-
"""
Python class to read a Matpower Case file
Copyright (C) 2016 Dheepak Krishnamurthy
"""

from __future__ import print_function, absolute_import

import os
from builtins import open
import logging

import numpy as np
from pyparsing import Word, nums, alphanums, LineEnd, Suppress, Literal, restOfLine, OneOrMore, Optional, Keyword, Group, printables

from ...utils import int_else_float_except_string

logger = logging.getLogger(__file__)

Float = Word(nums + '.' + '-' + '+' + 'e')
Name = Word(alphanums)
String = Optional(Suppress("'")) + Word(printables, alphanums) + Optional(Suppress("'"))
NL = LineEnd()
Comments = Suppress(Literal('%')) + restOfLine


def parse_file(attribute, string):
    if attribute in ['gen', 'gencost', 'bus', 'branch'] and attribute in string:
        return parse_table(attribute, string)
    elif attribute in ['version', 'baseMVA'] and attribute in string:
        return parse_line(attribute, string)
    else:
        logger.debug("Unable to parse mpc.%s. Please check the input file or contact the developer.", attribute)
        return None


def parse_line(attribute, string):

    Grammar = Suppress(Keyword('mpc.{}'.format(attribute)) + Keyword('=')) + String('data') + Suppress(Literal(';') + Optional(Comments))
    result, i, j = Grammar.scanString(string).next()

    return [int_else_float_except_string(s) for s in result['data'].asList()]


def parse_table(attribute, string):
    Line = OneOrMore(Float)('data') + Literal(';') + Optional(Comments, default='')('name')
    Grammar = Suppress(Keyword('mpc.{}'.format(attribute)) + Keyword('=') + Keyword('[') + Optional(Comments)) + OneOrMore(Group(Line)) + Suppress(Keyword(']') + Optional(Comments))

    result, i, j = Grammar.scanString(string).next()

    _list = list()
    for r in result:
        _list.append([int_else_float_except_string(s) for s in r['data'].asList()])

    return _list

