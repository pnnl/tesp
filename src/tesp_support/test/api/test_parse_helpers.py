# test_parse_helpers.py
import pytest
import math
from tesp_support.api.parse_helpers import (
    parse_number, parse_magnitude_1, parse_magnitude_2, 
    parse_helic_input, parse_magnitude, parse_mva, 
    parse_kva, parse_kva_old, parse_kw
)


@pytest.mark.parametrize("input_str, expected", [
    ("123.45", 123.45),
    ("0", 0.0),
    ("123.45 abc", 123.45),
    ("123.45E0", 123.45),
    ("1.2345e2 def", 123.45),
])
def test_parse_number(input_str, expected):
    result = parse_number(input_str)
    assert abs(result - expected) < 1e-10


@pytest.mark.parametrize("input_str, expected", [
    ('-0.00681678+0.00373295j', -6.81678e-06),
    ('-0.00681678-0.00373295j', -6.81678e-06),
    ('559966.6667+330033.3333j', 0.0),  # Falls back to parse_helic_input, which fails
    ('186283.85296131+110424.29850536j', 0.0),  # Falls back to parse_helic_input, which fails
])
def test_parse_kw(input_str, expected):
    result = parse_kw(input_str)
    assert abs(result - expected) < 1e-10


@pytest.mark.parametrize("input_str, expected", [
    ('-0.00681678-0.00373295j', 7.771962768239436e-06),
    ('-0.00681678+0.00373295j', 7.771962768239436e-06),
])
def test_parse_kva_old(input_str, expected):
    result = parse_kva_old(input_str)
    assert abs(result - expected) < 1e-15


@pytest.mark.parametrize("input_str, expected", [
    ('-0.00681678+0.00373295j', 7.771962768239436e-06),
    ('-0.00681678-0.00373295j', 7.771962768239436e-06),
    ('559966.6667+330033.3333j', 649.9882067424129),
    ('186283.85296131+110424.29850536j', 216.55299484078213),
])
def test_parse_kva(input_str, expected):
    result = parse_kva(input_str)
    assert abs(result - expected) < 1e-10


@pytest.mark.parametrize("input_str, expected_p, expected_q", [
    ('-0.00681678+0.00373295j', -6.81678e-09, 3.73295e-09),
    ('-0.00681678-0.00373295j', -6.81678e-09, -3.73295e-09),
    ('559966.6667+330033.3333j', 0.5599666667, 0.3300333333),
    ('186283.85296131+110424.29850536j', 0.18628385296131, 0.11042429850536),
])
def test_parse_mva(input_str, expected_p, expected_q):
    p, q = parse_mva(input_str)
    assert abs(p - expected_p) < 1e-10
    assert abs(q - expected_q) < 1e-10


@pytest.mark.parametrize("input_str, expected", [
    ('4.544512492208864e-2', 0.04544512492208864),
    ('120.0;', 120.0),
    ('-60.0 + 103.923 j;', 119.99995803749266),
    ('+77.86 degF', 77.86),
    ('-77.86 degF', 77.86),
    ('+77.86 degC', 77.86),
    ('-77.86 degC', 77.86),
    ('+115.781-4.01083d V', 115.781),
])
def test_parse_magnitude(input_str, expected):
    result = parse_magnitude(input_str)
    assert abs(result - expected) < 1e-10


@pytest.mark.parametrize("input_str, expected", [
    ('120.0;', 120.0),
    ('-60.0 + 103.923 j;', -60.0),
    ('+77.86 degF', 77.86),
    ('-77.86 degF', -77.86),
    ('+77.86 degC', 77.86),
    ('-77.86 degC', -77.86),
    ('+115.781-4.01083d V', 115.781),
])
def test_parse_magnitude_1(input_str, expected):
    result = parse_magnitude_1(input_str)
    assert abs(result - expected) < 1e-10


