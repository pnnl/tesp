from math import sqrt;
import re;

def parse_kva2(cplx):  # this only works if p and q are non-negative
    toks = list(filter(None,re.split('[\+j-]',cplx)))
#    print (toks)
    p = float(toks[0])
    q = float(toks[1])
    return 0.001 * sqrt(p*p + q*q)

def parse_kva(arg):
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

    print (arg, nsign, nexp, ndot)
    vals = [tok[:kpos],tok[kpos:]]
    print (kpos, vals)

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

    return sqrt (p*p + q*q)

#print (parse_kva ('-0.00681678-0.00373295j'))
print (parse_kva2 ('-0.00681678+0.00373295j'))
print (parse_kva2 ('-0.00681678-0.00373295j'))
print (parse_kva2 ('559966.6667+330033.3333j'))
print (parse_kva2 ('186283.85296131+110424.29850536j'))

