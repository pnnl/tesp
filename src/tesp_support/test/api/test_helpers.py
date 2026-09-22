# test_helpers.py
import json
import logging
import os
import tempfile

import numpy as np
import pytest
from tesp_support.api.helpers import (
    HelicsMsg,
    all_but_one_level,
    all_from_one_level_down,
    enable_logging,
    get_region,
    gld_strict_name,
    random_norm_trunc,
    randomize_commercial_skew,
    randomize_residential_skew,
    randomize_skew,
    zoneMeterName,
)


def test_enable_logging_debug_level():
    """Test enable_logging with DEBUG level"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_prefix = os.path.join(temp_dir, "test")
        
        logger = enable_logging('DEBUG', logging.INFO, log_prefix)
        
        # Check that log files were created
        assert os.path.exists(log_prefix + '_log.txt')
        assert os.path.exists(log_prefix + '_diag.txt')
        
        # Clean up handlers
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


def test_enable_logging_info_level():
    """Test enable_logging with INFO level"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_prefix = os.path.join(temp_dir, "test")
        
        logger = enable_logging('INFO', logging.WARNING, log_prefix)
        
        assert os.path.exists(log_prefix + '_log.txt')
        assert os.path.exists(log_prefix + '_diag.txt')
        
        # Clean up
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


def test_enable_logging_warning_level():
    """Test enable_logging with WARNING level"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_prefix = os.path.join(temp_dir, "test")
        
        logger = enable_logging('WARNING', logging.ERROR, log_prefix)
        
        assert os.path.exists(log_prefix + '_log.txt')
        assert os.path.exists(log_prefix + '_diag.txt')
        
        # Clean up
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


def test_enable_logging_invalid_level():
    """Test enable_logging with invalid level defaults to INFO"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_prefix = os.path.join(temp_dir, "test")
        
        logger = enable_logging('INVALID', logging.INFO, log_prefix)
        
        assert os.path.exists(log_prefix + '_log.txt')
        assert os.path.exists(log_prefix + '_diag.txt')
        
        # Clean up
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


def test_all_from_one_level_down_filter():
    """Test all_from_one_level_down filter class"""
    filter_obj = all_from_one_level_down(logging.WARNING)
    
    # Create mock log records
    class MockLogRecord:
        def __init__(self, level):
            self.levelno = level
    
    # Should pass records at or below WARNING level
    assert filter_obj.filter(MockLogRecord(logging.DEBUG))
    assert filter_obj.filter(MockLogRecord(logging.INFO))
    assert filter_obj.filter(MockLogRecord(logging.WARNING))
    assert not filter_obj.filter(MockLogRecord(logging.ERROR))
    assert not filter_obj.filter(MockLogRecord(logging.CRITICAL))


def test_all_but_one_level_filter():
    """Test all_but_one_level filter class"""
    filter_obj = all_but_one_level(11)
    
    class MockLogRecord:
        def __init__(self, level):
            self.levelno = level
    
    # Should filter out level 11
    assert filter_obj.filter(MockLogRecord(10))
    assert not filter_obj.filter(MockLogRecord(11))
    assert filter_obj.filter(MockLogRecord(12))


def test_randomize_skew():
    """Test randomize_skew function"""
    np.random.seed(42)
    
    skew_max = 7200.0
    value = 1800.0
    
    # Test basic functionality
    result = randomize_skew(value, skew_max)
    assert isinstance(result, float)
    assert -skew_max <= result <= skew_max
    
    # Test multiple calls give different results
    np.random.seed(42)
    result1 = randomize_skew(value, skew_max)
    result2 = randomize_skew(value, skew_max)
    assert result1 != result2  # Should be different (not seeded the same)
    
    # Test that extreme values are clamped
    np.random.seed(42)
    results = [randomize_skew(10000.0, skew_max) for _ in range(100)]
    for r in results:
        assert -skew_max <= r <= skew_max


def test_randomize_commercial_skew():
    """Test randomize_commercial_skew function"""
    np.random.seed(42)
    
    result = randomize_commercial_skew()
    
    assert isinstance(result, float)
    # Should be within commercial_skew_max = 5400
    assert -5400.0 <= result <= 5400.0


def test_randomize_residential_skew():
    """Test randomize_residential_skew function"""
    np.random.seed(42)
    
    # Test without water heater skew
    result = randomize_residential_skew(wh_skew=False)
    assert isinstance(result, float)
    assert -8100.0 <= result <= 8100.0  # residential_skew_max = 8100
    
    # Test with water heater skew (6x larger max)
    np.random.seed(42)
    result_wh = randomize_residential_skew(wh_skew=True)
    assert isinstance(result_wh, float)
    assert -48600.0 <= result_wh <= 48600.0  # 6 * 8100 = 48600


