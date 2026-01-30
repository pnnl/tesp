# Copyright (c) 2021-2025 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: parse_helpers.py

import math
import re


def parse_number(arg):
    """ Parse floating-point number from a string;

    Leading signs are handled so long as no space exists between sign and value.
        E.g., +100, not + 100.
    Trailing units are handled by the exception.
        E.g., +100 % or 

    Args:
        arg (str): The string value
    Returns:
        float: the parsed number
    """
    if 'inf' in arg:
        raise ValueError(f"Expected float, got {arg}")
    try:
        return float(arg)
    except ValueError:
        return float(arg.split(maxsplit=1)[0])


def parse_magnitude_1(arg):
    """ Parse the magnitude of a possibly complex number from a string

    Args:
        arg (str): The string value
    Returns:
        float: the parsed number, or 0 if parsing fails
    """
    tok = arg.strip('+-; MWVACFKdegrij')
    vals = re.split(r'[\+-]+', tok)
    if len(vals) < 2:  # only a real part provided
        vals.append('0')
    vals = [float(v) for v in vals]

    if '-' in tok:
        vals[1] *= -1.0
    if arg.startswith('-'):
        vals[0] *= -1.0
    return vals[0]


def parse_magnitude_2(arg):
    """ Helper function to find the magnitude of a possibly complex number from a string

    Args:
        arg (str): The string value
    Returns:
        float: the parsed number, or 0 if parsing fails
    """
    tok = arg.strip('+-; MWVACFKdegrij')
    vals = re.split(r'[\+-]+', tok)
    if len(vals) < 2:  # only a real part provided
        vals.append('0')

    vals[0] = float(vals[0])
    if arg.startswith('-'):
        vals[0] *= -1.0
    return vals[0]


def parse_helic_input(arg):
    """ Helper function to find the magnitude of a possibly complex number from a string

    Args:
        arg (str): The string value from HELICS
    Returns:
        float: the parsed number, or 0 if parsing fails
    """
    try:
        tok = arg.strip('[]')
        vals = re.split(',', tok)
        if len(vals) < 2:  # only a real part provided
            vals.append('0')

        vals[0] = float(vals[0])
        return vals[0]
    except Exception:
        print('parse_helic_input does not understand', arg)
        return 0


def parse_magnitude(arg):
    """ Parse the magnitude of a possibly complex number from a string

    Args:
        arg (str): The string value
    Returns:
        float: the parsed number, or 0 if parsing fails
    """
    try:
        if ('d ' in arg) or ('r ' in arg):  # polar form
            tok = arg.strip('; MWVAKdrij')
            nsign = nexp = ndot = 0
            for i in range(len(tok)):
                if (tok[i] == '+') or (tok[i] == '-'):
                    nsign += 1
                elif (tok[i] == 'e') or (tok[i] == 'E'):
                    nexp += 1
                elif tok[i] == '.':
                    ndot += 1
                if nsign == 1:
                    kpos = i
                if nsign == 2 and nexp == 0:
                    kpos = i
                    break
                if nsign == 3:
                    kpos = i
                    break

            vals = [tok[:kpos], tok[kpos:]]
            vals = [float(v) for v in vals]
            return vals[0]
        tok = arg.strip('; MWVACFKdegri').replace(" ", "")  # rectangular form, including real only
        b = complex(tok)
        return abs(b)  # b.real
    except Exception:
        try:
            return parse_helic_input(arg)
        except Exception:
            print('parse_magnitude does not understand' + arg)
            return 0


