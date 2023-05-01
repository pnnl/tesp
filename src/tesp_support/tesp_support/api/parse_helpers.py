# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: parse_helpers.py

import math
import re


def parse_number(arg):
    """ Parse floating-point number from a FNCS message; must not have leading sign or exponential notation

    Args:
        arg (str): the FNCS string value
    Returns:
        float: the parsed number
    """
    try:
        return float(arg)
    except:
        return float(''.join(ele for ele in arg if ele.isdigit() or ele == '.'))


def parse_magnitude_1(arg):
    """ Parse the magnitude of a possibly complex number from FNCS

    Args:
        arg (str): the FNCS string value
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
    """ Helper function to find the magnitude of a possibly complex number from FNCS

    Args:
        arg (str): The FNCS value
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
    """ Helper function to find the magnitude of a possibly complex number from Helics as a string

    Args:
        arg (str): The Helics value
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
    except:
        print('parse_helic_input does not understand', arg)
        return 0


def parse_magnitude(arg):
    """ Parse the magnitude of a possibly complex number from FNCS

    Args:
        arg (str): the FNCS string value
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
    except:
        try:
            return parse_helic_input(arg)
        except:
            print('parse_magnitude does not understand' + arg)
            return 0


def parse_mva(arg):
    """ Helper function to parse P+jQ from a FNCS value

    Args:
      arg (str): FNCS value in rectangular format
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
        arg (str): the GridLAB-D P+jQ value
    Returns:
        float: the parsed kva value
    """
    toks = list(filter(None, re.split('[\+j-]', arg)))
    p = float(toks[0])
    q = float(toks[1])
    return 0.001 * math.sqrt(p * p + q * q)


def parse_kva_old(arg):
    """ Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form

    Args:
        arg (str): the GridLAB-D P+jQ value
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
    """ Parse the kilowatt load of a possibly complex number from FNCS

    Args:
        arg (str): the FNCS string value
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
    except:
        try:
            return parse_helic_input(arg)/1000.0
        except:
            print('parse_kw does not understand', arg)
            return 0


def _test():
    print('parse_number')
    # print(parse_number('-0.00681678+0.00373295j'))
    # print(parse_number('-0.00681678-0.00373295j'))
    # print(parse_number('559966.6667+330033.3333j'))
    # print(parse_number('186283.85296131+110424.29850536j'))

    print('\nparse_kw')
    print(parse_kw('-0.00681678+0.00373295j'))
    print(parse_kw('-0.00681678-0.00373295j'))
    print(parse_kw('559966.6667+330033.3333j'))
    print(parse_kw('186283.85296131+110424.29850536j'))

    print('\nparse_kva_old')
    print(parse_kva_old('-0.00681678-0.00373295j'))
    print(parse_kva_old('-0.00681678-0.00373295j'))
    # print(parse_kva_old('559966.6667+330033.3333j'))
    # print(parse_kva_old('186283.85296131+110424.29850536j'))

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