def test_random_norm_trunc():
    """Test random_norm_trunc function"""
    np.random.seed(42)
    
    # Test with standard_deviation key
    dist_array = {
        'mean': 100.0,
        'standard_deviation': 10.0,
        'min': 80.0,
        'max': 120.0
    }
    
    result = random_norm_trunc(dist_array)
    assert isinstance(result, float)
    assert 80.0 <= result <= 120.0
    
    # Test with std key directly
    dist_array2 = {
        'mean': 50.0,
        'std': 5.0,
        'min': 40.0,
        'max': 60.0
    }
    
    result2 = random_norm_trunc(dist_array2)
    assert isinstance(result2, float)
    assert 40.0 <= result2 <= 60.0


def test_random_norm_trunc_distribution():
    """Test that random_norm_trunc produces reasonable distribution"""
    np.random.seed(42)
    
    dist_array = {
        'mean': 100.0,
        'std': 10.0,
        'min': 70.0,
        'max': 130.0
    }
    
    # Generate many samples
    samples = [random_norm_trunc(dist_array) for _ in range(1000)]
    
    # All should be within bounds
    assert all(70.0 <= s <= 130.0 for s in samples)
    
    # Mean should be close to specified mean
    mean_sample = np.mean(samples)
    assert 95.0 <= mean_sample <= 105.0  # Within reasonable range


def test_zoneMeterName():
    """Test zoneMeterName function"""
    # Test basic replacement
    assert zoneMeterName("zone_load_01") == "zone_meter_01"
    assert zoneMeterName("building_load_42") == "building_meter_42"
    assert zoneMeterName("test_load_123") == "test_meter_123"
    
    # Test multiple occurrences
    assert zoneMeterName("load_load_5") == "load_meter_5"
    
    # Test no match
    assert zoneMeterName("some_meter_99") == "some_meter_99"


def test_gld_strict_name():
    """Test gld_strict_name function"""
    # Test removing quotes
    assert gld_strict_name('"test_name"') == "test_name"
    
    # Test replacing hyphens with underscores
    assert gld_strict_name("test-name-with-hyphens") == "test_name_with_hyphens"
    
    # Test prepending gld_ to names starting with digit
    assert gld_strict_name("123_name") == "gld_123_name"
    assert gld_strict_name("4test") == "gld_4test"
    
    # Test combined cases
    assert gld_strict_name('"5-test-name"') == "gld_5_test_name"
    
    # Test normal name (no changes needed)
    assert gld_strict_name("normal_name") == "normal_name"
    
    # Test name starting with letter but containing hyphens
    assert gld_strict_name("test-123") == "test_123"


@pytest.mark.parametrize("input_str,expected_region", [
    ("R1-12.47-1", 1),
    ("R2-25.00-1", 2),
    ("R3-12.47-3", 3),
    ("R4-12.47-2", 4),
    ("R5-35.00-1", 5),
    ("IEEE-123", 0),  # No region marker
    ("test_feeder", 0),
    ("R1_test", 1),
    ("testR3name", 3),
])
def test_get_region(input_str, expected_region):
    """Test get_region function with various inputs"""
    assert get_region(input_str) == expected_region


def test_helics_msg_initialization():
    """Test HelicsMsg class initialization"""
    msg = HelicsMsg("test_federate", 60)
    
    assert msg._cnfg["name"] == "test_federate"
    assert msg._cnfg["period"] == 60
    assert msg._cnfg["logging"] == "warning"
    assert msg._pubs == []
    assert msg._subs == []


def test_helics_msg_config():
    """Test HelicsMsg config method"""
    msg = HelicsMsg("test", 30)
    
    msg.config("core_type", "zmq")
    msg.config("loglevel", "debug")
    
    assert msg._cnfg["core_type"] == "zmq"
    assert msg._cnfg["loglevel"] == "debug"


def test_helics_msg_pubs():
    """Test HelicsMsg pubs method (GridLAB-D style)"""
    msg = HelicsMsg("test", 30)
    
    msg.pubs(True, "voltage_A", "double", "meter_1", "voltage_A")
    
    assert len(msg._pubs) == 1
    pub = msg._pubs[0]
    assert pub["global"]
    assert pub["key"] == "voltage_A"
    assert pub["type"] == "double"
    assert pub["info"]["object"] == "meter_1"
    assert pub["info"]["property"] == "voltage_A"


