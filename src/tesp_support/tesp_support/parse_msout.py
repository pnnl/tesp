#   Copyright (C) 2020-2022 Battelle Memorial Institute
# file: parse_msout.py
import numpy as np


def next_val(fp, var, bInteger=True):
    match = '# name: ' + var
    looking = True
    val = None
    while looking:
        ln = fp.readline()
        if len(ln) < 1:
            print('EOF looking for', var)
            return val
        if ln.strip() == match:
            looking = False
            fp.readline()
            if bInteger:
                val = int(fp.readline().strip())
            else:
                val = float(fp.readline().strip())
    # print(var, '=', val)
    return val


def next_matrix(fp, var):
    match = '# name: ' + var
    looking = True
    mat = None
    while looking:
        ln = fp.readline()
        if len(ln) < 1:
            print('EOF looking for', var)
            return mat
        if ln.strip() == match:
            looking = False
            fp.readline()
            toks = fp.readline().strip().split()
            rows = int(toks[2])
            toks = fp.readline().strip().split()
            cols = int(toks[2])
            # print ('{:s} [{:d}x{:d}]'.format (var, rows, cols))
            mat = np.empty((rows, cols))
            for i in range(rows):
                mat[i] = np.fromstring(fp.readline().strip(), sep=' ')
    return mat


def read_most_solution(fname='msout.txt'):
    fp = open('msout.txt', 'r')

    f = next_val(fp, 'f', False)
    nb = next_val(fp, 'nb')
    ng = next_val(fp, 'ng')
    nl = next_val(fp, 'nl')
    ns = next_val(fp, 'ns')
    nt = next_val(fp, 'nt')
    nj_max = next_val(fp, 'nj_max')
    psi = next_matrix(fp, 'psi')
    Pg = next_matrix(fp, 'Pg')
    Pd = next_matrix(fp, 'Pd')
    Rup = next_matrix(fp, 'Rup')
    Rdn = next_matrix(fp, 'Rdn')
    Pf = next_matrix(fp, 'Pf')
    u = next_matrix(fp, 'u')
    lamP = next_matrix(fp, 'lamP')
    muF = next_matrix(fp, 'muF')
    fp.close()

    return f, nb, ng, nl, ns, nt, nj_max, Pg, Pd, Pf, u, lamP