def parse_mva(arg):
    """ Helper function to parse P+jQ from a string
        If unit tag on end of the string will be used
            KVA * 1
            MVA * 1000
            VA / 1000

    Args:
      arg (str): The string value in rectangular form
    Returns:
      float, float: P [MW] and Q [MVAR]
    """
    tok = arg.strip('; MWVAKdrij')
    bLastDigit = False
    bParsed = False
    vals = [0.0, 0.0]
    for i in range(len(tok)):
        if tok[i] == '+' or tok[i] == '-':
            if bLastDigit:
                vals[0] = float(tok[: i])
                vals[1] = float(tok[i:])
                bParsed = True
                break
        bLastDigit = tok[i].isdigit()
    if not bParsed:
        vals[0] = float(tok)

    if 'd' in arg:
        vals[1] *= (math.pi / 180.0)
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    elif 'r' in arg:
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    else:
        p = vals[0]
        q = vals[1]

    if 'KVA' in arg:
        p /= 1000.0
        q /= 1000.0
    elif 'MVA' in arg:
        p *= 1.0
        q *= 1.0
    else:  # VA
        p /= 1000000.0
        q /= 1000000.0
    return p, q


def parse_kva(arg):  # this drops the sign of p and q
    """ Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form

    Args:
        arg (str): the GridLAB-D P+jQ string value
    Returns:
        float: the parsed kva value
    """
    toks = list(filter(None, re.split(r'[\+j-]', arg)))
    p = float(toks[0])
    q = float(toks[1])
    return 0.001 * math.sqrt(p * p + q * q)


def parse_kva_old(arg):
    """ Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form
        If unit tag on end of the string will be used
            KVA * 1
            MVA * 1000
            VA / 1000

    Args:
        arg (str): the GridLAB-D P+jQ string value
    Returns:
        float: the parsed kva value
    """
    tok = arg.strip('; MWVAKdrij')
    nsign = nexp = ndot = 0
    for i in range(len(tok)):
        if (tok[i] == '+') or (tok[i] == '-'):
            nsign += 1
        elif (tok[i] == 'e') or (tok[i] == 'E'):
            nexp += 1
        elif tok[i] == '.':
            ndot += 1
        if nsign == 2 and nexp == 0:
            kpos = i
            break
        if nsign == 3:
            kpos = i
            break

    vals = [tok[:kpos], tok[kpos:]]
    vals = [float(v) for v in vals]

    if 'd' in arg:
        vals[1] *= (math.pi / 180.0)
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    elif 'r' in arg:
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    else:
        p = vals[0]
        q = vals[1]

    if 'KVA' in arg:
        p *= 1.0
        q *= 1.0
    elif 'MVA' in arg:
        p *= 1000.0
        q *= 1000.0
    else:  # VA
        p /= 1000.0
        q /= 1000.0
    return math.sqrt(p * p + q * q)


def parse_kw(arg):
    """ Parse the kilowatt load of a possibly complex number from a string
        If unit tag on end of the string will be used
            KVA * 1
            MVA * 1000
            VA / 1000

    Args:
        arg (str): The string value
    Returns:
        float: the parsed number in kW, or 0 if parsing fails
    """
    try:
        tok = arg.strip('; MWVAKdrij')
        nsign = nexp = ndot = 0
        for i in range(len(tok)):
            if (tok[i] == '+') or (tok[i] == '-'):
                nsign += 1
            elif (tok[i] == 'e') or (tok[i] == 'E'):
                nexp += 1
            elif tok[i] == '.':
                ndot += 1
            if nsign == 2 and nexp == 0:
                kpos = i
                break
            if nsign == 3:
                kpos = i
                break

        vals = [tok[:kpos], tok[kpos:]]
        vals = [float(v) for v in vals]

        if 'd' in arg:
            vals[1] *= (math.pi / 180.0)
            p = vals[0] * math.cos(vals[1])
            q = vals[0] * math.sin(vals[1])
        elif 'r' in arg:
            p = vals[0] * math.cos(vals[1])
            q = vals[0] * math.sin(vals[1])
        else:
            p = vals[0]
            q = vals[1]

        if 'KVA' in arg:
            p *= 1.0
            q *= 1.0
        elif 'MVA' in arg:
            p *= 1000.0
            q *= 1000.0
        else:  # VA
            p /= 1000.0
            q /= 1000.0

        return p
    except Exception:
        try:
            return parse_helic_input(arg)/1000.0
        except Exception:
            print('parse_kw does not understand', arg)
            return 0

