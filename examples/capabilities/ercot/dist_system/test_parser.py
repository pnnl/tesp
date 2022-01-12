# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: test_parser.py


import tesp_support.helpers as parse

print('parse_number')
# print(parse.parse_number('-0.00681678+0.00373295j'))
# print(parse.parse_number('-0.00681678-0.00373295j'))
# print(parse.parse_number('559966.6667+330033.3333j'))
# print(parse.parse_number('186283.85296131+110424.29850536j'))

print('\nparse_kw')
print(parse.parse_kw('-0.00681678+0.00373295j'))
print(parse.parse_kw('-0.00681678-0.00373295j'))
print(parse.parse_kw('559966.6667+330033.3333j'))
print(parse.parse_kw('186283.85296131+110424.29850536j'))

print('\nparse_kva_old')
print(parse.parse_kva_old('-0.00681678-0.00373295j'))
print(parse.parse_kva_old('-0.00681678-0.00373295j'))
#print(parse.parse_kva_old('559966.6667+330033.3333j'))
#print(parse.parse_kva_old('186283.85296131+110424.29850536j'))

print('\nparse_kva')
print(parse.parse_kva('-0.00681678+0.00373295j'))
print(parse.parse_kva('-0.00681678-0.00373295j'))
print(parse.parse_kva('559966.6667+330033.3333j'))
print(parse.parse_kva('186283.85296131+110424.29850536j'))

print('\nparse_mva')
print(parse.parse_mva('-0.00681678+0.00373295j'))
print(parse.parse_mva('-0.00681678-0.00373295j'))
print(parse.parse_mva('559966.6667+330033.3333j'))
print(parse.parse_mva('186283.85296131+110424.29850536j'))

print('\nparse_magnitude')
print(parse.parse_magnitude('4.544512492208864e-2'))
print(parse.parse_magnitude('120.0;'))
print(parse.parse_magnitude('-60.0 + 103.923 j;'))
print(parse.parse_magnitude('+77.86 degF'))
print(parse.parse_magnitude('-77.86 degF'))
print(parse.parse_magnitude('+77.86 degC'))
print(parse.parse_magnitude('-77.86 degC'))
print(parse.parse_magnitude('+115.781-4.01083d V'))

print('\nparse_magnitude_1')
#print(parse.parse_magnitude_1('4.544512492208864e-2'))
print(parse.parse_magnitude_1('120.0;'))
print(parse.parse_magnitude_1('-60.0 + 103.923 j;'))
print(parse.parse_magnitude_1('+77.86 degF'))
print(parse.parse_magnitude_1('-77.86 degF'))
#print(parse.parse_magnitude_1('+77.86 degC'))
#print(parse.parse_magnitude_1('-77.86 degC'))
print(parse.parse_magnitude_1('+115.781-4.01083d V'))

print('\nparse_magnitude_2')
#print(parse.parse_magnitude_2('4.544512492208864e-2'))
print(parse.parse_magnitude_2('120.0;'))
print(parse.parse_magnitude_2('-60.0 + 103.923 j;'))
print(parse.parse_magnitude_2('+77.86 degF'))
print(parse.parse_magnitude_2('-77.86 degF'))
#print(parse.parse_magnitude_2('+77.86 degC'))
#print(parse.parse_magnitude_2('-77.86 degC'))
print(parse.parse_magnitude_2('+115.781-4.01083d V'))

