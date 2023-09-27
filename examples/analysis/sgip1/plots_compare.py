# usage 'python plots_compare'

import tesp_support.sgip1.compare_pypower as cp
import tesp_support.sgip1.compare_csv as cc
import tesp_support.sgip1.compare_hvac as ch
import tesp_support.sgip1.compare_prices as cr
import tesp_support.sgip1.compare_auction as ca

cp.compare_pypower()
cc.compare_csv(9)  # set for LMP,  vaild idx are 0-18
ch.compare_hvac()
cr.compare_prices("SGIP1ex")  # vaild root names are SGIP1a, SGIP1b, SGIP1c, SGIP1d, SGIP1e, SGIP1ex
ca.compare_auction()