def test_helics_msg_pubs_n():
    """Test HelicsMsg pubs_n method (simple publication)"""
    msg = HelicsMsg("test", 30)
    
    msg.pubs_n(False, "test_key", "string")
    
    assert len(msg._pubs) == 1
    pub = msg._pubs[0]
    assert not pub["global"]
    assert pub["key"] == "test_key"
    assert pub["type"] == "string"
    assert "info" not in pub


def test_helics_msg_pubs_e():
    """Test HelicsMsg pubs_e method (EnergyPlus style)"""
    msg = HelicsMsg("test", 30)
    
    msg.pubs_e(True, "zone_temp", "double", "degC")
    
    assert len(msg._pubs) == 1
    pub = msg._pubs[0]
    assert pub["global"]
    assert pub["key"] == "zone_temp"
    assert pub["type"] == "double"
    assert pub["unit"] == "degC"


def test_helics_msg_subs():
    """Test HelicsMsg subs method (GridLAB-D style)"""
    msg = HelicsMsg("test", 30)
    
    msg.subs("voltage_A", "double", "meter_1", "voltage_A")
    
    assert len(msg._subs) == 1
    sub = msg._subs[0]
    assert sub["key"] == "voltage_A"
    assert sub["type"] == "double"
    assert sub["info"]["object"] == "meter_1"
    assert sub["info"]["property"] == "voltage_A"


def test_helics_msg_subs_n():
    """Test HelicsMsg subs_n method (simple subscription)"""
    msg = HelicsMsg("test", 30)
    
    msg.subs_n("test_key", "complex")
    
    assert len(msg._subs) == 1
    sub = msg._subs[0]
    assert sub["key"] == "test_key"
    assert sub["type"] == "complex"
    assert "info" not in sub


def test_helics_msg_subs_e():
    """Test HelicsMsg subs_e method (EnergyPlus style)"""
    msg = HelicsMsg("test", 30)
    
    msg.subs_e(True, "outdoor_temp", "double", {"source": "weather"})
    
    assert len(msg._subs) == 1
    sub = msg._subs[0]
    assert sub["key"] == "outdoor_temp"
    assert sub["type"] == "double"
    assert sub["require"]
    assert sub["info"]["source"] == "weather"


def test_helics_msg_write_file():
    """Test HelicsMsg write_file method"""
    with tempfile.TemporaryDirectory() as temp_dir:
        msg = HelicsMsg("test_federate", 60)
        
        # Add some publications and subscriptions
        msg.pubs(True, "voltage", "double", "meter", "voltage_A")
        msg.subs("current", "double", "meter", "current_A")
        msg.config("core_type", "zmq")
        
        # Write to file
        filepath = os.path.join(temp_dir, "test_helics.json")
        msg.write_file(filepath)
        
        # Verify file exists
        assert os.path.exists(filepath)
        
        # Read and verify content
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert data["name"] == "test_federate"
        assert data["period"] == 60
        assert data["core_type"] == "zmq"
        assert len(data["publications"]) == 1
        assert len(data["subscriptions"]) == 1


def test_helics_msg_multiple_pubs_subs():
    """Test HelicsMsg with multiple publications and subscriptions"""
    msg = HelicsMsg("multi_test", 30)
    
    # Add multiple publications
    msg.pubs(True, "voltage_A", "double", "meter_1", "voltage_A")
    msg.pubs(True, "voltage_B", "double", "meter_1", "voltage_B")
    msg.pubs_n(False, "status", "string")
    
    # Add multiple subscriptions
    msg.subs("current_A", "double", "meter_2", "current_A")
    msg.subs_n("control_signal", "integer")
    
    assert len(msg._pubs) == 3
    assert len(msg._subs) == 2


def test_helics_msg_write_read_consistency():
    """Test that written file can be read back correctly"""
    with tempfile.TemporaryDirectory() as temp_dir:
        msg = HelicsMsg("consistency_test", 45)
        
        msg.pubs(True, "test_pub", "complex", "obj1", "prop1")
        msg.subs("test_sub", "double", "obj2", "prop2")
        msg.config("time_delta", 1.0)
        
        filepath = os.path.join(temp_dir, "helics_test.json")
        msg.write_file(filepath)
        
        # Read back
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Verify all data is correct
        assert data["name"] == "consistency_test"
        assert data["period"] == 45
        assert data["time_delta"] == 1.0
        assert data["publications"][0]["key"] == "test_pub"
        assert data["subscriptions"][0]["key"] == "test_sub"