def complex_kva(arg):
    z1 = complex(arg)
    return math.sqrt(z1.real/1000 * z1.real/1000 + z1.imag/1000 * z1.imag/1000)


def test():
    print('parse_number')
    print(parse_number('6 m'))
    print(parse_number('-76'))
    print(parse_number('-0.0068 cm'))
    print(parse_number('10.0068'))
    # print(parse_number('-0.00681678+0.00373295j'))
    # print(parse_number('-0.00681678-0.00373295j'))
    # print(parse_number('559966.6667+330033.3333j'))
    # print(parse_number('186283.85296131+110424.29850536j'))

    print('\nparse_kw')
    print(parse_kw('-76'))
    print(parse_kw('-0.00681678+0.00373295j'))
    print(parse_kw('-0.00681678-0.00373295j'))
    print(parse_kw('559966.6667+330033.3333j'))
    print(parse_kw('186283.85296131+110424.29850536j'))

    print('\nparse_kva_old')
    print(parse_kva_old('-0.00681678+0.00373295j' ))
    print(parse_kva_old('-0.00681678-0.00373295j'))
    # print(parse_kva_old('559966.6667+330033.3333j'))
    # print(parse_kva_old('186283.85296131+110424.29850536j'))

    print('\ncomplex_kva')
    print(complex_kva('-0.00681678+0.00373295j'))
    print(complex_kva('-0.00681678-0.00373295j'))
    print(complex_kva('559966.6667+330033.3333j'))
    print(complex_kva('186283.85296131+110424.29850536j'))

    print('\nparse_kva')
    print(parse_kva('-0.00681678+0.00373295j'))
    print(parse_kva('-0.00681678-0.00373295j'))
    print(parse_kva('559966.6667+330033.3333j'))
    print(parse_kva('186283.85296131+110424.29850536j'))

    print('\nparse_mva')
    print(parse_mva('-0.00681678+0.00373295j'))
    print(parse_mva('-0.00681678-0.00373295j'))
    print(parse_mva('559966.6667+330033.3333j'))
    print(parse_mva('186283.85296131+110424.29850536j'))

    print('\nparse_magnitude')
    print(parse_magnitude('4.544512492208864e-2'))
    print(parse_magnitude('120.0;'))
    print(parse_magnitude('-60.0 + 103.923 j;'))
    print(parse_magnitude('+77.86 degF'))
    print(parse_magnitude('-77.86 degF'))
    print(parse_magnitude('+77.86 degC'))
    print(parse_magnitude('-77.86 degC'))
    print(parse_magnitude('+115.781-4.01083d V'))

    print('\nparse_magnitude_1')
    # print(parse_magnitude_1('4.544512492208864e-2'))
    print(parse_magnitude_1('120.0;'))
    print(parse_magnitude_1('-60.0 + 103.923 j;'))
    print(parse_magnitude_1('+77.86 degF'))
    print(parse_magnitude_1('-77.86 degF'))
    print(parse_magnitude_1('+77.86 degC'))
    print(parse_magnitude_1('-77.86 degC'))
    print(parse_magnitude_1('+115.781-4.01083d V'))

    print('\nparse_magnitude_2')
    # print(parse_magnitude_2('4.544512492208864e-2'))
    print(parse_magnitude_2('120.0;'))
    print(parse_magnitude_2('-60.0 + 103.923 j;'))
    print(parse_magnitude_2('+77.86 degF'))
    print(parse_magnitude_2('-77.86 degF'))
    print(parse_magnitude_2('+77.86 degC'))
    print(parse_magnitude_2('-77.86 degC'))
    print(parse_magnitude_2('+115.781-4.01083d V'))