@pytest.mark.parametrize("input_str, expected", [
    ('120.0;', 120.0),
    ('-60.0 + 103.923 j;', -60.0),
    ('+77.86 degF', 77.86),
    ('-77.86 degF', -77.86),
    ('+77.86 degC', 77.86),
    ('-77.86 degC', -77.86),
    ('+115.781-4.01083d V', 115.781),
])
def test_parse_magnitude_2(input_str, expected):
    result = parse_magnitude_2(input_str)
    assert abs(result - expected) < 1e-10


@pytest.mark.parametrize("input_str, expected", [
    ('[123.45, 67.89]', 123.45),
    ('[0.0, 0.0]', 0.0),
    ('[123.45]', 123.45),  # Only real part
    ('[-123.45, 67.89]', -123.45),
    ('invalid_input', 0),  # Should print error and return 0
    ('559966.6667+330033.3333j', 0),  # Not in Helics format
])
def test_parse_helic_input(input_str, expected):
    result = parse_helic_input(input_str)
    assert abs(result - expected) < 1e-10


def test_parse_magnitude_error_handling():
    """Test that parse_magnitude handles errors gracefully"""
    # These should not raise exceptions
    result = parse_magnitude("")
    assert result == 0
    
    result = parse_magnitude("completely_invalid")
    assert result == 0


def test_parse_kw_error_handling():
    """Test that parse_kw handles errors gracefully"""
    # Test with empty string
    result = parse_kw("")
    assert result == 0
    
    # Test with invalid format
    result = parse_kw("not_a_number")
    assert result == 0


def test_parse_mva_units():
    """Test parse_mva with different units"""
    # Test with KVA
    p, q = parse_mva('1000+500j KVA')
    assert abs(p - 1.0) < 1e-10  # Should be converted to MW
    assert abs(q - 0.5) < 1e-10  # Should be converted to MVAR
    
    # Test with MVA (should stay the same)
    p, q = parse_mva('1+0.5j MVA')
    assert abs(p - 1.0) < 1e-10
    assert abs(q - 0.5) < 1e-10


def test_parse_mva_polar_form():
    """Test parse_mva with polar coordinates"""
    # Test degree format
    p, q = parse_mva('100+30d MVA')  # 100 MVA at 30 degrees
    expected_p = 100 * math.cos(30 * math.pi / 180)
    expected_q = 100 * math.sin(30 * math.pi / 180)
    assert abs(p - expected_p) < 1e-10
    assert abs(q - expected_q) < 1e-10
    
    # Test radian format
    p, q = parse_mva('100+0.5236r MVA')  # 100 MVA at 0.5236 radians (30 degrees)
    expected_p = 100 * math.cos(0.5236)
    expected_q = 100 * math.sin(0.5236)
    assert abs(p - expected_p) < 1e-10
    assert abs(q - expected_q) < 1e-10


@pytest.mark.parametrize("function", [parse_magnitude_1, parse_magnitude_2])
def test_magnitude_functions_consistency(function):
    """Test that both magnitude functions handle similar inputs consistently"""
    test_cases = [
        '120.0;',
        '+77.86 degF',
        '-77.86 degF',
    ]
    
    for test_case in test_cases:
        result = function(test_case)
        assert isinstance(result, float)
        assert not math.isnan(result)


def test_complex_number_parsing():
    """Test complex number parsing across different functions"""
    complex_input = '100+50j'
    
    # Test that kva functions return magnitude
    kva_result = parse_kva(complex_input)
    expected_magnitude = math.sqrt(100**2 + 50**2) * 0.001  # Convert to kVA
    assert abs(kva_result - expected_magnitude) < 1e-10
    
    # Test that mva returns components
    p, q = parse_mva(complex_input)
    assert abs(p - 0.0001) < 1e-10  # 100 VA = 0.0001 MVA
    assert abs(q - 0.00005) < 1e-10  # 50 VAR = 0.00005 MVAR