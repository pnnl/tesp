# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: main.py

# This is a sample Python script.
import tesp_support.api.entity as e
import tesp_support.api.model as m
import tesp_support.api.modifier as mf
import tesp_support.api.store as s

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    e.test()
    m.test1()
    m.test2()
    mf.test1()
    mf.test2()
    s.test_debug_resample()
    s.test_csv()
    s.test_sqlite()
    s.test_read()
    s.test_dir()


